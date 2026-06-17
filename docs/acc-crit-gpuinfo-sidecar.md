# Acceptance Criteria - gpuinfo-nvidia sidecar (logging + graceful no-hardware)

The GPU-info sidecar logs its lifecycle so an operator can see it start, serve and what hardware it detected. A failure to start the container is an acceptable outcome - it means no NVIDIA hardware - and the hub degrades to GPU-off without stalling or alarming.

## Logging

- [x] **Startup line** - on boot the sidecar logs `[gpuinfo-nvidia] vX starting (vendor=nvidia)` via a FastAPI `lifespan`
  - log: 2026-06-17 `gpuinfo_nvidia/app.py` lifespan
- [x] **Detected hardware** - it samples once and logs each GPU (`GPU <i>: <name> (<uuid>, <N> GB)`), or a single `no NVIDIA driver/GPU detected - serving empty inventory` warning
  - log: 2026-06-17 `_log_detected_hardware`
- [x] **Health at startup** - each detected-GPU line also reports the current health snapshot (`- health: N% util, U/T GB mem, NN C, NN W`), skipping any metric the driver did not report (so a partial sample never prints `None`)
  - log: 2026-06-17 `_gpu_health` appended to the per-GPU line; operator "show the health of the gpus when starting"
- [x] **Serving line** - logs `ready - serving /health and /gpus`; uvicorn's own "Uvicorn running on ..." also shows
  - log: 2026-06-17
- [x] **Visible by default** - `GPUINFO_LOG_LEVEL` default changed `warning` -> `info` (warning hid uvicorn's running line); overridable via env
  - log: 2026-06-17 `__main__.py`
- [x] **No request spam** - `access_log=False`; the hub polls `/health`+`/gpus` every ~30s, so per-request lines would bury the useful logs
  - log: 2026-06-17
- [x] **Untyped-package import** - a `declare module` shim is not needed (the sidecar is Python); fastapi tests gate the image build (bare `TestClient` does not trigger the lifespan, so no nvidia-smi call in tests)
  - log: 2026-06-17 `tests/test_app.py` uses module-level `TestClient`

## Graceful no-hardware (container fail = no GPU = OK)

- [x] **Container fails to start = no GPU** - if the nvidia runtime is absent the container cannot launch; that is an expected, acceptable outcome meaning no NVIDIA hardware, not an error to surface
  - log: 2026-06-17 treated as the no-GPU path
- [x] **Hub self-start returns a bool** - `ensure_gpuinfo_sidecar` returns False when docker/nvidia is unavailable; the hub does not block on it
  - log: 2026-06-17 established (journal 269/270/273)
- [x] **Bounded boot probe** - the hub's GPU probe is time-bounded (~3s), so an unreachable/failed sidecar never stalls hub boot
  - log: 2026-06-17 established
- [x] **Degrades to GPU-off** - with no reachable sidecar the hub resolves GPU-off (empty inventory, GPU widgets hidden via `window.jhdata.gpu_enabled`)
  - log: 2026-06-17 established
- [x] **App still serves on a GPU-less host** - if the container DOES run without a driver, `/health` stays 200 and `/gpus` returns `available:false` (the no-driver warning is logged once at startup)
  - log: 2026-06-17 `driver_available()` defensive, `sample()` returns `(False, [])`
- [x] **Runtime: logs show start/serve/hardware** - on the live hub, `docker logs gpuinfo-nvidia` shows the startup, detected-GPU and serving lines (or the no-driver warning)
  - log: 2026-06-17 CONFIRMED live - the running container was a stale pre-fix image (default `warning`, no lifespan) reused by `ensure_gpuinfo_sidecar`; recreated from the rebuilt `:latest` -> full banner + 3 detected GPUs + serving line now show

## Lifecycle (tied to the hub)

The sidecar is hub-managed (created over the docker socket by `ensure_gpuinfo_sidecar`), not a compose service, so compose `down` leaves it orphaned. The hub now owns its teardown too.

- [x] **Removed on hub shutdown** - the hub registers `atexit(stop_gpuinfo_sidecar)` when it started/owns the sidecar, so a clean hub stop (`docker stop` / compose `down`) removes the sidecar instead of leaving it running with no parent
  - log: 2026-06-17 `stop_gpuinfo_sidecar` + `config/jupyterhub_config.py` atexit; needs a hub rebuild to go live
- [x] **Recreated fresh next boot** - because shutdown REMOVES (not just stops) the container, the next `ensure_gpuinfo_sidecar` creates it anew from the current `:latest`, so a rebuilt image is always picked up (this is the structural fix for the stale-reuse logging bug above)
  - log: 2026-06-17 remove-on-exit + create-on-boot
- [x] **Best-effort** - never raises; a hard SIGKILL of the hub skips the atexit, leaving the sidecar's `unless-stopped` policy to keep it until the next clean cycle
  - log: 2026-06-17 try/except, `containers.get(name).remove(force=True)`
- [ ] **Runtime: sidecar gone after hub stop** - on the live host, stopping the hub removes `gpuinfo-nvidia`; starting the hub recreates it
  - log: 2026-06-17 code clean; pends a hub rebuild + a stop/start cycle to confirm
