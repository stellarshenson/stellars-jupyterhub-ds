"""Docker utility functions for container and volume operations."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

_docker_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="docker-ops")


def encode_username_for_docker(username):
    """Encode username for Docker volume/container names.

    Uses escapism library (same as DockerSpawner) for compatibility.
    e.g., 'user.name' -> 'user-2ename' (. = ASCII 46 = 0x2e)
    """
    from escapism import escape
    return escape(username, escape_char='-').lower()


def get_container_stats(username):
    """Get CPU and memory stats for a user's container (blocking, fast ~2s)."""
    try:
        import docker
        docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        container_name = f'jupyterlab-{encode_username_for_docker(username)}'

        try:
            container = docker_client.containers.get(container_name)
            stats = container.stats(stream=False)

            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                        stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                           stats['precpu_stats']['system_cpu_usage']

            online_cpus = stats['cpu_stats'].get('online_cpus', 1) or 1
            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100

            # Assigned cores: the explicit CPU limit (HostConfig.NanoCpus, in
            # billionths of a core) when one is set, else the host cores the
            # container can actually use. cpu_cores_limited distinguishes the two
            # so the UI can say "assigned" vs "host (no limit)".
            nano_cpus = (container.attrs.get('HostConfig') or {}).get('NanoCpus') or 0
            cpu_cores = round(nano_cpus / 1e9, 2) if nano_cpus else online_cpus

            memory_usage = stats['memory_stats'].get('usage', 0)
            memory_limit = stats['memory_stats'].get('limit', 1)
            memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0

            return {
                'cpu_percent': round(cpu_percent, 1),
                'cpu_cores': cpu_cores,
                'cpu_cores_limited': bool(nano_cpus),
                'memory_mb': round(memory_usage / (1024 * 1024), 1),
                'memory_percent': round(memory_percent, 1),
                'memory_total_mb': round(memory_limit / (1024 * 1024), 1),
                # image id the container is running (from the inspect we already
                # did) - compared against the local tag for upgrade detection
                'image_id': container.attrs.get('Image'),
            }
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




def get_executor():
    """Return the shared thread pool executor for Docker operations."""
    return _docker_executor


# ── Lab image upgrade detection ──────────────────────────────────────────────
# "docker image ls" the lab repo and ask: is any local image more recently
# created than the one the running container uses? Recency (not just a differing
# id) so a re-tag to an older image never falsely offers an upgrade. The full
# image list is snapshotted briefly to keep the polled activity endpoint off the
# socket; the per-container check is then a dict lookup.
_IMAGE_TTL = 300  # seconds
_image_snapshot = {'data': None, 'expires': 0.0}  # data = (created_by_id, newest_by_repo)


def _image_repo(image_ref):
    """Bare repo (tag/digest stripped) for matching `docker image ls` RepoTags."""
    if not image_ref:
        return ''
    ref = image_ref.split('@', 1)[0]                 # drop @sha256 digest
    if ':' in ref.rsplit('/', 1)[-1]:                # a tag (a registry host:port keeps its ':')
        ref = ref.rsplit(':', 1)[0]
    return ref


def _image_snapshot_get():
    """(created_by_id, newest_by_repo) from `docker image ls -a`, cached ~5min.
    `Created` is the list endpoint's epoch int, so both sides compare in the same
    unit. Empty/best-effort on any docker failure."""
    now = time.monotonic()
    if _image_snapshot['data'] is not None and _image_snapshot['expires'] > now:
        return _image_snapshot['data']
    created_by_id = {}
    newest_by_repo = {}
    try:
        import docker
        client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        try:
            for img in client.images.list(all=True):
                created = img.attrs.get('Created')
                if not isinstance(created, int):
                    continue
                created_by_id[img.id] = created
                for tag in (img.attrs.get('RepoTags') or []):
                    repo = tag.rsplit(':', 1)[0]
                    if repo and repo != '<none>' and created > newest_by_repo.get(repo, -1):
                        newest_by_repo[repo] = created
        finally:
            client.close()
    except Exception:
        pass
    data = (created_by_id, newest_by_repo)
    _image_snapshot['data'] = data
    _image_snapshot['expires'] = now + _IMAGE_TTL
    return data


def newer_lab_image_available(image_ref, container_image_id):
    """True when `docker image ls` has a local image for image_ref's repo created
    more recently than the image the running container uses. Conservative: False
    when anything is unknown (image absent, docker unreachable, container image not
    in the listing) so the upgrade pill is never falsely shown."""
    repo = _image_repo(image_ref)
    if not repo or not container_image_id:
        return False
    created_by_id, newest_by_repo = _image_snapshot_get()
    return image_upgrade_available(newest_by_repo.get(repo), created_by_id.get(container_image_id))


def image_upgrade_available(newest_local_created, container_image_created):
    """Pure: True when a local image is more recently created than the running
    container's image. `Created` values are docker epochs (ints). False when
    either is missing (unknown -> never a false upgrade)."""
    return bool(newest_local_created and container_image_created and newest_local_created > container_image_created)
