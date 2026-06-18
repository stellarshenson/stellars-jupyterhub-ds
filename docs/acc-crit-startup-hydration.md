# Acceptance Criteria - startup hydration

A single startup-hydration step warms every cache and fires the deferred checks ONCE at boot, so a (re)started hub shows a populated portal immediately instead of an empty one until an admin first opens the Activity page. Everything runs on the IOLoop after the hub is serving (best-effort, never blocks boot) and is consolidated behind one entry point. Module: `hydrate.py::schedule_startup_hydration`; wired in `config/jupyterhub_config.py` Section 5. Verified against the code 2026-06-18.

## Consolidation

- [x] **Single entry point** - one `schedule_startup_hydration(...)` call replaces the previously scattered startup work (lazy refresher starts in the `/activity` handler + the separate favicon and policy callbacks)
  - log: 2026-06-18 operator: "sweep this initial hydration and consolidate"; `hydrate.py`, config Section 5 one call
- [x] **Deferred, never blocks boot** - hydration is registered via `IOLoop.current().add_callback` and runs after the hub is serving; the synchronous boot work (bounded GPU probe, sidecar self-start, branding) stays where it is
  - log: 2026-06-18 mirrors `schedule_policy_startup` / `schedule_startup_favicon_callback` pattern
- [x] **Best-effort** - each hydration step is wrapped so a failure (docker unreachable, etc.) is logged and skipped, never crashing boot or the IOLoop
  - log: 2026-06-18 per-step try/except in `_hydrate`
- [x] **Shared with the handler (fallback)** - the `/activity` handler calls the same `start_activity_refreshers(...)`, so a direct `/activity` hit still works if hydration was skipped; the refreshers are idempotent
  - log: 2026-06-18 `start_activity_refreshers` is the single code path; refresher `start()` is `if periodic_callback is not None: return`

## Cache hydration (populate right away)

- [x] **Activity refreshers started at boot** - volume sizes + container sizes refreshers start at hydration; each `start()` submits an immediate first refresh, so the caches warm without waiting for the first request
  - log: 2026-06-18 `start_activity_refreshers`; `start()` does `get_executor().submit(_refresh_*)`
- [x] **GPU utilisation gated on hardware** - the GPU-utilisation refresher is started only when the host has GPUs (`gpu_list` enumerated at boot); GPU-less hosts skip it (no pointless sidecar polling)
  - log: 2026-06-18 `if gpu_list:` in `start_activity_refreshers`
- [x] **Live stats warmed for survivors** - servers that survived the restart get a live-stats sample triggered at hydration, so the activity map shows CPU/memory immediately
  - log: 2026-06-18 `_warm_survivor_stats` enumerates `spawner.active` users -> `get_container_stats_with_refresh(active)`
- [x] **Periodic refresh continues** - after the immediate warm, each refresher keeps its normal PeriodicCallback cadence (volume 3600s, container size 300s, GPU util 30s, stats activity-gated 10s)
  - log: 2026-06-18 unchanged intervals; only the START moved to boot

## Pick up running servers (restart survivors)

- [x] **Survivor caches rehydrated** - the warmed size/volume/stats caches reflect already-running labs at boot, not only after the first `/activity` poll
  - log: 2026-06-18 refreshers enumerate running `jupyterlab-*` containers; stats warmed for active spawners
- [x] **Survivor CHP favicon routes** - per-user favicon routes for already-running servers are re-registered (pre_spawn_hook only fires on new spawns)
  - log: 2026-06-18 folded into hydration via `schedule_startup_favicon_callback`
- [x] **Survivor policy re-imposed** - each policy model's `on_hub_startup` runs for survivors (docker-proxy re-bind, download-block route re-registration, api-keys reconcile)
  - log: 2026-06-18 folded into hydration via `schedule_policy_startup` (skipped when no `policy_actx`)

## Image-update check (immediate)

- [x] **Image snapshot warmed at boot** - the slow `docker image ls` scan that backs "update available" is built at hydration, so the per-container check is immediate from the first `/activity` request instead of lazily on first access
  - log: 2026-06-18 `_check_image_updates` calls `_image_snapshot_get()`
- [x] **Configured lab image reported** - hydration logs whether the configured lab image is up to date, has a newer local build, or is not present yet
  - log: 2026-06-18 `_check_image_updates` compares the tag's target id vs the repo's newest

## Edge cases

- [x] **Edge: no survivors** - with nothing running, stats warming is a no-op (no docker calls); refreshers still start and find an empty fleet
  - log: 2026-06-18 `_warm_survivor_stats` only calls the cache when the active set is non-empty
- [x] **Edge: docker unreachable** - image snapshot + stats warming degrade to empty/last-known and log a warning; hydration completes
  - log: 2026-06-18 `_image_snapshot_get` is best-effort; step wrapped in try/except
- [x] **Edge: GPU-less host** - GPU-utilisation refresher is not started; no error
  - log: 2026-06-18 `gpu_list` empty -> skipped
- [x] **Edge: runs once** - hydration is a one-time boot callback; the refreshers' idempotent `start()` means a later `/activity` hit does not double-start them
  - log: 2026-06-18 one `add_callback`; `start()` guards on `periodic_callback`

## Tests

- [x] **Unit: shared helper + gating** - `start_activity_refreshers` starts volume + container-size refreshers always and GPU utilisation only when `gpu_list` is non-empty; the hydration entry is importable + callable
  - log: 2026-06-18 `tests/test_hydrate.py`; `make test`-runnable
- [ ] **Functional: restart with a running lab** - start a lab, restart the hub, then confirm the portal shows the survivor's sizes/stats and the update state without a manual `/activity` visit
  - log: 2026-06-18 needs a hub-restart harness step; pends (the current functional harness boots a fresh hub, no restart-with-survivors flow yet)
