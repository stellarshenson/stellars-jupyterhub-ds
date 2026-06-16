"""Background GPU utilisation cache with periodic refresh.

The hub queries the GPU-info sidecar (see ``gpu_client``) for live per-GPU load
instead of spinning an ephemeral nvidia container per sample. The HTTP call is
fast, but it still runs on a background tick so the activity page returns the
last cached sample immediately and never blocks on it.

Cache shape: ``{index(str): {utilization(int %), memory_used_mb(int),
processes(list)}}`` keyed by GPU index, so the activity handler can merge it onto
the static inventory (``stellars_config['gpu_list']``) by index. Empty on any
failure (sidecar down, no GPU) so callers never crash and the UI falls back to
plain inventory chips.
"""

import logging
import os
from datetime import datetime, timezone

from .docker_utils import get_executor

log = logging.getLogger('jupyterhub.custom_handlers')

# Cache: {'data': {index: {utilization, memory_used_mb, processes}}, 'timestamp': datetime, 'refreshing': bool}
_gpu_util_cache = {'data': {}, 'timestamp': None, 'refreshing': False}


def _get_logger():
    from traitlets.config import Application
    # Use the hub's Application logger only if one already exists; never create
    # the singleton here (Application.instance() would), which would pollute
    # global state for any later code/test that constructs its own Application.
    try:
        if Application.initialized():
            return Application.instance().log
    except Exception:
        pass
    return logging.getLogger('jupyterhub')


def _get_update_interval():
    return int(os.environ.get('JUPYTERHUB_GPU_UTIL_UPDATE_INTERVAL', 30))


def configure_gpu_cache(gpuinfo_url=None):
    """Point the sampler at the GPU-info sidecar URL (called at hub startup)."""
    from . import gpu_client
    if gpuinfo_url:
        gpu_client.configure(gpuinfo_url)
    _get_logger().info(f"[GPU Util] Sidecar endpoint: {gpu_client.get_url()}")


def _fetch_gpu_utilization():
    """Sample per-GPU utilisation from the sidecar (blocking HTTP, fast)."""
    from . import gpu_client

    data = {}
    for g in gpu_client.fetch_gpus():
        idx = g.get('index')
        if idx is None:
            continue
        data[str(idx)] = {
            'utilization': int(g.get('utilization') or 0),
            'memory_used_mb': int(g.get('memory_used_mb') or 0),
            'processes': g.get('processes', []) or [],
        }
    return data


def _refresh_sync():
    """Synchronous refresh of the GPU utilisation cache."""
    global _gpu_util_cache
    logger = _get_logger()

    if _gpu_util_cache['refreshing']:
        return

    _gpu_util_cache['refreshing'] = True
    try:
        data = _fetch_gpu_utilization()
        if data:
            _gpu_util_cache['data'] = data
            _gpu_util_cache['timestamp'] = datetime.now(timezone.utc)
            logger.info(f"[GPU Util] Cache updated: {len(data)} device(s)")
        else:
            logger.info("[GPU Util] Sample empty - keeping previous cache")
    finally:
        _gpu_util_cache['refreshing'] = False


def get_gpu_utilization_with_refresh():
    """Return the cached {index: {utilization, memory_used_mb, processes}}, refreshing if stale.

    Non-blocking: a stale cache triggers a background sample and returns the
    previous sample (or {} on first call) immediately.
    """
    now = datetime.now(timezone.utc)
    interval = _get_update_interval()
    needs_refresh = (
        _gpu_util_cache['timestamp'] is None
        or (now - _gpu_util_cache['timestamp']).total_seconds() > interval
    )
    if needs_refresh and not _gpu_util_cache['refreshing']:
        get_executor().submit(_refresh_sync)
    return _gpu_util_cache['data']


class GpuUtilizationRefresher:
    """Background scheduler for periodic GPU utilisation sampling."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.periodic_callback = None
        self.interval_seconds = _get_update_interval()
        _get_logger().info(f"[GpuUtilizationRefresher] Initialized with interval={self.interval_seconds}s")

    def start(self):
        from tornado.ioloop import PeriodicCallback
        logger = _get_logger()

        if self.periodic_callback is not None:
            return

        interval_ms = self.interval_seconds * 1000
        self.periodic_callback = PeriodicCallback(self._refresh_tick, interval_ms)
        self.periodic_callback.start()
        logger.info(f"[GpuUtilizationRefresher] Started - sampling every {self.interval_seconds}s")

        get_executor().submit(_refresh_sync)

    def stop(self):
        if self.periodic_callback is not None:
            self.periodic_callback.stop()
            self.periodic_callback = None

    def _refresh_tick(self):
        if not _gpu_util_cache['refreshing']:
            get_executor().submit(_refresh_sync)
