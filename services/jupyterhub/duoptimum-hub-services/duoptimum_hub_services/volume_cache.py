"""Background volume sizes cache with periodic refresh.

Uses docker system df to get volume usage data. This is a slow API call
(can take minutes) but runs in a background thread - the activity page
returns cached data immediately and never blocks on this.

Volume-name parsing is driven by templates configured at hub startup via
set_volume_name_templates() - the same map used by ManageVolumesHandler so
both code paths agree on what an on-disk volume is called. Each template
(e.g. "stellars-tech-ai-lab_jupyterlab_{username}_home") is compiled to a
regex with a capturing username group; disk volumes are matched against
all templates and the first hit wins.
"""

import logging
import os
import re
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


def _volume_mount_root():
    """Read-only host bind-mount of the Docker volumes dir, or '' to use df.

    When set (and present) the cache measures only the user volumes by walking
    `<root>/<volume>/_data` directly - deterministic and fast. Absent (e.g. Docker
    Desktop, where the path lives in the VM) -> fall back to `docker system df`.
    """
    return os.environ.get('JUPYTERHUB_DOCKER_VOLUMES_DIR', '/host-docker-volumes')


def _du_bytes(path):
    """Apparent size of `path` in bytes via `du -sb`. Returns 0 for a genuinely
    empty/absent data dir, None on an error (so the caller can SKIP it rather than
    poison the total with a fake 0 - the partial-result bug DEF-7)."""
    import subprocess
    if not os.path.isdir(path):
        return 0  # volume exists but no _data yet -> genuinely empty, not an error
    try:
        out = subprocess.run(
            ['du', '-sb', path], capture_output=True, text=True, timeout=_get_docker_timeout()
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        return int(out.stdout.split()[0])
    except Exception:
        return None


def _fetch_via_du(root):
    """Measure ONLY the user volumes by du-ing their `_data` dirs in parallel.

    Discovers volumes by listing `root` and matching the configured templates (same
    rule as the df path), then du's each match concurrently. A du that errors is
    SKIPPED, never recorded as 0, so a partial/incomplete pass is detectable (fewer
    users) instead of silently reporting zeros. Deterministic: du blocks until done.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    try:
        names = os.listdir(root)
    except OSError as e:
        _get_logger().error(f"[Volume Sizes] Cannot list volume root {root}: {e}")
        return {}

    matched = []  # (encoded_username, suffix, data_path)
    for name in names:
        for suffix, regex in _template_regexes:
            m = regex.match(name)
            if m:
                matched.append((m.group(1), suffix, os.path.join(root, name, '_data')))
                break  # first matching template wins

    if not matched:
        _get_logger().info(f"[Volume Sizes] No user volumes found under {root}")
        return {}

    user_data = {}
    skipped = 0
    with ThreadPoolExecutor(max_workers=min(8, len(matched)), thread_name_prefix="vol-du") as ex:
        futs = {ex.submit(_du_bytes, p): (u, s) for (u, s, p) in matched}
        for fut in as_completed(futs):
            encoded_username, suffix = futs[fut]
            size_bytes = fut.result()
            if size_bytes is None:
                skipped += 1
                continue
            size_mb = round(size_bytes / (1024 * 1024), 1)
            d = user_data.setdefault(encoded_username, {"total": 0.0, "volumes": {}})
            d["total"] += size_mb
            d["volumes"][suffix] = size_mb

    for u in user_data:
        user_data[u]["total"] = round(user_data[u]["total"], 1)

    total_size = sum(u["total"] for u in user_data.values())
    _get_logger().info(
        f"[Volume Sizes] Measured (du): {len(user_data)} users, {total_size:.1f} MB"
        + (f" ({skipped} volume(s) skipped on error)" if skipped else "")
    )
    return user_data


def _fetch_volume_sizes():
    """Fetch sizes of all user volumes. Targeted parallel du when the volume root is
    bind-mounted (deterministic + fast); else fall back to docker system df."""
    if not _template_regexes:
        _get_logger().warning(
            "[Volume Sizes] No volume-name templates configured; cache will be empty. "
            "Call configure_volume_cache(user_volume_name_templates) at hub startup."
        )
        return {}

    root = _volume_mount_root()
    if root and os.path.isdir(root):
        return _fetch_via_du(root)
    return _fetch_via_df()


def _fetch_via_df():
    """Fallback: fetch sizes via docker system df (blocking, slow, scans ALL volumes;
    can return a PARTIAL mid-scan snapshot - DEF-7 - so used only without the bind-mount)."""
    try:
        import docker
        api_client = docker.APIClient(base_url='unix://var/run/docker.sock', timeout=_get_docker_timeout())
        try:
            # type=volume skips slow image/container calculations (~10s vs ~360s)
            df_data = api_client._get(api_client._url('/system/df'), params={'type': 'volume'}).json()
            volumes_data = df_data.get('Volumes', []) or []

            user_data = {}
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
                        continue  # lazy-df sentinel (-1) for not-yet-computed; skip, don't record garbage (DEF-7)
                    size_mb = round(size_bytes / (1024 * 1024), 1)

                    if encoded_username not in user_data:
                        user_data[encoded_username] = {"total": 0, "volumes": {}}
                    user_data[encoded_username]["total"] += size_mb
                    user_data[encoded_username]["volumes"][suffix] = size_mb
                    break  # first matching template wins

            for user in user_data:
                user_data[user]["total"] = round(user_data[user]["total"], 1)

            total_size = sum(u["total"] for u in user_data.values())
            _get_logger().info(f"[Volume Sizes] Fetched: {len(user_data)} users, {total_size:.1f} MB")
            return user_data
        finally:
            api_client.close()
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
            save_cached('volume_sizes', data)  # survive restarts: replace last-known on disk
            logger.info(f"[Volume Sizes] Cache updated: {len(data)} users")
        else:
            logger.warning("[Volume Sizes] Refresh returned empty - keeping previous cache")
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
