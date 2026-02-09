"""Handler for managing user volumes."""

import json

import docker
from jupyterhub.handlers import BaseHandler
from tornado import web

from ..docker_utils import encode_username_for_docker


class ManageVolumesHandler(BaseHandler):
    """Handler for managing user volumes."""

    async def delete(self, username):
        """Delete selected user volumes (only when server is stopped).

        DELETE /hub/api/users/{username}/manage-volumes
        Body: {"volumes": ["home", "workspace", "cache"]}
        """
        self.log.info(f"[Manage Volumes] API endpoint called for user: {username}")

        current_user = self.current_user
        if current_user is None:
            self.log.warning("[Manage Volumes] Authentication failed - no current user")
            raise web.HTTPError(403, "Not authenticated")

        self.log.info(f"[Manage Volumes] Request from user: {current_user.name}, admin: {current_user.admin}")

        if not (current_user.admin or current_user.name == username):
            self.log.warning(f"[Manage Volumes] Permission denied - user {current_user.name} attempted to manage {username}'s volumes")
            raise web.HTTPError(403, "Permission denied")

        # Parse request body
        try:
            body = self.request.body.decode('utf-8')
            data = json.loads(body) if body else {}
            requested_volumes = data.get('volumes', [])
            self.log.info(f"[Manage Volumes] Requested volumes: {requested_volumes}")
        except Exception as e:
            self.log.error(f"[Manage Volumes] Failed to parse request body: {e}")
            return self.send_error(400, "Invalid request body")

        if not requested_volumes or not isinstance(requested_volumes, list):
            self.log.warning("[Manage Volumes] No volumes specified or invalid format")
            return self.send_error(400, "No volumes specified")

        user_volume_suffixes = self.settings['stellars_config']['user_volume_suffixes']
        valid_volumes = set(user_volume_suffixes)
        invalid_volumes = set(requested_volumes) - valid_volumes
        if invalid_volumes:
            self.log.warning(f"[Manage Volumes] Invalid volume types: {invalid_volumes}")
            return self.send_error(400, f"Invalid volume types: {invalid_volumes}")

        user = self.find_user(username)
        if not user:
            self.log.warning(f"[Manage Volumes] User {username} not found")
            return self.send_error(404, "User not found")

        spawner = user.spawner
        if spawner.active:
            self.log.warning("[Manage Volumes] Server is running, cannot reset volumes")
            return self.send_error(400, "Server must be stopped before resetting volumes")

        try:
            docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        except Exception as e:
            self.log.error(f"[Manage Volumes] Failed to connect to Docker: {e}")
            return self.send_error(500, "Failed to connect to Docker daemon")

        reset_volumes = []
        failed_volumes = []

        for volume_type in requested_volumes:
            volume_name = f'jupyterlab-{encode_username_for_docker(username)}_{volume_type}'
            self.log.info(f"[Manage Volumes] Processing volume: {volume_name}")

            try:
                volume = docker_client.volumes.get(volume_name)
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

        response = {
            "message": f"Successfully reset {len(reset_volumes)} volume(s)",
            "reset_volumes": reset_volumes,
            "failed_volumes": failed_volumes,
        }

        self.log.info(f"[Manage Volumes] Operation complete: {len(reset_volumes)} reset, {len(failed_volumes)} failed")
        self.set_status(200)
        self.finish(response)
