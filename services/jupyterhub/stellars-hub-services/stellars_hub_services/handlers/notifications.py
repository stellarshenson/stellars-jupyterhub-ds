"""Handlers for notification broadcasting."""

import asyncio
import json

from jupyterhub.handlers import BaseHandler
from tornado import web
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from ..docker_utils import encode_username_for_docker


class NotificationsPageHandler(BaseHandler):
    """Handler for rendering the notifications broadcast page."""

    @web.authenticated
    async def get(self):
        """Render the notifications broadcast page (admin only)."""
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this page")

        self.log.info(f"[Notifications Page] Admin {current_user.name} accessed notifications panel")
        html = self.render_template("notifications.html", sync=True, user=current_user)
        self.finish(html)


class ActiveServersHandler(BaseHandler):
    """Handler for listing active servers for notification targeting."""

    @web.authenticated
    async def get(self):
        """List all active JupyterLab servers (admin only)."""
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can list active servers")

        self.log.info(f"[Active Servers] Request from admin: {current_user.name}")

        active_servers = []
        from jupyterhub import orm
        for orm_user in self.db.query(orm.User).all():
            user = self.find_user(orm_user.name)
            if user and user.spawner and user.spawner.active:
                active_servers.append({"username": user.name})

        self.log.info(f"[Active Servers] Found {len(active_servers)} active server(s)")
        self.finish({"servers": active_servers})


class BroadcastNotificationHandler(BaseHandler):
    """Handler for broadcasting notifications to active JupyterLab servers."""

    async def post(self):
        """Broadcast a notification to active JupyterLab servers.

        POST /hub/api/notifications/broadcast
        Body: {
            "message": "string",
            "variant": "info|success|warning|error",
            "autoClose": false,
            "recipients": ["user1", "user2"]  # optional
        }
        """
        current_user = self.current_user
        if current_user is None:
            raise web.HTTPError(403, "Not authenticated")
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can broadcast notifications")

        self.log.info(f"[Broadcast Notification] Request from admin: {current_user.name}")

        # Parse request body
        try:
            body = self.request.body.decode('utf-8')
            data = json.loads(body) if body else {}
            message = data.get('message', '').strip()
            variant = data.get('variant', 'info')
            auto_close = data.get('autoClose', False)
            recipients = data.get('recipients', None)
        except Exception as e:
            self.log.error(f"[Broadcast Notification] Failed to parse request body: {e}")
            return self.send_error(400, "Invalid request body")

        if not message:
            return self.send_error(400, "Message cannot be empty")
        if len(message) > 140:
            return self.send_error(400, "Message cannot exceed 140 characters")

        valid_variants = ['default', 'info', 'success', 'warning', 'error', 'in-progress']
        if variant not in valid_variants:
            return self.send_error(400, f"Variant must be one of: {', '.join(valid_variants)}")

        # Get active spawners
        active_spawners = []
        from jupyterhub import orm
        for orm_user in self.db.query(orm.User).all():
            user = self.find_user(orm_user.name)
            if user and user.spawner and user.spawner.active:
                active_spawners.append((user, user.spawner))

        # Filter by recipients if specified
        if recipients and isinstance(recipients, list) and len(recipients) > 0:
            recipients_set = set(recipients)
            active_spawners = [(u, s) for u, s in active_spawners if u.name in recipients_set]

        if not active_spawners:
            return self.finish({
                "total": 0, "successful": 0, "failed": 0,
                "details": [], "message": "No active servers found",
            })

        notification_payload = {
            "message": message,
            "type": variant,
            "autoClose": auto_close,
            "actions": [{"label": "Dismiss", "caption": "Close this notification", "displayType": "default"}],
        }

        tasks = [self._send_notification(user, spawner, notification_payload) for user, spawner in active_spawners]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = 0
        failed = 0
        details = []

        for (user, spawner), result in zip(active_spawners, results):
            if isinstance(result, dict) and result.get('status') == 'success':
                successful += 1
                details.append({"username": user.name, "status": "success"})
            else:
                failed += 1
                error_msg = str(result) if isinstance(result, Exception) else result.get('error', 'Unknown error')
                details.append({"username": user.name, "status": "failed", "error": error_msg})

        total = len(active_spawners)
        self.log.info(f"[Broadcast Notification] Complete: {successful}/{total} successful, {failed}/{total} failed")

        self.set_status(200)
        self.finish({"total": total, "successful": successful, "failed": failed, "details": details})

    async def _send_notification(self, user, spawner, notification_payload):
        username = user.name

        try:
            token = user.new_api_token(note="notification-broadcast", expires_in=300)

            if not spawner.server:
                return {"status": "failed", "error": "Server not available"}

            base_url = spawner.server.base_url
            container_url = f"http://jupyterlab-{encode_username_for_docker(username)}:8888"
            endpoint = f"{container_url}{base_url}jupyterlab-notifications-extension/ingest"

            http_client = AsyncHTTPClient()
            request = HTTPRequest(
                url=endpoint,
                method="POST",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
                body=json.dumps(notification_payload),
                request_timeout=5.0,
                connect_timeout=5.0,
            )

            response = await http_client.fetch(request, raise_error=False)

            if response.code == 200:
                self.log.info(f"[Notification] {username}: '{notification_payload['message'][:50]}' ({notification_payload['type']}) - SUCCESS")
                return {"status": "success"}
            else:
                error_msg = f"HTTP {response.code}: {response.reason}"
                self.log.warning(f"[Notification] {username}: '{notification_payload['message'][:50]}' ({notification_payload['type']}) - FAILED: {error_msg}")
                return {"status": "failed", "error": error_msg}
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg or "Connection timed out" in error_msg:
                error_msg = "Server not responding"
            elif "404" in error_msg:
                error_msg = "Notification extension not installed"
            elif "401" in error_msg or "403" in error_msg:
                error_msg = "Authentication failed"

            self.log.error(f"[Notification] {username}: '{notification_payload['message'][:50]}' ({notification_payload['type']}) - ERROR: {error_msg}")
            return {"status": "failed", "error": error_msg}
