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

    @web.authenticated
    async def get(self, username):
        self._authorize(username)
        env_vars = UserEnvVarsManager.get_instance().get_env_vars(username)
        reserved_names, reserved_prefixes = self._reserved()
        self.finish({
            "env_vars": env_vars,
            "reserved_names": reserved_names,
            "reserved_prefixes": reserved_prefixes,
        })

    @web.authenticated
    async def put(self, username):
        self._authorize(username)
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
