"""Background container size cache with periodic refresh.

Container size (writable layer) requires inspect_container with size=True
which triggers slow disk usage calculation. Cached and refreshed in background
so the activity page loads instantly with CPU/memory from fast stats.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from .docker_utils import encode_username_for_docker, get_executor

log = logging.getLogger('jupyterhub.custom_handlers')

# Cache: {'data': {encoded_username: {size_rw_mb, size_rootfs_mb}}, 'timestamp': datetime, 'refreshing': bool}
_container_sizes_cache = {'data': {}, 'timestamp': None, 'refreshing': False}


def _get_logger():
    from traitlets.config import Application
    try:
        return Application.instance().log
    except Exception:
        return logging.getLogger('jupyterhub')


def _get_docker_timeout():
    return int(os.environ.get('JUPYTERHUB_DOCKER_TIMEOUT', 360))


def _get_refresh_interval():
    return int(os.environ.get('JUPYTERHUB_ACTIVITYMON_CONTAINER_SIZE_INTERVAL', 300))


def _fetch_all_container_sizes():
    """Fetch writable layer sizes for all jupyterlab containers (blocking).

    Uses a single Docker API call with size=True for all containers.
    """
    logger = _get_logger()
    try:
        import docker
        api_client = docker.APIClient(base_url='unix://var/run/docker.sock', timeout=_get_docker_timeout())
        try:
            containers = api_client._get(
                api_client._url('/containers/json'),
                params={'all': True, 'size': True}
            ).json()

            user_data = {}
            for ctr in containers:
                # Container names are like ['/jupyterlab-username']
                names = ctr.get('Names', [])
                for name in names:
                    name = name.lstrip('/')
                    if name.startswith('jupyterlab-'):
                        encoded_username = name[len('jupyterlab-'):]
                        size_rw = ctr.get('SizeRw', 0) or 0
                        size_rootfs = ctr.get('SizeRootFs', 0) or 0
                        user_data[encoded_username] = {
                            'size_rw_mb': round(size_rw / (1024 * 1024), 1),
                            'size_rootfs_mb': round(size_rootfs / (1024 * 1024), 1),
                        }

            logger.info(f"[Container Sizes] Fetched: {len(user_data)} containers")
            return user_data
        finally:
            api_client.close()
    except Exception as e:
        logger.error(f"[Container Sizes] Error fetching: {e}")
        return {}


def _refresh_container_sizes_sync():
    """Synchronous refresh of container sizes cache."""
    global _container_sizes_cache
    logger = _get_logger()

    if _container_sizes_cache['refreshing']:
        logger.info("[Container Sizes] Refresh already in progress, skipping")
        return

    _container_sizes_cache['refreshing'] = True
    try:
        data = _fetch_all_container_sizes()
        if data:
            _container_sizes_cache['data'] = data
            _container_sizes_cache['timestamp'] = datetime.now(timezone.utc)
            logger.info(f"[Container Sizes] Cache updated: {len(data)} containers")
        else:
            logger.warning("[Container Sizes] Refresh returned empty - keeping previous cache")
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


async def get_container_sizes_with_refresh():
    """Get container sizes, triggering background refresh if needed."""
    data, needs_refresh = get_cached_container_sizes()
    if needs_refresh:
        _get_logger().info("[Container Sizes] Cache stale, triggering background refresh")
        loop = asyncio.get_event_loop()
        loop.run_in_executor(get_executor(), _refresh_container_sizes_sync)
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
        _get_logger().info(f"[ContainerSizeRefresher] Initialized with interval={self.interval_seconds}s")

    def start(self):
        from tornado.ioloop import PeriodicCallback
        logger = _get_logger()

        if self.periodic_callback is not None:
            logger.info("[ContainerSizeRefresher] Already running")
            return

        interval_ms = self.interval_seconds * 1000
        self.periodic_callback = PeriodicCallback(self._refresh_tick, interval_ms)
        self.periodic_callback.start()
        logger.info(f"[ContainerSizeRefresher] Started - refreshing every {self.interval_seconds}s")

        asyncio.get_event_loop().call_soon(lambda: asyncio.ensure_future(self._refresh_tick_async()))

    def stop(self):
        if self.periodic_callback is not None:
            self.periodic_callback.stop()
            self.periodic_callback = None
            _get_logger().info("[ContainerSizeRefresher] Stopped")

    def _refresh_tick(self):
        asyncio.ensure_future(self._refresh_tick_async())

    async def _refresh_tick_async(self):
        logger = _get_logger()
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(get_executor(), _refresh_container_sizes_sync)
        except Exception as e:
            logger.error(f"[ContainerSizeRefresher] Error during refresh: {e}")
