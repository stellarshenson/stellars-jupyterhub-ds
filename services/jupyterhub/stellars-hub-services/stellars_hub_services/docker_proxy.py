"""In-process docker-proxy wiring.

The proxy runs inside the JupyterHub process - same asyncio event loop,
same container, no HTTP, no token, no second compose service. One module
singleton `Manager` holds N per-user `UnixSite` listeners under
`/var/run/stellars-proxy/` (a host bind mount in the hub container); each
listener is the same per-owner aiohttp app the package was already built
around.

`pre_spawn_hook` calls `register_user` directly (it's async, same loop);
`post_stop_hook` calls `unregister_user`. Quotas are re-applied on every
spawn because `pre_spawn_hook` resolves group config from the live DB
right before calling register - so admin group edits take effect on the
user's next lab start, no manual operator step.
"""

import logging
import os

log = logging.getLogger('jupyterhub.docker_proxy')

SOCK_MOUNT_DIR = '/run/dockersock'
SOCK_FILENAME = 'docker.sock'
DEFAULT_SOCKET_DIR = '/var/run/stellars-proxy'

_manager = None


def get_manager(socket_dir=DEFAULT_SOCKET_DIR):
    """Process-singleton Manager. Lazy-init on first call.

    Import is deferred so module import doesn't require stellars_docker_proxy
    to be on path (it always is in the production image; in local dev test
    suites for stellars_hub_services it doesn't need to be).
    """
    global _manager
    if _manager is None:
        from stellars_docker_proxy.manager import Manager
        _manager = Manager(socket_dir=socket_dir)
    return _manager


def docker_host_url():
    """DOCKER_HOST value pointing at the proxied socket inside the user container."""
    return f"unix://{SOCK_MOUNT_DIR}/{SOCK_FILENAME}"


def _socket_host_path(socket_dir, user):
    return os.path.join(socket_dir, f"{user}.sock")


def _build_overrides(resolved, compose_project=''):
    """Map the group_resolver dict to ProxyConfig field names."""
    overrides = {
        'max_containers': int(resolved.get('docker_limited_max_containers', 10)),
        'max_volumes': int(resolved.get('docker_limited_max_volumes', 10)),
        'max_networks': int(resolved.get('docker_limited_max_networks', 3)),
        'max_storage_gb': float(resolved.get('docker_limited_max_storage_gb', 50.0)),
        'cpu_cap_cores': float(resolved.get('docker_limited_cpu_cap_cores', 2.0)),
        'mem_cap_gb': float(resolved.get('docker_limited_mem_cap_gb', 8.0)),
    }
    if compose_project:
        overrides['compose_project'] = compose_project
    return overrides


async def register_user(username, resolved, *, socket_dir=DEFAULT_SOCKET_DIR,
                        compose_project=''):
    """Register a limited user - in-process. Idempotent: re-registers replace.

    Returns ``(socket_host_path, mount_dir, docker_host)`` so the spawn hook
    can wire `spawner.volumes` + `spawner.environment` directly. Raises on
    failure (caller logs + falls back to no docker access).
    """
    overrides = _build_overrides(resolved, compose_project=compose_project)
    mgr = get_manager(socket_dir)
    await mgr.register(username, overrides=overrides)
    socket_host_path = _socket_host_path(socket_dir, username)
    log.info(
        "registered docker-proxy for owner=%s socket=%s limits: containers=%s "
        "volumes=%s networks=%s storage_gb=%s cpu=%s mem_gb=%s compose_project=%s",
        username, socket_host_path,
        overrides['max_containers'], overrides['max_volumes'],
        overrides['max_networks'], overrides['max_storage_gb'],
        overrides['cpu_cap_cores'], overrides['mem_cap_gb'],
        compose_project or '<none>',
    )
    return socket_host_path, SOCK_MOUNT_DIR, docker_host_url()


async def unregister_user(username, *, socket_dir=DEFAULT_SOCKET_DIR):
    """Unregister a limited user (idempotent). Logs but never raises."""
    try:
        mgr = get_manager(socket_dir)
        removed = await mgr.unregister(username)
        if removed:
            log.info("unregistered docker-proxy for owner=%s", username)
    except Exception as e:
        log.warning("unregister docker-proxy for %s failed: %s", username, e)
