"""Central docker-proxy wiring (admin HTTP client).

The proxy is one container in the compose stack (`stellars-docker-proxy`)
running `python -m stellars_docker_proxy`. JupyterHub registers a limited user
on `pre_spawn_hook` (creates a per-user listener inside the proxy + a socket
file under a shared host directory) and unregisters on `post_stop_hook`. The
user's lab gets a single file-bind from `<host_socket_dir>/<user>.sock` to
`/run/dockersock/docker.sock` plus `DOCKER_HOST=unix:///run/dockersock/docker.sock`.

No per-user container is started by the hub. The package's admin API is the
only privileged surface; the data path (per-user unix sockets) is identical to
the previous sidecar layout.
"""

import asyncio
import logging
import os

import aiohttp

log = logging.getLogger('jupyterhub.docker_proxy')

SOCK_MOUNT_DIR = '/run/dockersock'
SOCK_FILENAME = 'docker.sock'

DEFAULT_ADMIN_URL = 'http://stellars-docker-proxy:9000'
DEFAULT_SOCKET_DIR = '/var/run/stellars-proxy'


def docker_host_url():
    """DOCKER_HOST value pointing at the proxied socket inside the user container."""
    return f"unix://{SOCK_MOUNT_DIR}/{SOCK_FILENAME}"


def _socket_host_path(socket_dir, user):
    return os.path.join(socket_dir, f"{user}.sock")


def _build_overrides(resolved, compose_project=''):
    """Map the resolver dict to ProxyConfig field names the admin API accepts."""
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


async def _post_register(admin_url, token, user, overrides, timeout=10):
    url = f"{admin_url.rstrip('/')}/admin/registered/{user}"
    headers = {'Authorization': f'Bearer {token}'}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as s:
        async with s.post(url, json={'overrides': overrides}, headers=headers) as r:
            if r.status != 200:
                body = await r.text()
                raise RuntimeError(f"register {user}: HTTP {r.status}: {body[:200]}")
            return await r.json()


async def _delete_register(admin_url, token, user, timeout=10):
    url = f"{admin_url.rstrip('/')}/admin/registered/{user}"
    headers = {'Authorization': f'Bearer {token}'}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as s:
        async with s.delete(url, headers=headers) as r:
            if r.status != 200:
                body = await r.text()
                raise RuntimeError(f"unregister {user}: HTTP {r.status}: {body[:200]}")
            return await r.json()


def register_user(username, resolved, *, admin_url, admin_token, socket_dir,
                  compose_project=''):
    """Register a limited user with the central proxy. Synchronous wrapper.

    Returns ``(socket_host_path, mount_dir, docker_host)`` so the spawn hook
    can wire `spawner.volumes` and `spawner.environment` directly.
    """
    overrides = _build_overrides(resolved, compose_project=compose_project)
    asyncio.run(_post_register(admin_url, admin_token, username, overrides))
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


def unregister_user(username, *, admin_url, admin_token):
    """Unregister a limited user (idempotent). Logs but never raises."""
    try:
        asyncio.run(_delete_register(admin_url, admin_token, username))
        log.info("unregistered docker-proxy for owner=%s", username)
    except Exception as e:
        log.warning("unregister docker-proxy for %s failed: %s", username, e)
