# GPU Vendor Abstraction

GPU device-passthrough was hardwired to NVIDIA. A `GpuVendorProvider` seam now owns the vendor-specific decisions so a non-NVIDIA GPU (AMD ROCm, Intel oneAPI, Apple Silicon) plugs in without editing the policy engine. The seam is built and wired with NVIDIA as the reference vendor; adding a second vendor is the only remaining work.

## Status

- **Wired** - `NvidiaGpuProvider` is the active reference, resolved once at boot and threaded to the spawn path
- **Behaviour-preserving** - the NVIDIA device request, visibility env and sidecar runtime are byte-identical to before (unit-proven)
- **Open** - a second vendor (provider + selection) is future work; the deployment is NVIDIA-only today

## The three NVIDIA touchpoints, now delegated

The vendor was assumed NVIDIA in three executable places; each now asks the provider.

- **Device request** - `policy/registry.py::GpuPolicy.apply` calls `provider.device_request(all_gpus, ids)` instead of building `{'Driver': 'nvidia', ...}`
- **Visibility env** - same stage calls `provider.visibility_env(...)` for `NVIDIA_/CUDA_VISIBLE_DEVICES` (a `None` value unsets the var)
- **Container runtime** - `gpuinfo_sidecar.py::ensure_gpuinfo_sidecar` takes `gpu_runtime` (from `provider.runtime_name()`), requested only when the host registers it
- **Sidecar image** - `gpuinfo-nvidia` is still NVIDIA-specific; a second vendor pairs its own sidecar image (out of this seam's scope)

## The seam

`GpuVendorProvider` ABC - one implementation per vendor, owns only the vendor-specific decisions; the policy engine keeps the access decision (who, which GPUs), hardware gating and the image-generic `ENABLE_GPU_SUPPORT`/`ENABLE_GPUSTAT` flags.

- **`runtime_name() -> str | None`** - docker runtime to request; caller still checks it is registered
- **`device_request(all_gpus, device_ids) -> dict`** - the `device_requests` entry
- **`visibility_env(access, all_gpus, device_ids, uuid_by_index) -> dict`** - per-container visibility env; value `None` means unset the var
- **Resolution** - `resolve_gpu_vendor_provider(vendor)` returns the provider from a one-entry registry (`{'nvidia': ...}`), defaults to nvidia

`NvidiaGpuProvider` is the faithful reference. The provider is resolved once in `config/jupyterhub_config.py` as `GPU_VENDOR`, passed to the sidecar launcher (its runtime) and threaded to the per-user GPU policy via `ApplyContext.gpu_vendor`. `GpuPolicy.apply` falls back to `NvidiaGpuProvider()` when the context carries none, so any caller (and the existing tests) keep the NVIDIA behaviour.

## Adding a second vendor

The seam is built; a new vendor is additive - no edit to the policy engine or the spawn path.

- **Implement** a `GpuVendorProvider` for the vendor (its driver string, runtime, visibility env naming)
- **Register** it in `gpu_vendor._VENDORS`
- **Select** it - drive the active vendor from detection or an env override (the resolver already takes a vendor name)
- **Pair** a vendor sidecar image if GPU detection needs one
- **Verify** - a unit test for the new provider, a GPU-regime functional run, and a live check that the NVIDIA path is unchanged

## Why NVIDIA-only today

- **No second vendor** - the deployment has only NVIDIA GPUs, so only the reference provider is registered
- **WSL2 reality** - the host is Docker Desktop / WSL2: GPUs arrive via a single `/dev/dxg`, per-GPU isolation is impossible regardless of vendor (subset selection is advisory)
- **The seam is the insurance** - building it now means future GPU work is designed against the provider, not the old hardcoded shape, so it cannot rot before a second vendor lands

## Scope boundaries

- **In** - the `GpuVendorProvider` contract, the NVIDIA reference, the resolver, and the wiring into the policy engine + sidecar launcher
- **Out** - a second vendor provider, vendor auto-detection, a non-NVIDIA sidecar image
