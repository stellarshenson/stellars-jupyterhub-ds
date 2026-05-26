"""Central proxy: many owners, one process, one listener per registered user.

Per-user socket layout:

    <socket_dir>/
        <user>/
            docker.sock     <- the per-user UnixSite listener

The user-keyed subdirectory exists so the spawner can mount JUST that subdir
into the user's lab via Docker's volume-subpath mount option. Each lab sees
exactly one socket file under `/run/dockersock/docker.sock` - mount-level
isolation, no cross-user visibility, identity baked at the socket level.

`register(user, overrides)` builds a fresh `ProxyConfig` + `ProxyApp` and
binds an aiohttp `UnixSite`. Re-register replaces (so quota edits apply on
next spawn). `unregister(user)` tears down the listener and removes the
socket file + its subdirectory.
"""

import logging
import os
import shutil
from dataclasses import asdict

from aiohttp import web

from .config import ProxyConfig
from .server import create_app

log = logging.getLogger("jupyterhub.docker_proxy_manager")

SOCKET_FILENAME = "docker.sock"


def _user_dir(socket_dir, user):
    return os.path.join(socket_dir, user)


def _socket_path(socket_dir, user):
    return os.path.join(_user_dir(socket_dir, user), SOCKET_FILENAME)


def _clear_path(path):
    """Remove whatever's at `path`: file, socket, or auto-created directory."""
    try:
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.unlink(path)
    except FileNotFoundError:
        pass


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
        user_dir = _user_dir(self.socket_dir, user)
        socket_path = _socket_path(self.socket_dir, user)
        os.makedirs(user_dir, exist_ok=True)
        # Stale state at the socket path can be a leftover socket file from a
        # previous run, a regular file (unlikely), or a directory (e.g.
        # auto-created by a prior failed bind-mount). Clear it either way so
        # UnixSite can bind cleanly.
        _clear_path(socket_path)
        cfg_kwargs = {
            "owner": user,
            "listen_socket": socket_path,
            "upstream_socket": self.upstream_socket,
        }
        if overrides:
            cfg_kwargs.update(overrides)
        cfg = ProxyConfig(**cfg_kwargs)
        app = await create_app(cfg)
        runner = web.AppRunner(app)
        await runner.setup()
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
        _clear_path(cfg.listen_socket)
        # Empty per-user subdir can go too; leave it if anything else lives there.
        try:
            os.rmdir(os.path.dirname(cfg.listen_socket))
        except OSError:
            pass

    async def close(self):
        for user in list(self._listeners):
            await self._stop(user)
