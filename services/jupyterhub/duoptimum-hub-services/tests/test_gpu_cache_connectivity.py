"""gpu_sidecar_connected() - the LIVE sidecar-reachability signal that gates GPU
display (DEF-4).

The GPU inventory is enumerated once at startup and seeded from a persisted cache
that can be hours old, so it OUTLIVES the gpuinfo-nvidia sidecar. "GPU available" is
(a) the sidecar is live AND (b) GPUs are detected, with a -> b: there is no b without
a. `gpu_sidecar_connected()` is the (a) signal: true ONLY when the latest utilisation
sample SUCCEEDED and is fresh. An empty sample (sidecar down/absent) sets last_ok
False; a stalled refresher ages the last attempt past the staleness window.
"""

from datetime import datetime, timedelta, timezone

import pytest

from duoptimum_hub_services import gpu_cache


@pytest.fixture(autouse=True)
def _reset_cache():
    """Snapshot/restore the module cache so a test never leaks into the next."""
    saved = dict(gpu_cache._gpu_util_cache)
    gpu_cache._gpu_util_cache.update(
        {'data': {}, 'timestamp': None, 'refreshing': False, 'last_attempt': None, 'last_ok': False}
    )
    yield
    gpu_cache._gpu_util_cache.clear()
    gpu_cache._gpu_util_cache.update(saved)


def _set(last_ok, age_seconds):
    gpu_cache._gpu_util_cache['last_ok'] = last_ok
    gpu_cache._gpu_util_cache['last_attempt'] = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)


def test_disconnected_before_any_sample():
    # cold start: no attempt yet -> not connected (hide GPUs until a live sample lands)
    assert gpu_cache.gpu_sidecar_connected() is False


def test_disconnected_when_last_sample_failed():
    # sidecar down/absent -> empty sample -> last_ok False -> disconnected even when recent
    _set(last_ok=False, age_seconds=1)
    assert gpu_cache.gpu_sidecar_connected() is False


def test_connected_when_recent_success():
    _set(last_ok=True, age_seconds=5)
    assert gpu_cache.gpu_sidecar_connected() is True


def test_disconnected_when_success_is_stale():
    # refresher stalled: the last success aged past the staleness window -> disconnected
    interval = gpu_cache._get_update_interval()
    stale = max(2 * interval, 90) + 5
    _set(last_ok=True, age_seconds=stale)
    assert gpu_cache.gpu_sidecar_connected() is False


def test_refresh_records_attempt_and_flips_on_empty(monkeypatch):
    # an empty fetch (sidecar down) records last_ok False; a later non-empty fetch
    # (even all-idle 0% GPUs) records True -> connected. Idle != disconnected.
    monkeypatch.setattr(gpu_cache, '_fetch_gpu_utilization', lambda: {})
    gpu_cache._refresh_sync()
    assert gpu_cache._gpu_util_cache['last_ok'] is False
    assert gpu_cache._gpu_util_cache['last_attempt'] is not None
    assert gpu_cache.gpu_sidecar_connected() is False

    monkeypatch.setattr(gpu_cache, '_fetch_gpu_utilization', lambda: {'0': {'utilization': 0}})
    gpu_cache._refresh_sync()
    assert gpu_cache._gpu_util_cache['last_ok'] is True
    assert gpu_cache.gpu_sidecar_connected() is True
