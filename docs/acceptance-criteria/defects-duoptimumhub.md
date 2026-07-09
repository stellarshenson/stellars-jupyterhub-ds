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
- [DEF-18: Hub-unreachable display (corner diode + full-screen modal) looks bad](#def-18-hub-unreachable-display-corner-diode--full-screen-modal-looks-bad) - open
- [DEF-19: Hub log lines printed to bare stdout, not a proper logger](#def-19-hub-log-lines-printed-to-bare-stdout-not-a-proper-logger) - open
- [DEF-20: html_templates_enhanced custom Bootstrap layer is a dead relic](#def-20-html_templates_enhanced-custom-bootstrap-layer-is-a-dead-relic) - open
- [DEF-21: Connection indicator - ux-review minors (5xx copy, uncapped elapsed, dual warning languages)](#def-21-connection-indicator---ux-review-minors-5xx-copy-uncapped-elapsed-dual-warning-languages) - open
- [DEF-22: Hub connect URL uses ephemeral container id, brittle on redeploy](#def-22-hub-connect-url-uses-ephemeral-container-id-brittle-on-redeploy) - fixed
- [DEF-23: Hub API bound to the gpuinfo interface after the DEF-22 alias fix - total spawn outage](#def-23-hub-api-bound-to-the-gpuinfo-interface-after-the-def-22-alias-fix---total-spawn-outage) - fixed
- [DEF-24: GPU undetected (sidecar down) still spawns labs with GPU - crash](#def-24-gpu-undetected-sidecar-down-still-spawns-labs-with-gpu---crash) - fixed
- [DEF-25: Open-server actions enter the lab before it truly serves](#def-25-open-server-actions-enter-the-lab-before-it-truly-serves) - open
- [DEF-26: Zero-activity meter floors to one pale-red bar](#def-26-zero-activity-meter-floors-to-one-pale-red-bar) - open
- [DEF-27: GPU utilisation bar shows non-zero fill at 0% load](#def-27-gpu-utilisation-bar-shows-non-zero-fill-at-0-load) - open
- [DEF-28: TTL extend animation reads as ~0.5s, not the intended 3s](#def-28-ttl-extend-animation-reads-as-05s-not-the-intended-3s) - open
- [DEF-29: TTL extend glow (box-shadow halo) looks awful and bleeds onto the controls](#def-29-ttl-extend-glow-box-shadow-halo-looks-awful-and-bleeds-onto-the-controls) - open
- [DEF-30: GroupConfig GET/PUT fabricate a phantom config for a non-existent group](#def-30-groupconfig-getput-fabricate-a-phantom-config-for-a-non-existent-group) - open
- [DEF-31: User names colliding with static /users routes (new, bulk) not reserved](#def-31-user-names-colliding-with-static-users-routes-new-bulk-not-reserved) - open

## Open

### DEF-31: User names colliding with static /users routes (new, bulk) not reserved

- [ ] **LOW** - the SPA router registers `users/new`, `users/bulk`, `users/bulk/result` as static siblings of `users/:name`, so a user literally named `new` or `bulk` would misroute the same way a group named `new`/`export` did before the group-side fix. `DuoptimumNativeAuthenticator.validate_username` (`services/jupyterhub/duoptimum-hub-services/duoptimum_hub_services/auth.py`) has no equivalent reserved list. Pre-existing; surfaced by the architect adversarial pass while adding the group-side `_RESERVED_GROUP_NAMES` guard. Fix: mirror the group guard - reject `new`, `bulk` (case-insensitive) in username validation. Cross-ref acc-crit `duoptimumhub::Edge: route-colliding name reserved` (group side, done)
  - log: 2026-07-09 reported (architect adversarial review, round 4 of the create-then-configure feature) - deferred as out of that feature's scope; group side fixed, user side left for a dedicated change

### DEF-30: GroupConfig GET/PUT fabricate a phantom config for a non-existent group

- [ ] **MEDIUM** - `GroupsConfigHandler.get`/`.put` (`services/jupyterhub/duoptimum-hub-services/duoptimum_hub_services/handlers/groups.py`) act on the raw `group_name` path param via `ensure_config`/`save_config` with no check that the group exists in `jupyterhub.orm.Group`, unlike `GroupsDeleteHandler.delete` which 404s. Hitting `/groups/{typo}` or a just-deleted name (stale bookmark, back-button after delete, concurrent second-admin delete) silently creates/updates a phantom `groups_config` row and returns 200. Orphan configs are only reaped one-directionally as a side effect of the group-list GET. Pre-existing; NOT triggered by the create-then-configure feature (which always routes to a just-created, existing group). Fix: look up `orm.Group` first in `get`/`put` and 404 like `delete`
  - log: 2026-07-09 reported (architect adversarial review, round 4 of the create-then-configure feature) - deferred as out of that feature's scope; the create flow's target always exists, so the feature itself is unaffected

### DEF-29: TTL extend glow (box-shadow halo) looks awful and bleeds onto the controls

- [ ] **MEDIUM** - the DEF-28 fix gave the extend boost a whole-bar accent halo via a `box-shadow` on the bar WRAPPER (`.doh-ttl-bar.doh-ttl-boost`). A `box-shadow` is never clipped by sibling layout, so the halo (peaked `0 0 26px 7px var(--color-accent)`) bloomed ~33px in every direction - over the Open Lab / Restart / Stop buttons above and the Extend control beside it - a large diffuse blue rectangular fog (operator screenshot). Operator: the animation now plays (DEF-28 duration fix) but "the glow looks awful" and "you must enable somehow clipping - by building custom animated gadget". Root cause: a wrapper box-shadow CANNOT be clipped; an outer halo on a thin bar inherently bleeds. Fix: replace the antd `Progress` + wrapper box-shadow with a custom track+fill gadget where the glow lives INSIDE the `overflow:hidden` track - an inner inset bloom on the fill (`box-shadow: inset ...`, clipped to the fill) + the brightness/saturation lift + a bright sheen that sweeps the whole track once (`doh-ttl-sweep`, cropped by the track). Contained: the boost glows as a whole, even at a pinned-100% fill, but never bleeds onto neighbouring controls. `services/jupyterhub/duoptimum-hub-web/src/components/meters.tsx` (`TtlGadget` bar JSX), `src/styles/global.css` (`doh-ttl-track`/`doh-ttl-fill`, `doh-ttl-fill-boost`/`doh-ttl-sweep` keyframes; old `doh-ttl-boost-bar`/`doh-ttl-boost-glow` removed). Acc-crit: `acc-crit-duoptimumhub.md` (Boost bar glow); signoff `ttl-animation-checklist.md`
  - log: 2026-06-26 reported (operator: "now animation works, but the glow looks awful" + screenshot; "you must enable somehow clipping - by building custom animated gadget")
  - log: 2026-06-26 fix applied - custom clipped track+fill gadget; boost glow moved inside the track (inset bloom + brightness lift + one sheen sweep), antd `Progress` dropped from `TtlGadget`; typecheck clean; verify pending live rebuild + operator eyeball; acc-crit / `ttl-animation-checklist.md` glow items follow live sign-off

### DEF-28: TTL extend animation reads as ~0.5s, not the intended 3s

- [ ] **MEDIUM** - operator reports the extend boost animation "lasts like 0.5s total" - far short of the intended 3s envelope. Root cause CONFIRMED by live frame-capture: the animation is technically a full 3s but the headline element - the bar fill - is FROZEN, so it READS as a sub-second flash. The capture (60ms cadence, +4h extend) shows the boost class live t=60ms->t=2940ms (~2.88s), `animation-duration` resolving to `3s` every frame, and the counter smoothly counting `24h 0m -> 28h 0m` across the full 3s - yet the fill `width` reads `100%` on EVERY frame, never moving. Cause: the high-water-mark scaling ([DEF-13](#def-13-ttl-bar-scaled-to-absolute-ceiling-35h-reads-50)) targets `pctFor(target, target)` = 100% from a start that is also ~100% whenever the session is at/above base TTL (the common case - operators extend before it runs low), so the fill has nowhere to grow. The only remaining motion is the counter tick and a subtle ~0.75s glow flourish (brightness 1.18 on the dark accent + a forward box-shadow); with the bar - where the eye sits - static, the 3s envelope is imperceptible as duration. Ruled out and irrelevant to the cause: stale build (bundle current), failed-extend abort (extend `200` in ~15ms), reduced-motion (guard intact), wrong duration (`ttlExtendMs:3e3` = 3000ms; CSS `var(--doh-ttl-anim, 3s)`), early class-drop (class held the full 2.88s). Fix direction (operator + ux-designer call): give the bar a visible boost cue that plays regardless of fill % (e.g. a one-shot shimmer / width-pulse / sweep across the track), and/or strengthen the glow so the 3s reads as deliberate effort even at a pinned 100%. `services/jupyterhub/duoptimum-hub-web/src/components/meters.tsx` (`TtlGadget` apply / rAF / minCycle), `src/styles/global.css` (`doh-ttl-boost-*` keyframes), `src/services/config.ts` (`ANIMATION.ttlExtendMs`). Signoff contract: `ttl-animation-checklist.md`
  - log: 2026-06-26 reported (operator: "why does the ttl animation last like 0.5s total????")
  - log: 2026-06-26 investigation - deployed duration confirmed 3s (`3e3` + CSS var), extend `200`, reduced-motion guard present, hold timer 3000ms; stale-build / failed-extend / reduced-motion / wrong-duration ruled out
  - log: 2026-06-26 root cause CONFIRMED via live frame-capture (functest, throwaway probe, since removed) - boost class lives the full ~2.88s and the counter counts 24h->28h over 3s, but the fill width is pinned at 100% the whole time (high-water-mark, DEF-13): the bar never animates when extending an at/above-base session, so the 3s envelope reads as a brief flash; fix is to add a fill-independent boost cue + signoff against `ttl-animation-checklist.md`
  - log: 2026-06-26 fix attempt 1 (operator contract: full-bar boost keeps 3s + counter blur/count, and the WHOLE bar glows the bright accent) - new `doh-ttl-boost-glow` whole-bar accent halo on the bar WRAPPER (`.doh-ttl-bar.doh-ttl-boost`, not clipped by the track), ramped with the envelope; the old forward box-shadow on the fill (clipped away at 100%) removed; `doh-ttl-boost-bar` reduced to the brightness/saturation lift
  - log: 2026-06-26 attempt 1 INSUFFICIENT (operator "lasts just a fraction of a second" on the deployed build) - live frame-capture of the deployed glow showed the mechanism worked (class ~2.88s, animation-duration 3s, counter 24h->28h over 3s, glow ramps smoothly) but the glow was TOO FAINT: it used `--color-accent-ring` (rgba .35) blurred 16px -> peaked at `rgba(10,130,184,0.35)`, imperceptible on the dark theme, and the fill brightness was only 1.18 on dark; so the boost still read as a sub-second flash
  - log: 2026-06-26 fix attempt 2 - glow now uses the SOLID `--color-accent` (alpha 1, ~3x brighter), 20px blur / 4px spread, held bright 18%->82% so the bar is lit ~2.3s of the 3s; fill brightness raised 1.18->1.3 (dark) / 1.4->1.45 (light); `global.css`; verify via rebuild + capture (glow peak now solid accent, not .35 ring)
  - log: 2026-06-26 ACTUAL root cause found - NOT the frozen fill but `prefers-reduced-motion`: the operator's OS "reduce motion" tripped both the CSS `@media (prefers-reduced-motion: reduce)` guard and a JS reduce-branch (`minCycle = reduce ? null : timer`), collapsing the one-shot boost to ~0ms regardless of glow brightness - which is why every glow iteration still read as a flash. Fixed by EXEMPTING the user-triggered boost from BOTH guards (only the infinite expiry pulses stay reduced-motion-gated); functest under emulated `reduced_motion=reduce` measured the boost class lifetime 2939ms (was ~0); operator confirmed "now animation works"
  - log: 2026-06-26 the box-shadow whole-bar halo (attempts 1-2) then read as "awful" and bled onto the buttons/Extend -> spun off as [DEF-29](#def-29-ttl-extend-glow-box-shadow-halo-looks-awful-and-bleeds-onto-the-controls) and replaced by a custom CLIPPED gadget; the `doh-ttl-boost-bar`/`doh-ttl-boost-glow` box-shadow keyframes removed

### DEF-27: GPU utilisation bar shows non-zero fill at 0% load

- [ ] **LOW** - the per-GPU striped bar (`GpuMeter`, `meters.tsx:92`) renders each fill as `width: \`${Math.max(3, g)}%\``, flooring every bar at 3% - so a GPU at 0% utilisation still shows a 3% striped sliver and a genuine idle GPU reads as lightly loaded. Same class of bug as [DEF-26](#def-26-zero-activity-meter-floors-to-one-pale-red-bar) (zero-activity meter floored to one bar). The 3% floor is a deliberate min-visible width so a low-but-nonzero load stays perceptible, but it must NOT apply at exactly zero. Fix: `width: g > 0 ? Math.max(3, g) : 0` (positive load keeps the 3% min-visible sliver; exactly 0 renders an empty striped track). `services/jupyterhub/duoptimum-hub-web/src/components/meters.tsx:92`. Acc-crit: `acc-crit-duoptimumhub.md` (GPU bar zero-load reads empty)
  - log: 2026-06-26 reported (operator: "why GPU utilisation bars have non-zero length while gpu utilisation is reported to be 0%?")
  - log: 2026-06-26 fix applied - `width: g > 0 ? Math.max(3, g) : 0` (0% load -> empty track; a positive load keeps the 3% min-visible sliver); supersedes the 2026-06-25 "identity stripe survives idle" floor (identity now comes from the GPU name); `meters.tsx:92`; verify pending rebuild + live (functest runs GPU off, so not functest-coverable)

### DEF-26: Zero-activity meter floors to one pale-red bar

- [ ] **LOW** - the 5-segment activity meter (`MeterBody`, `meters.tsx`) computed `lit = Math.min(5, Math.max(1, round(value/20)))`, so a user with EXACTLY zero 7-day activity still lit ONE pale-red bar - the meter could never read empty and a genuine 0 looked like a low-but-present score. The `Math.max(1, ...)` floor was deliberate ("a genuine 0% reads as the alarming low end") but the operator wants zero to be exactly zero. Fix: extract `litBars` / `meterTone` to `lib/activityMeter.ts`; `litBars(0) = 0` (and any negative), positive values still light >= 1; tone is empty at 0 bars; `meters.tsx` consumes them. `services/jupyterhub/duoptimum-hub-web/src/lib/activityMeter.ts`, `src/components/meters.tsx`. Acc-crit: `acc-crit-duoptimumhub.md` (Zero activity lights zero bars)
  - log: 2026-06-26 reported (operator: "how come users with zero activity have 1 bar of activity? It should be exactly zero" / "A - yes, zero if zero")
  - log: 2026-06-26 fix applied - `litBars(value <= 0) -> 0`; 8 vitest unit cases (`lib/activityMeter.test.ts`, green) + functional `test_activity_zero.py` (API-created user reads activity 0 -> 0 lit `i.on`); verify pending live rebuild + functional run

### DEF-25: Open-server actions enter the lab before it truly serves

- [ ] **MEDIUM** - the portal "Open Lab" (`ServerHero`) and per-row open / `enterSession` (`ServerRowActions`, own + admin-other) navigate straight to the lab via `window.location.assign(userServerUrl(...))` with NO readiness gate, so opening a running-but-not-yet-serving lab (just spawned, restarting, still booting) lands on the hub's stock spawn-pending / 503 page instead of the lab. The cold-start Starting page already gates entry behind the hub-side `lab-ready` probe (`GET /hub/api/users/{username}/lab-ready`, see [DEF-1](#def-1-start-server-falls-to-stock-spawn-screen-no-logs)) but these direct-open buttons bypass it. Fix: route the Open action through the same `lab-ready` gate (probe-until-ready then navigate, or hand off to the Starting page) before assigning location. `services/jupyterhub/duoptimum-hub-web/src/components/ServerHero.tsx` (Open Lab ~L46), `src/components/ServerRowActions.tsx` (`enterSession` own+other ~L23,L31); ref `src/pages/Starting.tsx`, `handlers/lab_ready.py`. Acc-crit: [acc-crit-open-server-readiness.md](acc-crit-open-server-readiness.md)
  - log: 2026-06-23 reported (operator: "allow open the server only after it is truly available (doesn't return [an error])")
  - log: 2026-06-23 scope/decision: Option A (in-place "Opening..." busy state, no Starting-page handoff for a running server); the Open control is ACTIVE only once `lab-ready` confirms serving - gated after start AND restart (restart resets to becoming-ready), on the Servers page rows + Home "Active servers" widget + the ServerHero "Open Lab" button; acc-crit [acc-crit-open-server-readiness.md](acc-crit-open-server-readiness.md)
  - log: 2026-06-23 fix applied - shared `waitForLabReady` gate + `ServerLifecycle` becoming-ready `pending` map with a per-user generation token (`isServing` optimistic); controls gated; `Starting.tsx` refactored onto the shared gate. Adversarial review 2 rounds (caught + fixed a stale-settle premature-activation CRITICAL via the generation token, plus a try/finally hardening). Verified: `make rebuild` (image `42fb650e1659`) + signup regime 89 passed / 0 failed (new `test_open_readiness.py`); STILL OPEN pending live redeploy + verify

### DEF-20: html_templates_enhanced custom Bootstrap layer is a dead relic

- [ ] **LOW** - the `html_templates_enhanced/` directory (14 Jinja templates extending a custom Bootstrap `page.html`, plus `custom.css`, `session-timer.js`, `mobile.js`) is the platform's pre-SPA UI layer; the React portal now owns every user/admin journey, so the layer is dead weight - "clunky and flaky" (operator). Six templates were already shadowed/bypassed relics; of the rest, change-password / change-password-admin / authorization-area are owned by the SPA (headless/API) and the remainder are only reached as stock JupyterHub/NativeAuth framework plumbing. Fix: delete the directory entirely - the few reachable framework pages fall back to stock JupyterHub/NativeAuth (only basic JupyterHub persists, unbranded); NOT a reskin and NOT a stock-fallback we own. Page verdicts from a read-only reachability sweep with adversarial verification; `Dockerfile.jupyterhub`, `idle_culler.py`
  - log: 2026-06-21 reported (operator: "html_templates_enhanced is the old relic"; "make them obsolete, not needed"; "only basic functionality of JupyterHub to persist; all other our system"; "tested end to end")
  - log: 2026-06-21 fix applied - dir removed (`git rm -r`), Dockerfile COPY/cp lines + orphaned `rm admin.html` dropped (admin-react.js removal kept), `session-timer.js` mirror comment removed from `idle_culler.py`; 4 unit guard tests green (dir-gone, no-source-ref, Dockerfile-clean, wheel-provides-names); 7 e2e tests written (`test_template_elimination.py`); live no-old-asset + e2e verify pending redeploy; acc-crit "Elimination of html_templates_enhanced"

### DEF-19: Hub log lines printed to bare stdout, not a proper logger

- [ ] **LOW** - many hub runtime lines (`[Activity Sampler]`, `[Config] File-download`, `[Admin Bootstrap]`, `[GPU debug]`, the per-GPU `[GPU]` lines, the NativeAuth/Activity/Profile sync + cleanup lines in events.py) used bare `print()` to stdout - no level, no timestamp, inconsistent with the hub's own formatted log; `[GPU debug]` was debug-worded for info content; and some module loggers used a stdlib `getLogger("JupyterHub")` whose INFO can fail to render (it is not the app logger). Fix: route all RUNTIME lines through one loguru sink (`logging_setup`), coloured when the terminal permits; `[GPU debug]` -> `[GPU]` at INFO; build-time `event_schema_fix` keeps `print` by design; `logging_setup.py`, `config.py`, `services.py`, `admin_bootstrap.py`, `events.py`, `gpuinfo_sidecar.py`, hub-services `pyproject.toml`
  - log: 2026-06-21 reported (operator: "must all be logged with proper logger, not just stdout"; "use loguru if we can, coloured if terminal permits"; "no more GPU Debug, change this line to be the Info")
  - log: 2026-06-21 fix applied - loguru sink + conversions; 869 hub-services + 65 docker-proxy unit tests green; live coloured-render verify pending redeploy; shell-script startup logs tracked separately (#415)
  - log: 2026-06-21 sweep completed - ALL remaining runtime emitters on the shared loguru `log` (event_log, groups_config, user_profiles, activity/monitor+service, docker_proxy %-style->f-string, 5 getter caches, handlers/settings, hydrate, sent_notification_log, user_display_preferences); dead bindings removed (gpu_client, activity/helpers); `activity/service` basicConfig dropped; `JUPYTERHUB_LOG_LEVEL` env (default INFO, typo-safe `_resolve_level`); config validator warnings routed onto loguru (last stdlib `import logging` gone from config); `caplog` conftest bridge; start-platform.d INFO logs via `platform-log.sh` (#415); 879 hub-services unit tests green. Independent adversarial-architect pass + live coloured-render still due

### DEF-18: Hub-unreachable display (corner diode + full-screen modal) looks bad

- [ ] **MEDIUM** - the hub-unreachable presentation - a fixed top-right corner diode plus a blocking full-screen "Hub not responding" modal - reads as poor UX: the corner diode is "not right", the modal "looks quite terrible" (washes the screen, demands a dismiss). Fix: replace with a quiet persistent header connection-status pill (between the theme/language controls and the stage badge) carrying a softly pulsing diode + elapsed "for XXXX", plus a single pale in-flow warning panel on mobile; drop the corner diode and the modal; `HubConnectionIndicator.tsx`, `AppLayout.tsx`, `global.css`, `services/config.ts`, `lib/useHubHealth.ts`
  - log: 2026-06-21 reported (operator: corner diode "not right" - "abandon it"; modal "looks quite terrible"; wants a soft slowly-pulsating halo and a header status pill that "takes less space and still communicates"); redesign tracked in acc-crit "Hub-unreachable warning indicator" + tasks #396-#400, #404

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

### DEF-24: GPU undetected (sidecar down) still spawns labs with GPU - crash

- [x] **HIGH** - when `gpuinfo-nvidia` fails to start the live probe is correctly skipped (`probe_sidecar=False`), but `resolve_gpu_mode`'s cache-seeding `else` branch ran UNCONDITIONALLY and reseeded `gpu_list` from the last-known persisted inventory (`gpu_inventory.json` from a prior boot when GPUs were present) -> `nvidia_detected=1` -> resolver reports GPU ON -> `GpuPolicy.apply` attaches Docker `device_requests` -> nvidia prestart hook crashes EVERY spawn (`nvidia-container-cli: WSL environment detected but no adapters were found`) -> 500, no lab. A sidecar that failed to start means GPU was NOT autodetected; a stale snapshot is not detection, and the hub must never claim GPUs it has no live sidecar to back. Fix: early `if not probe_sidecar: return 0, 0, []` BEFORE any cache access - only a sidecar that is UP but answers empty (cold/slow start) seeds from last-known; `gpu.py`
  - log: 2026-06-22 reported live (operator: lab spawn 500 `nvidia-container-cli: WSL environment detected but no adapters were found`; "if gpuinfo failed to start, gpu was not autodetected - lab must start WITHOUT GPU"; "you - like a maniac - tried to start the lab with GPU")
  - log: 2026-06-22 root cause: regression from dd14b75 (two-mode detection + sidecar gating) - the `else` seeding branch in `resolve_gpu_mode` fired even when `probe_sidecar=False`, resurrecting a stale inventory; `nvidia_detected=1` -> `device_requests` attached -> prestart hook crash on a host with no live GPU adapter
  - log: 2026-06-22 fix applied: early return on `not probe_sidecar` (OFF, no seed) before any cache read; only sidecar-up-but-empty seeds last-known; `test_probe_sidecar_false_off_even_with_last_known` guards it (asserts `(0,0,[])` even with a persisted cache on disk)
  - log: 2026-06-22 adversarial-review (3 parallel claude -p Mode-1 + a consolidated re-confirm round, all SHIP after triage; the DO-NOT-SHIP rested on a false positive - `record_event` is best-effort - and a prior-reviewed up+empty trade-off); added an Invariant-1 test guard asserting `load_cached` is never read on the down path
  - log: 2026-06-22 VERIFIED: 910 hub-services unit tests + functional `gpu-missing` regime (2/2 against the rebuilt image: hub logs enabled=0 detected=0 + explicit "sidecar did not start" warning, spawned lab has no `device_requests` yet starts CPU-only); live redeploy (`make rebuild` v4.0.12 + `../stop.sh && ../start.sh`) confirms the NORMAL path intact - `[GPU] enabled=1 detected=1` (3 GPUs), no false warning, konrad lab survived + `hub:8080/hub/api` 200
  - ref: acc-crit "GPU autodetection - sidecar down -> GPU off, CPU-only lab"; tasks #464-#473

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

### DEF-21: Connection indicator - ux-review minors (5xx copy, uncapped elapsed, dual warning languages)

- [ ] **LOW** - the final `adversarial-ux-designer` skill pass on the hub-unreachable indicator (SHIP WITH FIXES) raised two MAJORs - mobile gave no screen-reader recovery announcement, and "for XXXX" started at 0s when the hub had already been down ~15-38s - BOTH now fixed (persistent mobile `role="status"` live region + `.doh-sr-only` recovery line; `useHubHealth` stamps the first-failure timestamp as `downSince`). These three lower-priority findings are deferred to a focused follow-up: (1) a reachable hub returning 5xx is counted as a failure and reads "Not responding" - the copy is wrong for the degraded-but-up case (`useHubHealth.ts` `!res.ok` branch); (2) `elapsedShort` is uncapped and the down pill is `white-space: nowrap`, so a multi-hour outage with the tab left open can widen the pill and crowd the breadcrumb (`format.ts`, `global.css` `.doh-conn-pill.down`) - cap or coarsen past 1h; (3) the connection panel uses its own warning treatment (`.doh-hub-warn-panel`) distinct from the established `.doh-notice.warning` pattern - two warning languages, a deliberate-or-unify call
  - log: 2026-06-21 logged from the final ux-designer skill review; 2 MAJOR fixed, these 3 deferred (LOW)

### DEF-22: Hub connect URL uses ephemeral container id, brittle on redeploy

- [x] **HIGH** - `c.JupyterHub.hub_connect_url` host was `socket.gethostname()` = the hub's container short id, which the hub bakes into every lab's `JUPYTERHUB_API_URL` at spawn; a hub redeploy / config change / watchtower update mints a NEW container id, so every already-running lab is permanently stranded (`Error connecting to http://<old-id>:8080/hub/api: [Errno -2] Name or service not known`); fix: drive the host from a STABLE network alias `hub` (= `JUPYTERHUB_LABEL_CONTAINER_ROLE_HUB`) that compose stamps on the hub's `hub_network` attachment AND as the `hub.container.role` label; `config/jupyterhub_config.py`, `compose.yml`, `Dockerfile.jupyterhub`, `settings_dictionary.yml`, `config_validator.py`
  - log: 2026-06-21 reported live: lab log `Error connecting to http://a811573186e8:8080/hub/api: ... Name or service not known` after a hub redeploy; old labs could not reconnect, only a respawn fixed each one
  - log: 2026-06-21 root cause: gethostname() = ephemeral container id baked into JUPYTERHUB_API_URL; new id on redeploy -> stale labs resolve a name that no longer exists in the embedded DNS
  - log: 2026-06-21 fix: hub_connect_url host = JUPYTERHUB_LABEL_CONTAINER_ROLE_HUB ('hub'); compose stamps it as a hub_network alias + container role label; baked Dockerfile ENV + settings_dictionary; validator-required (`hub_container_role_label`); orphan `import socket` dropped
  - log: 2026-06-21 unit `test_config_validator.py` (46 pass) + functional `test_hub_connect_url.py` added (label + alias + DNS resolve + :8080 reachability); live verify pending rebuild + redeploy
  - log: 2026-06-21 adversarial-review (claude -p, 2 rounds -> FIXES-SOUND): (1) added a binding guard - `test_container_policy.py` asserts the spawned lab's `JUPYTERHUB_API_URL` starts `http://hub:8080` (the plumbing tests passed even with the fix reverted); (2) boot-time `socket.gethostbyname(_HUB_HOST)` -> `log.error` so a dropped alias is loud at boot, not a silent per-spawn strand (the old gethostname always resolved)
  - log: 2026-06-22 the alias fix REGRESSED in production (-> DEF-23): the alias value `hub` was ALSO the compose SERVICE NAME, so docker auto-aliased `hub` on BOTH hub nets; the multi-homed hub resolved its own `hub_connect_url` host to the gpuinfo IP and bound the Hub API off the lab net -> every spawn "connection refused" (total outage)
  - log: 2026-06-22 FINAL fix (resolves DEF-22 + DEF-23): drop `hub_connect_url`; advertise via `hub_connect_ip` = the hub's compose SERVICE NAME, discovered from its own `com.docker.compose.service` label (`resolve_self_compose_service`, mirrors `resolve_self_compose_project`); keep `hub_ip=0.0.0.0` (advertise != bind); drop the hand-stamped alias (service name IS the DNS name); service stays `hub`. Live: "Hub API listening on http://0.0.0.0:8080" + "Private Hub API connect url http://hub:8080"; lab-net peer GET http://hub:8080/hub/api -> 200. Architect re-review: production fix SOUND, all constraints honored
  - log: 2026-06-22 follow-up: dropped the now-vestigial `JUPYTERHUB_LABEL_CONTAINER_ROLE_HUB` env + `hub.container.role=hub` label entirely (the connect host is the discovered service name, so a hub role label served no purpose); removed from `compose.yml`, `Dockerfile.jupyterhub`, `settings_dictionary.yml`, `config/jupyterhub_config.py`, `config_validator.py`, `test_config_validator.py`, functest `compose.functional.yml`; gpuinfo sidecar + spawned labs still carry their role labels
  - related: DEF-17 (role-label keys/values baked in compose, not only Dockerfile) - this extends the role-label discovery scheme to the hub's own container + its DNS alias; DEF-23 (the regression this fix's first attempt caused)
  - ref: acc-crit "Redeploy-proof hub connect URL"; tasks #430-#442

### DEF-23: Hub API bound to the gpuinfo interface after the DEF-22 alias fix - total spawn outage

- [x] **CRITICAL** - the DEF-22 fix set `hub_connect_url` host to the alias `hub`; because `hub` was ALSO the compose SERVICE NAME, docker auto-registered it on EVERY network the multi-homed hub joins (hub_network=lab AND hub_gpuinfo_network). JupyterHub derives the Hub-API BIND interface from resolving `hub_connect_url`'s host FROM THE HUB; that resolved to the gpuinfo IP, so the API bound to `172.20.x:8080` only - off the lab net. Every spawn failed: labs (on hub_network) hit `http://hub:8080/hub/api` -> connection refused, `oauth_callback` 500. Fix: stop using `hub_connect_url` (it drives the bind); advertise via `hub_connect_ip` = the hub's discovered compose service name; `hub_ip=0.0.0.0` listens on all interfaces; drop the hand-stamped alias; `config/jupyterhub_config.py`, `docker_utils.py`, `compose.yml`, wrapper `compose_override.yml`
  - log: 2026-06-22 reported live (operator): "Failed to connect to Hub API at 'http://hub:8080/hub/api' ... my labs don't start properly"; spawn `oauth_callback` 500, lab `ConnectionRefusedError` to http://hub:8080/hub/api
  - log: 2026-06-22 root cause: service-name `hub` auto-aliased on both hub nets -> hub self-resolved the connect host to the gpuinfo IP -> API bound off the lab net (confirmed: 172.20.0.2:8080 OPEN, 172.19.0.2:8080 + 0.0.0.0 REFUSED despite `hub_ip=0.0.0.0`, because `hub_connect_url` overrides the bind)
  - log: 2026-06-22 fix applied + live-verified: `hub_connect_ip` = discovered `com.docker.compose.service` ('hub'); `hub_connect_url` removed; alias dropped; `hub_ip=0.0.0.0`. Hub log "listening on http://0.0.0.0:8080" + "connect url http://hub:8080"; both lab(172.19)+gpuinfo(172.20) :8080 OPEN; lab-net peer GET http://hub:8080/hub/api -> 200. `make rebuild` (v4.0.12) + redeploy
  - log: 2026-06-22 adversarial-architect re-review: production fix SOUND, honors all operator constraints (service=`hub`, no alias, no env, no bind hack, redeploy-proof); UNIFY-NEEDED only for the functest multi-homing guard + stale comment drift (both addressed)
  - related: DEF-22 (the redeploy-brittleness whose alias fix introduced this; the connect_ip change resolves both)
  - ref: acc-crit "Redeploy-proof hub connect URL"; tasks #439-#442
