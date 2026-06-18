"""Lightweight, activity-gated cache of per-container CPU/memory stats.

Live `docker stats` is ~1-2s per container (it samples twice). Running that
synchronously over every active user on the `/activity` request path stalled the
endpoint for 5-6s. This keeps a warm snapshot of per-user stats and refreshes it
**lazily and only for users that are signalling activity**:

- the refresh fires only when `/activity` is polled (no always-on timer) and at
  most once per interval (the refreshing-guard),
- it samples stats **only for recently-active users** (the platform's existing
  `last_activity`-based signal) - idle-but-running containers keep their last
  value and are never polled, and
- when no user is active there are **zero docker calls**.

`/activity` reads the snapshot non-blocking (returns instantly, no docker gather).
Cache is keyed by the escapism-encoded username (the `jupyterlab-<encoded>`
container-name suffix), matching how the handler looks it up.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from .docker_utils import stats_from_container

log = logging.getLogger('jupyterhub.custom_handlers')

# Cache: {encoded_username: {cpu_percent, cpu_cores, memory_mb, ...}}
_container_stats_cache = {'data': {}, 'timestamp': None, 'refreshing': False}

# Dedicated executor for stats fetches (separate from the size/ops executors)
_stats_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="docker-stats")


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


def _get_docker_timeout():
    return int(os.environ.get('JUPYTERHUB_DOCKER_TIMEOUT', 360))


def _get_refresh_interval():
    # How fresh an active user's CPU/memory cell is. Kept off the request path and
    # only sampled for active users while the portal is viewed, so a modest 10s is
    # lightweight (no continuous docker polling).
    return int(os.environ.get('JUPYTERHUB_ACTIVITYMON_STATS_INTERVAL', 10))


def _fetch_single_container_stats(container_name, timeout):
    """Fetch stats for one container (blocking). Returns (encoded_username, data) or None."""
    try:
        import docker
        client = docker.DockerClient(base_url='unix://var/run/docker.sock', timeout=timeout)
        try:
            container = client.containers.get(container_name)
            data = stats_from_container(container)
            if data is None:
                return None
            encoded_username = container_name[len('jupyterlab-'):]
            return encoded_username, data
        finally:
            client.close()
    except Exception:
        return None


def _refresh_active_container_stats(active_encoded):
    """Sample stats for the given recently-active users (encoded names), in parallel.

    Only containers whose encoded username is in `active_encoded` are sampled -
    idle-but-running containers are left untouched (their last snapshot stands).
    Stale entries for stopped containers are pruned. Updates the cache incrementally.
    """
    global _container_stats_cache
    logger = _get_logger()

    if _container_stats_cache['refreshing']:
        return
    active_encoded = set(active_encoded or ())
    if not active_encoded:
        return  # nobody active -> no docker calls at all

    _container_stats_cache['refreshing'] = True
    try:
        import docker
        # List only RUNNING containers (no all=True - excludes stopped)
        api = docker.APIClient(base_url='unix://var/run/docker.sock', timeout=30)
        try:
            containers = api._get(api._url('/containers/json')).json()
        finally:
            api.close()

        running_users = set()
        names = []  # names we will actually sample (active AND running)
        for ctr in containers:
            for name in ctr.get('Names', []):
                name = name.lstrip('/')
                if name.startswith('jupyterlab-'):
                    encoded = name[len('jupyterlab-'):]
                    running_users.add(encoded)
                    if encoded in active_encoded:
                        names.append(name)

        # Drop snapshot entries for containers that are no longer running
        stale = [u for u in _container_stats_cache['data'] if u not in running_users]
        for u in stale:
            del _container_stats_cache['data'][u]
        if stale:
            logger.info(f"[Container Stats] Cleared {len(stale)} stale entries")

        if not names:
            _container_stats_cache['timestamp'] = datetime.now(timezone.utc)
            return

        timeout = _get_docker_timeout()
        futures = {_stats_executor.submit(_fetch_single_container_stats, n, timeout): n for n in names}

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            if result:
                encoded_username, data = result
                _container_stats_cache['data'][encoded_username] = data
                completed += 1

        _container_stats_cache['timestamp'] = datetime.now(timezone.utc)
        logger.info(f"[Container Stats] Refreshed: {completed}/{len(names)} active containers")

    except Exception as e:
        logger.error(f"[Container Stats] Error during refresh: {e}")
    finally:
        _container_stats_cache['refreshing'] = False


def get_cached_container_stats():
    """Get cached container stats (non-blocking). Returns (data, needs_refresh)."""
    now = datetime.now(timezone.utc)
    interval = _get_refresh_interval()

    needs_refresh = (
        _container_stats_cache['timestamp'] is None
        or (now - _container_stats_cache['timestamp']).total_seconds() > interval
    )

    return _container_stats_cache['data'], needs_refresh


def get_container_stats_with_refresh(active_encoded=()):
    """Get container stats, triggering a background refresh of the active users if
    stale. Non-blocking.

    `active_encoded` is the set of escapism-encoded usernames that are currently
    signalling activity (the handler builds it from `recently_active`); only those
    are sampled. There is no always-on timer - the refresh fires only here, at most
    once per interval, and only when at least one user is active. Returns the
    snapshot keyed by encoded username; the handler maps each active user via
    ``encode_username_for_docker(user.name)``.
    """
    data, needs_refresh = get_cached_container_stats()
    if active_encoded and needs_refresh and not _container_stats_cache['refreshing']:
        from .docker_utils import get_executor
        get_executor().submit(_refresh_active_container_stats, active_encoded)
    return data
