"""Tests for the host-status provider abstraction.

Covers the DockerHostStatusProvider contract (capabilities subset, status shape,
GPU gating + degradation) and resolve_host_status_provider (declared vs none).
The /proc helpers have their own tests (test_host_cpu / test_host_memory); here
they are monkeypatched so the provider logic is exercised in isolation.
"""

import duoptimum_hub_services.host_status as hs
from duoptimum_hub_services.host_status import (
    CPU,
    DEGRADED,
    GPU,
    MEM,
    OK,
    UNAVAILABLE,
    DockerHostStatusProvider,
    HostStatusProvider,
    resolve_host_status_provider,
)


def _patch_proc(monkeypatch, cores=8, mem_mb=64000.0):
    monkeypatch.setattr(hs, "_host_cpu_count", lambda: cores)
    monkeypatch.setattr(hs, "_host_total_memory_mb", lambda: mem_mb)


def _patch_gpu_cache(monkeypatch, connected=True, util=None):
    import duoptimum_hub_services.gpu_cache as gc

    monkeypatch.setattr(gc, "gpu_sidecar_connected", lambda: connected)
    monkeypatch.setattr(gc, "get_gpu_utilization_with_refresh", lambda: util or {})


_ONE_GPU = [{"index": 0, "name": "NVIDIA A100", "uuid": "GPU-abc", "memory_mb": 81920}]


def test_capabilities_cpu_mem_only_when_gpu_off():
    p = DockerHostStatusProvider({"gpu_enabled": False})
    assert p.capabilities() == {CPU, MEM}


def test_capabilities_includes_gpu_when_enabled():
    p = DockerHostStatusProvider({"gpu_enabled": True, "gpu_list": _ONE_GPU})
    assert p.capabilities() == {CPU, MEM, GPU}


def test_status_keys_are_subset_of_capabilities(monkeypatch):
    _patch_proc(monkeypatch)
    _patch_gpu_cache(monkeypatch, connected=True, util={})
    p = DockerHostStatusProvider({"gpu_enabled": True, "gpu_list": _ONE_GPU})
    assert set(p.get_status().keys()) <= p.capabilities()


def test_status_cpu_mem_ok_with_real_values(monkeypatch):
    _patch_proc(monkeypatch, cores=8, mem_mb=64000.0)
    p = DockerHostStatusProvider({"gpu_enabled": False})
    status = p.get_status()
    assert status[CPU] == {"host_total_cores": 8, "status": OK}
    assert status[MEM] == {"host_total_mb": 64000.0, "status": OK}
    assert GPU not in status  # not a capability -> absent, not unavailable


def test_status_cpu_mem_unavailable_on_proc_failure(monkeypatch):
    _patch_proc(monkeypatch, cores=None, mem_mb=None)
    p = DockerHostStatusProvider({"gpu_enabled": False})
    status = p.get_status()
    assert status[CPU]["host_total_cores"] is None
    assert status[CPU]["status"] == UNAVAILABLE
    assert status[MEM]["status"] == UNAVAILABLE


def test_gpu_ok_when_connected_with_sample(monkeypatch):
    _patch_proc(monkeypatch)
    util = {"0": {"utilization": 42, "memory_used_mb": 1000, "temperature_c": 40, "power_w": 120, "processes": []}}
    _patch_gpu_cache(monkeypatch, connected=True, util=util)
    p = DockerHostStatusProvider({"gpu_enabled": True, "gpu_list": _ONE_GPU})
    gpu = p.get_status()[GPU]
    assert gpu["connected"] is True
    assert gpu["status"] == OK
    assert gpu["devices"][0]["utilization"] == 42
    assert gpu["devices"][0]["name"] == "NVIDIA A100"


def test_gpu_degraded_when_inventory_but_sidecar_down(monkeypatch):
    """Stale inventory, no live sample -> degraded (not unavailable)."""
    _patch_proc(monkeypatch)
    _patch_gpu_cache(monkeypatch, connected=False, util={})
    p = DockerHostStatusProvider({"gpu_enabled": True, "gpu_list": _ONE_GPU})
    gpu = p.get_status()[GPU]
    assert gpu["connected"] is False
    assert gpu["status"] == DEGRADED
    assert len(gpu["devices"]) == 1  # inventory still listed


def test_gpu_unavailable_when_no_inventory(monkeypatch):
    """GPU a capability but zero devices enumerated -> unavailable, empty list."""
    _patch_proc(monkeypatch)
    p = DockerHostStatusProvider({"gpu_enabled": True, "gpu_list": []})
    gpu = p.get_status()[GPU]
    assert gpu["devices"] == []
    assert gpu["connected"] is False
    assert gpu["status"] == UNAVAILABLE


def test_cpu_mem_unaffected_by_gpu_state(monkeypatch):
    """A down sidecar degrades only GPU; CPU/MEM keep their real values."""
    _patch_proc(monkeypatch, cores=4, mem_mb=32000.0)
    _patch_gpu_cache(monkeypatch, connected=False, util={})
    p = DockerHostStatusProvider({"gpu_enabled": True, "gpu_list": _ONE_GPU})
    status = p.get_status()
    assert status[CPU]["status"] == OK
    assert status[MEM]["status"] == OK
    assert status[GPU]["status"] == DEGRADED


def test_serializable(monkeypatch):
    """get_status() is plain JSON-serializable data, no provider object leaks."""
    import json

    _patch_proc(monkeypatch)
    _patch_gpu_cache(monkeypatch, connected=True, util={})
    p = DockerHostStatusProvider({"gpu_enabled": True, "gpu_list": _ONE_GPU})
    json.dumps(p.get_status())  # raises if not serializable


def test_none_context_defaults_gpu_off():
    """No context -> GPU not a capability, no crash (a dumb/no-info spawner)."""
    p = DockerHostStatusProvider(None)
    assert p.capabilities() == {CPU, MEM}


def test_empty_context_defaults_gpu_off():
    p = DockerHostStatusProvider({})
    assert GPU not in p.capabilities()


def test_gpu_device_merges_live_sample(monkeypatch):
    """A live sample is merged onto the inventory device by index."""
    _patch_proc(monkeypatch)
    util = {"0": {"utilization": 77, "memory_used_mb": 2048, "temperature_c": 55, "power_w": 200, "processes": [{"pid": 1}]}}
    _patch_gpu_cache(monkeypatch, connected=True, util=util)
    p = DockerHostStatusProvider({"gpu_enabled": True, "gpu_list": _ONE_GPU})
    dev = p.get_status()[GPU]["devices"][0]
    assert dev["utilization"] == 77
    assert dev["memory_used_mb"] == 2048
    assert dev["temperature_c"] == 55
    assert dev["power_w"] == 200
    assert dev["processes"] == [{"pid": 1}]


def test_gpu_device_inventory_only_without_sample(monkeypatch):
    """Connected but no per-index sample -> inventory fields only, no util keys."""
    _patch_proc(monkeypatch)
    _patch_gpu_cache(monkeypatch, connected=True, util={})
    p = DockerHostStatusProvider({"gpu_enabled": True, "gpu_list": _ONE_GPU})
    dev = p.get_status()[GPU]["devices"][0]
    assert dev["name"] == "NVIDIA A100"
    assert dev["uuid"] == "GPU-abc"
    assert dev["memory_mb"] == 81920
    assert "utilization" not in dev


# ── resolve_host_status_provider ──────────────────────────────────────────────

class _SpawnerWithProvider:
    host_status_provider_class = DockerHostStatusProvider


class _SpawnerWithoutProvider:
    pass


def test_resolve_returns_provider_instance():
    p = resolve_host_status_provider(_SpawnerWithProvider, {"gpu_enabled": False})
    assert isinstance(p, DockerHostStatusProvider)
    assert isinstance(p, HostStatusProvider)


def test_resolve_none_when_spawner_declares_no_provider():
    assert resolve_host_status_provider(_SpawnerWithoutProvider, {}) is None


def test_resolve_imports_dotted_string():
    p = resolve_host_status_provider(
        "duoptimum_hub_services.spawner.DuoptimumDockerSpawner",
        {"gpu_enabled": False},
    )
    assert isinstance(p, DockerHostStatusProvider)


def test_resolve_passes_context_to_provider():
    """The resolved provider reflects the boot context it was constructed with."""
    p = resolve_host_status_provider(_SpawnerWithProvider, {"gpu_enabled": True, "gpu_list": _ONE_GPU})
    assert p.capabilities() == {CPU, MEM, GPU}


def test_resolve_none_context_ok():
    p = resolve_host_status_provider(_SpawnerWithProvider, None)
    assert isinstance(p, DockerHostStatusProvider)
    assert p.capabilities() == {CPU, MEM}
