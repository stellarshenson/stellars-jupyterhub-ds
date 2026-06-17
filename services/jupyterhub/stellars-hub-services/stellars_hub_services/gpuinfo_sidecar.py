"""Hub-managed GPU-info sidecar lifecycle.

The hub starts the ``gpuinfo-nvidia`` sidecar itself (it already holds the docker
socket and uses ``runtime=nvidia`` via the SDK for GPU detection) instead of
relying on the compose orchestration to bring it up - so it works the same no
matter which compose project launched the hub.

Idempotent and best-effort: reuse a running container, start a stopped one,
create a missing one; any failure degrades to GPU-off (``gpu_client`` /
``gpu_cache`` already tolerate an unreachable sidecar). The sidecar runs on a
dedicated network that the hub joins, so spawned user labs cannot reach it.
"""

import logging
import socket
from urllib.parse import urlparse

log = logging.getLogger('jupyterhub')

_SIDECAR_ENV = {
    'NVIDIA_VISIBLE_DEVICES': 'all',
    'NVIDIA_DRIVER_CAPABILITIES': 'utility',
    'GPUINFO_PORT': '8000',
}


def container_name_from_url(url):
    """Derive the sidecar container name (= DNS name) from its URL host."""
    return urlparse(url).hostname or 'gpuinfo-nvidia'


def _connect_hub(client, network):
    """Attach the hub's own container to the network (idempotent)."""
    try:
        hub = client.containers.get(socket.gethostname())  # Docker sets HOSTNAME to the container id
    except Exception:
        return
    try:
        network.connect(hub)
        log.info(f"[GPUInfo] connected hub to network {network.name}")
    except Exception:
        pass  # already connected (409) or transient - non-fatal


def ensure_gpuinfo_sidecar(image, network_name, url, compose_project=''):
    """Ensure the GPU-info sidecar container is running. Never raises.

    Returns True if the sidecar ends up running (reused, started, or created),
    False if docker is unavailable or anything failed - the caller uses that to
    decide whether to even probe (and to fall back to last-known GPU state).

    The container + network are stamped with the same compose-project labels the
    spawned user containers get (see hooks.py), so the hub-started sidecar belongs
    to the compose project (shows in `docker compose ps`) rather than running as a
    standalone container.
    """
    import docker

    name = container_name_from_url(url)
    project_labels = {'com.docker.compose.project': compose_project} if compose_project else {}
    container_labels = dict(project_labels)
    if compose_project:
        container_labels.update({
            'com.docker.compose.service': name,
            'com.docker.compose.container-number': '1',
            'com.docker.compose.oneoff': 'False',
        })
    try:
        client = docker.DockerClient('unix://var/run/docker.sock')
    except Exception as e:
        log.warning(f"[GPUInfo] docker unavailable; sidecar not started: {e}")
        return False

    running = False
    try:
        # 1. dedicated network (create if absent), then join the hub to it.
        try:
            network = client.networks.get(network_name)
        except docker.errors.NotFound:
            network = client.networks.create(network_name, driver='bridge', labels=(project_labels or None))
            log.info(f"[GPUInfo] created network {network_name}")
        _connect_hub(client, network)

        # 2. reuse / start / create the sidecar container.
        try:
            c = client.containers.get(name)
            if c.status != 'running':
                c.start()
                log.info(f"[GPUInfo] started existing sidecar '{name}'")
            else:
                log.info(f"[GPUInfo] sidecar '{name}' already running")
            return True
        except docker.errors.NotFound:
            pass

        client.containers.run(
            image=image,
            name=name,
            detach=True,
            restart_policy={'Name': 'unless-stopped'},
            runtime='nvidia',
            environment=dict(_SIDECAR_ENV),
            network=network_name,
            labels=container_labels,
        )
        log.info(f"[GPUInfo] created sidecar '{name}' from {image} on {network_name}")
        running = True
    except Exception as e:
        log.warning(f"[GPUInfo] could not ensure sidecar: {e}")
    finally:
        try:
            client.close()
        except Exception:
            pass
    return running
