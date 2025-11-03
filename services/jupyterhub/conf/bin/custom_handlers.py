#!/usr/bin/env python3
"""
Custom JupyterHub API handlers for volume management and server control
"""

from jupyterhub.handlers import BaseHandler
from jupyterhub.utils import admin_or_self
import docker


class ResetHomeVolumeHandler(BaseHandler):
    """Handler for resetting user home volumes"""

    @admin_or_self
    async def delete(self, username):
        """
        Delete a user's home volume (only when server is stopped)

        DELETE /hub/api/users/{username}/reset-home-volume
        """
        # 1. Verify user exists
        user = self.find_user(username)
        if not user:
            self.log.warning(f"Reset volume request failed: user {username} not found")
            return self.send_error(404, "User not found")

        # 2. Check server is stopped
        spawner = user.spawner
        if spawner.active:
            self.log.warning(f"Reset volume request failed: {username}'s server is running")
            return self.send_error(400, "Server must be stopped before resetting volume")

        # 3. Connect to Docker
        try:
            docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        except Exception as e:
            self.log.error(f"Failed to connect to Docker: {e}")
            return self.send_error(500, "Failed to connect to Docker daemon")

        # 4. Verify volume exists
        volume_name = f'jupyterlab-{username}_home'
        try:
            volume = docker_client.volumes.get(volume_name)
        except docker.errors.NotFound:
            self.log.warning(f"Volume {volume_name} not found")
            return self.send_error(404, f"Volume {volume_name} not found")
        except Exception as e:
            self.log.error(f"Error checking volume {volume_name}: {e}")
            return self.send_error(500, f"Failed to check volume: {str(e)}")

        # 5. Remove volume
        try:
            volume.remove()
            self.log.info(f"Successfully removed volume {volume_name} for user {username}")
            self.set_status(200)
            self.finish({"message": f"Volume {volume_name} successfully reset"})
        except docker.errors.APIError as e:
            self.log.error(f"Failed to remove volume {volume_name}: {e}")
            return self.send_error(500, f"Failed to remove volume: {str(e)}")
        finally:
            docker_client.close()


class RestartServerHandler(BaseHandler):
    """Handler for restarting user servers"""

    @admin_or_self
    async def post(self, username):
        """
        Restart a user's server using Docker container restart

        POST /hub/api/users/{username}/restart-server
        """
        # 1. Verify user exists
        user = self.find_user(username)
        if not user:
            self.log.warning(f"Restart server request failed: user {username} not found")
            return self.send_error(404, "User not found")

        # 2. Check server is running
        spawner = user.spawner
        if not spawner.active:
            self.log.warning(f"Restart server request failed: {username}'s server is not running")
            return self.send_error(400, "Server is not running")

        # 3. Get container name from spawner
        container_name = f'jupyterlab-{username}'

        # 4. Connect to Docker and restart container
        try:
            docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        except Exception as e:
            self.log.error(f"Failed to connect to Docker: {e}")
            return self.send_error(500, "Failed to connect to Docker daemon")

        try:
            # Get the container
            container = docker_client.containers.get(container_name)

            # Restart the container (graceful restart with 10s timeout)
            self.log.info(f"Restarting container {container_name} for user {username}")
            container.restart(timeout=10)

            self.log.info(f"Successfully restarted container {container_name}")
            self.set_status(200)
            self.finish({"message": f"Container {container_name} successfully restarted"})
        except docker.errors.NotFound:
            self.log.warning(f"Container {container_name} not found")
            return self.send_error(404, f"Container {container_name} not found")
        except docker.errors.APIError as e:
            self.log.error(f"Failed to restart container {container_name}: {e}")
            return self.send_error(500, f"Failed to restart container: {str(e)}")
        finally:
            docker_client.close()
