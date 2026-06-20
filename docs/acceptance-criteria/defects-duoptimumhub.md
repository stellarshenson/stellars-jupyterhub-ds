# Defects - Duoptimum Hub

Defect tracker, acc-crit style. Grouped `## Open` / `## Fixed` for addressed-vs-unaddressed at a glance; per-defect `[x]` fixed / `[ ]` open (fix-applied-but-unverified stays `[ ]`). Each `log:` line is dated evolution - reported -> root cause -> fix -> verified. TOC below jumps to any defect.

## Contents

- [DEF-1: Start-server falls to stock spawn screen, no logs](#def-1-start-server-falls-to-stock-spawn-screen-no-logs) - open
- [DEF-2: Server Status hero Activity 0 when stopped](#def-2-server-status-hero-activity-0-when-stopped) - open
- [DEF-3: Host Status CPU/Mem bars blank when idle](#def-3-host-status-cpumem-bars-blank-when-idle) - open
- [DEF-4: GPUs shown without live health when sidecar down](#def-4-gpus-shown-without-live-health-when-sidecar-down) - open
- [DEF-5: Infinite login redirect loop](#def-5-infinite-login-redirect-loop) - fixed
- [DEF-6: New-user activity spikes ~300%](#def-6-new-user-activity-spikes-300) - fixed
- [DEF-7: Volume sizes show ~0 GB](#def-7-volume-sizes-show-0-gb) - open
- [DEF-8: Traefik dashboard reachable when closed](#def-8-traefik-dashboard-reachable-when-closed) - fixed
- [DEF-9: Events audit feed stale on reload](#def-9-events-audit-feed-stale-on-reload) - fixed
- [DEF-10: Functest leaks spawned lab containers](#def-10-functest-leaks-spawned-lab-containers) - fixed
- [DEF-11: Functional UI tests brittle on new frontend](#def-11-functional-ui-tests-brittle-on-new-frontend) - fixed
- [DEF-12: Live hub 504 Gateway Timeout via Traefik](#def-12-live-hub-504-gateway-timeout-via-traefik) - fixed

## Open

### DEF-1: Start-server falls to stock spawn screen, no logs

- [ ] **HIGH** - SSE-drop fallback took `spawning` as ready -> premature 100% + redirect before lab served HTTP; fix: fallback needs active/idle, redirect probes `/lab-ready`; `useSpawnProgress.ts`, `Starting.tsx`
  - log: 2026-06-19 reported; root cause: fallback accepts `spawning` + unguarded hub-`ready` redirect false-positive
  - log: 2026-06-19 fix applied (fallback tightened, redirect gated on `/lab-ready`, 60s deadline); tsc/eslint clean
  - log: 2026-06-19 verify pending rebuild; edge: confirm `/server/logs` 200 mid-spawn
  - ref: acc-crit dedicated Start-server page

### DEF-2: Server Status hero Activity 0 when stopped

- [ ] **MED** - hero gated meter `running ? activity : 0`; activity is a 7-day metric, valid when stopped; fix: drop gate, read `hero.activity` direct; `ServerHero.tsx`
  - log: 2026-06-19 reported; root cause: `running ?` gate re-zeroed the already-ungated score
  - log: 2026-06-19 fix applied; functional `test_hero_activity_shown_when_stopped` added
  - log: 2026-06-19 verify pending rebuild
  - ref: acc-crit activity reporting consistency

### DEF-3: Host Status CPU/Mem bars blank when idle

- [ ] **MED** - `getTotalResources` early-returned 0 with no tip/error flags at 0 servers; fix: drop early return, general path runs at 0 servers; `liveSource.ts`
  - log: 2026-06-19 reported; root cause: zero-server early return drops `cpuTip`/`memTip`/`cpuError`/`memError`
  - log: 2026-06-19 fix applied (honest 0% + tooltip); `test_host_status_bars_have_tooltips` added
  - log: 2026-06-19 verify pending rebuild
  - ref: acc-crit resource bars (limits + tooltips)

### DEF-4: GPUs shown without live health when sidecar down

- [ ] **MED** - inventory outlives sidecar (seeded from 15h-old cache), no live-reachability signal; fix: `gpu_sidecar_connected()` -> `gpu_connected`, frontend drops row when disconnected; `gpu_cache.py`, `liveSource.ts`, `meters.tsx`
  - log: 2026-06-19 reported; root cause: display gated on startup capability + static inventory, never live sidecar reachability
  - log: 2026-06-19 fix applied (last_ok + freshness signal; group GPU-grant editor reconciles to live devices)
  - log: 2026-06-19 verify pending rebuild (gpu stack); `test_gpu_hidden_when_sidecar_down` added
  - ref: acc-crit last-known cache + GPU-widget gating

### DEF-7: Volume sizes show ~0 GB

- [ ] **HIGH** - boot `/system/df?type=volume` catches du mid-scan (big volumes 0), result cached + persisted, refresh hourly; warm call 131.7s (scans ALL host volumes); `volume_cache.py`, `handlers/activity.py`
  - log: 2026-06-20 reported (workspace 0 GB vs 87 GB on disk) + root cause confirmed live (identical partials in `/data/volume_sizes.json`; df 131.7s)
  - log: 2026-06-20 OPEN - fix = never cache incomplete (complete-or-retry) + targeted per-user parallel size, not full-system df; functional test + `Already running` log-spam cleanup pending
  - ref: acc-crit volume-size reporting; task #347

## Fixed

### DEF-5: Infinite login redirect loop

- [x] **BLOCKER** - module-level cache-warm/prefetch in `App.tsx` fired on `import` even on auth pages -> `getCurrentUser` 403 -> `loginRedirect` wrapped own URL (nested `?next=`); fix: side effects moved into `App` body behind `useRef`; `App.tsx`, `main.tsx`, `client.ts`
  - log: 2026-06-19 reproduced (Playwright, live); root cause: static `import App` runs side effects on auth pages (which render `AuthApp`)
  - log: 2026-06-19 fix applied (side effects run once on mount)
  - log: 2026-06-20 VERIFIED live: single un-nested `?next`, login renders, no loop
  - ref: acc-crit Auth & bootstrap

### DEF-6: New-user activity spikes ~300%

- [x] **MED** - `_weighted_active_fraction` denominator counted only existing samples; new mostly-active account -> frac ~1.0 -> ~24h/day -> 300%; fix: divide by `_weighted_expected_total()` (full retention window); `activity/monitor.py`
  - log: 2026-06-20 reported; root cause: denominator = samples on hand, not full-window expected total
  - log: 2026-06-20 fix applied (geometric-series full-window denominator; not-yet-elapsed slots inactive -> ramps from zero)
  - log: 2026-06-20 VERIFIED: unit tests `TestNewUserRamp` + rewrites, 743 pass
  - ref: acc-crit activity scoring

### DEF-8: Traefik dashboard reachable when closed

- [x] **HIGH/security** - docker provider scanned whole host daemon -> a foreign deployment's enabled `/traefik` router served via local `api@internal` despite `traefik.enable=false`; fix: project-scoped `--providers.docker.constraints`; `compose.yml`, `compose.functional-traefik.yml`
  - log: 2026-06-20 reproduced live (closed stack `/traefik/api/overview` 200; routers carried operator-project labels)
  - log: 2026-06-20 root cause: provider not namespace-scoped; probe showed basePath alone 404, leak came only from the foreign router
  - log: 2026-06-20 fix: `--providers.docker.constraints=Label(com.docker.compose.project,<project>)` (prod scopes `${COMPOSE_PROJECT_NAME}`, functest overlay `stellars-functest`)
  - log: 2026-06-20 VERIFIED: `run.sh traefik` 3/3 (open 200), `run.sh traefik-closed` 1/1 (closed 404)
  - ref: acc-crit Traefik dashboard - Closeable; task #349

### DEF-9: Events audit feed stale on reload

- [x] **MED** - persisted query cache + `staleTime 30s` painted the pre-event list; just-recorded events (e.g. rename) missing up to 30s after a hard reload; fix: exclude `events` from cache persistence; `persistCache.ts`
  - log: 2026-06-20 isolated via probe (cold load shows row instant; warm/persisted load shows pre-rename list); passes isolation, fails only full regime
  - log: 2026-06-20 root cause: hydrated-fresh cache not refetched on load (paint-from-cache design); an audit feed must be fresh
  - log: 2026-06-20 fix: `EXCLUDE=['tokens','events']` -> reload refetches the feed cold
  - log: 2026-06-20 VERIFIED via probe; full-regime `test_rename_user` confirm in post-rebuild run
  - ref: acc-crit rename-user

### DEF-10: Functest leaks spawned lab containers

- [x] **LOW/harness** - baked `{compose}_labs` puts labs in a separate project; `run.sh::clean` reaps by `=stellars-functest` only -> orphan `jupyterlab-*`; fix: keep functest labs in the hub project; `compose.functional.yml`
  - log: 2026-06-20 observed (orphan lab after teardown; `test_container_policy` asserted the old project label)
  - log: 2026-06-20 fix: `JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME=` empty -> labs stay in `stellars-functest`, reaped by `clean()`
  - log: 2026-06-20 VERIFIED: `test_container_policy` passes, no orphans
  - ref: acc-crit Role labels, namespace and config validator

### DEF-11: Functional UI tests brittle on new frontend

- [x] **LOW/test** - ambiguous selectors + a gpu test run without its overlay; fix: footer-scoped Close, content-scoped tooltip, gpu tests only in the gpu regime; `test_remove_user.py`, `test_servers_resources.py`, `run.sh`
  - log: 2026-06-20 observed: Close matched X-icon + footer; tooltip matched custom + antd sort tip; gpu net test ran in signup (no overlay)
  - log: 2026-06-20 fix applied (footer Close; content tooltip; signup regime GPU off -> gpu tests to gpu regime; dropped orphan `detect_gpu`)
  - log: 2026-06-20 VERIFIED: remove_user + container_policy pass; gpu net tests pass in the gpu regime
  - ref: acc-crit Role labels, namespace and config validator

### DEF-12: Live hub 504 Gateway Timeout via Traefik

- [x] **HIGH** - hub on 2 nets (`hub_network` + `hub_gpuinfo_network`), traefik only on `hub_network`, no `traefik.docker.network` label -> traefik picked the unreachable gpuinfo IP and hung -> 504 right after start, intermittent across restarts; fix: pin `traefik.docker.network=${COMPOSE_PROJECT_NAME}_hub_network`; `compose.yml`
  - log: 2026-06-20 reported (504 right after start, intermittent; recent regression from the DEF/#366 two-network split)
  - log: 2026-06-20 root cause confirmed live: traefik->`172.19.0.2:8000` (hub_network) OK, traefik->`172.20.0.2:8000` (gpuinfo) timeout; multi-network backend, no net pin, gpuinfo IP sorts first
  - log: 2026-06-20 fix: `traefik.docker.network` label pins the backend to hub_network; redeploy (compose-only, no rebuild)
  - log: 2026-06-20 VERIFIED: curl + Playwright real-browser through traefik 200 (`/hub/login` "Sign in - Duoptimum Hub", `/` -> login redirect); was a 10s timeout
  - ref: task #362; DEF/#366 network rename
