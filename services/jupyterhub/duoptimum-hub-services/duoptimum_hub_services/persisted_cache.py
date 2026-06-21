"""Last-known cached data, persisted across hub restarts.

Slow server-side aggregates (volume sizes, GPU inventory, ...) are cached in
memory and refreshed in the background so the portal answers instantly. Those
in-memory caches start cold on every boot, though - so right after a restart the
portal shows nothing until the first slow refresh finishes.

This module is the shared "keep the last state, serve it, refresh in background"
mechanism: each consumer persists its last good snapshot as
``{timestamp, data}`` JSON on the data volume and seeds itself from that file on
boot. The snapshot is used only while it is recent enough - older than
``JUPYTERHUB_CACHED_DATA_TTL_MINUTES`` (default 24h) it is ignored, so we never
show genuinely stale data; we just bridge the gap until the first refresh.

Best-effort throughout: any IO/parse failure degrades to "no seed" and never
raises, so a missing or corrupt file can never block hub startup.
"""

import json
import os
import tempfile
from datetime import datetime, timezone

from .logging_setup import log


def _persist_dir():
    return os.environ.get('JUPYTERHUB_DATA_DIR', '/data')


def _persist_path(name):
    return os.path.join(_persist_dir(), f'{name}.json')


def _ttl_seconds():
    """Max age a persisted snapshot may have to still seed a cache on boot.

    Configured in minutes via JUPYTERHUB_CACHED_DATA_TTL_MINUTES (default 24h).
    """
    return int(os.environ.get('JUPYTERHUB_CACHED_DATA_TTL_MINUTES', 60 * 24)) * 60


def save_cached(name, data):
    """Atomically persist ``data`` as the last-known snapshot for ``name``.

    Writes ``{timestamp, data}`` via tempfile + os.replace so a crash mid-write
    can't corrupt the seed. Best-effort: logs a warning and returns on failure.
    """
    path = _persist_path(name)
    payload = {'timestamp': datetime.now(timezone.utc).isoformat(), 'data': data}
    try:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=f'.{name}-', suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(payload, f)
            os.replace(tmp, path)  # atomic swap
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except Exception as e:
        log.warning(f"[Cache] Could not persist '{name}' to {path}: {e}")


def load_cached(name):
    """Return ``(data, timestamp)`` for ``name`` if the snapshot is recent enough.

    Returns None when the file is missing, unreadable, or older than the TTL -
    the caller then shows nothing until its first refresh. Never raises.
    """
    path = _persist_path(name)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            payload = json.load(f)
        ts = datetime.fromisoformat(payload['timestamp'])
        data = payload.get('data')
    except Exception as e:
        log.warning(f"[Cache] Ignoring unreadable persisted '{name}' at {path}: {e}")
        return None

    age = (datetime.now(timezone.utc) - ts).total_seconds()
    ttl = _ttl_seconds()
    if age > ttl:
        log.info(
            f"[Cache] Persisted '{name}' is stale ({age / 3600:.1f}h > {ttl / 3600:.0f}h TTL); "
            "ignoring until first refresh"
        )
        return None
    log.info(f"[Cache] Seeded '{name}' from persisted state ({age / 3600:.1f}h old)")
    return data, ts
