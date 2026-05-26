"""Handler for restarting user servers."""

import docker
from jupyterhub.handlers import BaseHandler
from tornado import web

from ..docker_utils import encode_username_for_docker


class RestartServerHandler(BaseHandler):
    """Handler for restarting user servers."""

    async def post(self, username):
        """Restart a user's server using Docker container restart.

        POST /hub/api/users/{username}/restart-server
        """
        self.log.info(f"[Restart Server] API endpoint called for user: {username}")

        current_user = self.current_user
        if current_user is None:
            self.log.warning("[Restart Server] Authentication failed - no current user")
            raise web.HTTPError(403, "Not authenticated")

        if not (current_user.admin or current_user.name == username):
            self.log.warning(f"[Restart Server] Permission denied - user {current_user.name} attempted to restart {username}'s server")
            raise web.HTTPError(403, "Permission denied")

        user = self.find_user(username)
        if not user:
            self.log.warning(f"[Restart Server] User {username} not found")
            return self.send_error(404, "User not found")

        spawner = user.spawner
        if not spawner.active:
            self.log.warning("[Restart Server] Server is not running, cannot restart")
            return self.send_error(400, "Server is not running")

        container_name = f'jupyterlab-{encode_username_for_docker(username)}'

        try:
            docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        except Exception as e:
            self.log.error(f"[Restart Server] Failed to connect to Docker: {e}")
            return self.send_error(500, "Failed to connect to Docker daemon")

        try:
            container = docker_client.containers.get(container_name)
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
