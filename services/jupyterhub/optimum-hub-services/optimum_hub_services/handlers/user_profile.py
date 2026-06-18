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


class UserRenameHandler(BaseHandler):
    """POST /api/users/{user}/rename - admin-only. Renames the user through the
    JupyterHub orm (which fires events.py::sync_nativeauth_on_rename to carry the
    NativeAuth UserInfo, activity samples and display profile across), and records
    a rename event that NAMES the acting admin (who renamed whom). The actor is
    taken from the authenticated session, never the client. Volumes are keyed on
    the old encoded name and are intentionally NOT moved - the admin migrates them
    separately (the UI confirm dialog states this)."""

    @web.authenticated
    async def post(self, username):
        current_user = self.current_user
        if current_user is None or not current_user.admin:
            raise web.HTTPError(403, "Only administrators can rename users")
        body = json.loads(self.request.body or b'{}')
        new_name = (body.get('name') or '').strip()
        if not new_name:
            raise web.HTTPError(400, "A new username is required")
        if new_name == username:
            raise web.HTTPError(400, "The new username is the same as the current one")
        user = self.find_user(username)
        if user is None:
            raise web.HTTPError(404, f"No such user: {username}")
        if self.find_user(new_name):
            raise web.HTTPError(409, f"User {new_name} already exists, username must be unique")

        from ..events import set_rename_actor, reset_rename_actor
        token = set_rename_actor(current_user.name)
        try:
            user.name = new_name      # fires the rename sync listener synchronously
            self.db.commit()
        finally:
            reset_rename_actor(token)
        self.log.info(f"[rename] {current_user.name} renamed '{username}' -> '{new_name}'")
        self.finish({"name": new_name})
