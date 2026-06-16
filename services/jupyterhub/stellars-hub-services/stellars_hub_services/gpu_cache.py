"""Background GPU utilisation cache with periodic refresh.

The hub container has no GPU access of its own, so host GPU load is sampled the
same way the startup inventory is enumerated: by running ``nvidia-smi`` in an
ephemeral CUDA container (runtime=nvidia). That call is slow (~1-3s of container
spin) so it runs in a background thread on a periodic tick - the activity page
returns the last cached sample immediately and never blocks on it.

Cache shape: ``{index(str): {utilization(int %), memory_used_mb(int)}}`` keyed by
the nvidia-smi GPU index, so the activity handler can merge it onto the static
inventory (``stellars_config['gpu_list']``) by index. Empty on any failure (no
GPU, no nvidia runtime, docker error) so callers never crash and the UI falls
back to plain inventory chips.
"""

import logging
import os
from datetime import datetime, timezone

from .docker_utils import get_executor

log = logging.getLogger('jupyterhub.custom_handlers')

# Cache: {'data': {index: {utilization, memory_used_mb}}, 'timestamp': datetime, 'refreshing': bool}
_gpu_util_cache = {'data': {}, 'timestamp': None, 'refreshing': False}

# Nvidia image used for the sampling container (set at hub startup).
_nvidia_image = 'nvidia/cuda:13.0.2-base-ubuntu24.04'


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


def configure_gpu_cache(nvidia_image):
    """Set the CUDA image the sampler runs nvidia-smi in (called at hub startup)."""
    global _nvidia_image
    if nvidia_image:
        _nvidia_image = nvidia_image
    _get_logger().info(f"[GPU Util] Configured sampler image: {_nvidia_image}")


def _fetch_gpu_utilization():
    """Sample per-GPU utilisation via nvidia-smi in a CUDA container (blocking)."""
    import docker

    data = {}
    client = None
    try:
        client = docker.DockerClient('unix://var/run/docker.sock')
        output = client.containers.run(
            image=_nvidia_image,
            command=(
                'nvidia-smi '
                '--query-gpu=index,utilization.gpu,memory.used '
                '--format=csv,noheader,nounits'
            ),
            runtime='nvidia',
            name='jupyterhub_gpu_util',
            stderr=False,
            stdout=True,
            remove=False,
        )
        for line in output.decode('utf-8', 'replace').strip().splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 3:
                continue
            index = parts[0]
            try:
                util = int(parts[1])
            except ValueError:
                util = 0
            try:
                mem_used = int(parts[2])
            except ValueError:
                mem_used = 0
            data[index] = {'utilization': util, 'memory_used_mb': mem_used}
    except Exception as e:
        _get_logger().warning(f"[GPU Util] Sample failed: {e}")
        data = {}
    if client is not None:
        try:
            client.containers.get('jupyterhub_gpu_util').remove(force=True)
        except Exception:
            pass
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
    """Return the cached {index: {utilization, memory_used_mb}}, refreshing if stale.

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
