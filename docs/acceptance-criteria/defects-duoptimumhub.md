# Defects - Duoptimum Hub

Defect registry for the Duoptimum Hub portal and platform - one section per defect, same checklist model as the acceptance criteria ([acc-crit-duoptimumhub.md](acc-crit-duoptimumhub.md)). One document, not many.

Checkbox state: `[ ]` = open / unresolved, `[x]` = fixed and verified; in-progress stays `[ ]` and is marked in the latest `log:` line. Each defect carries severity, status, symptom, then repro / root cause / fix / verification as checklist items with a dated `log:` trail. Severity: BLOCKER (platform unusable) > HIGH (core flow broken) > MED (degraded) > LOW (cosmetic).

## Contents

- [DEF-1: Start-server page falls through to the stock JupyterHub spawn screen, no logs](#def-1-start-server-page-falls-through-to-the-stock-jupyterhub-spawn-screen-no-logs)
- [DEF-2: Server Status hero shows Activity 0 when the server is stopped](#def-2-server-status-hero-shows-activity-0-when-the-server-is-stopped)
- [DEF-3: Host Status CPU/Memory bars blank with no tooltip when no servers are active](#def-3-host-status-cpumemory-bars-blank-with-no-tooltip-when-no-servers-are-active)
- [DEF-4: GPUs shown without live health when the gpuinfo sidecar is disconnected](#def-4-gpus-shown-without-live-health-when-the-gpuinfo-sidecar-is-disconnected)

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
