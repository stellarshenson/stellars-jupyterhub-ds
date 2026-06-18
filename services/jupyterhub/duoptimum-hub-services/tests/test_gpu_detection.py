"""Tests for non-blocking GPU detection (resolve_gpu_mode).

The sidecar is stubbed so we never touch the network. Covers: a reachable
sidecar (detect + persist + bounded probe budget), an unreachable sidecar that
falls back to the last-known persisted inventory, the no-seed collapse (mode 2
off / mode 1 forced-on-empty), mode 0 never probing, and probe_sidecar=False
skipping the probe entirely so a missing sidecar can never stall boot.
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


def test_unreachable_falls_back_to_last_known(monkeypatch, _data_dir):
    # first a reachable probe persists the inventory
    _stub_payload(monkeypatch, REACHABLE)
    gpu.resolve_gpu_mode(2, probe_sidecar=True)
    # now the sidecar is unreachable -> seed from the persisted last-known
    _stub_payload(monkeypatch, None)
    enabled, detected, gpus = gpu.resolve_gpu_mode(2, probe_sidecar=True)
    assert (enabled, detected) == (1, 1)
    assert gpus and gpus[0]["uuid"] == "GPU-abc"


def test_unreachable_no_seed_mode2_off(monkeypatch, _data_dir):
    _stub_payload(monkeypatch, None)
    assert gpu.resolve_gpu_mode(2, probe_sidecar=True) == (0, 0, [])


def test_unreachable_no_seed_mode1_forced_on_empty(monkeypatch, _data_dir):
    _stub_payload(monkeypatch, None)
    assert gpu.resolve_gpu_mode(1, probe_sidecar=True) == (1, 0, [])


def test_mode0_never_probes(monkeypatch, _data_dir):
    calls = _stub_payload(monkeypatch, REACHABLE)
    assert gpu.resolve_gpu_mode(0) == (0, 0, [])
    assert calls["n"] == 0


def test_probe_sidecar_false_skips_probe(monkeypatch, _data_dir):
    calls = _stub_payload(monkeypatch, REACHABLE)
    enabled, detected, gpus = gpu.resolve_gpu_mode(2, probe_sidecar=False)
    assert (enabled, detected, gpus) == (0, 0, [])
    assert calls["n"] == 0  # a known-down sidecar is never probed -> no stall


def test_probe_sidecar_false_uses_last_known(monkeypatch, _data_dir):
    _stub_payload(monkeypatch, REACHABLE)
    gpu.resolve_gpu_mode(2, probe_sidecar=True)  # persist
    calls = _stub_payload(monkeypatch, REACHABLE)
    enabled, detected, gpus = gpu.resolve_gpu_mode(2, probe_sidecar=False)
    assert (enabled, detected) == (1, 1)
    assert gpus and gpus[0]["uuid"] == "GPU-abc"
    assert calls["n"] == 0  # seeded from disk, still no probe
