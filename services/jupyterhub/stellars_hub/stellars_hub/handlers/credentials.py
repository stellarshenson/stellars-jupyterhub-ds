"""Handler for retrieving credentials of newly created users."""

import json

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..password_cache import get_cached_password


class GetUserCredentialsHandler(BaseHandler):
    """Handler for retrieving cached credentials of newly created users."""

    @web.authenticated
    async def post(self):
        """Retrieve cached credentials for newly created users (admin only).

        POST /hub/api/admin/credentials
        Body: {"usernames": ["user1", "user2", ...]}
        """
        current_user = self.current_user
        if current_user is None or not current_user.admin:
            raise web.HTTPError(403, "Only administrators can retrieve credentials")

        try:
            body = self.request.body.decode('utf-8')
            data = json.loads(body) if body else {}
            usernames = data.get('usernames', [])
        except Exception as e:
            self.log.error(f"[Get Credentials] Failed to parse request body: {e}")
            raise web.HTTPError(400, "Invalid request body")

        self.log.info(f"[Get Credentials] Admin {current_user.name} requesting credentials for: {usernames}")

        credentials = []
        for username in usernames:
            password = get_cached_password(username)
            if password:
                credentials.append({"username": username, "password": password})
                self.log.info(f"[Get Credentials] Found cached password for: {username}")
            else:
                self.log.info(f"[Get Credentials] No cached password for: {username}")

        self.log.info(f"[Get Credentials] Returning {len(credentials)} credential(s)")
        self.finish({"credentials": credentials})
