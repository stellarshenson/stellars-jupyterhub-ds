"""Per-user Docker proxy sidecar orchestration.

For a "limited docker" user, ensure a `stellars-docker-proxy` sidecar is running
that vends an owner-scoped Docker socket on a shared volume, and return the
wiring the spawner needs (volume name, mount dir, DOCKER_HOST). The sidecar runs
from the hub's own image (which has `stellars_docker_proxy` installed). None of
the proxy filtering logic lives here - this only launches and points at it.
"""

import logging
import socket as _socket

log = logging.getLogger('stellars_hub.docker_proxy')

SOCK_MOUNT_DIR = '/run/dockersock'
SOCK_FILENAME = 'docker.sock'
HOST_DOCKER_SOCK = '/var/run/docker.sock'


def docker_host_url():
    """DOCKER_HOST value pointing at the proxied socket inside the user container."""
    return f"unix://{SOCK_MOUNT_DIR}/{SOCK_FILENAME}"


def _client():
    import docker
    return docker.DockerClient(base_url='unix://var/run/docker.sock')


def detect_self_image(client=None):
    """Best-effort: the hub's own image tag, used to run the sidecar.

    Returns None on failure - the caller treats that as "limited proxy
    unavailable" and skips wiring rather than failing the spawn.
    """
    try:
        client = client or _client()
        container = client.containers.get(_socket.gethostname())
        tags = container.image.tags
        return tags[0] if tags else container.image.id
    except Exception as e:
        log.warning("could not detect hub image for docker-proxy sidecar: %s", e)
        return None


def _names(name_base):
    return f"jupyterlab-{name_base}_dockersock", f"jupyterlab-{name_base}-dockerproxy"


def ensure_user_proxy(username, name_base, resolved, *, proxy_image,
                      network_name, compose_project='', client=None):
    """Ensure the per-user proxy sidecar and its socket volume are running.

    Returns (volume_name, mount_dir, docker_host). Raises on hard failure; the
    caller decides whether to fail the spawn or fall back to no docker access.
    """
    client = client or _client()
    vol_name, proxy_name = _names(name_base)

    try:
        client.volumes.get(vol_name)
    except Exception:
        client.volumes.create(
            name=vol_name,
            labels={'stellars.managed': 'true', 'stellars.owner': username},
        )

    # Reuse an existing sidecar (start it if stopped) so we don't churn it on
    # every spawn; config changes take effect after it is removed and recreated.
    try:
        existing = client.containers.get(proxy_name)
        if existing.status != 'running':
            existing.start()
        return vol_name, SOCK_MOUNT_DIR, docker_host_url()
    except Exception:
        pass

    command = [
        'python', '-m', 'stellars_docker_proxy',
        '--owner', username,
        '--listen-socket', f"{SOCK_MOUNT_DIR}/{SOCK_FILENAME}",
        '--upstream-socket', HOST_DOCKER_SOCK,
        '--max-containers', str(resolved['docker_limited_max_containers']),
        '--max-volumes', str(resolved['docker_limited_max_volumes']),
        '--max-networks', str(resolved['docker_limited_max_networks']),
        '--max-storage-gb', str(resolved['docker_limited_max_storage_gb']),
        '--cpu-cap-cores', str(resolved['docker_limited_cpu_cap_cores']),
        '--mem-cap-gb', str(resolved['docker_limited_mem_cap_gb']),
    ]
    if compose_project:
        command += ['--compose-project', compose_project]

    labels = {
        'stellars.managed': 'true',
        'stellars.owner': username,
        'stellars.role': 'docker-proxy',
    }
    if compose_project:
        labels['com.docker.compose.project'] = compose_project

    client.containers.run(
        proxy_image,
        command=command,
        name=proxy_name,
        detach=True,
        network=network_name,
        restart_policy={'Name': 'unless-stopped'},
        volumes={
            HOST_DOCKER_SOCK: {'bind': HOST_DOCKER_SOCK, 'mode': 'rw'},
            vol_name: {'bind': SOCK_MOUNT_DIR, 'mode': 'rw'},
        },
        labels=labels,
    )
    log.info("started docker-proxy sidecar %s for owner=%s", proxy_name, username)
    return vol_name, SOCK_MOUNT_DIR, docker_host_url()


def stop_user_proxy(name_base, client=None):
    """Stop and remove a user's proxy sidecar (on server stop / cleanup).

    User-created containers are independent of the sidecar and keep running; the
    proxy is recreated on the next spawn.
    """
    try:
        client = client or _client()
        _, proxy_name = _names(name_base)
        client.containers.get(proxy_name).remove(force=True)
        log.info("removed docker-proxy sidecar %s", proxy_name)
    except Exception:
        pass
