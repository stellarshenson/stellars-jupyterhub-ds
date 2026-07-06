"""Handler for restarting user servers."""

import asyncio
import time

import docker
from jupyterhub.handlers import BaseHandler
from tornado import web

from ..docker_utils import get_docker_client, get_executor, lab_container_name


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
            raise web.HTTPError(404, "User not found")

        spawner = user.spawner
        if not spawner.active:
            self.log.warning("[Restart Server] Server is not running, cannot restart")
            raise web.HTTPError(400, "Server is not running")

        container_name = lab_container_name(username)

        try:
            docker_client = get_docker_client()
        except Exception as e:
            self.log.error(f"[Restart Server] Failed to connect to Docker: {e}")
            raise web.HTTPError(500, "Failed to connect to Docker daemon")

        # container.restart() blocks up to 10s+; run the Docker calls on the shared
        # executor so one user's restart can't freeze the hub event loop for every
        # other user. Tornado response I/O and error mapping stay on the loop.
        def _restart():
            container = docker_client.containers.get(container_name)
            # [Timing] probes around container.restart() so the operator can
            # see in the hub log how long the Docker-side restart took. The
            # full user-visible restart includes additional lab-boot time on
            # top of this duration; the home.html poll observes that part.
            self.log.info(
                "[Timing] container.restart() called user=%s container=%s",
                username,
                container_name,
            )
            t0 = time.perf_counter()
            try:
                container.restart(timeout=10)
            finally:
                self.log.info(
                    "[Timing] container.restart() returned in %.3fs user=%s",
                    time.perf_counter() - t0,
                    username,
                )

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(get_executor(), _restart)
            self.log.info(f"[Restart Server] Container {container_name} successfully restarted for user {username}")
            self.set_status(200)
            self.finish({"message": f"Container {container_name} successfully restarted"})
        except docker.errors.NotFound:
            self.log.warning(f"[Restart Server] Container {container_name} not found")
            raise web.HTTPError(404, f"Container {container_name} not found")
        except docker.errors.APIError as e:
            self.log.error(f"[Restart Server] Failed to restart container {container_name}: {e}")
            raise web.HTTPError(500, f"Failed to restart container: {str(e)}")
        finally:
            docker_client.close()


class ServerLogsHandler(BaseHandler):
    """Tail a spawned container's logs (admin-or-self).

    GET /hub/api/users/{username}/server/logs?tail=15 -> {"lines": [...]}

    Backs the Start-server page's live log feed (the spawn-progress SSE carries
    status text, not container stdout/stderr). Bounded tail only - never the full
    log. 403 for a non-owner non-admin; 404 while the container does not exist yet
    (the page shows a "waiting for container" placeholder until it appears).
    """

    _DEFAULT_TAIL = 15
    _MAX_TAIL = 200

    @web.authenticated
    async def get(self, username):
        current_user = self.current_user
        if current_user is None or not (current_user.admin or current_user.name == username):
            raise web.HTTPError(403, "Permission denied")

        try:
            tail = int(self.get_argument('tail', str(self._DEFAULT_TAIL)))
        except (TypeError, ValueError):
            tail = self._DEFAULT_TAIL
        tail = max(1, min(self._MAX_TAIL, tail))

        container_name = lab_container_name(username)
        try:
            docker_client = get_docker_client()
        except Exception as e:
            self.log.error(f"[Server Logs] Failed to connect to Docker: {e}")
            raise web.HTTPError(500, "Failed to connect to Docker daemon")

        # container.logs() is a blocking Docker read; offload it to the shared
        # executor so a slow log fetch can't freeze the hub loop. The response
        # write stays on the loop.
        def _read_logs():
            container = docker_client.containers.get(container_name)
            raw = container.logs(tail=tail, stdout=True, stderr=True, timestamps=False)
            text = raw.decode('utf-8', errors='replace') if isinstance(raw, (bytes, bytearray)) else str(raw)
            return text.splitlines()[-tail:]

        loop = asyncio.get_event_loop()
        try:
            lines = await loop.run_in_executor(get_executor(), _read_logs)
            self.finish({"lines": lines})
        except docker.errors.NotFound:
            raise web.HTTPError(404, "Container not found")
        except docker.errors.APIError as e:
            self.log.error(f"[Server Logs] Failed to read logs for {container_name}: {e}")
            raise web.HTTPError(500, "Failed to read container logs")
        finally:
            docker_client.close()
