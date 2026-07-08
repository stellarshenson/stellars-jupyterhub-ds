"""Handler for reading and updating a user's environment variables.

Per-user env vars injected into the user's lab container on spawn. Self-or-admin
auth (the same rule as the profile handler) so a user edits their own set and an
admin edits anyone's. GET also returns the reserved names/prefixes so the SPA can
validate live; PUT rejects reserved/invalid names with a structured 400 the SPA
maps to the offending rows.
"""

import json

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..user_env_vars import EnvVarError, UserEnvVarsManager


class UserEnvVarsHandler(BaseHandler):
    """GET/PUT a user's environment variables.

    Authorized for an administrator (any user) or the user themselves (own vars) -
    the same self-or-admin rule the profile handler uses.
    """

    def _authorize(self, username):
        current_user = self.current_user
        if current_user is None:
            raise web.HTTPError(403)
        if not current_user.admin and current_user.name != username:
            raise web.HTTPError(403, "You can only view or edit your own environment variables")

    def _reserved(self):
        """Reserved names + prefixes from the platform config (env-sourced, single
        source of truth), returned as sorted lists for the client validator."""
        cfg = self.settings.get('stellars_config', {})
        names = cfg.get('reserved_env_var_names', frozenset())
        prefixes = cfg.get('reserved_env_var_prefixes', ())
        return sorted(names), list(prefixes)

    def _system_env_enabled(self, username):
        """Resolve the target user's effective system-env: the winning group's value,
        else the platform lab default. A NON-admin (the user themselves) may only see
        or edit their env vars while this is on; an admin always may (role privilege)."""
        from jupyterhub import orm
        from ..groups_config import GroupsConfigManager
        from ..policy import effective_user_env_enable, resolve_policies
        cfg = self.settings.get('stellars_config') or {}
        orm_user = self.db.query(orm.User).filter(orm.User.name == username).first()
        group_names = [g.name for g in orm_user.groups] if orm_user else []
        try:
            all_configs = GroupsConfigManager.get_instance().get_all_configs()
        except Exception as e:
            self.log.error(f"[UserEnvVars] group config load failed for '{username}': {e}")
            all_configs = []
        resolved = resolve_policies(
            user_group_names=group_names, all_group_configs=all_configs,
            gpu_available=cfg.get('gpu_available', False),
            reserved_names=cfg.get('reserved_env_var_names', frozenset()),
            reserved_prefixes=cfg.get('reserved_env_var_prefixes', ()),
        )
        # Same shared fold SudoPolicy.apply + the spawn hook use, so this handler's
        # see/edit decision can never drift from what is enforced at spawn.
        return effective_user_env_enable(resolved, cfg.get('lab_user_env_enable', 1))

    @web.authenticated
    async def get(self, username):
        self._authorize(username)
        is_admin = bool(self.current_user and self.current_user.admin)
        system_env_enabled = self._system_env_enabled(username)
        # editable == may see AND edit. A non-admin (self) loses both when system-env is
        # off; an admin keeps them. The vars are withheld when not editable so a locked
        # user cannot even read them (role-level restriction, acc-crit 2A).
        editable = is_admin or system_env_enabled
        reserved_names, reserved_prefixes = self._reserved()
        env_vars = UserEnvVarsManager.get_instance().get_env_vars(username) if editable else []
        self.finish({
            "env_vars": env_vars,
            "reserved_names": reserved_names,
            "reserved_prefixes": reserved_prefixes,
            "system_env_enabled": system_env_enabled,
            "editable": editable,
        })

    @web.authenticated
    async def put(self, username):
        self._authorize(username)
        # A non-admin cannot edit their env vars while system-env is off (admin may,
        # role privilege). Server-side enforcement mirrors the hidden editor in the SPA.
        if not (self.current_user and self.current_user.admin) and not self._system_env_enabled(username):
            raise web.HTTPError(
                403, "System environment variables are disabled for your account by policy; "
                     "you cannot edit them.")
        try:
            body = json.loads(self.request.body or b'{}')
        except (ValueError, TypeError):
            raise web.HTTPError(400, "Invalid JSON body")
        env_vars = body.get('env_vars')
        if not isinstance(env_vars, list):
            raise web.HTTPError(400, 'Body must be {"env_vars": [ ... ]}')
        cfg = self.settings.get('stellars_config', {})
        reserved_names = cfg.get('reserved_env_var_names', frozenset())
        reserved_prefixes = cfg.get('reserved_env_var_prefixes', ())
        manager = UserEnvVarsManager.get_instance()
        try:
            stored = manager.set_env_vars(username, env_vars, reserved_names, reserved_prefixes)
        except EnvVarError as e:
            # Structured body so the SPA can highlight the rejected rows.
            self.set_status(400)
            self.finish({"code": e.code, "message": str(e), "rejected": e.rejected})
            return
        except ValueError as e:
            raise web.HTTPError(400, str(e))
        self.log.info(f"[UserEnvVars] {self.current_user.name} updated env vars for '{username}' ({len(stored)} set)")
        self.finish({"env_vars": stored})
