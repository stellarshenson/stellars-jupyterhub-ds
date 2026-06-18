# Acceptance Criteria - last-known cache + non-blocking GPU + GPU-widget gating

The portal stays responsive across hub restarts: slow server-side aggregates (volume sizes, GPU inventory) persist their last-known snapshot and seed from it on boot, GPU detection never stalls startup, and the GPU widget is hidden when the platform has no GPU. `[x]` = implemented + verified by code-read / unit-check; `[ ]` = pending runtime confirmation (needs an image rebuild + restart). ESFO: every box below was re-verified against the code on 2026-06-17, not assumed.

## Persisted last-known cache (shared helper)

- [x] **Helper exists** - `persisted_cache.py` exposes `save_cached(name, data)` + `load_cached(name)`
  - log: 2026-06-17 verified (persisted_cache.py:52,76)
- [x] **Atomic write** - snapshot written via tempfile + `os.replace` so a crash mid-write cannot corrupt the seed
  - log: 2026-06-17 verified (persisted_cache.py:65 os.replace)
- [x] **Shape** - file is `{timestamp: iso, data}` on the data volume (`JUPYTERHUB_DATA_DIR`, default `/data`)
  - log: 2026-06-17 verified (persisted_cache.py save/load + _persist_dir)
- [x] **TTL-gated load** - a snapshot older than `JUPYTERHUB_CACHED_DATA_TTL_MINUTES` (default 1440 = 24h) is ignored on boot, returns None
  - log: 2026-06-17 verified by unit check (TTL=0 -> None; 30min within 60min TTL -> seed); persisted_cache.py:49
- [x] **Best-effort** - missing or corrupt file returns None and never raises (cannot block startup)
  - log: 2026-06-17 verified by unit check (corrupt "{not json" -> None, warning logged)
- [x] **Configurable TTL in minutes** - `JUPYTERHUB_CACHED_DATA_TTL_MINUTES` read in minutes, multiplied to seconds
  - log: 2026-06-17 verified (persisted_cache.py:49 `* 60`)
- [x] **Env baked, not in compose** - the TTL env is in the Dockerfile + settings dictionary only
  - log: 2026-06-17 verified (Dockerfile.jupyterhub:268, settings_dictionary.yml:199; absent from compose.yml)

## Volume sizes (first consumer)

- [x] **Uses the helper** - volume_cache persists on refresh and seeds on boot via the shared helper
  - log: 2026-06-17 verified (volume_cache.py:21 import, :160 save_cached, :94 seed call)
- [x] **Seed only when no live data** - boot seed does not regress live in-memory data
  - log: 2026-06-17 verified by unit check (live cache not overwritten by disk)
- [x] **Non-blocking** - the fetch is deferred to the shared executor; startup only compiles templates + loads the seed
  - log: 2026-06-17 verified (configure_volume_cache compiles regex + _load_persisted; _fetch runs in get_executor)
- [ ] **Runtime: survives restart** - after a hub restart the portal shows last-known volume sizes immediately, not empty
  - log: 2026-06-17 pending deploy (logic verified, runtime needs rebuild)

## GPU inventory + non-blocking detection

- [x] **Self-start sidecar** - the hub starts the `gpuinfo-nvidia` sidecar itself; `ensure_gpuinfo_sidecar` returns a bool (True running / False unavailable)
  - log: 2026-06-17 verified (gpuinfo_sidecar.py returns True/False; config:498 captures it; __init__ exports it)
- [x] **Skip probe when sidecar down** - when self-start returns False, detection skips the live probe entirely (no DNS/connect stall)
  - log: 2026-06-17 verified by unit check (probe_sidecar=False -> 0 fetch calls, ~20ms); gpu.py:70
- [x] **Bounded probe** - the boot probe is ~6x0.5s (max ~3s), not the old 20x1.0s (~20s)
  - log: 2026-06-17 verified (gpu.py:18 _BOOT_PROBE attempts 6 delay 0.5 timeout 2)
- [x] **Persist fresh inventory** - a successful probe saves the inventory as last-known
  - log: 2026-06-17 verified by unit check (reachable -> gpu_inventory.json written); gpu.py:72
- [x] **Seed from last-known** - an empty/skipped probe seeds gpu_list from the persisted inventory (within TTL)
  - log: 2026-06-17 verified by unit check (unreachable + last-known -> detected ON from disk); gpu.py:74
- [x] **Mode semantics** - mode 0 never probes; mode 2 collapses to on/off from inventory; mode 1 stays forced-on with empty list when sidecar down
  - log: 2026-06-17 verified by unit check (mode0 untouched; mode2 off no-seed; mode1 forced-on-empty)
- [x] **Runtime: no 20s boot stall** - boot logs show the sidecar self-start line and no ~20s GPU gap
  - log: 2026-06-17 VERIFIED LIVE after rebuild - hub self-started gpuinfo-nvidia, `[GPU debug] enabled=1 detected=1` with 3 GPUs (was enabled=0 detected=0); sidecar container Up

## GPU widget global gating

- [x] **Authoritative flag exposed** - `gpu_enabled` is injected into the portal shell `window.jhdata` (template_var)
  - log: 2026-06-17 verified (config:616 template_vars, portal.html:31 window.jhdata.gpu_enabled)
- [x] **Frontend accessor** - `gpuSupported()` reads `window.jhdata.gpu_enabled`, defaults true in mock/dev
  - log: 2026-06-17 verified (app/capabilities.ts; client.ts JhData type gains gpu_enabled)
- [x] **Widgets gated** - ResourceBars (Home + ServerHero), the Servers GPU column, and the GroupPolicy GPU section render only when supported
  - log: 2026-06-17 verified (meters.tsx ResourceBars filter, Servers.tsx column spread, GroupPolicyTab.tsx section guard; 7 gpuSupported usages; tsc green)
- [x] **Mock keeps GPU on** - design pages still demo GPU (no jhdata -> default true)
  - log: 2026-06-17 verified (capabilities.ts `?? true`)
- [ ] **Runtime: no-GPU host hides every GPU surface** - on a GPU-less deployment no GPU widget appears anywhere
  - log: 2026-06-17 show-path confirmed live (this host has GPU -> gpu_enabled=1 -> window.jhdata.gpu_enabled=true -> widgets render); the HIDE path still needs a GPU-less host to confirm

## Prefetch all key pages

- [x] **Key-page data warmed at start** - prefetchCore warms servers/users/groups/events/stats/resources/hub-info plus tokens/lab-container/settings/sent-notifications
  - log: 2026-06-17 verified (App.tsx warm[] includes the four added keys; tsc green)
- [x] **No off-screen DOM prerender** - routes are statically bundled (no React.lazy), so only data is warmed, not hidden component trees
  - log: 2026-06-17 verified (router.tsx all static element imports; no lazy)
