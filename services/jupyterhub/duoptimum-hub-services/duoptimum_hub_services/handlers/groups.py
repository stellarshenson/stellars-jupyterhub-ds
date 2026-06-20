"""Handlers for group management page and API."""

import html
import json

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..event_log import record_event
from ..groups_config import GroupsConfigManager, validate_group_name
from ..policy import (
    PolicyCoerceError,
    PolicyCtx,
    coerce_config,
    summarize_config,
    validate_all,
)


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
                # Per-type display summaries (badge + tooltip line), computed
                # server-side from the registry so the client never recomputes
                # policy-display logic.
                'policy_summary': summarize_config(config['config']),
            })

        result.sort(key=lambda g: g['priority'], reverse=True)

        # Normalise priorities to a contiguous rank (top row = highest) so the
        # stored value always matches the displayed row position - no gaps after
        # a delete, no 0-ties after a create. Sort is stable, so existing relative
        # order is preserved; persist only when something actually drifted.
        desired = {g['name']: len(result) - i for i, g in enumerate(result)}
        if any(g['priority'] != desired[g['name']] for g in result):
            manager.reorder([{'name': n, 'priority': p} for n, p in desired.items()])
            for g in result:
                g['priority'] = desired[g['name']]

        # Standard shared volume: the UI shows its resolved name + a human
        # description (read from the volume's duoptimum-hub.volume.description label)
        # and offers the grant only when the volume actually exists on the host.
        # Docker errors fail safe (exists=False -> grant disabled; manual rows still work).
        stellars_config = self.settings.get('stellars_config') or {}
        shared_name = stellars_config.get('shared_volume_name', '')
        from ..docker_utils import volume_labels_async
        labels = await volume_labels_async(shared_name) if shared_name else None
        shared_exists = labels is not None  # one inspect: None means absent / docker error
        shared_desc = (labels or {}).get('duoptimum-hub.volume.description', '')

        self.log.info(f"[Groups Data] Returning {len(result)} group(s)")
        self.finish({
            'groups': result,
            'shared_volume': {'name': shared_name, 'exists': shared_exists, 'description': shared_desc},
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

        record_event('group', f'Group <b>{html.escape(name)}</b> created')
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

        record_event('group', f'Group <b>{html.escape(group_name)}</b> deleted')
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

        manager = GroupsConfigManager.get_instance()
        # Merge onto the existing config to preserve unset fields; the api-keys
        # coerce needs the stored pool to keep secrets by slot.
        existing = manager.ensure_config(group_name)

        stellars_config = self.settings.get('stellars_config', {})
        ctx = PolicyCtx(
            reserved_names=stellars_config.get('reserved_env_var_names', frozenset()),
            reserved_prefixes=stellars_config.get('reserved_env_var_prefixes', ()),
        )

        # Coerce every field through the policy registry (one loop over the
        # types, replacing the old field-by-field branches). A structured
        # PolicyCoerceError renders the stable reserved-name JSON; a plain one
        # maps to a bare 400, matching the legacy handler shapes.
        try:
            config_dict = coerce_config(body, existing['config'], ctx)
        except PolicyCoerceError as e:
            if e.structured:
                self.set_status(400)
                self.finish({'error': e.code, 'message': e.message, **e.extra})
                return
            raise web.HTTPError(400, e.message)

        merged = existing['config'].copy()
        merged.update(config_dict)

        # Per-type coherence checks (registry-driven); first failure wins and
        # maps to HTTP 400 with a stable JSON shape.
        valid, code, msg = validate_all(merged)
        if not valid:
            self.set_status(400)
            self.finish({'error': code, 'message': msg})
            return

        manager.save_config(group_name, description=description, config_dict=merged)

        record_event('policy', f'Policy updated on group <b>{html.escape(group_name)}</b>')
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
