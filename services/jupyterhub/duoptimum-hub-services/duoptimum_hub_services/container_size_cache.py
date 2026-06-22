"""Background container size cache with per-container parallel refresh.

Each container's writable layer size is fetched via inspect(size=True) in its
own thread. Results trickle into the cache as each completes - no waiting for
the slowest container to finish before showing any data.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from .logging_setup import log

# Cache: {encoded_username: {size_rw_mb, size_rootfs_mb}}
_container_sizes_cache = {'data': {}, 'timestamp': None, 'refreshing': False}

# Dedicated executor for size fetches (separate from stats executor)
_size_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="docker-size")


def _get_docker_timeout():
    return int(os.environ.get('JUPYTERHUB_HUB_DOCKER_API_TIMEOUT', 360))


def _get_refresh_interval():
    return int(os.environ.get('JUPYTERHUB_ACTIVITYMON_CONTAINER_SIZE_INTERVAL', 300))


def _fetch_single_container_size(container_name, timeout):
    """Fetch size for one container (blocking). Returns (encoded_username, data) or None."""
    try:
        import docker
        api = docker.APIClient(base_url='unix://var/run/docker.sock', timeout=timeout)
        try:
            resp = api._get(
                api._url('/containers/{0}/json', container_name),
                params={'size': True}
            ).json()
            size_rw = resp.get('SizeRw', 0) or 0
            size_rootfs = resp.get('SizeRootFs', 0) or 0
            from .docker_utils import encoded_username_from_lab_container
            encoded_username = encoded_username_from_lab_container(container_name)
            return encoded_username, {
                'size_rw_mb': round(size_rw / (1024 * 1024), 1),
                'size_rootfs_mb': round(size_rootfs / (1024 * 1024), 1),
            }
        finally:
            api.close()
    except Exception:
        return None


def _refresh_all_container_sizes():
    """Fetch sizes for all jupyterlab containers in parallel. Updates cache incrementally."""
    global _container_sizes_cache
    if _container_sizes_cache['refreshing']:
        return

    _container_sizes_cache['refreshing'] = True
    try:
        import docker
        # List only RUNNING containers (no all=True - excludes stopped)
        api = docker.APIClient(base_url='unix://var/run/docker.sock', timeout=30)
        try:
            containers = api._get(api._url('/containers/json')).json()
        finally:
            api.close()

        from .docker_utils import encoded_username_from_lab_container
        names = []
        current_users = set()
        for ctr in containers:
            for name in ctr.get('Names', []):
                name = name.lstrip('/')
                encoded = encoded_username_from_lab_container(name)
                if encoded is not None:
                    names.append(name)
                    current_users.add(encoded)

        # Remove stale entries for stopped containers
        stale = [u for u in _container_sizes_cache['data'] if u not in current_users]
        for u in stale:
            del _container_sizes_cache['data'][u]
        if stale:
            log.info(f"[Container Sizes] Cleared {len(stale)} stale entries")

        if not names:
            log.info("[Container Sizes] No running jupyterlab containers found")
            _container_sizes_cache['timestamp'] = datetime.now(timezone.utc)
            return

        timeout = _get_docker_timeout()
        futures = {_size_executor.submit(_fetch_single_container_size, n, timeout): n for n in names}

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            if result:
                encoded_username, data = result
                _container_sizes_cache['data'][encoded_username] = data
                completed += 1

        _container_sizes_cache['timestamp'] = datetime.now(timezone.utc)
        log.info(f"[Container Sizes] Refreshed: {completed}/{len(names)} running containers")

    except Exception as e:
        log.error(f"[Container Sizes] Error during refresh: {e}")
    finally:
        _container_sizes_cache['refreshing'] = False


def get_cached_container_sizes():
    """Get cached container sizes (non-blocking). Returns (data, needs_refresh)."""
    now = datetime.now(timezone.utc)
    interval = _get_refresh_interval()

    needs_refresh = (
        _container_sizes_cache['timestamp'] is None
        or (now - _container_sizes_cache['timestamp']).total_seconds() > interval
    )

    return _container_sizes_cache['data'], needs_refresh


def get_container_sizes_with_refresh():
    """Get container sizes, triggering background refresh if stale. Non-blocking."""
    data, needs_refresh = get_cached_container_sizes()
    if needs_refresh and not _container_sizes_cache['refreshing']:
        log.info("[Container Sizes] Cache stale, triggering background refresh")
        from .docker_utils import get_executor
        get_executor().submit(_refresh_all_container_sizes)
    return data


class ContainerSizeRefresher:
    """Background scheduler for periodic container size refresh."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.periodic_callback = None
        self.interval_seconds = _get_refresh_interval()
        log.info(f"[ContainerSizeRefresher] Initialized with interval={self.interval_seconds}s")

    def start(self):
        from tornado.ioloop import PeriodicCallback

        if self.periodic_callback is not None:
            log.info("[ContainerSizeRefresher] Already running")
            return

        interval_ms = self.interval_seconds * 1000
        self.periodic_callback = PeriodicCallback(self._refresh_tick, interval_ms)
        self.periodic_callback.start()
        log.info(f"[ContainerSizeRefresher] Started - refreshing every {self.interval_seconds}s")

        # First refresh immediately
        from .docker_utils import get_executor
        get_executor().submit(_refresh_all_container_sizes)

    def stop(self):
        if self.periodic_callback is not None:
            self.periodic_callback.stop()
            self.periodic_callback = None
            log.info("[ContainerSizeRefresher] Stopped")

    def _refresh_tick(self):
        if not _container_sizes_cache['refreshing']:
            from .docker_utils import get_executor
            get_executor().submit(_refresh_all_container_sizes)
