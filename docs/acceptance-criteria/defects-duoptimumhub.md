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
- [DEF-13: TTL bar scaled to absolute ceiling (35h reads 50%)](#def-13-ttl-bar-scaled-to-absolute-ceiling-35h-reads-50) - fixed
- [DEF-14: TTL extend glow stuck at full opacity, no blur](#def-14-ttl-extend-glow-stuck-at-full-opacity-no-blur) - fixed
- [DEF-15: TTL extend bar flips to 100% instead of growing](#def-15-ttl-extend-bar-flips-to-100-instead-of-growing) - open
- [DEF-16: Stopped-server readout shows "stopped now ago"](#def-16-stopped-server-readout-shows-stopped-now-ago) - open
- [DEF-17: Role-label keys/values baked only in Dockerfile, not in compose.yml](#def-17-role-label-keysvalues-baked-only-in-dockerfile-not-in-composeyml) - open

## Open

### DEF-17: Role-label keys/values baked only in Dockerfile, not in compose.yml

- [ ] **LOW** - the 8 resource role-label envs (3 KEYS + 5 per-role VALUES: `JUPYTERHUB_LABEL_NETWORK_ROLE_KEY`, `JUPYTERHUB_LABEL_NETWORK_ROLE_LAB`, `JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO`, `JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY`, `JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO`, `JUPYTERHUB_LABEL_VOLUME_ROLE_KEY`, `JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED`, `JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY`) were baked only as Dockerfile ENV and never surfaced in `compose.yml`, even though compose stamps the MATCHING labels on the networks/volumes/sidecar - the discovery contract (env value MUST equal the stamped label) was split across two files with the env half invisible, a silent drift risk; fix: surface all 8 in a "HUB: role-label discovery contract" section of the hub `environment:` block, values identical to the Dockerfile defaults (no behaviour change), beside the resource labels they must match; `compose.yml`
  - log: 2026-06-20 reported (operator: "why aren't the volume, container, network keys and labels envs in compose.yml? I have asked you to put them there"); had been parked on an ambiguous "unsurface" wording instead of acted on - that was the miss
  - log: 2026-06-20 fix applied - 8 envs added to compose.yml role-label section; verify on next redeploy (no-op: values == Dockerfile defaults, hub already validated them)
  - open: `settings_dictionary.yml` carries 5 of the 8 (network + container) but not the 3 volume role labels - pending operator call on "unsurface": remove all role labels from the admin Settings page (infra-only) vs add the 3 missing for completeness

### DEF-16: Stopped-server readout shows "stopped now ago"

### DEF-16: Stopped-server readout shows "stopped now ago"

- [ ] **LOW** - the offline TTL-slot readout built `stopped ${timeAgoShort(iso)} ago`, and `timeAgoShort` returns `now` for the sub-minute case, yielding the ungrammatical "stopped now ago" right after a stop; fix: new `stoppedAgo(iso)` helper renders "stopped a moment ago" for sub-minute (and "never started" for null), used by the hero; `format.ts`, `ServerHero.tsx`
  - log: 2026-06-20 reported (operator: "'stopped now ago' is not a good message; if now, it should say 'stopped a moment ago'")
  - log: 2026-06-20 fixed - `stoppedAgo()` helper; typecheck + lint clean; functional regex `(stopped .+ ago|never started)` still matches; visual + functional verify pending next rebuild (task #382)
  - log: 2026-06-20 functional test added - `test_ttl_extend.py::test_stopped_server_reads_a_moment_ago` (start -> stop own server, assert "stopped a moment ago" visible + "now ago" never rendered); verify on rebuild run

### DEF-15: TTL extend bar flips to 100% instead of growing

- [ ] **LOW** - on extend the TTL progress bar jumps straight to its new fill (100% for a banked extend) instead of growing from its current position; the counter count-up animates but the bar does not; root cause: the fill relied on a CSS width transition ENABLED by the same `.doh-ttl-boost` class toggle that also changed the bar percent in the same React commit - enabling a transition and changing the animated value in one frame does not reliably animate (the browser may not paint the pre-change state), so the bar flips to the end value; antd's own `.ant-progress-bg` width transition compounded it; fix: drive the bar percent with the SAME `requestAnimationFrame` loop that animates the counter - grow from the captured current fill to the target in lockstep - and disable the CSS width transition (`.doh-ttl-boost .ant-progress-bg { transition: none }`) so rAF is the sole driver (guaranteed from->to growth, no flip); `meters.tsx`, `global.css`, `config.ts`
  - log: 2026-06-20 reported (operator: "on extend the bar just flips 100%; it should start at its current position and progress as part of the animation")
  - log: 2026-06-20 root cause: same-frame transition-enable + value-change does not animate; rAF is deterministic
  - log: 2026-06-20 fix applied (rAF-driven bar fill in lockstep with the counter; antd width transition killed); tsc/eslint clean; verify pending rebuild + live extend
  - ref: task #375; DEF-14 (glow); acc-crit "TTL extend bar animation"


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

### DEF-14: TTL extend glow stuck at full opacity, no blur

- [x] **MEDIUM** - on the live Server Control TTL bar, an extend leaves the glow overlay at FULL opacity (a near-solid white wash over the bar), it pulses once then stays, and the counter never blurs; operator screenshot mid-animation; root cause: the tint-overlay rewrite (#370, drop-shadow halo -> `::after` tint overlay) had three faults at once - (1) WASH: the overlay had no resting `opacity: 0` and no `animation-fill-mode`, so outside the 1.2s `doh-ttl-glow` keyframe it reverts to CSS-default opacity 1, and the boost window (`ttlExtendMs` 3s + until the value lands) outlasts the 1.2s glow, so the bar sits under a full-opacity tint after the single pulse; (2) PULSE: a keyframe (0 -> .5 -> 0) inherently ramps up AND back down inside its own window, so it reads as a one-shot pulse, not a glow held for the fill; (3) NO BLUR: the counter `doh-ttl-blur` keyframe had the same fill-mode gap; the design-page render looked good because it is a STATIC 50% tint (= the held state, no keyframe), and the past (@12d9734) render looked good because it used a drop-shadow HALO synced to the fill duration - a halo glows AROUND the bar and can never wash the fill, unlike a covering overlay; fix: restore the proven drop-shadow halo (brighter, `color-mix(currentColor, white 60%)`) and drive it with a CSS `transition` not a keyframe - the `.doh-ttl-boost` class toggles the filter on, the 100ms transition ramps it ON, HOLDS it for the whole boost window, ramps OFF in 100ms when the value lands (trapezoid envelope, no pulse); counter blurs `.75px` the same way (no halo, blur only); `global.css`, `meters.tsx`, `config.ts`
  - log: 2026-06-20 reported (operator screenshot: "glow is weird (full opacity), there is pulsing, there is no blur; all is bad")
  - log: 2026-06-20 root cause confirmed (wash + pulse + no-blur, all from keyframe overlay with no fill-mode; design page = static tint, past = halo synced to fill)
  - log: 2026-06-20 fix applied (drop-shadow halo + transition-held envelope, 100ms ramps, hold for fill; `ttlGlowMs` 1200 -> 100); tsc clean
  - log: 2026-06-20 VERIFIED live (operator: "ttl visual design is good - glow & blur")
  - lessons (CSS animation): (1) `@keyframes` ramps up AND back down inside its own window, so it always reads as a pulse; for a "ramp on / HOLD / ramp off" envelope use a CSS `transition` toggled by a class (trapezoid), never a keyframe; (2) a keyframe with no resting rule and no `animation-fill-mode` reverts to the property's CSS default outside its active window - a glow overlay then washes the element once the trigger outlives the keyframe; (3) a glow that COVERS the element (tint overlay) can wash it out, a glow that SURROUNDS it (drop-shadow halo) never can - prefer the halo; (4) enabling a transition and changing the animated value in the SAME commit does not reliably animate, so the element flips to the end value - for a guaranteed from->to animation drive the value with `requestAnimationFrame` and disable the CSS transition (see DEF-15)
  - ref: task #370 (tint-overlay glow), #374; DEF-15 (bar growth); acc-crit "TTL extend bar animation"

### DEF-13: TTL bar scaled to absolute ceiling (35h reads 50%)

- [x] **MEDIUM** - the React TTL bar measured banked time against the absolute ceiling (`base + max_extension` = 72h), so a session extended to 35h read ~48.6% the instant it was extended; the glow/blur also read as broken because the bar SHRANK on extend, and the slider defaulted to the (shifting) maximum instead of a stable recommendation; fix: measure against the backend-stored high-water mark `display_ceiling`, default the slider to +4h, restore the glow; `meters.tsx`, `session.py`, `idle_culler.py`, `global.css`, `config.ts`, `types.ts`, `liveSource.ts`
  - log: 2026-06-20 reported (operator: "extended to 35h, slider at 50%, 35h didn't become 100%"; "doesn't glow when grows"; "blur invisible"; "recommended extra sometimes max, sometimes 11h")
  - log: 2026-06-20 root cause: `pctFor` used `ceilingMin = timeLeft + maxAddHours*60` = the invariant 72h absolute ceiling, so banked % = remaining/72h; glow played on a shrinking bar; `useState(maxH)` defaulted the slider to the (shrinking) max; a reduced-motion guard had begun suppressing the pulse
  - log: 2026-06-20 fix: backend stores `display_ceiling` (remaining last extended TO) at extend and returns `display_ceiling_seconds`; bar measures against it (SSOT `calc_progress_pct_extended`, unit-tested); slider default +4h; colour gradual by % of base (`TTL_COLOR`); glow/blur ramp configurable (`ttlGlowMs`) + reduced-motion suppression removed; bar tooltip adds %, +h over standard, cull ETA
  - log: 2026-06-20 VERIFIED: 71 idle-culler unit tests pass; functional test + live check (below)
  - ref: task #363; acc-crit "TTL progress bar behaviour matrix" + "TTL extend bar animation"
