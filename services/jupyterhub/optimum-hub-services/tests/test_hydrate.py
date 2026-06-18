"""Startup hydration (hydrate.py).

The consolidated startup-hydration entry and the shared refresher-start helper are
importable from the package, and start_activity_refreshers starts exactly the
right refreshers (GPU utilisation only when the host has GPUs). The full
schedule_startup_hydration orchestration needs a live hub + IOLoop, so it is
exercised in the functional harness; here we lock in the importable surface and the
GPU gating that the /activity handler also relies on.
"""


def test_hydration_entry_importable():
    from optimum_hub_services import schedule_startup_hydration, start_activity_refreshers
    assert callable(schedule_startup_hydration)
    assert callable(start_activity_refreshers)


def test_start_activity_refreshers_gates_gpu(monkeypatch):
    from optimum_hub_services import start_activity_refreshers
    from optimum_hub_services import volume_cache, container_size_cache, gpu_cache

    started = []

    class _Stub:
        def __init__(self, label):
            self.label = label

        def start(self):
            started.append(self.label)

    monkeypatch.setattr(volume_cache.VolumeSizeRefresher, "get_instance",
                        classmethod(lambda cls: _Stub("vol")))
    monkeypatch.setattr(container_size_cache.ContainerSizeRefresher, "get_instance",
                        classmethod(lambda cls: _Stub("ctr")))
    monkeypatch.setattr(gpu_cache.GpuUtilizationRefresher, "get_instance",
                        classmethod(lambda cls: _Stub("gpu")))

    # no GPUs -> volume + container size only, GPU utilisation NOT started
    start_activity_refreshers(gpu_list=[])
    assert started == ["vol", "ctr"]

    # GPUs present -> GPU utilisation refresher also started
    started.clear()
    start_activity_refreshers(gpu_list=[{"index": "0"}])
    assert started == ["vol", "ctr", "gpu"]
