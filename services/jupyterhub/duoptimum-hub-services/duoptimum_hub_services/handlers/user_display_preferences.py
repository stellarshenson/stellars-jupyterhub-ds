"""Handler for reading and updating a user's display preferences (opaque JSON).

The portal owns the preference schema; this endpoint just persists and returns the
blob so a user's Display Options follow them across browsers. Self-or-admin auth,
the same rule as the profile handler.
"""

import json

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..user_display_preferences import UserDisplayPreferencesManager


class UserDisplayPreferencesHandler(BaseHandler):
    """GET/PUT a user's display preferences.

    Authorized for an administrator (any user) or the user themselves (own
    preferences) - the same self-or-admin rule the profile handler uses.
    """

    def _authorize(self, username):
        current_user = self.current_user
        if current_user is None:
            raise web.HTTPError(403)
        if not current_user.admin and current_user.name != username:
            raise web.HTTPError(403, "You can only view or edit your own preferences")

    @web.authenticated
    async def get(self, username):
        self._authorize(username)
        prefs = UserDisplayPreferencesManager.get_instance().get_prefs(username)
        self.finish({"prefs": prefs})

    @web.authenticated
    async def put(self, username):
        self._authorize(username)
        try:
            body = json.loads(self.request.body or b'{}')
        except (ValueError, TypeError):
            raise web.HTTPError(400, "Invalid JSON body")
        prefs = body.get('prefs')
        if not isinstance(prefs, dict):
            raise web.HTTPError(400, 'Body must be {"prefs": { ... }}')
        manager = UserDisplayPreferencesManager.get_instance()
        try:
            merged = manager.save_prefs(username, prefs)
        except ValueError as e:
            raise web.HTTPError(400, str(e))
        self.log.info(f"[DisplayPrefs] {self.current_user.name} updated preferences for '{username}'")
        self.finish({"prefs": merged})
