"""JSON API over NativeAuthenticator UserInfo for the portal.

The stock NativeAuth authorization area is an HTML page (see
``auth.CustomAuthorizationAreaHandler``); the SPA portal needs the same data as
JSON. Two endpoints, both admin-only:

- ``GET  /hub/api/native-users`` - list every signup with its authorization
  state, so the portal can surface pending (signed-up, not-yet-authorized) users
  that have no hub User row yet and therefore never appear in ``/hub/api/users``.
- ``POST /hub/api/native-users/{name}/authorization`` - idempotently set
  ``is_authorized`` to a target value. NativeAuth's own ``/authorize/{name}`` is a
  *toggle*, which is unsafe to drive from a checkbox (a stale value flips the
  wrong way); this sets the requested state directly.
"""

import json

from jupyterhub.handlers import BaseHandler
from tornado import web


class NativeUsersHandler(BaseHandler):
    """GET /hub/api/native-users - list NativeAuth signups (admin only)."""

    @web.authenticated
    async def get(self):
        current_user = self.current_user
        if current_user is None or not current_user.admin:
            raise web.HTTPError(403, "Only administrators can list users")

        from nativeauthenticator.orm import UserInfo
        from jupyterhub import orm

        hub_usernames = {u.name for u in self.db.query(orm.User).all()}
        rows = self.db.query(UserInfo).all()
        self.finish({
            "users": [
                {
                    "username": u.username,
                    "is_authorized": bool(u.is_authorized),
                    "is_hub_user": u.username in hub_usernames,
                }
                for u in rows
            ]
        })


class NativeUserAuthorizationHandler(BaseHandler):
    """POST /hub/api/native-users/{name}/authorization - idempotent set (admin only).

    Body: ``{"authorized": bool}`` (defaults to true). No-op when already in the
    requested state.
    """

    @web.authenticated
    async def post(self, username):
        current_user = self.current_user
        if current_user is None or not current_user.admin:
            raise web.HTTPError(403, "Only administrators can change authorization")

        try:
            body = json.loads(self.request.body or b"{}")
        except ValueError:
            raise web.HTTPError(400, "invalid JSON body")
        authorized = bool(body.get("authorized", True))

        from nativeauthenticator.orm import UserInfo

        user = UserInfo.find(self.db, username)
        if user is None:
            raise web.HTTPError(404, f"No signup found for '{username}'")

        if bool(user.is_authorized) != authorized:
            user.is_authorized = authorized
            self.db.commit()
            self.log.info(
                f"[NativeUsers] Admin {current_user.name} set is_authorized={authorized} for '{username}'"
            )
        self.finish({"username": username, "is_authorized": authorized})
