#!/usr/bin/env python3
"""
Custom JupyterHub API handlers for volume management and server control
"""

from jupyterhub.handlers import BaseHandler
from tornado import web
import docker
import json


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

        # Validate volume types
        valid_volumes = {'home', 'workspace', 'cache'}
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
