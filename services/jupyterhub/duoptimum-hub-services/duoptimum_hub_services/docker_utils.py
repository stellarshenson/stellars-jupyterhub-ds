"""Docker utility functions for container and volume operations."""

import asyncio
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

_docker_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="docker-ops")


def encode_username_for_docker(username):
    """Encode username for Docker volume/container names.

    Uses escapism library (same as DockerSpawner) for compatibility.
    e.g., 'user.name' -> 'user-2ename' (. = ASCII 46 = 0x2e)
    """
    from escapism import escape
    return escape(username, escape_char='-').lower()


def derive_cpu_assignment(hostcfg, online_cpus):
    """Assigned CPU cores and whether it is an explicit limit, from a container's
    HostConfig. A DockerSpawner ``cpu_limit`` sets ``NanoCpus`` (billionths of a
    core); a cgroup cfs quota sets ``CpuQuota`` / ``CpuPeriod``. Either means the
    user is capped, so the bar measures against that ceiling. With neither, the
    assignment is the host cores the container may use (no limit).

    Returns ``(cores, limited)``. Pure - unit-tested independently of Docker.
    """
    nano_cpus = hostcfg.get('NanoCpus') or 0
    cpu_quota = hostcfg.get('CpuQuota') or 0
    if nano_cpus:
        return round(nano_cpus / 1e9, 2), True
    if cpu_quota > 0:
        cpu_period = hostcfg.get('CpuPeriod') or 100000  # kernel cfs default
        return round(cpu_quota / cpu_period, 2), True
    return online_cpus, False


def derive_memory_assignment(hostcfg, stats_limit_bytes):
    """Assigned memory (bytes) and whether it is an explicit limit, from a
    container's HostConfig. A DockerSpawner ``mem_limit`` sets ``HostConfig.Memory``
    (bytes) - the user's ceiling, what the bar measures against. Without it the
    cgroup ``limit`` Docker reports in stats is the host RAM, so the bar falls back
    to the host total (no limit). Parallel to ``derive_cpu_assignment``.

    Returns ``(bytes, limited)``. Pure - unit-tested independently of Docker.
    """
    mem_limit = hostcfg.get('Memory') or 0
    if mem_limit > 0:
        return mem_limit, True
    return stats_limit_bytes, False


def mem_usage_excluding_cache(memory_stats):
    """Real memory usage in bytes - the cgroup ``usage`` minus reclaimable file
    cache, matching what ``docker stats`` / Docker Desktop display. The raw
    ``usage`` field counts the page cache a container holds, so an idle container
    that has merely read/written many files reports tens of GB it is not actually
    consuming (this over-reported the host memory bar - 143 GB vs the real 41 GB).
    Same formula the Docker CLI uses: subtract ``total_inactive_file`` (cgroup v1)
    or ``inactive_file`` (cgroup v2) when it is below ``usage``. Pure - unit-tested
    independently of Docker.
    """
    usage = memory_stats.get('usage', 0)
    st = memory_stats.get('stats') or {}
    for key in ('total_inactive_file', 'inactive_file'):
        inactive = st.get(key)
        if inactive is not None and inactive < usage:
            return usage - inactive
    return usage


def stats_from_container(container):
    """CPU/memory/image stats dict for an already-resolved Docker container object
    (blocking, ~2s - `stats(stream=False)` samples twice). Single source of truth
    for the stats math, shared by the ad-hoc `get_container_stats` and the
    background `ContainerStatsRefresher`. Returns the dict, or None on any failure."""
    try:
        stats = container.stats(stream=False)

        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                    stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                       stats['precpu_stats']['system_cpu_usage']

        online_cpus = stats['cpu_stats'].get('online_cpus', 1) or 1
        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * online_cpus * 100

        # Assigned cores: the explicit CPU limit when one is set, else the host
        # cores the container can actually use. A limit comes two ways -
        # DockerSpawner cpu_limit sets HostConfig.NanoCpus (billionths of a
        # core); a cgroup cfs quota (the cpu-quota-* groups) sets CpuQuota /
        # CpuPeriod. Check both so a quota-limited user's bar measures against
        # their ceiling, not the host. cpu_cores_limited drives the "assigned"
        # vs "host (no limit)" tooltip.
        hostcfg = container.attrs.get('HostConfig') or {}
        cpu_cores, cpu_cores_limited = derive_cpu_assignment(hostcfg, online_cpus)

        memory_usage = mem_usage_excluding_cache(stats['memory_stats'])
        memory_assigned, memory_limited = derive_memory_assignment(
            hostcfg, stats['memory_stats'].get('limit', 1))
        memory_percent = (memory_usage / memory_assigned) * 100 if memory_assigned > 0 else 0

        return {
            'cpu_percent': round(cpu_percent, 1),
            'cpu_cores': cpu_cores,
            'cpu_cores_limited': cpu_cores_limited,
            'memory_mb': round(memory_usage / (1024 * 1024), 1),
            'memory_percent': round(memory_percent, 1),
            # assigned ceiling when mem-limited, else the host RAM the cgroup
            # reports; memory_limited tells the UI which, for the bar label
            'memory_total_mb': round(memory_assigned / (1024 * 1024), 1),
            'memory_limited': memory_limited,
            # image id the container is running (from the inspect we already
            # did) - compared against the local tag for upgrade detection
            'image_id': container.attrs.get('Image'),
        }
    except Exception:
        return None


def get_container_stats(username):
    """Get CPU and memory stats for a user's container (blocking, fast ~2s)."""
    try:
        import docker
        docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        container_name = f'jupyterlab-{encode_username_for_docker(username)}'

        try:
            container = docker_client.containers.get(container_name)
            return stats_from_container(container)
        finally:
            docker_client.close()
    except Exception:
        return None


async def get_container_stats_async(username):
    """Async wrapper - runs in thread pool to avoid blocking."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_docker_executor, get_container_stats, username)


def volume_exists(volume_name):
    """True when a Docker volume with this exact name exists (blocking)."""
    try:
        import docker
        docker_client = docker.from_env()
        try:
            docker_client.volumes.get(volume_name)
            return True
        finally:
            docker_client.close()
    except Exception:
        return False


async def volume_exists_async(volume_name):
    """Async wrapper - runs in thread pool to avoid blocking the hub loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_docker_executor, volume_exists, volume_name)


def resolve_self_mount_volume(destination):
    """The Docker volume name backing a mount inside THIS (hub) container.

    Inspects the hub's own container (HOSTNAME == the short container id Docker
    assigns) and returns the Name of the named volume mounted at ``destination``
    (e.g. the docker-proxy socket dir). Lets the hub subpath-mount that exact
    volume into each lab WITHOUT reconstructing the compose-namespaced volume name
    from strings - so renaming the volume on the compose side can never drift from
    what the hub references. Returns None when it cannot be determined (not in a
    container, docker socket unreachable, or no named volume mounted there).
    """
    try:
        import socket
        import docker
        client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        try:
            container = client.containers.get(socket.gethostname())
            for m in (container.attrs.get('Mounts') or []):
                if m.get('Type') == 'volume' and m.get('Destination') == destination:
                    return m.get('Name')
        finally:
            client.close()
    except Exception:
        return None
    return None


def get_executor():
    """Return the shared thread pool executor for Docker operations."""
    return _docker_executor


# ── Lab image upgrade detection ──────────────────────────────────────────────
# Ask: does the lab image tag now resolve to a different image than the one the
# running container uses? Compare image IDs, not Created times - a rebuilt+pruned
# image (the moment an upgrade exists) is gone from the store, so its timestamp is
# unreadable; the tag's current target id is the reliable signal. A re-tag to an
# older image is rejected by requiring the tag to be the repo's newest image. The
# image list is snapshotted briefly (~5min) to keep the polled activity endpoint
# off the socket; the per-container check is then a dict lookup.
_IMAGE_TTL = 300  # seconds
_image_snapshot = {'data': None, 'expires': 0.0}  # data = (tag_to_id, newest_id_by_repo)


def _image_repo(image_ref):
    """Bare repo (tag/digest stripped) for matching `docker image ls` RepoTags."""
    if not image_ref:
        return ''
    ref = image_ref.split('@', 1)[0]                 # drop @sha256 digest
    if ':' in ref.rsplit('/', 1)[-1]:                # a tag (a registry host:port keeps its ':')
        ref = ref.rsplit(':', 1)[0]
    return ref


def _parse_created(created):
    """Epoch float from a docker image's ``Created`` field. Current docker clients
    return an ISO-8601 string with up to nanosecond precision and a trailing 'Z';
    older ones return an epoch int/float. Returns None when unparseable (unknown)."""
    if isinstance(created, (int, float)):
        return float(created)
    if not isinstance(created, str) or not created:
        return None
    s = created.strip()
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    s = re.sub(r'(\.\d{6})\d+', r'\1', s)        # trim ns -> us (fromisoformat limit)
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def _normalize_ref(image_ref):
    """Full ``repo:tag`` for matching ``RepoTags``: drop any @sha256 digest and add
    an implicit ``:latest`` when the ref carries no tag (docker's own default)."""
    if not image_ref:
        return ''
    ref = image_ref.split('@', 1)[0]             # drop @sha256 digest
    if ':' not in ref.rsplit('/', 1)[-1]:        # no tag on the final path segment
        ref += ':latest'
    return ref


def _image_snapshot_get():
    """(tag_to_id, newest_id_by_repo) from `docker image ls -a`, cached ~5min.

    tag_to_id maps each ``repo:tag`` to the image id it currently points to, so the
    configured lab image tag resolves to its current target. newest_id_by_repo maps
    a repo to the id of its most-recently-created image, used to reject a re-tag to
    an older image. ``Created`` is parsed via ``_parse_created``. Best-effort/empty
    on any docker failure."""
    now = time.monotonic()
    if _image_snapshot['data'] is not None and _image_snapshot['expires'] > now:
        return _image_snapshot['data']
    tag_to_id = {}
    newest = {}                                  # repo -> (created_epoch, id)
    try:
        import docker
        client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        try:
            for img in client.images.list(all=True):
                created = _parse_created(img.attrs.get('Created'))
                for tag in (img.attrs.get('RepoTags') or []):
                    repo = tag.rsplit(':', 1)[0]
                    if not repo or repo == '<none>':
                        continue
                    tag_to_id[tag] = img.id
                    if created is not None and created > newest.get(repo, (-1.0, None))[0]:
                        newest[repo] = (created, img.id)
        finally:
            client.close()
    except Exception:
        pass
    data = (tag_to_id, {repo: cid for repo, (_, cid) in newest.items()})
    _image_snapshot['data'] = data
    _image_snapshot['expires'] = now + _IMAGE_TTL
    return data


def newer_lab_image_available(image_ref, container_image_id):
    """True when the configured lab image tag now resolves to a different image than
    the one the running container uses - i.e. a stop/start would pick up a newer
    image.

    Compares image IDs, not ``Created`` times: the image a running container was
    built from is frequently pruned right after a rebuild (the very moment an
    upgrade exists), so its timestamp is unreadable - the reliable signal is that
    the tag's current target id differs from the running id. Guarded so the tag must
    also be the repo's newest image, so a deliberate re-tag to an OLDER image never
    offers a false upgrade. Conservative False when anything is unknown."""
    ref = _normalize_ref(image_ref)
    if not ref or not container_image_id:
        return False
    tag_to_id, newest_id_by_repo = _image_snapshot_get()
    repo = _image_repo(ref)
    return image_upgrade_available(tag_to_id.get(ref), container_image_id, newest_id_by_repo.get(repo))


def image_upgrade_available(latest_tag_id, container_image_id, newest_repo_id):
    """Pure: True when the lab image tag's current target differs from the running
    container's image AND that target is the repo's newest image (so a re-tag to an
    older image is not offered as an upgrade). False when the tag id or the running
    id is unknown."""
    if not latest_tag_id or not container_image_id:
        return False
    if latest_tag_id == container_image_id:
        return False
    return latest_tag_id == newest_repo_id
