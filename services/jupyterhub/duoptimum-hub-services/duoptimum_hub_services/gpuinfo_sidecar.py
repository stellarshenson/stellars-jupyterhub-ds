"""Hub-managed GPU-info sidecar lifecycle.

The hub starts the ``gpuinfo-nvidia`` sidecar itself (it already holds the docker
socket and uses ``runtime=nvidia`` via the SDK for GPU detection) instead of
relying on the compose orchestration to bring it up - so it works the same no
matter which compose project launched the hub.

Recreate-fresh and best-effort: every hub boot removes any pre-existing sidecar
and creates a new one from the CURRENT image (so a rebuilt image is always picked
up and a container that survived a hard hub SIGKILL is never reused stale); any
failure degrades to GPU-off (``gpu_client`` / ``gpu_cache`` already tolerate an
unreachable sidecar). The sidecar runs on a dedicated network that the hub joins,
so spawned user labs cannot reach it.
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
    """Sidecar DNS host parsed from its URL - the fallback name only when no
    explicit container name is configured (no hardcoded default)."""
    return urlparse(url).hostname if url else None


def _find_hub_container(client):
    """Find the hub's own container. Docker normally sets HOSTNAME to the short
    container id, so containers.get(hostname) resolves it - but an explicit compose
    `hostname:` (e.g. `jupyterhub`) overrides HOSTNAME, and then get() raises
    NotFound and the hub silently never joins the sidecar network. Fall back to
    matching Config.Hostname, which equals socket.gethostname() in both cases."""
    host = socket.gethostname()
    try:
        return client.containers.get(host)
    except Exception:
        pass
    try:
        for c in client.containers.list():
            if (c.attrs.get('Config') or {}).get('Hostname') == host:
                return c
    except Exception:
        pass
    return None


def _connect_hub(client, network):
    """Attach the hub's own container to the network (idempotent)."""
    hub = _find_hub_container(client)
    if hub is None:
        log.warning(f"[GPUInfo] could not identify the hub container; not joined to network {network.name}")
        return
    try:
        network.connect(hub)
        log.info(f"[GPUInfo] connected hub to network {network.name}")
    except Exception:
        pass  # already connected (409) or transient - non-fatal


def ensure_gpuinfo_sidecar(image, network_name, url, compose_project='', container_name=None):
    """Ensure the GPU-info sidecar container is running. Never raises.

    Returns True if the sidecar ends up running (reused, started, or created),
    False if docker is unavailable or anything failed - the caller uses that to
    decide whether to even probe (and to fall back to last-known GPU state).

    ``container_name`` is the explicit sidecar name (= its DNS name on the
    network); it falls back to the URL host only when not supplied, and the
    sidecar is skipped (GPU off) if neither yields a name - never a hardcoded one.

    The container + network are stamped with the same compose-project labels the
    spawned user containers get (see hooks.py), so the hub-started sidecar belongs
    to the compose project (shows in `docker compose ps`) rather than running as a
    standalone container.
    """
    import docker

    name = container_name or container_name_from_url(url)
    if not name:
        log.warning(
            "[GPUInfo] no sidecar container name configured "
            "(JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME) and none derivable from the URL; "
            "sidecar not started - GPU off"
        )
        return False
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

        # 2. recreate fresh: remove any pre-existing sidecar (a clean hub stop
        # already removes it via stop_gpuinfo_sidecar, but a hard SIGKILL can leave
        # one behind), then create a new one below - so the hub ALWAYS (re)creates
        # the sidecar from the CURRENT image, never reuses a stale container.
        try:
            client.containers.get(name).remove(force=True)
            log.info(f"[GPUInfo] removed pre-existing sidecar '{name}' to recreate fresh")
        except docker.errors.NotFound:
            pass

        # Don't let containers.run auto-pull a missing image - a cold/absent image
        # would block hub boot on a registry pull (the very stall this self-start
        # exists to avoid). If it isn't present locally, degrade to GPU-off; the
        # caller skips the probe and seeds the UI from last-known inventory.
        try:
            client.images.get(image)
        except docker.errors.ImageNotFound:
            log.warning(f"[GPUInfo] image '{image}' not present locally; not pulling at boot - GPU off until available")
            return False

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


def stop_gpuinfo_sidecar(url, container_name=None):
    """Stop + remove the GPU-info sidecar. Never raises.

    Registered as the hub's at-exit cleanup so the hub-managed sidecar does not
    outlive its parent: when the hub stops, the sidecar stops too, instead of
    lingering as an orphaned container (compose `down` leaves it untouched - the
    hub owns it, not compose). Removing rather than only stopping also means the
    next hub boot recreates it fresh from the current image (so a rebuilt image
    is always picked up, never a stale reused container). Best-effort: a hard
    SIGKILL of the hub skips this, leaving the `unless-stopped` policy to keep
    the sidecar until the next clean cycle.
    """
    import docker

    name = container_name or container_name_from_url(url)
    if not name:
        return
    try:
        client = docker.DockerClient('unix://var/run/docker.sock')
    except Exception:
        return
    try:
        client.containers.get(name).remove(force=True)
        log.info(f"[GPUInfo] removed sidecar '{name}' on hub shutdown")
    except docker.errors.NotFound:
        pass
    except Exception as e:
        log.warning(f"[GPUInfo] could not stop sidecar on shutdown: {e}")
    finally:
        try:
            client.close()
        except Exception:
            pass
