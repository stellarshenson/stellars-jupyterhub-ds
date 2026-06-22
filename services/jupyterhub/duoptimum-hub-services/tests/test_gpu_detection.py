"""Tests for non-blocking GPU detection (resolve_gpu_mode).

The sidecar is stubbed so we never touch the network. Covers: a reachable
sidecar (detect + persist + bounded probe budget), a sidecar that is up but
answers empty falling back to the last-known persisted inventory, the no-seed
collapse to off (autodetect with nothing found), mode 0 never probing, and a
DOWN sidecar (probe_sidecar=False) resolving OFF even with a last-known on disk
- a sidecar that failed to start means GPU was not autodetected, never stale-on.
"""

import pytest

from duoptimum_hub_services import gpu
from duoptimum_hub_services import gpu_client


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("JUPYTERHUB_CACHED_DATA_TTL_MINUTES", raising=False)
    return tmp_path


def _stub_payload(monkeypatch, payload):
    """Make the sidecar client return `payload` and record the probe budget."""
    calls = {"n": 0, "kwargs": None}

    def fake(**kwargs):
        calls["n"] += 1
        calls["kwargs"] = kwargs
        return payload

    monkeypatch.setattr(gpu_client, "fetch_payload_with_retry", fake)
    return calls


REACHABLE = {"gpus": [{"index": 0, "name": "NVIDIA A100", "uuid": "GPU-abc", "memory_total_mb": 80000}]}


def test_reachable_detects_persists_and_uses_bounded_probe(monkeypatch, _data_dir):
    calls = _stub_payload(monkeypatch, REACHABLE)
    enabled, detected, gpus = gpu.resolve_gpu_mode(2, probe_sidecar=True)
    assert (enabled, detected) == (1, 1)
    assert gpus and gpus[0]["uuid"] == "GPU-abc"
    # bounded boot probe (~5s worst case), not the old 20x1s
    assert calls["kwargs"] == {"attempts": 3, "delay": 0.5, "timeout": 1}
    assert (_data_dir / "gpu_inventory.json").exists()


def test_up_but_empty_probe_seeds_from_last_known(monkeypatch, _data_dir):
    # sidecar IS up (probe_sidecar=True) but the live probe answers empty (cold/slow
    # start) -> reuse the persisted last-known so a present-but-slow sidecar does not
    # flap GPU off for the whole session (Invariant 3)
    _stub_payload(monkeypatch, REACHABLE)
    gpu.resolve_gpu_mode(2, probe_sidecar=True)  # persist last-known
    _stub_payload(monkeypatch, None)             # live probe now empty
    enabled, detected, gpus = gpu.resolve_gpu_mode(2, probe_sidecar=True)
    assert (enabled, detected) == (1, 1)
    assert gpus and gpus[0]["uuid"] == "GPU-abc"


def test_up_but_empty_no_seed_mode2_off(monkeypatch, _data_dir):
    # sidecar up, probe empty, nothing persisted -> off
    _stub_payload(monkeypatch, None)
    assert gpu.resolve_gpu_mode(2, probe_sidecar=True) == (0, 0, [])


def test_up_but_empty_no_seed_mode1_off(monkeypatch, _data_dir):
    # mode 1 autodetect (no forced-on): up + empty probe + no last-known -> off
    _stub_payload(monkeypatch, None)
    assert gpu.resolve_gpu_mode(1, probe_sidecar=True) == (0, 0, [])


def test_mode0_never_probes(monkeypatch, _data_dir):
    calls = _stub_payload(monkeypatch, REACHABLE)
    assert gpu.resolve_gpu_mode(0) == (0, 0, [])
    assert calls["n"] == 0


def test_probe_sidecar_false_skips_probe(monkeypatch, _data_dir):
    calls = _stub_payload(monkeypatch, REACHABLE)
    enabled, detected, gpus = gpu.resolve_gpu_mode(2, probe_sidecar=False)
    assert (enabled, detected, gpus) == (0, 0, [])
    assert calls["n"] == 0  # a known-down sidecar is never probed -> no stall


def test_probe_sidecar_false_off_even_with_last_known(monkeypatch, _data_dir):
    # A down sidecar (probe_sidecar=False) means GPU was NOT autodetected. Even with a
    # last-known inventory persisted on disk, the mode MUST resolve OFF - the hub cannot
    # back GPUs the absent sidecar is not there to confirm, and attaching device_requests
    # from a stale snapshot crashes every gpu-access spawn in the nvidia prestart hook.
    _stub_payload(monkeypatch, REACHABLE)
    gpu.resolve_gpu_mode(2, probe_sidecar=True)  # persist a last-known inventory
    calls = _stub_payload(monkeypatch, REACHABLE)
    # Invariant 1 guard: the down path must not even READ the cache (the early return
    # sits before any load_cached), so a future refactor cannot reintroduce stale-on.
    reads = {"n": 0}
    orig_load = gpu.load_cached
    def _counting_load(*a, **k):
        reads["n"] += 1
        return orig_load(*a, **k)
    monkeypatch.setattr(gpu, "load_cached", _counting_load)
    assert gpu.resolve_gpu_mode(2, probe_sidecar=False) == (0, 0, [])
    assert calls["n"] == 0  # a down sidecar is never probed
    assert reads["n"] == 0  # nor is the persisted inventory ever read on the down path
