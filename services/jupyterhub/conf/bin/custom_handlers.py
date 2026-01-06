#!/usr/bin/env python3
"""
Custom JupyterHub API handlers for volume management, server control, and notifications
"""

from jupyterhub.handlers import BaseHandler
from tornado import web
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
import docker
import json
import asyncio
import time


# =============================================================================
# Password Cache for Admin User Creation
# =============================================================================

# Temporary password cache - stores {username: (password, timestamp)}
_password_cache = {}
_CACHE_EXPIRY_SECONDS = 300  # 5 minutes


def cache_password(username, password):
    """Store a password in the cache with timestamp"""
    _password_cache[username] = (password, time.time())


def get_cached_password(username):
    """Get a password from cache if not expired"""
    if username in _password_cache:
        password, timestamp = _password_cache[username]
        if time.time() - timestamp < _CACHE_EXPIRY_SECONDS:
            return password
        else:
            del _password_cache[username]
    return None


def clear_cached_password(username):
    """Remove a password from cache"""
    _password_cache.pop(username, None)


class ManageVolumesHandler(BaseHandler):
    """Handler for managing user volumes"""

    async def delete(self, username):
        """
        Delete selected user volumes (only when server is stopped)

        DELETE /hub/api/users/{username}/manage-volumes
        Body: {"volumes": ["home", "workspace", "cache"]}
        """
        self.log.info(f"[Manage Volumes] API endpoint called for user: {username}")

        # 0. Check permissions: user must be admin or requesting their own volumes
        current_user = self.current_user
        if current_user is None:
            self.log.warning(f"[Manage Volumes] Authentication failed - no current user")
            raise web.HTTPError(403, "Not authenticated")

        self.log.info(f"[Manage Volumes] Request from user: {current_user.name}, admin: {current_user.admin}")

        if not (current_user.admin or current_user.name == username):
            self.log.warning(f"[Manage Volumes] Permission denied - user {current_user.name} attempted to manage {username}'s volumes")
            raise web.HTTPError(403, "Permission denied")

        self.log.info(f"[Manage Volumes] Permission check passed")

        # 1. Parse request body
        try:
            body = self.request.body.decode('utf-8')
            data = json.loads(body) if body else {}
            requested_volumes = data.get('volumes', [])
            self.log.info(f"[Manage Volumes] Requested volumes: {requested_volumes}")
        except Exception as e:
            self.log.error(f"[Manage Volumes] Failed to parse request body: {e}")
            return self.send_error(400, "Invalid request body")

        if not requested_volumes or not isinstance(requested_volumes, list):
            self.log.warning(f"[Manage Volumes] No volumes specified or invalid format")
            return self.send_error(400, "No volumes specified")

        # Validate volume types against configured USER_VOLUME_SUFFIXES
        from jupyterhub_config import USER_VOLUME_SUFFIXES
        valid_volumes = set(USER_VOLUME_SUFFIXES)
        invalid_volumes = set(requested_volumes) - valid_volumes
        if invalid_volumes:
            self.log.warning(f"[Manage Volumes] Invalid volume types: {invalid_volumes}")
            return self.send_error(400, f"Invalid volume types: {invalid_volumes}")

        # 2. Verify user exists
        user = self.find_user(username)
        if not user:
            self.log.warning(f"[Manage Volumes] User {username} not found")
            return self.send_error(404, "User not found")

        self.log.info(f"[Manage Volumes] User {username} found")

        # 3. Check server is stopped
        spawner = user.spawner
        self.log.info(f"[Manage Volumes] Server status for {username}: active={spawner.active}")

        if spawner.active:
            self.log.warning(f"[Manage Volumes] Server is running, cannot reset volumes")
            return self.send_error(400, "Server must be stopped before resetting volumes")

        self.log.info(f"[Manage Volumes] Server is stopped, proceeding with volume reset")

        # 4. Connect to Docker
        self.log.info(f"[Manage Volumes] Connecting to Docker daemon")
        try:
            docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
            self.log.info(f"[Manage Volumes] Successfully connected to Docker")
        except Exception as e:
            self.log.error(f"[Manage Volumes] Failed to connect to Docker: {e}")
            return self.send_error(500, "Failed to connect to Docker daemon")

        # 5. Remove requested volumes
        reset_volumes = []
        failed_volumes = []

        for volume_type in requested_volumes:
            volume_name = f'jupyterlab-{username}_{volume_type}'
            self.log.info(f"[Manage Volumes] Processing volume: {volume_name}")

            try:
                volume = docker_client.volumes.get(volume_name)
                self.log.info(f"[Manage Volumes] Volume {volume_name} found, removing...")
                volume.remove()
                self.log.info(f"[Manage Volumes] Successfully removed volume {volume_name}")
                reset_volumes.append(volume_type)
            except docker.errors.NotFound:
                self.log.warning(f"[Manage Volumes] Volume {volume_name} not found, skipping")
                failed_volumes.append({"volume": volume_type, "reason": "not found"})
            except docker.errors.APIError as e:
                self.log.error(f"[Manage Volumes] Failed to remove volume {volume_name}: {e}")
                failed_volumes.append({"volume": volume_type, "reason": str(e)})

        docker_client.close()
        self.log.info(f"[Manage Volumes] Docker client closed")

        # 6. Return response
        response = {
            "message": f"Successfully reset {len(reset_volumes)} volume(s)",
            "reset_volumes": reset_volumes,
            "failed_volumes": failed_volumes
        }

        self.log.info(f"[Manage Volumes] Operation complete: {len(reset_volumes)} reset, {len(failed_volumes)} failed")
        self.set_status(200)
        self.finish(response)


class RestartServerHandler(BaseHandler):
    """Handler for restarting user servers"""

    async def post(self, username):
        """
        Restart a user's server using Docker container restart

        POST /hub/api/users/{username}/restart-server
        """
        self.log.info(f"[Restart Server] API endpoint called for user: {username}")

        # 0. Check permissions: user must be admin or requesting their own server
        current_user = self.current_user
        if current_user is None:
            self.log.warning(f"[Restart Server] Authentication failed - no current user")
            raise web.HTTPError(403, "Not authenticated")

        self.log.info(f"[Restart Server] Request from user: {current_user.name}, admin: {current_user.admin}")

        if not (current_user.admin or current_user.name == username):
            self.log.warning(f"[Restart Server] Permission denied - user {current_user.name} attempted to restart {username}'s server")
            raise web.HTTPError(403, "Permission denied")

        self.log.info(f"[Restart Server] Permission check passed")

        # 1. Verify user exists
        user = self.find_user(username)
        if not user:
            self.log.warning(f"[Restart Server] User {username} not found")
            return self.send_error(404, "User not found")

        self.log.info(f"[Restart Server] User {username} found")

        # 2. Check server is running
        spawner = user.spawner
        self.log.info(f"[Restart Server] Server status for {username}: active={spawner.active}")

        if not spawner.active:
            self.log.warning(f"[Restart Server] Server is not running, cannot restart")
            return self.send_error(400, "Server is not running")

        self.log.info(f"[Restart Server] Server is running, proceeding with restart")

        # 3. Get container name from spawner
        container_name = f'jupyterlab-{username}'
        self.log.info(f"[Restart Server] Container name: {container_name}")

        # 4. Connect to Docker and restart container
        self.log.info(f"[Restart Server] Connecting to Docker daemon")
        try:
            docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
            self.log.info(f"[Restart Server] Successfully connected to Docker")
        except Exception as e:
            self.log.error(f"[Restart Server] Failed to connect to Docker: {e}")
            return self.send_error(500, "Failed to connect to Docker daemon")

        try:
            # Get the container
            self.log.info(f"[Restart Server] Getting container: {container_name}")
            container = docker_client.containers.get(container_name)
            self.log.info(f"[Restart Server] Container found, status: {container.status}")

            # Restart the container (graceful restart with 10s timeout)
            self.log.info(f"[Restart Server] Initiating container restart (timeout=10s)")
            container.restart(timeout=10)

            self.log.info(f"[Restart Server] Container {container_name} successfully restarted for user {username}")
            self.set_status(200)
            self.finish({"message": f"Container {container_name} successfully restarted"})
        except docker.errors.NotFound:
            self.log.warning(f"[Restart Server] Container {container_name} not found")
            return self.send_error(404, f"Container {container_name} not found")
        except docker.errors.APIError as e:
            self.log.error(f"[Restart Server] Failed to restart container {container_name}: {e}")
            return self.send_error(500, f"Failed to restart container: {str(e)}")
        finally:
            docker_client.close()
            self.log.info(f"[Restart Server] Docker client closed")


class NotificationsPageHandler(BaseHandler):
    """Handler for rendering the notifications broadcast page"""

    @web.authenticated
    async def get(self):
        """
        Render the notifications broadcast page (admin only)

        GET /notifications
        """
        current_user = self.current_user

        # Only admins can access notifications panel
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this page")

        self.log.info(f"[Notifications Page] Admin {current_user.name} accessed notifications panel")

        # Render the template (sync=True to get string instead of awaitable)
        html = self.render_template("notifications.html", sync=True, user=current_user)
        self.finish(html)


class BroadcastNotificationHandler(BaseHandler):
    """Handler for broadcasting notifications to all active JupyterLab servers"""

    async def post(self):
        """
        Broadcast a notification to all active JupyterLab servers

        POST /hub/api/notifications/broadcast
        Body: {
            "message": "string",
            "variant": "info|success|warning|error",
            "autoClose": false
        }
        """
        self.log.info(f"[Broadcast Notification] API endpoint called")

        # 0. Check permissions: only admins can broadcast
        current_user = self.current_user
        if current_user is None:
            self.log.warning(f"[Broadcast Notification] Authentication failed - no current user")
            raise web.HTTPError(403, "Not authenticated")

        if not current_user.admin:
            self.log.warning(f"[Broadcast Notification] Permission denied - user {current_user.name} is not admin")
            raise web.HTTPError(403, "Only administrators can broadcast notifications")

        self.log.info(f"[Broadcast Notification] Request from admin: {current_user.name}")

        # 1. Parse request body
        try:
            body = self.request.body.decode('utf-8')
            data = json.loads(body) if body else {}
            message = data.get('message', '').strip()
            variant = data.get('variant', 'info')
            auto_close = data.get('autoClose', False)

            self.log.info(f"[Broadcast Notification] Message: {message[:50]}..., Variant: {variant}, AutoClose: {auto_close}")
        except Exception as e:
            self.log.error(f"[Broadcast Notification] Failed to parse request body: {e}")
            return self.send_error(400, "Invalid request body")

        # 2. Validate input
        if not message:
            self.log.warning(f"[Broadcast Notification] Empty message provided")
            return self.send_error(400, "Message cannot be empty")

        if len(message) > 140:
            self.log.warning(f"[Broadcast Notification] Message too long: {len(message)} characters")
            return self.send_error(400, "Message cannot exceed 140 characters")

        valid_variants = ['default', 'info', 'success', 'warning', 'error', 'in-progress']
        if variant not in valid_variants:
            self.log.warning(f"[Broadcast Notification] Invalid variant: {variant}")
            return self.send_error(400, f"Variant must be one of: {', '.join(valid_variants)}")

        # 3. Get all active spawners
        self.log.info(f"[Broadcast Notification] Querying active spawners")
        active_spawners = []

        from jupyterhub import orm
        for orm_user in self.db.query(orm.User).all():
            # Use find_user to get the wrapped user object with spawner property
            user = self.find_user(orm_user.name)
            if user and user.spawner and user.spawner.active:
                active_spawners.append((user, user.spawner))

        self.log.info(f"[Broadcast Notification] Found {len(active_spawners)} active server(s)")

        if not active_spawners:
            self.log.info(f"[Broadcast Notification] No active servers found")
            return self.finish({
                "total": 0,
                "successful": 0,
                "failed": 0,
                "details": [],
                "message": "No active servers found"
            })

        # 4. Broadcast to all active servers concurrently
        notification_payload = {
            "message": message,
            "type": variant,
            "autoClose": auto_close,
            "actions": [
                {
                    "label": "Dismiss",
                    "caption": "Close this notification",
                    "displayType": "default"
                }
            ]
        }

        tasks = []
        for user, spawner in active_spawners:
            task = self._send_notification(user, spawner, notification_payload)
            tasks.append(task)

        # Gather all results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 5. Compile response
        successful = 0
        failed = 0
        details = []

        for (user, spawner), result in zip(active_spawners, results):
            if isinstance(result, dict) and result.get('status') == 'success':
                successful += 1
                details.append({
                    "username": user.name,
                    "status": "success"
                })
            else:
                failed += 1
                error_msg = str(result) if isinstance(result, Exception) else result.get('error', 'Unknown error')
                details.append({
                    "username": user.name,
                    "status": "failed",
                    "error": error_msg
                })

        total = len(active_spawners)
        self.log.info(f"[Broadcast Notification] Complete: {successful}/{total} successful, {failed}/{total} failed")

        response = {
            "total": total,
            "successful": successful,
            "failed": failed,
            "details": details
        }

        self.set_status(200)
        self.finish(response)

    async def _send_notification(self, user, spawner, notification_payload):
        """
        Send notification to a single JupyterLab server

        Args:
            user: JupyterHub user object
            spawner: User's spawner object
            notification_payload: Notification data dict

        Returns:
            dict: {"status": "success"} or {"status": "failed", "error": "message"}
        """
        username = user.name

        try:
            # 1. Get or create API token for the user
            self.log.info(f"[Broadcast Notification] Getting API token for user: {username}")

            # Generate a new API token for notification purposes
            # Note: APIToken.token is write-only, we cannot read existing tokens
            # We create a new token with note identifying it as for notifications
            token = user.new_api_token(note="notification-broadcast", expires_in=300)
            self.log.info(f"[Broadcast Notification] Generated temporary API token for {username}")

            # 2. Construct JupyterLab URL
            # Use the spawner's internal connection URL (direct container access)
            # The spawner.server.url contains the public-facing URL
            if not spawner.server:
                self.log.warning(f"[Broadcast Notification] Spawner for {username} has no server")
                return {"status": "failed", "error": "Server not available"}

            # Get the base URL from spawner server (e.g., /jupyterhub/user/konrad/)
            base_url = spawner.server.base_url
            # Construct internal container URL
            container_url = f"http://jupyterlab-{username}:8888"
            endpoint = f"{container_url}{base_url}jupyterlab-notifications-extension/ingest"

            self.log.info(f"[Notification] Constructed endpoint for {username}: {endpoint}")

            # 3. Make HTTP request
            http_client = AsyncHTTPClient()

            request = HTTPRequest(
                url=endpoint,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                },
                body=json.dumps(notification_payload),
                request_timeout=5.0,
                connect_timeout=5.0
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

            # Provide more specific error messages
            if "Connection refused" in error_msg or "Connection timed out" in error_msg:
                error_msg = "Server not responding"
            elif "404" in error_msg:
                error_msg = "Notification extension not installed"
            elif "401" in error_msg or "403" in error_msg:
                error_msg = "Authentication failed"

            self.log.error(f"[Notification] {username}: '{notification_payload['message'][:50]}' ({notification_payload['type']}) - ERROR: {error_msg}")
            return {"status": "failed", "error": error_msg}


class GetUserCredentialsHandler(BaseHandler):
    """Handler for retrieving credentials of newly created users"""

    @web.authenticated
    async def post(self):
        """
        Retrieve cached credentials for newly created users (admin only)

        POST /hub/api/admin/credentials
        Body: {"usernames": ["user1", "user2", ...]}
        Returns: {"credentials": [{"username": "...", "password": "..."}, ...]}
        """
        # Admin-only permission check
        current_user = self.current_user
        if current_user is None or not current_user.admin:
            self.log.warning(f"[Get Credentials] Permission denied - admin required")
            raise web.HTTPError(403, "Only administrators can retrieve credentials")

        # Parse request body
        try:
            body = self.request.body.decode('utf-8')
            data = json.loads(body) if body else {}
            usernames = data.get('usernames', [])
        except Exception as e:
            self.log.error(f"[Get Credentials] Failed to parse request body: {e}")
            raise web.HTTPError(400, "Invalid request body")

        self.log.info(f"[Get Credentials] Admin {current_user.name} requesting credentials for: {usernames}")

        # Get credentials from cache
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
