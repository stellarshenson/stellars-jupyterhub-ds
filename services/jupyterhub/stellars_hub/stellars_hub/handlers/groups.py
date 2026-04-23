"""Handlers for group management page and API."""

import json

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..groups_config import GroupsConfigManager, validate_group_name


class GroupsPageHandler(BaseHandler):
    """Handler for rendering the groups management page (admin only)."""

    @web.authenticated
    async def get(self):
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this page")

        self.log.info(f"[Groups Page] Admin {current_user.name} accessed groups management")
        html = self.render_template("groups.html", sync=True, user=current_user)
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
        self.log.info(f"[Groups Data] Returning {len(result)} group(s)")
        self.finish({'groups': result})


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
            config_dict['env_vars'] = env_vars

        if 'gpu_access' in body:
            config_dict['gpu_access'] = bool(body['gpu_access'])
        if 'docker_access' in body:
            config_dict['docker_access'] = bool(body['docker_access'])
        if 'docker_privileged' in body:
            config_dict['docker_privileged'] = bool(body['docker_privileged'])

        manager = GroupsConfigManager.get_instance()

        # Merge with existing config to preserve unset fields
        existing = manager.ensure_config(group_name)
        merged = existing['config'].copy()
        merged.update(config_dict)

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
