"""Central proxy: many owners, one process, one listener per registered user.

The package's `create_app` builds an aiohttp app bound to a single owner's
ProxyConfig. The Manager wraps that with a registration model: `register(user,
quotas)` instantiates a fresh ProxyConfig + ProxyApp, binds a `UnixSite` to a
per-user socket path under `socket_dir`, and tracks the runner so it can be torn
down on `unregister(user)`. The result is N listeners in one process - the
JupyterHub sidecar pattern collapsed into a single container.

Identity stays baked-at-socket: whichever container mounts the per-user socket
file acts as that user. No tokens, no per-request headers, no auth on the data
path - the data path is identical to the per-sidecar layout the package was
designed for. The HTTP admin API (see admin.py) is the only privileged surface.
"""

import asyncio
import logging
import os
from dataclasses import asdict

from aiohttp import web

from .config import ProxyConfig
from .server import create_app

log = logging.getLogger("jupyterhub.docker_proxy_manager")


def _socket_path(socket_dir, user):
    return os.path.join(socket_dir, f"{user}.sock")


class Manager:
    """Owns a dict of `user -> (AppRunner, UnixSite, ProxyConfig)` listeners.

    All methods are async because aiohttp's runner + site setup/teardown are
    coroutines. The manager is not thread-safe; the admin app is single-event-
    loop so concurrent register/unregister for the same user is serialised by
    aiohttp's request dispatcher.
    """

    def __init__(self, socket_dir, upstream_socket="/var/run/docker.sock"):
        self.socket_dir = socket_dir
        self.upstream_socket = upstream_socket
        self._listeners = {}
        os.makedirs(socket_dir, exist_ok=True)

    def registered(self):
        return [
            {"user": user, "socket_path": _socket_path(self.socket_dir, user),
             "config": asdict(cfg)}
            for user, (_runner, _site, cfg) in self._listeners.items()
        ]

    def is_registered(self, user):
        return user in self._listeners

    async def register(self, user, overrides=None):
        """Idempotent: re-register replaces the previous listener (so quotas
        can be updated by calling register again with new overrides).
        """
        if not user:
            raise ValueError("user is required")
        if user in self._listeners:
            await self._stop(user)
        cfg_kwargs = {
            "owner": user,
            "listen_socket": _socket_path(self.socket_dir, user),
            "upstream_socket": self.upstream_socket,
        }
        if overrides:
            cfg_kwargs.update(overrides)
        cfg = ProxyConfig(**cfg_kwargs)
        app = await create_app(cfg)
        runner = web.AppRunner(app)
        await runner.setup()
        try:
            os.unlink(cfg.listen_socket)
        except FileNotFoundError:
            pass
        site = web.UnixSite(runner, cfg.listen_socket)
        await site.start()
        os.chmod(cfg.listen_socket, cfg.socket_mode)
        self._listeners[user] = (runner, site, cfg)
        log.info(
            "registered user=%s listen=%s limits: containers=%s volumes=%s "
            "networks=%s storage_gb=%s cpu=%s mem_gb=%s compose_project=%s",
            user, cfg.listen_socket,
            cfg.max_containers, cfg.max_volumes, cfg.max_networks,
            cfg.max_storage_gb, cfg.cpu_cap_cores, cfg.mem_cap_gb,
            cfg.compose_project or "<none>",
        )
        return cfg.listen_socket

    async def unregister(self, user):
        """Idempotent: returns True if a listener was torn down, False if not
        registered."""
        if user not in self._listeners:
            return False
        await self._stop(user)
        log.info("unregistered user=%s", user)
        return True

    async def _stop(self, user):
        runner, _site, cfg = self._listeners.pop(user)
        await runner.cleanup()
        try:
            os.unlink(cfg.listen_socket)
        except FileNotFoundError:
            pass

    async def close(self):
        for user in list(self._listeners):
            await self._stop(user)
