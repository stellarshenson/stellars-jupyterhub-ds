"""Background volume sizes cache with periodic refresh."""

import asyncio
import logging
import os
from datetime import datetime, timezone

from .docker_utils import get_executor

log = logging.getLogger('jupyterhub.custom_handlers')

# Cache: {'data': {encoded_username: {total, volumes}}, 'timestamp': datetime, 'refreshing': bool}
_volume_sizes_cache = {'data': {}, 'timestamp': None, 'refreshing': False}


def _get_logger():
    from traitlets.config import Application
    try:
        return Application.instance().log
    except Exception:
        return logging.getLogger('jupyterhub')


def _get_volumes_update_interval():
    return int(os.environ.get('JUPYTERHUB_ACTIVITYMON_VOLUMES_UPDATE_INTERVAL', 3600))


def _fetch_volume_sizes():
    """Fetch sizes of all user volumes (blocking). Returns dict by encoded_username."""
    try:
        import docker
        docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        try:
            df_data = docker_client.df()
            volumes_data = df_data.get('Volumes', []) or []

            user_data = {}
            for vol in volumes_data:
                name = vol.get('Name', '')
                if name.startswith('jupyterlab-') and '_' in name:
                    parts = name[len('jupyterlab-'):].rsplit('_', 1)
                    if len(parts) == 2:
                        encoded_username, suffix = parts
                        usage_data = vol.get('UsageData', {}) or {}
                        size_bytes = usage_data.get('Size', 0) or 0
                        size_mb = round(size_bytes / (1024 * 1024), 1)

                        if encoded_username not in user_data:
                            user_data[encoded_username] = {"total": 0, "volumes": {}}
                        user_data[encoded_username]["total"] += size_mb
                        user_data[encoded_username]["volumes"][suffix] = size_mb

            for user in user_data:
                user_data[user]["total"] = round(user_data[user]["total"], 1)

            total_size = sum(u["total"] for u in user_data.values())
            _get_logger().info(f"[Volume Sizes] Fetched: {len(user_data)} users, total {total_size:.1f} MB")
            return user_data
        finally:
            docker_client.close()
    except Exception as e:
        _get_logger().error(f"[Volume Sizes] Error fetching: {e}")
        return {}


def _refresh_volume_sizes_sync():
    """Synchronous refresh of volume sizes cache."""
    global _volume_sizes_cache
    logger = _get_logger()

    if _volume_sizes_cache['refreshing']:
        logger.info("[Volume Sizes] Refresh already in progress, skipping")
        return

    _volume_sizes_cache['refreshing'] = True
    try:
        data = _fetch_volume_sizes()
        if data:
            _volume_sizes_cache['data'] = data
            _volume_sizes_cache['timestamp'] = datetime.now(timezone.utc)
            logger.info(f"[Volume Sizes] Cache updated: {len(data)} users")
        else:
            logger.warning("[Volume Sizes] Refresh returned empty - keeping previous cache")
    finally:
        _volume_sizes_cache['refreshing'] = False


async def _refresh_volume_sizes_background():
    """Trigger background refresh (non-blocking, fire-and-forget)."""
    loop = asyncio.get_event_loop()
    loop.run_in_executor(get_executor(), _refresh_volume_sizes_sync)


def get_cached_volume_sizes():
    """Get cached volume sizes (non-blocking). Returns (data, needs_refresh)."""
    now = datetime.now(timezone.utc)
    interval = _get_volumes_update_interval()

    needs_refresh = (
        _volume_sizes_cache['timestamp'] is None
        or (now - _volume_sizes_cache['timestamp']).total_seconds() > interval
    )

    return _volume_sizes_cache['data'], needs_refresh


async def get_volume_sizes_with_refresh():
    """Get volume sizes, triggering background refresh if needed."""
    data, needs_refresh = get_cached_volume_sizes()
    if needs_refresh:
        _get_logger().info("[Volume Sizes] Cache stale, triggering background refresh")
        await _refresh_volume_sizes_background()
    return data


class VolumeSizeRefresher:
    """Background scheduler for periodic volume size refresh."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.periodic_callback = None
        self.interval_seconds = _get_volumes_update_interval()
        _get_logger().info(f"[VolumeSizeRefresher] Initialized with interval={self.interval_seconds}s")

    def start(self):
        from tornado.ioloop import PeriodicCallback
        logger = _get_logger()

        if self.periodic_callback is not None:
            logger.info("[VolumeSizeRefresher] Already running")
            return

        interval_ms = self.interval_seconds * 1000
        self.periodic_callback = PeriodicCallback(self._refresh_tick, interval_ms)
        self.periodic_callback.start()
        logger.info(f"[VolumeSizeRefresher] Started - refreshing every {self.interval_seconds}s")

        asyncio.get_event_loop().call_soon(lambda: asyncio.ensure_future(self._refresh_tick_async()))

    def stop(self):
        if self.periodic_callback is not None:
            self.periodic_callback.stop()
            self.periodic_callback = None
            _get_logger().info("[VolumeSizeRefresher] Stopped")

    def _refresh_tick(self):
        asyncio.ensure_future(self._refresh_tick_async())

    async def _refresh_tick_async(self):
        logger = _get_logger()
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(get_executor(), _refresh_volume_sizes_sync)
            data = _volume_sizes_cache.get('data', {})
            total_size = sum(u.get("total", 0) for u in data.values())
            logger.info(f"[VolumeSizeRefresher] Tick complete: {len(data)} users, {total_size:.1f} MB total")
        except Exception as e:
            logger.error(f"[VolumeSizeRefresher] Error during refresh: {e}")


def start_volume_size_refresher():
    """Start the background volume size refresher."""
    refresher = VolumeSizeRefresher.get_instance()
    refresher.start()
