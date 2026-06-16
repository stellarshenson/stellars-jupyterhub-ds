"""Handler for reading and updating a user's display profile (name + email)."""

import json

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..user_profiles import UserProfileManager


class UserProfileHandler(BaseHandler):
    """GET/PUT a user's first/last name + email.

    Authorized for an administrator (any user) or the user themselves (own
    profile) - the same self-or-admin rule the manage-volumes handler uses.
    """

    def _authorize(self, username):
        current_user = self.current_user
        if current_user is None:
            raise web.HTTPError(403)
        if not current_user.admin and current_user.name != username:
            raise web.HTTPError(403, "You can only view or edit your own profile")

    @web.authenticated
    async def get(self, username):
        self._authorize(username)
        profile = UserProfileManager.get_instance().get_profile(username)
        self.finish(profile)

    @web.authenticated
    async def put(self, username):
        self._authorize(username)
        body = json.loads(self.request.body)
        manager = UserProfileManager.get_instance()
        manager.save_profile(
            username,
            first_name=body.get('first_name'),
            last_name=body.get('last_name'),
            email=body.get('email'),
        )
        self.log.info(f"[UserProfile] {self.current_user.name} updated profile for '{username}'")
        self.finish(manager.get_profile(username))
