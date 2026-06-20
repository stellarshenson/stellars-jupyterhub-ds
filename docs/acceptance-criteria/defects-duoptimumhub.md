# Defects - Duoptimum Hub

Defect registry for the Duoptimum Hub portal and platform - one section per defect, same checklist model as the acceptance criteria ([acc-crit-duoptimumhub.md](acc-crit-duoptimumhub.md)). One document, not many.

Checkbox state: `[ ]` = open / unresolved, `[x]` = fixed and verified; in-progress stays `[ ]` and is marked in the latest `log:` line. Each defect carries severity, status, symptom, then repro / root cause / fix / verification as checklist items with a dated `log:` trail. Severity: BLOCKER (platform unusable) > HIGH (core flow broken) > MED (degraded) > LOW (cosmetic).

## Contents

- [DEF-1: Start-server page falls through to the stock JupyterHub spawn screen, no logs](#def-1-start-server-page-falls-through-to-the-stock-jupyterhub-spawn-screen-no-logs)
- [DEF-2: Server Status hero shows Activity 0 when the server is stopped](#def-2-server-status-hero-shows-activity-0-when-the-server-is-stopped)
- [DEF-3: Host Status CPU/Memory bars blank with no tooltip when no servers are active](#def-3-host-status-cpumemory-bars-blank-with-no-tooltip-when-no-servers-are-active)
- [DEF-4: GPUs shown without live health when the gpuinfo sidecar is disconnected](#def-4-gpus-shown-without-live-health-when-the-gpuinfo-sidecar-is-disconnected)
- [DEF-5: Infinite login redirect loop (nested ?next=) on the auth pages](#def-5-infinite-login-redirect-loop-nested-next-on-the-auth-pages)
- [DEF-6: New user activity spikes to ~300% instead of ramping from zero](#def-6-new-user-activity-spikes-to-300-instead-of-ramping-from-zero)
- [DEF-7: Volume sizes show ~0 GB (partial cold-boot df result cached for an hour)](#def-7-volume-sizes-show-0-gb-partial-cold-boot-df-result-cached-for-an-hour)

---

## DEF-1: Start-server page falls through to the stock JupyterHub spawn screen, no logs

- **Severity**: HIGH - the dedicated Start-server experience (progress bar + live log tail) is bypassed
- **Status**: fix applied (code); runtime verify pending operator rebuild (2026-06-19)
- **Surface**: `src/pages/Starting.tsx` (route `servers/:name/starting`), `hooks/useSpawnProgress.ts`, `hooks/useContainerLogTail.ts`
- **Origin**: NOT the `/dashboard` -> `/home` rename (that only coincided); introduced by the React-portal rewrite (`3dd620b`), which replaced the readiness-probing `home.html` start flow with a page that trusts the hub `ready` flag

Clicking Start on your own server opens the dedicated Starting page; the progress bar jumps quickly to 100%, then the browser switches to the stock JupyterHub spawn-pending screen and no container logs are ever shown. Worked before the portal rewrite.

Root cause: the SSE-drop fallback poll in `useSpawnProgress.ts` treated `'spawning'` as "running" and flipped the bar to `percent:100, phase:'ready'` on the first poll (~1.5s after Start, when the spawner is merely present). That premature `ready` (a) hard-navigated to `/user/{name}/` before the lab served HTTP, so the hub rendered its stock `spawn_pending.html`, and (b) ended the `'spawning'` phase before the 1.5s log-tail poll ran, so the panel stayed empty. A residual ~1s false-positive also exists on the genuine path: the hub `ready` flag flips before the lab actually answers. The purpose-built `LabReadyHandler` (`/api/users/{name}/lab-ready`, always-200 `{ready}`) that the old flow used was never wired into the React page.

- [x] **Repro** - Start your own stopped server; progress shoots to 100% (~1.5s) then the stock hub spawn page replaces the dedicated page; the log-tail panel stays empty
  - log: 2026-06-19 reported by operator; mechanism confirmed by code trace
- [x] **Root cause identified** - SSE-drop fallback accepts `'spawning'` as ready (`useSpawnProgress.ts`) plus an unguarded hub-`ready` false-positive on the redirect (`Starting.tsx`)
  - log: 2026-06-19 confirmed
- [x] **Fix** - fallback now requires `active`/`idle` (not `spawning`); the own-server redirect probes `/lab-ready` and enters only once the lab truly answers (60s deadline last-resort)
  - log: 2026-06-19 `useSpawnProgress.ts` fallback condition tightened + dead `isRunning` removed; `Starting.tsx` redirect gated on `hubGet('/users/{name}/lab-ready')`; tsc + eslint clean
- [x] **No premature 100%** - the bar stays `spawning` through the real spawn; reaches `ready` only on active/idle (fallback) or the hub `ready` SSE frame
  - log: 2026-06-19 code
- [x] **Logs shown** - phase stays `'spawning'` for the spawn duration, so `useContainerLogTail` keeps polling and renders lines while the container boots
  - log: 2026-06-19 code
- [ ] **Verified** - confirmed on the live stack after the operator rebuilds the image
  - log: 2026-06-19 pending rebuild
- [ ] **Edge: log endpoint reachability** - confirm `GET /api/users/{name}/server/logs` returns 200 during a spawn; a 500 would mean the hub can't reach the docker socket (a separate cause of empty logs the silent catch hides)
  - log: 2026-06-19 runtime check to rule out a second cause

### Cross-references

- acc-crit: [dedicated Start-server page with live container-log feed](acc-crit-duoptimumhub.md#dedicated-start-server-page-with-live-container-log-feed)

---

## DEF-2: Server Status hero shows Activity 0 when the server is stopped

- **Severity**: MED - the Server Status hero misreports a real, monitored metric as zero
- **Status**: fix applied (code); runtime verify pending operator rebuild (2026-06-19)
- **Surface**: `src/components/ServerHero.tsx` (the Activity row of the Server Status / Server Control hero on Home)

Activity is a 7-day engagement metric sampled for every user - active and offline - and decays over ~3 days (72h half-life); it exists and is meaningful whether or not the server is running right now. The hero zeroed it the instant the server stopped, so a user who worked all day showed Activity 0 the moment their lab was culled.

- [x] **Repro** - stop your lab (or let it cull); the Server Status hero Activity meter drops to empty even though the Servers and Users lists still show your real 7-day activity
  - log: 2026-06-19 reported by operator on the live stack
- [x] **Root cause identified** - `ServerHero.tsx` rendered `<ActivityMeterFill value={running ? hero.activity : 0} .../>` - a `running ?` gate that zeroed the meter when stopped. The data layer (`liveSource.getServerHero`) already returns the ungated 7-day score; only the hero re-zeroed it. Same class of bug the Servers/Users rows had (fixed earlier in `liveSource.activityFields`), left behind on the hero
  - log: 2026-06-19 confirmed by code trace
- [x] **Fix** - drop the gate; the hero meter reads `hero.activity` / `hero.activityHours` / `hero.activityPct` directly, matching every other surface
  - log: 2026-06-19 `ServerHero.tsx` Activity row ungated; tsc/eslint pending verify
- [ ] **Verified** - on the live stack after rebuild: stop a server with non-zero activity, confirm the hero meter matches the Servers/Users meters
  - log: 2026-06-19 functional test `test_activity_consistency::test_hero_activity_shown_when_stopped` added; runtime pending rebuild

### Cross-references

- acc-crit: [activity reporting consistency](acc-crit-duoptimumhub.md#activity-reporting-consistency)

---

## DEF-3: Host Status CPU/Memory bars blank with no tooltip when no servers are active

- **Severity**: MED - the Host Status panel reads as broken (empty bars, no hover detail) whenever the platform is idle
- **Status**: fix applied (code); runtime verify pending operator rebuild (2026-06-19)
- **Surface**: `src/services/hub/liveSource.ts::getTotalResources` (Host Status card on the admin Home)

With zero active user servers the Host Status CPU and Memory bars showed a bare 0% with no tooltip and no error state - indistinguishable from a genuine failure. GPUs still listed (inventory is independent), which made the empty CPU/MEM bars look doubly broken.

- [x] **Repro** - on the admin Home with no labs running, the Host Status CPU and Memory bars are empty and have no tooltip on hover (the GPU row still shows)
  - log: 2026-06-19 reported by operator on the live stack
- [x] **Root cause identified** - `getTotalResources` early-returned `{ cpu: 0, mem: 0, gpu, gpus, gpuDevices }` when `active.length === 0`, dropping `cpuTip` / `memTip` and the `cpuError` / `memError` host-total flags that the normal path supplies
  - log: 2026-06-19 confirmed by code trace
- [x] **Fix** - removed the early return; the general path now runs for zero servers too - an honest 0% bar that still carries the tooltip ("0 of N cores used across 0 servers", "0% used ... across 0 servers") and sets `cpuError` / `memError` when the host totals are unreadable
  - log: 2026-06-19 `getTotalResources` early return removed; aggregation over an empty active set yields 0 with full tooltip/error handling
- [ ] **Edge: host totals unreadable** - when `cpu_host_total` / `memory_host_total_mb` come back null the bar renders an explicit "unavailable" (error flag) with its tooltip, never a fabricated 0%
  - log: 2026-06-19 preserved from the existing path, now reached at 0 servers too
- [ ] **Verified** - on the live stack after rebuild: idle platform, hover the Host Status CPU/Memory bars, confirm a tooltip
  - log: 2026-06-19 functional test `test_host_status::test_host_status_bars_have_tooltips` added; runtime pending rebuild

### Cross-references

- acc-crit: [resource bars (limits + tooltips)](acc-crit-duoptimumhub.md#resource-bars-limits--tooltips)

---

## DEF-4: GPUs shown without live health when the gpuinfo sidecar is disconnected

- **Severity**: MED - the platform claims GPUs it has no live information about
- **Status**: fix applied (code); runtime verify pending operator rebuild (2026-06-19)
- **Surface**: `duoptimum_hub_services/gpu_cache.py`, `handlers/activity.py`, `src/services/hub/liveSource.ts::getTotalResources`, `src/components/meters.tsx::ResourceBars`

The GPU inventory is enumerated once at hub startup and seeded from a persisted cache (observed 15h old in the live log) - it OUTLIVES the gpuinfo-nvidia sidecar. When the sidecar is down (e.g. its image is absent: `[GPUInfo] image '...duoptimum-gpuinfo-nvidia:latest' not present locally; GPU off until available`) the hub still reported `enabled=1 detected=1 gpus=[A500, 5090, 5000 Ada]` from the stale cache, so the Host Status listed three GPUs with no utilisation, memory, temperature or power - "we have GPUs" with nothing actually known about them.

- [x] **Repro** - with the gpuinfo sidecar stopped/absent, the Host Status GPU row lists the devices but every tooltip is bare (no utilisation / memory / temp / power)
  - log: 2026-06-19 reported by operator; confirmed by the hub startup log (sidecar image absent, inventory seeded from 15h-old persisted cache)
- [x] **Root cause identified** - there was no LIVE sidecar-reachability signal. The display gated only on `gpu_enabled` (a startup capability) and the static inventory, never on whether the sidecar is currently answering. Empty utilisation samples were silently swallowed ("Sample empty - keeping previous cache")
  - log: 2026-06-19 confirmed by code trace
- [x] **Fix (backend)** - `gpu_cache` records `last_attempt` / `last_ok` on every refresh; new `gpu_sidecar_connected()` is true only when the latest sample succeeded AND is fresh (staleness `max(2x interval, 90s)`). `handlers/activity.py` exposes it as `gpu_connected`
  - log: 2026-06-19 `gpu_cache.py` + `handlers/activity.py`
- [x] **Fix (frontend)** - `getTotalResources` sets `gpuDisconnected` and strips live-health fields when `gpu_connected` is false; `ResourceBars` drops any GPU row flagged `gpuDisconnected`, so the Host Status shows NO GPU info when the sidecar is down
  - log: 2026-06-19 `liveSource.ts`, `meters.tsx`, `Home.tsx`, `types.ts`
- [x] **Edge: group GPU-grant editor reflects live availability** - the editor lists the CURRENTLY-available devices (none when the sidecar is down); the stored grant is preserved until edited, and saving reconciles `gpu_device_ids` against the available devices so editing re-syncs the grant to reality (new devices or none)
  - log: 2026-06-19 `gpuDevices` gated on `gpu_connected`; `GroupPolicyTab` emit drops granted ids not currently present once the inventory loaded
- [ ] **Verified** - on the live (GPU) stack after rebuild: stop the gpuinfo sidecar, confirm the Host Status GPU row disappears within the staleness window; restart it, confirm it returns with live health
  - log: 2026-06-19 backend unit test for `gpu_sidecar_connected`; functional `test_host_status::test_gpu_hidden_when_sidecar_down` (gpu-marked) added; runtime pending rebuild

### Cross-references

- acc-crit: [last-known cache + non-blocking GPU + GPU-widget gating](acc-crit-duoptimumhub.md#last-known-cache--non-blocking-gpu--gpu-widget-gating)
- operational note: the sidecar image is `stellars/duoptimum-gpuinfo-nvidia:latest` (rebrand); if it is absent the sidecar never starts - a separate build/pull concern, but the portal now degrades correctly regardless

---

## DEF-5: Infinite login redirect loop (nested ?next=) on the auth pages

- **Severity**: BLOCKER - the site is unusable; visiting it produces an ever-nesting `/hub/login?next=/hub/login?next=...%2Fhub%2Fhome` URL and hundreds of `/hub/api/*` calls returning 302/403
- **Status**: fixed, deployed and verified (2026-06-20)
- **Surface**: `src/App.tsx`, `src/main.tsx`, `src/services/hub/client.ts` (`loginRedirect`, `getCurrentUser`), `src/services/hub/liveSource.ts` (`getTokens`)

Loading the hub root bounced through an unbounded chain of `/hub/login?next=...` redirects, each wrapping the previous URL, while the network tab filled with `/hub/api/*` requests returning 302/403.

Root cause: JavaScript import side effects. `App.tsx` ran `hydrateQueryCache`, `persistQueryCache` and `prefetchCore()` as module-level statements. `main.tsx` statically `import`s `App` to choose between `<App/>` and `<AuthApp/>`, so merely importing the module executed those statements on EVERY page - including the login/signup pages (which render `<AuthApp/>`). `prefetchCore()` warms the `tokens` query via `getTokens()` -> `getCurrentUser()`, which on an unauthenticated auth page gets 403 and calls `loginRedirect()`. `loginRedirect()` encodes the current URL into `?next=` and assigns it; run from the login page itself, each pass wraps the prior `?next=`, so the URL grows without bound.

- [x] **Repro** - open the hub root unauthenticated (Playwright against the live URL); the address bar shows nested `/hub/login?next=/hub/login?next=...` and many `/hub/api/*` 302/403 calls
  - log: 2026-06-19 reproduced with Playwright against the live deployment
- [x] **Root cause identified** - module-level cache-warm/prefetch side effects in `App.tsx` fire on `import` even on auth pages (main.tsx statically imports App); the `tokens` warm-up hits `getCurrentUser` -> 403 -> `loginRedirect` wraps the current login URL into `?next=` -> infinite nesting
  - log: 2026-06-19 confirmed empirically via Playwright instrumentation (the static `import App` executes the side effects; login renders `AuthApp`, not `App`)
- [x] **Fix** - moved the three side effects into the `App` component body behind a `useRef` guard so they run once when `<App/>` actually mounts, never on the auth pages; auth pages render `<AuthApp/>` with no portal GETs
  - log: 2026-06-19 `App.tsx` (side effects gated to component mount); rebuilt with `make rebuild`, `hub_data` volume reset, stack restarted
- [x] **Verified** - post-deploy Playwright: clean `/hub/login?next=%2Fhub%2Fhome` (single, un-nested), login form renders, 2 navigations, no loop
  - log: 2026-06-19 verified on the live stack after rebuild

### Cross-references

- acc-crit: [Auth & bootstrap](acc-crit-duoptimumhub.md#auth--bootstrap) - login/redirect workflow functional test tracked there

---

## DEF-6: New user activity spikes to ~300% instead of ramping from zero

- **Severity**: MED - misleading activity reading; a brand-new user looks heavily loaded when they have barely been active
- **Status**: fixed (2026-06-20) - denominator changed to a full-window expected total; unit-tested
- **Surface**: `duoptimum_hub_services/activity/monitor.py` (`_weighted_active_fraction`, `_weighted_expected_total`, `get_score`, `get_avg_active_hours`), `docs/activity-tracking-methodology.md`, the activity meters on the portal

A just-created user (the freshly bootstrapped admin), active for only a short while, shows an activity meter that jumps to ~300% almost immediately instead of growing progressively from zero. Expected: a new account starts near zero and ramps as real activity accumulates over the scoring window.

Root cause: the score model normalises `active_frac * 24` against the daily target on the assumption that samples are taken 24/7, so the decay-weighted active fraction equals the real share of the day active. But `_weighted_active_fraction` builds `weighted_total` from only the samples that EXIST in the DB, not from true elapsed wall-clock. A brand-new account has just a handful of samples, nearly all ACTIVE (it was created and the user immediately used the lab), so `active_frac` is ~1.0. `get_avg_active_hours` then returns ~24.0 honest-hours/day UNCAPPED, and the portal percentage (honest hours / 8h target) reads ~300%. `get_score` itself clamps at 100% (`min(1.0, ...)`, L146), so the 300% surfaces through the uncapped avg-hours / frontend-pct path. The documented 24h / ~144-sample minimum-data threshold (`activity-tracking-methodology.md`) is not enforced in the score path.

- [x] **Repro** - create a new admin, use the lab briefly, observe the activity meter reading ~300% rather than a low ramping value
  - log: 2026-06-20 reported by operator
- [x] **Root cause identified** - `_weighted_active_fraction` denominator counts only existing samples, not 24/7 elapsed time; a new mostly-active account gives `active_frac`~1.0 -> `get_avg_active_hours`~24h/day -> 24/8 = ~300%; the documented 24h min-data threshold is not enforced
  - log: 2026-06-20 confirmed by code trace (monitor.py) against the design doc
- [x] **Fix** - `_weighted_active_fraction` now divides decay-weighted active samples by `_weighted_expected_total()`: the decay-weighted count of every slot a FULLY sampled retention window holds (geometric series, `sum r**k`, `r = exp(-lambda*dt)`, `n = retention/dt`), not the samples on hand. Not-yet-elapsed slots count as inactive, so a new account's fraction starts near zero and ramps; an established account (window already full) is unchanged. Fraction capped at 1.0 (hours <= 24). NOTE: "elapsed since first sample" was rejected - it still spikes (few early samples, all active -> frac ~1.0); only a FULL-window denominator ramps from zero. Removing the init inactive sample is also WRONG (would force frac=1.0)
  - log: 2026-06-20 implemented in `activity/monitor.py`
- [x] **Verified** - new account reads near-zero immediately after creation and grows monotonically with real activity, never exceeding 24h/day from a short burst; established 8h/day still reads 100
  - log: 2026-06-20 unit tests `TestNewUserRamp` + rewritten `TestScoring`/`TestTargetNormalisation` (full-window seeds), 743 pass

### Cross-references

- acc-crit: [activity scoring (target-hours normalisation + honest hours)](acc-crit-duoptimumhub.md#activity-scoring-target-hours-normalisation-honest-hours)

---

## DEF-7: Volume sizes show ~0 GB (partial cold-boot df result cached for an hour)

- **Severity**: HIGH - the Servers / Manage-Volumes UI reports volume sizes that are wildly wrong (workspace 0 GB while 87 GB on disk), so quota usage is meaningless and a user looks empty when they are full
- **Status**: open - root cause confirmed on the live stack; fix + faster method pending
- **Surface**: `duoptimum_hub_services/volume_cache.py` (`_fetch_volume_sizes`, `_refresh_volume_sizes_sync`, `VolumeSizeRefresher`), `handlers/activity.py` (`volume_size_mb` / `volume_breakdown`), the Servers list + Manage-Volumes table

On the live stack the Manage-Volumes / Servers UI shows `konrad.jelen`'s workspace as 0 GB and home as ~0.5 GB, while on disk the workspace is 86.96 GB and home 38.42 GB. The hub's persisted cache (`/data/volume_sizes.json`, written at boot) holds byte-identical sizes for all three users (`home 482.9, workspace 0.0, cache 425.9` MB) - impossible for real independent data.

Root cause: `_fetch_volume_sizes` calls Docker `/system/df?type=volume` once at hub boot and reads `UsageData.Size`. Docker computes df volume sizes lazily and returns whatever is ready when asked - the boot call (logged ~14s after start) caught the du scan MID-FLIGHT: the small `cache` volume had finished (425.9 vs real 446), `home` was partway (482.9 vs 38 GB), the large `workspace` had not started (0). The hub cached AND persisted that partial result, and only refreshes every `JUPYTERHUB_ACTIVITYMON_VOLUMES_UPDATE_INTERVAL=3600s`, so the wrong sizes persist up to an hour. Two compounding problems: (1) `/system/df` can return an incomplete snapshot with no completeness signal, and (2) the call is brutally slow - a warm `type=volume` call timed at 131.7s because it re-scans every volume on the host (23 volumes incl. the live 250 GB), not just the user's.

- [x] **Repro** - on the live stack, Manage-Volumes shows `konrad.jelen` workspace 0 GB; `/data/volume_sizes.json` has identical partial sizes for all 3 users; a fresh in-process re-fetch returns correct distinct sizes
  - log: 2026-06-20 reported by operator ("volumes massive, server shows almost nothing"); confirmed by reading the persisted cache + reproducing the df call inside the hub
- [x] **Root cause identified** - boot-time `/system/df?type=volume` returns a partial mid-scan result (big volumes 0); cached + persisted; only refreshed hourly. Warm call measured 131.7s, scanning ALL host volumes
  - log: 2026-06-20 timing + partial-result evidence captured from the running hub
- [ ] **Fix (correctness)** - never cache/persist an incomplete result; the size source must be deterministic (complete-or-retry), so the UI never shows a partial/zero size
- [ ] **Fix (faster method)** - replace the full-system `/system/df` scan with a TARGETED, parallel per-volume size of only the user's volumes (model on `container_size_cache`'s parallel `inspect(size=True)`); avoids re-scanning system + every other user's volumes
- [ ] **Edge: empty volume** - a genuinely empty volume reports ~0, not an error; 0 must be distinguishable from "not yet computed"
- [ ] **Edge: orphaned/renamed-project volumes** - stale `stellars-tech-ai-lab_*` volumes (a prior project name) coexist with `stellars-tech-ai-workbench_*`; the size total must count only the active project's templated volumes, not double-count the orphans (separate disk-cleanup, not a code defect)
- [ ] **Functional test** - small volume -> reported small; grow cache/home/workspace to ~1.5 GB each -> reported ~1.5 GB (not 0), within tolerance
- [ ] **Verified** - on the live stack after rebuild/redeploy: Manage-Volumes shows `konrad.jelen` workspace ~87 GB / home ~38 GB, refreshed within seconds of boot
- [ ] **Log spam** - `VolumeSizeRefresher.start()` logs `[VolumeSizeRefresher] Already running` every ~15s (activity-poll cadence); should be quiet when already running

### Cross-references

- acc-crit: [volume-size reporting](acc-crit-duoptimumhub.md#volume-size-reporting)
- task: #347
