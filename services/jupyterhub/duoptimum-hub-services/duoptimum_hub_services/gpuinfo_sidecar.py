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

# Sidecar runtime env (NVIDIA_VISIBLE_DEVICES, NVIDIA_DRIVER_CAPABILITIES, GPUINFO_PORT),
# port + command baked into sidecar IMAGE (services/jupyterhub/gpuinfo-nvidia/Dockerfile).
# Image = single source of truth for sidecar's own spec; hub does not re-declare here (no
# env to containers.run). Hub only orchestrates: net, name, labels, conditional runtime,
# recreate, teardown.


def container_name_from_url(url):
    """Sidecar DNS host parsed from its URL - the fallback name only when no
    explicit container name is configured (no hardcoded default)."""
    return urlparse(url).hostname if url else None


def resolve_gpuinfo_url(url, hostname):
    """Substitute the ``{hostname}`` placeholder in the sidecar URL template with the
    runtime-discovered sidecar address, so the host is never hardcoded in the URL. A
    URL without the placeholder passes through unchanged; an empty hostname leaves the
    placeholder in place (degrades to an unreachable host)."""
    if url and hostname:
        return url.replace('{hostname}', hostname)
    return url


def _sidecar_host(container, network_name):
    """The sidecar's address on the dedicated network, read from the LIVE container -
    never a hardcoded host. Primary is its IP on that network (assigned by docker at
    create time); the fallback is the container's own name (docker's embedded DNS
    resolves it on a user-defined network) if the IP isn't populated yet. Returns
    None if neither can be read, which the caller treats as "sidecar unreachable"."""
    try:
        container.reload()
        nets = (container.attrs.get('NetworkSettings') or {}).get('Networks') or {}
        ip = (nets.get(network_name) or {}).get('IPAddress')
        if ip:
            return ip
    except Exception:
        pass
    try:
        return container.name
    except Exception:
        return None


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


def ensure_gpuinfo_sidecar(image, network_name, url, compose_project='', container_name=None,
                           container_role_label_key='', container_role_label_value=''):
    """Ensure the GPU-info sidecar container is running. Never raises.

    Returns the sidecar base URL with the ``{hostname}`` placeholder filled in from the
    address the hub DISCOVERS for the container it just created (its IP on the
    dedicated network, read from the live container - never a hardcoded host), so
    the URL always points at the real running sidecar. Returns '' if docker is
    unavailable, the image is absent, or anything failed - the caller treats the
    empty string as "sidecar not up" (skip the probe, fall back to last-known GPU
    state). ``url`` is the template (e.g. ``http://{hostname}:8000``); a literal URL
    with no placeholder is returned unchanged.

    ``container_name`` is the name the hub gives the sidecar it creates (and finds /
    removes it by); it falls back to the URL host only when not supplied, and the
    sidecar is skipped (GPU off) if neither yields a name - never a hardcoded one.

    Dedicated net DECLARED in compose.yml (compose owns/creates it; hub discovers it by
    duoptimum-hub.network.role=gpuinfo and only joins - never creates here). Container stamped
    with the same compose-project labels spawned user containers get (see hooks.py) plus
    its container-role label (container_role_label_key/_value, e.g.
    duoptimum-hub.container.role=gpuinfo) - sidecar belongs to the compose project (shows in
    `docker compose ps`), discoverable by role. Sidecar's own runtime spec (NVIDIA env,
    port, command) comes from the image, not here.
    """
    import docker

    name = container_name or container_name_from_url(url)
    if not name:
        log.warning(
            "[GPUInfo] no sidecar container name configured "
            "(JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME) and none derivable from the URL; "
            "sidecar not started - GPU off"
        )
        return ""
    if not network_name:
        log.warning(
            "[GPUInfo] no hub<->sidecar network resolved (the labelled network declared "
            "in compose.yml was not found); sidecar not started - GPU off"
        )
        return ""
    project_labels = {'com.docker.compose.project': compose_project} if compose_project else {}
    container_labels = dict(project_labels)
    if compose_project:
        container_labels.update({
            'com.docker.compose.service': name,
            'com.docker.compose.container-number': '1',
            'com.docker.compose.oneoff': 'False',
        })
    # Container role label (e.g. duoptimum-hub.container.role=gpuinfo), mirrored from the
    # compose service decl - lets future code discover gpuinfo containers by role.
    if container_role_label_key and container_role_label_value:
        container_labels[container_role_label_key] = container_role_label_value
    try:
        client = docker.DockerClient('unix://var/run/docker.sock')
    except Exception as e:
        log.warning(f"[GPUInfo] docker unavailable; sidecar not started: {e}")
        return ""

    resolved = ""
    try:
        # 1. dedicated network: compose DECLARES and creates it (labelled, discovered
        # by the hub) - the hub never creates it here (that historically clashed with
        # compose's own "not created by compose" ownership check). Just join the hub to
        # the existing network; if it is missing, compose did not bring it up, so degrade
        # to GPU-off rather than recreating a network compose would then reject.
        try:
            network = client.networks.get(network_name)
        except docker.errors.NotFound:
            log.warning(f"[GPUInfo] network '{network_name}' not found (declared in compose.yml?); sidecar not started - GPU off")
            return ""
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
            return ""

        # Request the nvidia runtime only when the docker host actually registers it.
        # A real sidecar needs it for GPU access, but asking for an unregistered runtime
        # just fails the run; on a host without it there are no GPUs anyway (a real
        # sidecar reports none) and a mock sidecar still starts (used by the functional
        # tests, which run the mock on any host).
        run_kwargs = {}
        try:
            if 'nvidia' in ((client.info() or {}).get('Runtimes') or {}):
                run_kwargs['runtime'] = 'nvidia'
        except Exception:
            pass
        container = client.containers.run(
            image=image,
            name=name,
            detach=True,
            restart_policy={'Name': 'unless-stopped'},
            network=network_name,
            labels=container_labels,
            **run_kwargs,
        )
        # Discover the sidecar's address at runtime (its IP on the dedicated network,
        # read from the live container) and fill it into the URL - the host is never
        # hardcoded. If we cannot determine an address the sidecar is unreachable, so
        # report "not up" (empty) and let the caller fall back to last-known/off.
        host = _sidecar_host(container, network_name)
        if host:
            resolved = resolve_gpuinfo_url(url, host)
            log.info(f"[GPUInfo] created sidecar '{name}' from {image} on {network_name}; reachable at {host} -> {resolved}")
        else:
            log.warning(f"[GPUInfo] created sidecar '{name}' but could not determine its address; GPU off")
    except Exception as e:
        log.warning(f"[GPUInfo] could not ensure sidecar: {e}")
    finally:
        try:
            client.close()
        except Exception:
            pass
    return resolved


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
