"""Activity-gated container-stats cache - the shared stats math, snapshot
staleness, and the refresh-trigger gating that keeps it lightweight (sample only
recently-active users, never when all idle). Exercised without real Docker.
"""

from datetime import datetime, timedelta, timezone

import pytest

from duoptimum_hub_services import container_stats_cache as csc
from duoptimum_hub_services.docker_utils import stats_from_container


# ── stats_from_container (shared math) ───────────────────────────────────────

class _FakeContainer:
    def __init__(self, stats, attrs, raise_stats=False):
        self._stats = stats
        self.attrs = attrs
        self._raise = raise_stats

    def stats(self, stream=False):
        if self._raise:
            raise RuntimeError("docker stats failed")
        return self._stats


def _stats_payload():
    return {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 200},
            "system_cpu_usage": 2000,
            "online_cpus": 4,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 100},
            "system_cpu_usage": 1000,
        },
        "memory_stats": {"usage": 512 * 1024 * 1024, "limit": 8 * 1024 ** 3},
    }


def test_stats_from_container_limited():
    # cpu_delta=100, system_delta=1000, online=4 -> 0.1*4*100 = 40%
    # NanoCpus 2e9 -> 2.0 cores limited; Memory 1GiB -> 512/1024 = 50%
    c = _FakeContainer(
        _stats_payload(),
        {"HostConfig": {"NanoCpus": 2_000_000_000, "Memory": 1024 * 1024 * 1024},
         "Image": "sha256:abc"},
    )
    out = stats_from_container(c)
    assert out["cpu_percent"] == 40.0
    assert out["cpu_cores"] == 2.0 and out["cpu_cores_limited"] is True
    assert out["memory_mb"] == 512.0
    assert out["memory_percent"] == 50.0
    assert out["memory_total_mb"] == 1024.0 and out["memory_limited"] is True
    assert out["image_id"] == "sha256:abc"


def test_stats_from_container_unlimited_falls_back_to_host():
    # no NanoCpus/Memory -> cores = online_cpus (unlimited); mem total = stats limit
    c = _FakeContainer(_stats_payload(), {"HostConfig": {}, "Image": "sha256:x"})
    out = stats_from_container(c)
    assert out["cpu_cores"] == 4 and out["cpu_cores_limited"] is False
    assert out["memory_limited"] is False
    assert out["memory_total_mb"] == round(8 * 1024 ** 3 / (1024 * 1024), 1)


def test_stats_from_container_none_on_error():
    c = _FakeContainer({}, {}, raise_stats=True)
    assert stats_from_container(c) is None


# ── snapshot staleness + trigger gating ──────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_cache():
    csc._container_stats_cache = {'data': {}, 'timestamp': None, 'refreshing': False}
    yield
    csc._container_stats_cache = {'data': {}, 'timestamp': None, 'refreshing': False}


class _FakeExecutor:
    def __init__(self):
        self.submitted = []

    def submit(self, fn, *args):
        self.submitted.append((fn, args))


@pytest.fixture
def fake_executor(monkeypatch):
    ex = _FakeExecutor()
    # get_container_stats_with_refresh does `from .docker_utils import get_executor`
    # at call time, so patching the attribute on docker_utils is picked up.
    import duoptimum_hub_services.docker_utils as du
    monkeypatch.setattr(du, "get_executor", lambda: ex)
    return ex


def test_needs_refresh_when_never_sampled():
    _, needs = csc.get_cached_container_stats()
    assert needs is True  # timestamp None


def test_fresh_timestamp_not_stale(monkeypatch):
    csc._container_stats_cache['timestamp'] = datetime.now(timezone.utc)
    _, needs = csc.get_cached_container_stats()
    assert needs is False


def test_old_timestamp_is_stale():
    csc._container_stats_cache['timestamp'] = datetime.now(timezone.utc) - timedelta(hours=1)
    _, needs = csc.get_cached_container_stats()
    assert needs is True


def test_no_refresh_when_no_active_user(fake_executor):
    # stale (never sampled) but no active users -> no docker work submitted
    csc.get_container_stats_with_refresh(set())
    assert fake_executor.submitted == []


def test_refresh_submitted_when_active_and_stale(fake_executor):
    data = csc.get_container_stats_with_refresh({"alice"})
    assert data is csc._container_stats_cache['data']
    assert len(fake_executor.submitted) == 1
    fn, args = fake_executor.submitted[0]
    assert fn is csc._refresh_active_container_stats
    assert args == ({"alice"},)


def test_no_refresh_when_fresh(fake_executor):
    csc._container_stats_cache['timestamp'] = datetime.now(timezone.utc)
    csc.get_container_stats_with_refresh({"alice"})
    assert fake_executor.submitted == []  # snapshot still fresh


def test_no_refresh_while_already_refreshing(fake_executor):
    csc._container_stats_cache['refreshing'] = True
    csc.get_container_stats_with_refresh({"alice"})
    assert fake_executor.submitted == []
