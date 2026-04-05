"""Background volume sizes cache with per-user parallel refresh.

Each user's volumes are measured by spawning a lightweight alpine container
with all volumes mounted read-only and running du -sb. Results trickle into
the cache as each user's measurement completes.
"""

import logging
import os
from concurrent.futures import as_completed
from datetime import datetime, timezone

from .docker_utils import get_executor

log = logging.getLogger('jupyterhub.custom_handlers')

# Cache: {'data': {encoded_username: {total, volumes}}, 'timestamp': datetime, 'refreshing': bool}
_volume_sizes_cache = {'data': {}, 'timestamp': None, 'refreshing': False}

# Alpine image for du measurements
_DU_IMAGE = 'alpine:latest'


def _get_logger():
    from traitlets.config import Application
    try:
        return Application.instance().log
    except Exception:
        return logging.getLogger('jupyterhub')


def _get_volumes_update_interval():
    return int(os.environ.get('JUPYTERHUB_ACTIVITYMON_VOLUMES_UPDATE_INTERVAL', 3600))


def _get_docker_timeout():
    return int(os.environ.get('JUPYTERHUB_DOCKER_TIMEOUT', 360))


def _measure_user_volumes(encoded_username, volume_names):
    """Measure all volumes for one user via alpine container (blocking).

    Spawns a container with all volumes mounted read-only at /vols/<suffix>,
    runs du -sb on each, returns {encoded_username: {total, volumes}}.
    """
    try:
        import docker
        client = docker.DockerClient(base_url='unix://var/run/docker.sock', timeout=_get_docker_timeout())
        try:
            # Build volume mounts: {volume_name: {'bind': '/vols/suffix', 'mode': 'ro'}}
            mounts = {}
            suffixes = []
            for vol_name in volume_names:
                suffix = vol_name.rsplit('_', 1)[-1]
                suffixes.append(suffix)
                mounts[vol_name] = {'bind': f'/vols/{suffix}', 'mode': 'ro'}

            # Run du in a single container with all volumes
            result = client.containers.run(
                _DU_IMAGE,
                command='sh -c "for d in /vols/*; do du -sb \\"$d\\"; done"',
                volumes=mounts,
                remove=True,
                network_mode='none',
                mem_limit='32m',
                stderr=True,
            )

            # Parse du output: "12345\t/vols/home\n67890\t/vols/workspace\n"
            output = result.decode('utf-8', errors='replace').strip()
            volumes = {}
            total = 0
            for line in output.split('\n'):
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    size_bytes = int(parts[0])
                    suffix = parts[1].split('/')[-1]
                    size_mb = round(size_bytes / (1024 * 1024), 1)
                    volumes[suffix] = size_mb
                    total += size_mb

            return encoded_username, {"total": round(total, 1), "volumes": volumes}
        finally:
            client.close()
    except Exception as e:
        _get_logger().error(f"[Volume Sizes] Error measuring {encoded_username}: {e}")
        return encoded_username, None


def _refresh_volume_sizes():
    """Fetch all user volume sizes in parallel (one thread per user)."""
    global _volume_sizes_cache
    logger = _get_logger()

    if _volume_sizes_cache['refreshing']:
        logger.info("[Volume Sizes] Refresh already in progress, skipping")
        return

    _volume_sizes_cache['refreshing'] = True
    try:
        import docker
        client = docker.DockerClient(base_url='unix://var/run/docker.sock', timeout=30)
        try:
            all_volumes = [v.name for v in client.volumes.list()
                          if v.name.startswith('jupyterlab-') and '_' in v.name]
        finally:
            client.close()

        # Group volumes by encoded_username
        user_volumes = {}
        for vol_name in all_volumes:
            prefix = vol_name[:vol_name.rsplit('_', 1)[0].__len__()]
            encoded_username = vol_name[len('jupyterlab-'):].rsplit('_', 1)[0]
            if encoded_username not in user_volumes:
                user_volumes[encoded_username] = []
            user_volumes[encoded_username].append(vol_name)

        if not user_volumes:
            logger.info("[Volume Sizes] No jupyterlab volumes found")
            _volume_sizes_cache['timestamp'] = datetime.now(timezone.utc)
            return

        # Pull alpine once (fast if cached)
        try:
            import docker as docker_mod
            c = docker_mod.DockerClient(base_url='unix://var/run/docker.sock', timeout=30)
            try:
                c.images.get(_DU_IMAGE)
            except docker_mod.errors.ImageNotFound:
                logger.info(f"[Volume Sizes] Pulling {_DU_IMAGE}...")
                c.images.pull(_DU_IMAGE)
            finally:
                c.close()
        except Exception:
            pass

        # Submit per-user measurements in parallel
        from .docker_utils import get_executor as get_main_executor
        executor = get_main_executor()
        futures = {
            executor.submit(_measure_user_volumes, user, vols): user
            for user, vols in user_volumes.items()
        }

        completed = 0
        for future in as_completed(futures):
            encoded_username, data = future.result()
            if data:
                _volume_sizes_cache['data'][encoded_username] = data
                completed += 1

        _volume_sizes_cache['timestamp'] = datetime.now(timezone.utc)
        total_size = sum(u.get("total", 0) for u in _volume_sizes_cache['data'].values())
        logger.info(f"[Volume Sizes] Refreshed: {completed}/{len(user_volumes)} users, {total_size:.1f} MB total")

    except Exception as e:
        logger.error(f"[Volume Sizes] Error during refresh: {e}")
    finally:
        _volume_sizes_cache['refreshing'] = False


def get_cached_volume_sizes():
    """Get cached volume sizes (non-blocking). Returns (data, needs_refresh)."""
    now = datetime.now(timezone.utc)
    interval = _get_volumes_update_interval()

    needs_refresh = (
        _volume_sizes_cache['timestamp'] is None
        or (now - _volume_sizes_cache['timestamp']).total_seconds() > interval
    )

    return _volume_sizes_cache['data'], needs_refresh


def get_volume_sizes_with_refresh():
    """Get volume sizes, triggering background refresh if stale. Non-blocking."""
    data, needs_refresh = get_cached_volume_sizes()
    if needs_refresh and not _volume_sizes_cache['refreshing']:
        _get_logger().info("[Volume Sizes] Cache stale, triggering background refresh")
        from .docker_utils import get_executor
        get_executor().submit(_refresh_volume_sizes)
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

        from .docker_utils import get_executor
        get_executor().submit(_refresh_volume_sizes)

    def stop(self):
        if self.periodic_callback is not None:
            self.periodic_callback.stop()
            self.periodic_callback = None
            _get_logger().info("[VolumeSizeRefresher] Stopped")

    def _refresh_tick(self):
        if not _volume_sizes_cache['refreshing']:
            from .docker_utils import get_executor
            get_executor().submit(_refresh_volume_sizes)
