# Acceptance Criteria - GPU Vendor Abstraction

A `GpuVendorProvider` seam decouples GPU device-passthrough from NVIDIA so a non-NVIDIA GPU (AMD ROCm, Intel oneAPI, Apple Silicon) plugs in without editing the policy engine. The seam is built and wired with NVIDIA as the reference vendor. Design: [gpu-abstraction.md](../gpu-abstraction.md).

## Seam (done)

- [x] **Contract** - `GpuVendorProvider` ABC defines `runtime_name()`, `device_request()`, `visibility_env()`; lives in a dedicated `gpu_vendor` module, not in the policy engine
  - log: 2026-06-23 implemented (`gpu_vendor.py`); unit `test_gpu_vendor.py`
- [x] **Reference provider** - `NvidiaGpuProvider` reproduces the NVIDIA behaviour verbatim (device request `{'Driver': 'nvidia', Count/-DeviceIDs}`, runtime `nvidia`, `NVIDIA_/CUDA_VISIBLE_DEVICES`)
  - log: 2026-06-23 implemented; unit covers all/subset/no-access + uuid map + fallback
- [x] **Resolver** - `resolve_gpu_vendor_provider(vendor)` returns the provider from a vendor registry, defaults to nvidia, None on unknown
  - log: 2026-06-23 implemented (`_VENDORS`); exported from the package `__init__`
- [x] **Documented** - design, the three touchpoints, add-a-vendor steps, NVIDIA-only rationale
  - log: 2026-06-23 `docs/gpu-abstraction.md`

## Wiring (done)

- [x] **Resolved once** - the provider is built at boot (`GPU_VENDOR = resolve_gpu_vendor_provider()`) in `config/jupyterhub_config.py`
  - log: 2026-06-23 done
- [x] **Threaded to policy** - `ApplyContext.gpu_vendor` carries it; `make_pre_spawn_hook` receives `gpu_vendor` and puts it on the context
  - log: 2026-06-23 done (`base.py`, `hooks.py`)
- [x] **Registry delegates** - `GpuPolicy.apply` calls `provider.device_request()` / `provider.visibility_env()` instead of inline literals; env dict merged, `None` values popped
  - log: 2026-06-23 done; `test_delegates_to_vendor_provider`, `test_provider_none_value_pops_preexisting_env`
- [x] **Sidecar delegates** - `ensure_gpuinfo_sidecar` takes `gpu_runtime` (from `provider.runtime_name()`) instead of literal `'nvidia'`, keeping the runtime-registered guard
  - log: 2026-06-23 done; `test_ensure_requests_vendor_runtime_when_registered` + omit tests
- [x] **NVIDIA unchanged** - with the NVIDIA provider wired, the device request, visibility env and runtime are byte-identical to before
  - log: 2026-06-23 the 4 pre-existing `TestGpuApply` cases pass unmodified via the `NvidiaGpuProvider()` fallback
- [x] **Image flags stay** - `ENABLE_GPU_SUPPORT` / `ENABLE_GPUSTAT` remain caller-side image switches, not vendor policy
  - log: 2026-06-23 done; set in `GpuPolicy.apply`, not in the provider
- [x] **Fallback default** - `GpuPolicy.apply` falls back to `NvidiaGpuProvider()` when the context carries none, so no caller is stranded
  - log: 2026-06-23 done; guards tests and any ApplyContext built without the field

## Verification

- [x] **Unit - provider** - `test_gpu_vendor.py`: name, runtime, device request (all/subset/empty), visibility env (all/subset/uuid/fallback/partial/no-access), resolver (default/named/unknown)
  - log: 2026-06-23 done; full unit suite 1015 pass (950 hub-services)
- [x] **Unit - delegation** - the policy stage uses a custom provider's output, and a provider `None` value unsets a pre-existing env var
  - log: 2026-06-23 done (`test_policy_apply.py`)
- [x] **Unit - sidecar runtime** - runtime requested when registered + vendor set; omitted when unregistered or vendor None
  - log: 2026-06-23 done (`test_gpuinfo_sidecar.py`)
- [x] **Adversarial review** - architect sweep (seam consistency, no driver/runtime drift, NVIDIA path unchanged, no env leak)
  - log: 2026-06-23 architect Mode-2 CLEAN + bug-hunt Mode-1 SHIP (NVIDIA byte-identical all 4 branches, seam load-bearing not a bypass, SoC holds, no vendor literal in spawn logic); 2 fixes applied (config boot fallback `resolve...() or NvidiaGpuProvider()` so resolution never strands boot; `_VENDORS` keyed off `NvidiaGpuProvider.name.lower()`); re-confirm round SHIP
  - log: 2026-06-23 deferred to second-vendor work: `RESERVED_ENV_VAR_NAMES` hardcodes `NVIDIA_/CUDA_VISIBLE_DEVICES` - a future vendor's selector (e.g. `HIP_VISIBLE_DEVICES`) must be derived from the provider then, or a group could override it
- [ ] **Functional - GPU regime** - GPU passthrough still works end-to-end after delegation
  - log: 2026-06-23 pending rebuild + functional run
- [ ] **Live unchanged** - rebuild + redeploy; GPU spawn on the NVIDIA host identical to before
  - log: 2026-06-23 pending rebuild + redeploy

## Edge cases

- [x] **Edge: unknown vendor** - `resolve_gpu_vendor_provider` returns None on an unknown name
  - log: 2026-06-23 verified `test_resolve_unknown_vendor_is_none`
- [x] **Edge: runtime not registered** - `gpu_runtime` set but docker lacks it -> runtime not requested
  - log: 2026-06-23 verified `test_ensure_omits_runtime_when_not_registered`
- [x] **Edge: no vendor provider on context** - `GpuPolicy.apply` falls back to NVIDIA, behaviour unchanged
  - log: 2026-06-23 verified via the unmodified `TestGpuApply` cases
- [x] **Edge: WSL2 single /dev/dxg** - subset selection is advisory (not kernel-enforced) for any vendor on WSL2, as for NVIDIA
  - log: 2026-06-23 noted; documented in `gpu_vendor.py` + the policy comment

## Scope boundaries

- [ ] **Second vendor** - an AMD/Intel/Apple provider, vendor auto-detection and a non-NVIDIA sidecar image are future, additive work against this seam
  - log: 2026-06-23 out of scope; seam shaped to make it additive
- [x] **Out: GPU isolation** - per-GPU container isolation is a host-platform limit (WSL2 `/dev/dxg`), unrelated to vendor abstraction
  - log: 2026-06-23 noted
