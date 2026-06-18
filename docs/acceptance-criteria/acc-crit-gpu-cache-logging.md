# Acceptance Criteria - GPU Utilisation Cache Logging

The background GPU-utilisation sampler (`gpu_cache._refresh_sync`) ticks every `JUPYTERHUB_GPU_UTIL_UPDATE_INTERVAL` seconds (default 30). Per-tick "cache updated" lines are noise, so only the first successful sample logs at INFO - carrying the refresh cadence - and every later refresh logs at DEBUG.

- [x] **First sample INFO** - first successful refresh (cache timestamp was `None`) logs once at INFO: device count plus `refreshing every <interval>s`
  - log: 2026-06-17 implemented (gpu_cache.py:_refresh_sync)
- [x] **Interval source** - the cadence in the INFO line reads `_get_update_interval()` (`JUPYTERHUB_GPU_UTIL_UPDATE_INTERVAL`, default 30), not a hardcoded number
  - log: 2026-06-17 implemented
- [x] **Subsequent samples DEBUG** - every refresh after the first logs `Cache updated: N device(s)` at DEBUG, off by default at INFO log level
  - log: 2026-06-17 implemented (was INFO every tick - the reported noise)
- [x] **First detection** - "first" keyed off `_gpu_util_cache['timestamp'] is None` before the write, so it fires exactly once per process lifetime
  - log: 2026-06-17 implemented
- [ ] **Edge: empty sample** - sidecar returns nothing -> `Sample empty - keeping previous cache` stays at INFO (left unchanged; flags a degraded sidecar, not routine churn)
  - log: 2026-06-17 left at INFO per scope; revisit if a persistently-down sidecar spams
- [ ] **Edge: sample after empties** - if the very first non-empty sample arrives after one or more empty ticks, it still logs the INFO init line (timestamp still `None` until a non-empty write)
  - log: 2026-06-17 verified by design - timestamp only set on non-empty data
