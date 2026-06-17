# Acceptance Criteria - gpuinfo-nvidia sidecar (logging + graceful no-hardware)

The GPU-info sidecar logs its lifecycle so an operator can see it start, serve and what hardware it detected. A failure to start the container is an acceptable outcome - it means no NVIDIA hardware - and the hub degrades to GPU-off without stalling or alarming.

## Logging

- [x] **Startup line** - on boot the sidecar logs `[gpuinfo-nvidia] vX starting (vendor=nvidia)` via a FastAPI `lifespan`
  - log: 2026-06-17 `gpuinfo_nvidia/app.py` lifespan
- [x] **Detected hardware** - it samples once and logs each GPU (`GPU <i>: <name> (<uuid>, <N> GB)`), or a single `no NVIDIA driver/GPU detected - serving empty inventory` warning
  - log: 2026-06-17 `_log_detected_hardware`
- [x] **Health at startup** - each detected-GPU line also reports the current health snapshot (`- health: N% util, U/T GB mem, NN C, NN W`), skipping any metric the driver did not report (so a partial sample never prints `None`)
  - log: 2026-06-17 `_gpu_health` appended to the per-GPU line; operator "show the health of the gpus when starting"
- [x] **Hub logs caps + health too** - besides the sidecar's own log, the HUB logs a readable per-card line at boot - `[GPU] GPU <i>: <name> (<N> GB) - <util>% util, <used>/<total> GB, <temp> C, <power> W` - capabilities (name, total mem) + a live health snapshot, omitting any metric the sidecar did not report; the raw `[GPU debug] gpus=[...]` dict line stays for debugging
  - log: 2026-06-17 `gpu_summary_lines()` (gpu.py, fresh sidecar fetch) logged in `jupyterhub_config.py`; 3 unit tests; operator "must show in the logs the info about cards health and capabilities"
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

- [x] **SIGTERM reaches the hub (exec)** - `start-platform.sh` now `exec`s jupyterhub so it is PID 1 and receives docker's SIGTERM directly on `docker stop` / compose down/restart; without exec the signal hit the shell (no forwarding), jupyterhub was SIGKILLed after the grace period and atexit never ran - the real reason teardown did not fire
  - log: 2026-06-17 `exec jupyterhub -f ... "$@"` (operator: "torn down when jupyterhub main service dies")
- [x] **Removed on hub shutdown** - the hub registers `atexit(stop_gpuinfo_sidecar)` when it owns the sidecar; with the exec fix a clean hub stop (SIGTERM -> clean exit) now actually runs it and removes the sidecar instead of leaving it parentless
  - log: 2026-06-17 `stop_gpuinfo_sidecar` + atexit; activates with the exec fix; needs a hub rebuild to go live
- [x] **Recreated fresh from the hub every boot** - `ensure_gpuinfo_sidecar` REMOVES any pre-existing sidecar then CREATEs a new one from the current image, so the hub always recreates it (current `:latest`, never a stale reuse) even if a hard SIGKILL left one behind; the structural fix for the stale-reuse logging bug above
  - log: 2026-06-17 reworked - ensure removes-then-creates (was: reuse a running container)
- [x] **Best-effort** - never raises; a hard SIGKILL of the hub still skips the atexit, but the next boot's recreate-fresh removes+replaces any survivor, so a stale sidecar never persists across a boot
  - log: 2026-06-17 try/except + recreate-fresh-on-boot safety net
- [ ] **Runtime: sidecar gone after hub stop** - on the live host, stopping the hub removes `gpuinfo-nvidia`; starting the hub recreates it
  - log: 2026-06-17 code clean (exec + atexit + recreate-fresh); pends a hub rebuild + a stop/start cycle to confirm
