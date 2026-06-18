# Acceptance Criteria - Activity map freshness (lightweight, activity-gated)

The portal's per-user activity map (status + CPU/memory) must reflect a lab's current state promptly, without a slow `/activity` request and without polling idle containers. Live `docker stats` is moved off the request path into a warm snapshot that is refreshed **lazily and only for recently-active users**. Backend: `container_stats_cache.py` (snapshot + `get_container_stats_with_refresh`), `docker_utils.py::stats_from_container` (shared stats math), `handlers/activity.py` (reads the snapshot). Verified against the code 2026-06-18.

## Endpoint latency

- [x] **No synchronous docker gather on the request path** - `/activity` no longer does `asyncio.gather(get_container_stats_async ...)` over active users; it reads the warm snapshot and returns instantly
  - log: 2026-06-18 replaced the blocking gather with `get_container_stats_with_refresh()` (was the operator's "~5-6s after I switched to portal")
- [x] **Status is request-fresh** - per-user active/idle status (`recently_active`) is computed live from `spawner.orm_spawner.last_activity` each request (no Docker), so the status pill is current the moment `/activity` returns
  - log: 2026-06-18 unchanged path; only the cpu/mem cells come from the snapshot
- [x] **Instant on navigation** - switching to a portal page paints the current status immediately (the snapshot read is non-blocking); cpu/mem fill from the snapshot (<= one interval old)
  - log: 2026-06-18 the navigation-time fix

## Lightweight + activity-gated refresh

- [x] **No always-on timer** - there is no background `PeriodicCallback`; the refresh fires only when `/activity` is polled and the snapshot is stale
  - log: 2026-06-18 lazy `get_container_stats_with_refresh`, chosen over an always-on refresher (operator: "let this tracking be lightweight")
- [x] **Only active users are sampled** - the refresh samples `docker stats` ONLY for users in the recently-active set (`recently_active`, the kernel `last_activity` signal the platform already uses); idle-but-running containers are never polled
  - log: 2026-06-18 operator: "triggered when container gives active signal, so we don't poll things that are just sitting idle"; handler builds `active_encoded` from `recently_active`
- [x] **Idle-but-running keeps its last value** - a running container that is not recently active retains its last snapshot entry (not refreshed, not pruned), so its cell still shows the last sampled cpu/mem (~0 once idle)
  - log: 2026-06-18 prune is keyed on container-stopped, not on idle
- [x] **Zero docker calls when all idle** - when no user is recently active the refresh is not even triggered (`active_encoded` empty -> no submit, no `/containers/json` list)
  - log: 2026-06-18 `get_container_stats_with_refresh` early-returns the snapshot without submitting when the active set is empty
- [x] **At most once per interval** - a `refreshing` guard + the staleness check mean overlapping polls collapse to a single in-flight refresh per interval
  - log: 2026-06-18 mirrors `container_size_cache` semantics
- [x] **Interval is env-configurable** - `JUPYTERHUB_ACTIVITYMON_STATS_INTERVAL` (default 10s) sets how fresh an active user's cpu/mem cell is
  - log: 2026-06-18 read inside the cache module (no compose wiring), like the container-size interval

## Snapshot correctness

- [x] **Keyed by encoded username** - the snapshot is keyed by the escapism-encoded username (the `jupyterlab-<encoded>` suffix); the handler maps each active user via `encode_username_for_docker(user.name)`
  - log: 2026-06-18 matches `container_size_cache` keying
- [x] **Stopped containers pruned** - on a refresh that runs, entries whose encoded username is not among the running containers are dropped
  - log: 2026-06-18 prune step in `_refresh_active_container_stats`
- [x] **Shared stats math** - cpu%/cores(+limited)/memory(+limited)/image_id come from `docker_utils.stats_from_container`, the single source used by both the ad-hoc `get_container_stats` and the refresher (no duplicated formula)
  - log: 2026-06-18 factored out of `get_container_stats`
- [x] **Edge: docker unreachable** - any docker failure in a fetch leaves the prior snapshot intact and never raises into `/activity` (the fetch returns None, the response still finishes)
  - log: 2026-06-18 try/except in `_fetch_single_container_stats` + `_refresh_active_container_stats`
- [x] **Edge: cold start** - before the first refresh lands the snapshot is empty, so an active user's cpu/mem is briefly absent (status still shown) and fills on the next poll; never a blocking wait
  - log: 2026-06-18 non-blocking by design

## Tests

- [x] **stats_from_container** - cpu%/assigned cores/memory/image_id computed from a fake container, limited and unlimited paths, None on a stats error
  - log: 2026-06-18 `tests/test_container_stats_cache.py`
- [x] **Staleness + trigger gating** - `get_cached_container_stats` flags stale when never/expired; `get_container_stats_with_refresh` submits a refresh only when the active set is non-empty AND stale, and never when the active set is empty
  - log: 2026-06-18 `tests/test_container_stats_cache.py` (executor monkeypatched, no real docker)

## API

- `GET /hub/api/activity` -> per-user `{..., cpu_percent, cpu_cores, memory_mb, memory_percent, memory_total_mb, recently_active, ...}` (admin); cpu/mem sourced from the warm snapshot, status from `last_activity`
