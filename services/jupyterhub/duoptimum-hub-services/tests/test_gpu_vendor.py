"""GPU vendor abstraction - the provider contract.

`GpuVendorProvider` owns the vendor-specific GPU passthrough decisions (driver,
runtime, visibility env). `NvidiaGpuProvider` is the active reference; it must
reproduce the exact literals the policy engine + sidecar used before the seam.
Per-spawn delegation through `ApplyContext.gpu_vendor` is covered in
test_policy_apply.py; the sidecar runtime in test_gpuinfo_sidecar.py.
"""

from duoptimum_hub_services.gpu_vendor import (
    GpuVendorProvider,
    NvidiaGpuProvider,
    resolve_gpu_vendor_provider,
)


def _nvidia():
    return NvidiaGpuProvider()


# ── identity / runtime ─────────────────────────────────────────────────────────

def test_name_is_nvidia():
    assert _nvidia().name == "nvidia"


def test_runtime_name_is_nvidia():
    assert _nvidia().runtime_name() == "nvidia"


# ── device_request ─────────────────────────────────────────────────────────────

def test_device_request_all():
    assert _nvidia().device_request(True, []) == {
        "Driver": "nvidia", "Count": -1, "Capabilities": [["gpu"]]}


def test_device_request_all_ignores_ids():
    # all_gpus wins even if ids are present
    assert _nvidia().device_request(True, ["0", "1"]) == {
        "Driver": "nvidia", "Count": -1, "Capabilities": [["gpu"]]}


def test_device_request_subset():
    assert _nvidia().device_request(False, ["0", "2"]) == {
        "Driver": "nvidia", "DeviceIDs": ["0", "2"], "Capabilities": [["gpu"]]}


def test_device_request_empty_ids_falls_back_to_all():
    assert _nvidia().device_request(False, []) == {
        "Driver": "nvidia", "Count": -1, "Capabilities": [["gpu"]]}


# ── visibility_env ─────────────────────────────────────────────────────────────

def test_visibility_env_no_access_is_void():
    # None means UNSET; void overrides the image's baked-in 'all'
    assert _nvidia().visibility_env(False, True, [], {}) == {
        "NVIDIA_VISIBLE_DEVICES": "void", "CUDA_VISIBLE_DEVICES": None}


def test_visibility_env_all():
    assert _nvidia().visibility_env(True, True, [], {}) == {
        "NVIDIA_VISIBLE_DEVICES": "all", "CUDA_VISIBLE_DEVICES": None}


def test_visibility_env_subset_with_uuid_map():
    assert _nvidia().visibility_env(True, False, ["0", "2"], {"0": "U0", "2": "U2"}) == {
        "NVIDIA_VISIBLE_DEVICES": "0,2", "CUDA_VISIBLE_DEVICES": "U0,U2"}


def test_visibility_env_subset_no_uuid_falls_back_to_indices():
    assert _nvidia().visibility_env(True, False, ["1"], {}) == {
        "NVIDIA_VISIBLE_DEVICES": "1", "CUDA_VISIBLE_DEVICES": "1"}


def test_visibility_env_subset_partial_uuid_map():
    # only known indices contribute UUIDs; absent ones drop from the UUID list
    out = _nvidia().visibility_env(True, False, ["0", "2"], {"0": "U0"})
    assert out["NVIDIA_VISIBLE_DEVICES"] == "0,2"
    assert out["CUDA_VISIBLE_DEVICES"] == "U0"


# ── resolver ───────────────────────────────────────────────────────────────────

def test_resolve_defaults_to_nvidia():
    p = resolve_gpu_vendor_provider()
    assert isinstance(p, NvidiaGpuProvider)


def test_resolve_named_nvidia_case_insensitive():
    assert isinstance(resolve_gpu_vendor_provider("NVIDIA"), NvidiaGpuProvider)


def test_resolve_unknown_vendor_is_none():
    assert resolve_gpu_vendor_provider("amd") is None


def test_nvidia_provider_is_a_gpu_vendor_provider():
    assert isinstance(_nvidia(), GpuVendorProvider)
