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


class UserProfilesListHandler(BaseHandler):
    """GET every user's profile as {username: {first_name, last_name, email}}.

    Admin-only. Backs the Users list, which shows each user's display name under
    the username; one bulk read avoids an N+1 per-user profile fetch.
    """

    @web.authenticated
    async def get(self):
        current_user = self.current_user
        if current_user is None or not current_user.admin:
            raise web.HTTPError(403, "Only administrators can list user profiles")
        profiles = UserProfileManager.get_instance().get_all_profiles()
        self.finish({"profiles": profiles})


class UserForcePasswordChangeHandler(BaseHandler):
    """POST /api/users/{user}/force-password-change - admin-only. Sets/clears the
    must-change-password-on-next-use flag. Admin-only on purpose: a user must not
    be able to clear their own flag (that would defeat the gate). The current flag
    value is read back through the profile GET (`must_change_password`)."""

    @web.authenticated
    async def post(self, username):
        current_user = self.current_user
        if current_user is None or not current_user.admin:
            raise web.HTTPError(403, "Only administrators can set the force-password-change flag")
        body = json.loads(self.request.body or b'{}')
        value = bool(body.get('value', True))
        UserProfileManager.get_instance().set_must_change_password(username, value)
        self.log.info(f"[force-pw] {current_user.name} set force-password-change={value} for '{username}'")
        self.finish({"username": username, "must_change_password": value})
