"""Handlers for group management page and API."""

import json
import os

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..api_keys_pool import merge_pool_on_save
from ..group_resolver import is_reserved_env_var
from ..groups_config import (
    GroupConfigValidator,
    GroupsConfigManager,
    validate_group_name,
)


class GroupsPageHandler(BaseHandler):
    """Handler for rendering the groups management page (admin only)."""

    @web.authenticated
    async def get(self):
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this page")

        self.log.info(f"[Groups Page] Admin {current_user.name} accessed groups management")

        # Host GPUs were enumerated once at startup by the ephemeral CUDA detection
        # container (the hub has no GPU access of its own); this is a cached read,
        # no container spin per page load. Empty list -> the GPU section renders
        # grayed-out and the per-GPU checkboxes are omitted.
        stellars_config = self.settings.get('stellars_config') or {}
        gpus = stellars_config.get('gpu_list', [])
        # False on WSL2 -> the GPU section shows an "advisory, not a hard limit" note
        gpu_isolation_enforced = stellars_config.get('gpu_isolation_enforced', True)

        # host_cpu_count hints the admin at the upper bound for the per-group CPU
        # limit (cores visible to the hub container = host cores in the usual
        # unconstrained-hub deployment).
        html = self.render_template(
            "groups.html", sync=True, user=current_user,
            host_cpu_count=(os.cpu_count() or 1),
            gpus=gpus,
            gpu_isolation_enforced=gpu_isolation_enforced,
        )
        self.finish(html)


class GroupsDataHandler(BaseHandler):
    """Handler for listing all groups with config and member count."""

    @web.authenticated
    async def get(self):
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this endpoint")

        from jupyterhub import orm

        manager = GroupsConfigManager.get_instance()
        groups = self.db.query(orm.Group).all()
        orm_group_names = {g.name for g in groups}

        # Sync: remove orphaned configs for groups deleted via admin panel
        all_configs = manager.get_all_configs()
        for cfg in all_configs:
            if cfg['group_name'] not in orm_group_names:
                manager.delete_config(cfg['group_name'])
                self.log.info(f"[Groups Sync] Removed orphaned config for '{cfg['group_name']}'")

        # Ensure every ORM group has a config entry (auto-creates for groups added via admin panel)
        result = []
        for group in groups:
            config = manager.ensure_config(group.name)
            result.append({
                'name': group.name,
                'description': config['description'],
                'priority': config['priority'],
                'member_count': len(group.users),
                'members': [u.name for u in group.users],
                'config': config['config'],
            })

        result.sort(key=lambda g: g['priority'], reverse=True)

        # Standard shared volume: the UI offers a one-click "/mnt/shared" mount
        # only when the volume actually exists on the host. Docker errors fail
        # safe (exists=False -> quick-add hidden; manual rows still work).
        stellars_config = self.settings.get('stellars_config') or {}
        shared_name = stellars_config.get('shared_volume_name', '')
        from ..docker_utils import volume_exists_async
        shared_exists = bool(shared_name) and await volume_exists_async(shared_name)

        self.log.info(f"[Groups Data] Returning {len(result)} group(s)")
        self.finish({
            'groups': result,
            'shared_volume': {'name': shared_name, 'exists': shared_exists},
        })


class GroupsCreateHandler(BaseHandler):
    """Handler for creating a new group."""

    @web.authenticated
    async def post(self):
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can create groups")

        body = json.loads(self.request.body)
        name = body.get('name', '').strip()
        description = body.get('description', '').strip()

        valid, error = validate_group_name(name)
        if not valid:
            raise web.HTTPError(400, error)

        from jupyterhub.orm import Group

        existing = self.db.query(Group).filter(Group.name == name).first()
        if existing:
            raise web.HTTPError(409, f"Group '{name}' already exists")

        new_group = Group(name=name)
        self.db.add(new_group)
        self.db.commit()

        manager = GroupsConfigManager.get_instance()
        manager.save_config(name, description=description, priority=0)

        self.log.info(f"[Groups] Admin {current_user.name} created group '{name}'")
        self.finish({'success': True, 'name': name})


class GroupsDeleteHandler(BaseHandler):
    """Handler for deleting a group."""

    @web.authenticated
    async def delete(self, group_name):
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can delete groups")

        from jupyterhub.orm import Group

        group = self.db.query(Group).filter(Group.name == group_name).first()
        if not group:
            raise web.HTTPError(404, f"Group '{group_name}' not found")

        self.db.delete(group)
        self.db.commit()

        manager = GroupsConfigManager.get_instance()
        manager.delete_config(group_name)

        self.log.info(f"[Groups] Admin {current_user.name} deleted group '{group_name}'")
        self.finish({'success': True})


class GroupsConfigHandler(BaseHandler):
    """Handler for reading and updating group configuration."""

    @web.authenticated
    async def get(self, group_name):
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access group config")

        manager = GroupsConfigManager.get_instance()
        config = manager.ensure_config(group_name)
        self.finish(config)

    @web.authenticated
    async def put(self, group_name):
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can update group config")

        body = json.loads(self.request.body)

        description = body.get('description')
        config_dict = {}

        if 'env_vars' in body:
            env_vars = body['env_vars']
            if not isinstance(env_vars, list):
                raise web.HTTPError(400, "env_vars must be a list")
            for var in env_vars:
                if not isinstance(var, dict) or 'name' not in var:
                    raise web.HTTPError(400, "Each env_var must have a 'name' field")

            # Reject names reserved by JupyterHub or the platform config
            stellars_config = self.settings.get('stellars_config', {})
            reserved_names = stellars_config.get('reserved_env_var_names', frozenset())
            reserved_prefixes = stellars_config.get('reserved_env_var_prefixes', ())
            rejected = [
                var['name'] for var in env_vars
                if is_reserved_env_var(var['name'], reserved_names, reserved_prefixes)
            ]
            if rejected:
                self.set_status(400)
                self.finish({
                    'error': 'reserved_env_var_names',
                    'message': (
                        "Reserved variable names cannot be set in group config: "
                        + ", ".join(sorted(set(rejected)))
                        + ". These are controlled by JupyterHub or the platform configuration."
                    ),
                    'rejected': sorted(set(rejected)),
                })
                return
            config_dict['env_vars'] = env_vars

        # Section active flags: off = section reads as unconfigured at resolve
        # time, but its data persists and re-enabling restores it
        for _key in ('env_vars_active', 'docker_active', 'volume_mounts_active'):
            if _key in body:
                config_dict[_key] = bool(body[_key])

        if 'gpu_access' in body:
            config_dict['gpu_access'] = bool(body['gpu_access'])
        if 'gpu_all' in body:
            config_dict['gpu_all'] = bool(body['gpu_all'])
        if 'gpu_device_ids' in body:
            ids = body['gpu_device_ids']
            if not isinstance(ids, list):
                raise web.HTTPError(400, "gpu_device_ids must be a list")
            config_dict['gpu_device_ids'] = [str(x) for x in ids]
        if 'docker_access' in body:
            config_dict['docker_access'] = bool(body['docker_access'])
        if 'docker_limited' in body:
            config_dict['docker_limited'] = bool(body['docker_limited'])
        for _key in ('docker_limited_max_containers', 'docker_limited_max_volumes',
                     'docker_limited_max_networks'):
            if _key in body:
                try:
                    config_dict[_key] = max(0, int(body[_key]))
                except (TypeError, ValueError):
                    config_dict[_key] = 0
        for _key in ('docker_limited_max_storage_gb', 'docker_limited_cpu_cap_cores',
                     'docker_limited_mem_cap_gb'):
            if _key in body:
                try:
                    config_dict[_key] = max(0.0, round(float(body[_key]), 1))
                except (TypeError, ValueError):
                    config_dict[_key] = 0
        if 'docker_limited_allow_dangerous_flags' in body:
            config_dict['docker_limited_allow_dangerous_flags'] = bool(body['docker_limited_allow_dangerous_flags'])
        if 'docker_limited_user_compose_project_enabled' in body:
            config_dict['docker_limited_user_compose_project_enabled'] = bool(body['docker_limited_user_compose_project_enabled'])
        if 'docker_limited_user_compose_project_allow_override' in body:
            config_dict['docker_limited_user_compose_project_allow_override'] = bool(body['docker_limited_user_compose_project_allow_override'])
        if 'docker_limited_hub_network_access' in body:
            config_dict['docker_limited_hub_network_access'] = bool(body['docker_limited_hub_network_access'])
        if 'docker_privileged' in body:
            config_dict['docker_privileged'] = bool(body['docker_privileged'])
        if 'mem_limit_enabled' in body:
            config_dict['mem_limit_enabled'] = bool(body['mem_limit_enabled'])
        if 'mem_limit_gb' in body:
            try:
                gb = float(body['mem_limit_gb'])
            except (TypeError, ValueError):
                gb = 0.0
            config_dict['mem_limit_gb'] = max(0.0, round(gb, 1))
        if 'mem_swap_disabled' in body:
            config_dict['mem_swap_disabled'] = bool(body['mem_swap_disabled'])
        if 'cpu_limit_enabled' in body:
            config_dict['cpu_limit_enabled'] = bool(body['cpu_limit_enabled'])
        if 'cpu_limit_cores' in body:
            try:
                cores = float(body['cpu_limit_cores'])
            except (TypeError, ValueError):
                cores = 0.0
            config_dict['cpu_limit_cores'] = max(0.0, round(cores, 1))

        manager = GroupsConfigManager.get_instance()

        # Merge with existing config to preserve unset fields
        existing = manager.ensure_config(group_name)

        # API keys pool: reconcile incoming (masked) credentials against the
        # stored ones by slot so an admin save never overwrites a real stored
        # secret with its own mask; mint slot ids for new entries. Reserved
        # target names are rejected the same way env_vars are.
        if 'api_keys_pool' in body:
            pool_in = body['api_keys_pool']
            if not isinstance(pool_in, dict):
                raise web.HTTPError(400, "api_keys_pool must be an object")
            stellars_config = self.settings.get('stellars_config', {})
            reserved_names = stellars_config.get('reserved_env_var_names', frozenset())
            reserved_prefixes = stellars_config.get('reserved_env_var_prefixes', ())
            pool_names = [
                pool_in.get('env_var_id'),
                pool_in.get('env_var_secret'),
                pool_in.get('env_var_key'),
            ]
            rejected = [
                n for n in pool_names
                if n and is_reserved_env_var(n, reserved_names, reserved_prefixes)
            ]
            if pool_in.get('enabled') and rejected:
                self.set_status(400)
                self.finish({
                    'error': 'reserved_env_var_names',
                    'message': (
                        "Reserved variable names cannot be used for the API keys pool: "
                        + ", ".join(sorted(set(rejected)))
                        + ". These are controlled by JupyterHub or the platform configuration."
                    ),
                    'rejected': sorted(set(rejected)),
                })
                return
            existing_pool = existing['config'].get('api_keys_pool') or {}
            config_dict['api_keys_pool'] = merge_pool_on_save(pool_in, existing_pool)

        if 'volume_mounts' in body:
            mounts_in = body['volume_mounts']
            if not isinstance(mounts_in, list):
                raise web.HTTPError(400, "volume_mounts must be a list")
            # Normalise; protection (blacklist, name/path validity, duplicates)
            # is imposed at save time by validate_volume_mounts in validate_all.
            config_dict['volume_mounts'] = [
                {
                    'volume': (m.get('volume') or '').strip(),
                    'mountpoint': (m.get('mountpoint') or '').strip(),
                }
                for m in mounts_in if isinstance(m, dict)
            ]

        merged = existing['config'].copy()
        merged.update(config_dict)

        # Per-field coherence: GPU selection, Docker mutual exclusivity + quota
        # sanity, CPU cap presence-with-positive-value, Mem cap likewise. The
        # validator class returns the first failure; the handler maps the error
        # code to HTTP 400 with a stable JSON shape.
        valid, code, msg = GroupConfigValidator.validate_all(merged)
        if not valid:
            self.set_status(400)
            self.finish({'error': code, 'message': msg})
            return

        manager.save_config(group_name, description=description, config_dict=merged)

        self.log.info(f"[Groups] Admin {current_user.name} updated config for '{group_name}'")
        updated = manager.get_config(group_name)
        self.finish(updated)


class GroupsReorderHandler(BaseHandler):
    """Handler for updating group priorities."""

    @web.authenticated
    async def post(self):
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can reorder groups")

        body = json.loads(self.request.body)
        groups = body.get('groups', [])

        if not isinstance(groups, list):
            raise web.HTTPError(400, "groups must be a list of {name, priority}")

        manager = GroupsConfigManager.get_instance()
        manager.reorder(groups)

        self.log.info(f"[Groups] Admin {current_user.name} reordered {len(groups)} group(s)")
        self.finish({'success': True})
