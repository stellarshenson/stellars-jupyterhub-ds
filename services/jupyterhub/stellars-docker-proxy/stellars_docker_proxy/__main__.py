"""Central-proxy entrypoint.

One process, N listeners. JupyterHub registers a user via the admin HTTP API;
the proxy spins up a fresh per-user listener bound to a unix socket under
`socket_dir`. Compose lifecycle (`make start`/`make stop`), not per-spawn.

Env vars:
  STELLARS_PROXY_ADMIN_TOKEN   required - bearer token gating the admin API
  STELLARS_PROXY_SOCKET_DIR    default /var/run/stellars-proxy
  STELLARS_PROXY_UPSTREAM      default /var/run/docker.sock
  STELLARS_PROXY_ADMIN_HOST    default 0.0.0.0
  STELLARS_PROXY_ADMIN_PORT    default 9000
  STELLARS_PROXY_LOG_LEVEL     default INFO
"""

import asyncio
import logging
import os
import signal

from aiohttp import web

from .admin import create_admin_app
from .manager import Manager


async def _serve():
    token = os.environ.get("STELLARS_PROXY_ADMIN_TOKEN", "").strip()
    if not token:
        raise SystemExit("STELLARS_PROXY_ADMIN_TOKEN is required")
    socket_dir = os.environ.get("STELLARS_PROXY_SOCKET_DIR", "/var/run/stellars-proxy")
    upstream = os.environ.get("STELLARS_PROXY_UPSTREAM", "/var/run/docker.sock")
    host = os.environ.get("STELLARS_PROXY_ADMIN_HOST", "0.0.0.0")
    port = int(os.environ.get("STELLARS_PROXY_ADMIN_PORT", "9000"))

    manager = Manager(socket_dir=socket_dir, upstream_socket=upstream)
    app = create_admin_app(manager, token)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logging.getLogger("jupyterhub.docker_proxy").info(
        "central-proxy admin api listening on %s:%s socket_dir=%s upstream=%s",
        host, port, socket_dir, upstream,
    )

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    try:
        await stop.wait()
    finally:
        await manager.close()
        await runner.cleanup()


def main():
    logging.basicConfig(
        level=getattr(logging, os.environ.get("STELLARS_PROXY_LOG_LEVEL", "INFO").upper(),
                      logging.INFO),
        format="[%(levelname)1.1s %(asctime)s %(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
