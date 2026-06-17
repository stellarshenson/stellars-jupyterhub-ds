"""Hub-side probe endpoint for lab readiness.

Used by the restart flow in `home.html` instead of probing the lab directly:
the browser would log devtools-visible 5xx errors for every poll tick while
the lab is still booting. This handler always returns HTTP 200 with a JSON
{ready: bool} payload, doing the actual probe server-side via Tornado's
async HTTP client - so the browser console stays clean.
"""

from __future__ import annotations

from jupyterhub.handlers import BaseHandler
from tornado import web
from tornado.httpclient import AsyncHTTPClient, HTTPRequest


class LabReadyHandler(BaseHandler):
    """GET /hub/api/users/{username}/lab-ready -> {"ready": bool, ...}."""

    async def get(self, username: str) -> None:
        current_user = self.current_user
        if current_user is None:
            raise web.HTTPError(403, "Not authenticated")
        if not (current_user.admin or current_user.name == username):
            raise web.HTTPError(403, "Permission denied")

        user = self.find_user(username)
        if user is None:
            # 200 + ready:false rather than 404 - keep the polling client
            # path simple, no special-casing for "user vanished mid-restart".
            self.set_status(200)
            self.finish({"ready": False, "reason": "user_not_found"})
            return

        spawner = user.spawner
        if not spawner or not spawner.active or not spawner.server:
            self.set_status(200)
            self.finish({"ready": False, "reason": "not_active"})
            return

        server = spawner.server
        # Hit the lab's /api endpoint on its upstream socket, bypassing CHP -
        # so a not-yet-listening lab gives us a fast ConnectionRefused rather
        # than the longer CHP 503 path.
        url = f"{server.proto}://{server.ip}:{server.port}{server.base_url}api"

        client = AsyncHTTPClient()
        req = HTTPRequest(
            url,
            method="GET",
            connect_timeout=2.0,
            request_timeout=5.0,
            follow_redirects=False,
            validate_cert=False,
        )
        try:
            # raise_error=False -> HTTPClientError suppressed for 4xx/5xx, but
            # network-level failures (connect refused, DNS, timeout) still raise.
            resp = await client.fetch(req, raise_error=False)
        except Exception as e:
            self.set_status(200)
            self.finish({"ready": False, "reason": type(e).__name__})
            return

        # Any HTTP response back from the lab (200, 302, 401, etc.) means the
        # lab process is up and serving - that's the bar the old client-side
        # probe used, mirrored here exactly.
        self.set_status(200)
        self.finish({"ready": True, "status": resp.code})
