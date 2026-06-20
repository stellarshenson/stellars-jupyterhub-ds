"""Background volume sizes cache with periodic refresh.

Uses `docker system df` (type=volume) to get volume usage. A cold daemon hands back
sizes mid-computation (uncomputed volumes carry Size=-1); caching that partial
snapshot was DEF-7 (zeros stuck for the whole refresh interval). So the refresh
caches ONLY a COMPLETE pass - one where every matched user volume has a computed
size - retrying on a short delay until df has gathered them all, bounded by a
safety-net attempt cap. The df call is slow (can take minutes) but runs in a
background executor thread, so the activity page returns cached data immediately
and never blocks on it.

Volume-name parsing is driven by templates configured at hub startup via
configure_volume_cache() - the same map used by ManageVolumesHandler so both code
paths agree on what an on-disk volume is called. Each template (e.g.
"stellars-tech-ai-lab_jupyterlab_{username}_home") is compiled to a regex with a
capturing username group; disk volumes are matched against all templates and the
first hit wins.
"""

import logging
import os
import re
import time
from datetime import datetime, timezone

from .docker_utils import get_executor
from .persisted_cache import load_cached, save_cached

log = logging.getLogger('jupyterhub.custom_handlers')

# Cache: {'data': {encoded_username: {total, volumes}}, 'timestamp': datetime, 'refreshing': bool}
_volume_sizes_cache = {'data': {}, 'timestamp': None, 'refreshing': False}

# Volume-name template config (set by configure_volume_cache at hub startup).
# _volume_name_templates: {suffix: template_string_with_{username}_placeholder}
# _template_regexes:      [(suffix, compiled_regex_with_username_group), ...]
_volume_name_templates = {}
_template_regexes = []


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


def _get_volumes_update_interval():
    return int(os.environ.get('JUPYTERHUB_ACTIVITYMON_VOLUMES_UPDATE_INTERVAL', 3600))


def _get_docker_timeout():
    return int(os.environ.get('JUPYTERHUB_DOCKER_TIMEOUT', 360))


def _get_df_retry_delay():
    # cold-daemon df returns sizes mid-computation; wait this long between passes
    # until a complete one lands (DEF-7), instead of caching a partial snapshot.
    return int(os.environ.get('JUPYTERHUB_ACTIVITYMON_VOLUMES_DF_RETRY_DELAY', 15))


def _get_df_max_attempts():
    # safety net: cap the wait-for-complete passes so a permanently-degraded df
    # cannot pin a worker of the shared 4-worker executor forever.
    return int(os.environ.get('JUPYTERHUB_ACTIVITYMON_VOLUMES_DF_MAX_ATTEMPTS', 12))


def _load_persisted_volume_sizes():
    """Seed the in-memory cache from the persisted last-known snapshot.

    Uses the shared persisted_cache helper (TTL-gated, best-effort) so right
    after a restart the portal shows the last-known sizes instead of empty until
    the first background refresh replaces them.
    """
    global _volume_sizes_cache
    if _volume_sizes_cache['data'] and _volume_sizes_cache['timestamp']:
        return  # already have live data this process; do not regress to disk
    seeded = load_cached('volume_sizes')
    if seeded is None:
        return
    data, ts = seeded
    _volume_sizes_cache['data'] = data or {}
    _volume_sizes_cache['timestamp'] = ts


def configure_volume_cache(templates):
    """Set the canonical volume-name templates the cache uses to match disk volumes.

    `templates` maps suffix -> template string with literal "{username}" placeholder
    (e.g. {"home": "stellars-tech-ai-lab_jupyterlab_{username}_home", ...}). Same
    map produced by `get_user_volume_name_templates(DOCKER_SPAWNER_VOLUMES,
    COMPOSE_PROJECT_NAME)` and consumed by ManageVolumesHandler - keeps both code
    paths reading from one source of truth so e.g. a COMPOSE_PROJECT_NAME refactor
    only needs touching the templates helper, not this module.

    Each template is compiled to a regex that anchors the full volume name and
    captures the encoded username; _fetch_volume_sizes tries every regex per disk
    volume, first match wins.
    """
    global _volume_name_templates, _template_regexes
    _volume_name_templates = dict(templates)
    _template_regexes = []
    placeholder = re.escape('{username}')
    for suffix, template in _volume_name_templates.items():
        pattern = '^' + re.escape(template).replace(placeholder, '(.+)') + '$'
        _template_regexes.append((suffix, re.compile(pattern)))
    _get_logger().info(
        f"[Volume Sizes] Configured {len(_volume_name_templates)} name template(s): "
        f"{list(_volume_name_templates.keys())}"
    )
    _load_persisted_volume_sizes()


def _fetch_volume_sizes():
    """Fetch all user-volume sizes via `docker system df`. Returns (data, complete);
    `complete` is False when any matched volume is still mid-computation (df -1) or the
    call errored, so the caller never caches a partial snapshot (DEF-7)."""
    if not _template_regexes:
        _get_logger().warning(
            "[Volume Sizes] No volume-name templates configured; cache will be empty. "
            "Call configure_volume_cache(user_volume_name_templates) at hub startup."
        )
        return {}, False
    return _fetch_via_df()


def _fetch_via_df():
    """Read user-volume sizes from `docker system df` (type=volume, skips the slow
    image/container calc). Returns (data, complete). `complete` is False if any matched
    volume carries the lazy-df -1 sentinel (not yet computed) or the call errors - the
    caller waits for a complete pass instead of caching the partial result (DEF-7)."""
    try:
        import docker
        api_client = docker.APIClient(base_url='unix://var/run/docker.sock', timeout=_get_docker_timeout())
        try:
            df_data = api_client._get(api_client._url('/system/df'), params={'type': 'volume'}).json()
            volumes_data = df_data.get('Volumes', []) or []

            user_data = {}
            complete = True
            pending = 0
            for vol in volumes_data:
                name = vol.get('Name', '')
                for suffix, regex in _template_regexes:
                    m = regex.match(name)
                    if not m:
                        continue
                    encoded_username = m.group(1)
                    usage_data = vol.get('UsageData', {}) or {}
                    size_bytes = usage_data.get('Size', 0) or 0
                    if size_bytes < 0:
                        complete = False  # not-yet-computed (-1); skip + mark pass partial (DEF-7)
                        pending += 1
                        break
                    size_mb = round(size_bytes / (1024 * 1024), 1)

                    if encoded_username not in user_data:
                        user_data[encoded_username] = {"total": 0, "volumes": {}}
                    user_data[encoded_username]["total"] += size_mb
                    user_data[encoded_username]["volumes"][suffix] = size_mb
                    break  # first matching template wins

            for user in user_data:
                user_data[user]["total"] = round(user_data[user]["total"], 1)

            total_size = sum(u["total"] for u in user_data.values())
            if complete:
                _get_logger().info(f"[Volume Sizes] Fetched (complete): {len(user_data)} users, {total_size:.1f} MB")
            else:
                _get_logger().info(
                    f"[Volume Sizes] df still computing: {pending} user volume(s) pending (-1); "
                    "not caching this partial pass"
                )
            return user_data, complete
        finally:
            api_client.close()
    except Exception as e:
        _get_logger().error(f"[Volume Sizes] Error fetching: {e}")
        return {}, False


def _refresh_volume_sizes_sync():
    """Refresh the cache from df in a background executor thread (off the event loop).
    Caches ONLY a complete df pass; a cold daemon returns sizes mid-computation and
    caching that partial snapshot was DEF-7 (zeros stuck for the whole interval). Retries
    on a short delay until df has gathered every volume, bounded by a safety-net attempt
    cap so a degraded df cannot pin a worker of the shared executor forever."""
    global _volume_sizes_cache
    logger = _get_logger()

    if _volume_sizes_cache['refreshing']:
        logger.info("[Volume Sizes] Refresh already in progress, skipping")
        return

    _volume_sizes_cache['refreshing'] = True
    try:
        max_attempts = _get_df_max_attempts()
        retry_delay = _get_df_retry_delay()
        for attempt in range(1, max_attempts + 1):
            data, complete = _fetch_volume_sizes()
            if complete:
                _volume_sizes_cache['data'] = data
                _volume_sizes_cache['timestamp'] = datetime.now(timezone.utc)
                save_cached('volume_sizes', data)  # survive restarts: replace last-known on disk
                logger.info(f"[Volume Sizes] Cache updated: {len(data)} users")
                return
            if attempt >= max_attempts:
                logger.warning(
                    f"[Volume Sizes] df still partial after {max_attempts} attempts; "
                    "keeping previous cache, retrying at next interval"
                )
                return
            time.sleep(retry_delay)
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
        get_executor().submit(_refresh_volume_sizes_sync)
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
            return  # already scheduled; quiet - start() is called on every activity poll

        interval_ms = self.interval_seconds * 1000
        self.periodic_callback = PeriodicCallback(self._refresh_tick, interval_ms)
        self.periodic_callback.start()
        logger.info(f"[VolumeSizeRefresher] Started - refreshing every {self.interval_seconds}s")

        get_executor().submit(_refresh_volume_sizes_sync)

    def stop(self):
        if self.periodic_callback is not None:
            self.periodic_callback.stop()
            self.periodic_callback = None
            _get_logger().info("[VolumeSizeRefresher] Stopped")

    def _refresh_tick(self):
        if not _volume_sizes_cache['refreshing']:
            get_executor().submit(_refresh_volume_sizes_sync)
