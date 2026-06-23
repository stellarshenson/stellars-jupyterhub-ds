"""GPU vendor abstraction.

GPU device-passthrough used to be hardwired to NVIDIA in three places; each now
delegates to a `GpuVendorProvider` so a non-NVIDIA GPU (AMD ROCm, Intel oneAPI,
Apple Silicon) plugs in without editing the policy engine:
  - policy/registry.py   device_requests + visibility env  -> device_request() / visibility_env()
  - gpuinfo_sidecar.py   container runtime                 -> runtime_name()
  - the gpuinfo-nvidia sidecar image itself                -> a vendor's own sidecar image

The provider owns ONLY the vendor-specific decisions (driver string, runtime, env
naming); the access decision (who, which GPUs), hardware gating and the image-generic
ENABLE_GPU_SUPPORT/GPUSTAT flags stay in the policy engine.

Status: WIRED, NVIDIA reference active. `resolve_gpu_vendor_provider` builds the
provider once at boot; it is threaded to the per-user GPU policy via
`ApplyContext.gpu_vendor` and to the sidecar launcher via its runtime name. A second
vendor = add a `GpuVendorProvider`, register it in `_VENDORS`, drive the selection.
See docs/gpu-abstraction.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class GpuVendorProvider(ABC):
    """Vendor-specific GPU passthrough policy. One per GPU vendor."""

    name: str  # vendor id, e.g. "nvidia" / "amd" / "intel"

    @abstractmethod
    def runtime_name(self) -> str | None:
        """Docker runtime to request for GPU access, or None when the vendor needs
        none. Caller still verifies the runtime is registered before using it."""

    @abstractmethod
    def device_request(self, all_gpus: bool, device_ids: list[str]) -> dict:
        """The docker `device_requests` entry granting GPU access - all GPUs when
        `all_gpus`, else the given host index strings."""

    @abstractmethod
    def visibility_env(
        self, access: bool, all_gpus: bool, device_ids: list[str], uuid_by_index: dict
    ) -> dict:
        """Per-container GPU visibility env vars. A value of None means UNSET the var
        (caller pops it). Covers access+all, access+subset and no-access."""


class NvidiaGpuProvider(GpuVendorProvider):
    """Reference vendor - today's hardcoded NVIDIA behaviour, captured verbatim."""

    name = "nvidia"

    def runtime_name(self) -> str | None:
        return "nvidia"

    def device_request(self, all_gpus: bool, device_ids: list[str]) -> dict:
        if all_gpus or not device_ids:
            return {"Driver": "nvidia", "Count": -1, "Capabilities": [["gpu"]]}
        return {"Driver": "nvidia", "DeviceIDs": list(device_ids), "Capabilities": [["gpu"]]}

    def visibility_env(
        self, access: bool, all_gpus: bool, device_ids: list[str], uuid_by_index: dict
    ) -> dict:
        if not access:
            # void overrides the image's baked-in 'all'
            return {"NVIDIA_VISIBLE_DEVICES": "void", "CUDA_VISIBLE_DEVICES": None}
        if all_gpus or not device_ids:
            return {"NVIDIA_VISIBLE_DEVICES": "all", "CUDA_VISIBLE_DEVICES": None}
        ids = list(device_ids)
        # NVIDIA_VISIBLE_DEVICES = host indices (toolkit's authoritative selector);
        # CUDA_VISIBLE_DEVICES = UUIDs so CUDA survives re-indexing, falls back to ids
        uuids = [uuid_by_index[i] for i in ids if i in uuid_by_index]
        return {
            "NVIDIA_VISIBLE_DEVICES": ",".join(ids),
            "CUDA_VISIBLE_DEVICES": ",".join(uuids) if uuids else ",".join(ids),
        }


# Vendor registry - one entry today. Future vendors register here; selection becomes
# detection/env-driven (the gpuinfo sidecar already anticipates amd/intel/applesilicon
# peers). Keyed off each provider's own `name` so the registry key and the attribute
# cannot drift; lower-cased to match the case-insensitive lookup below. Defaults to nvidia.
_VENDORS = {NvidiaGpuProvider.name.lower(): NvidiaGpuProvider}


def resolve_gpu_vendor_provider(vendor: str | None = None) -> GpuVendorProvider | None:
    """Provider for the named GPU vendor, or None if unknown. Defaults to nvidia -
    the only vendor registered today. Called once at boot by the config; the result
    is threaded to the GPU policy and the sidecar launcher."""
    cls = _VENDORS.get((vendor or "nvidia").lower())
    return cls() if cls else None
