# Acceptance Criteria - Duoptimum Hub

Consolidated acceptance criteria for the Duoptimum Hub portal and platform - one section per feature, scope or design. This is the single source of record: the former individual `acc-crit-*.md` files have been merged here verbatim, every criterion, `log:` line and edge case preserved.

Cross-document conflicts found during consolidation are tracked in [concerns.md](concerns.md) and have not yet been actioned.

## Contents

- [activity reporting consistency](#activity-reporting-consistency)
- [Activity map freshness (lightweight, activity-gated)](#activity-map-freshness-lightweight-activity-gated)
- [activity scoring (target-hours normalisation + honest hours)](#activity-scoring-target-hours-normalisation-honest-hours)
- [Advanced menu ordering](#advanced-menu-ordering)
- [API Keys Pool Group Config](#api-keys-pool-group-config)
- [background refresh + immediate update](#background-refresh-immediate-update)
- [environment-stage badge](#environment-stage-badge)
- [broadcast auto-close duration](#broadcast-auto-close-duration)
- [last-known cache + non-blocking GPU + GPU-widget gating](#last-known-cache-non-blocking-gpu-gpu-widget-gating)
- [Cert Provisioning](#cert-provisioning)
- [Compose Project Naming](#compose-project-naming)
- [portal critic sweep (inconsistencies + illogical behaviour)](#portal-critic-sweep-inconsistencies-illogical-behaviour)
- [design language (system-wide)](#design-language-system-wide)
- [docker policy access mode](#docker-policy-access-mode)
- [drop the `/portal` URL segment](#drop-the-portal-url-segment)
- [duoptimumhub service + image rename](#duoptimumhub-service-image-rename)
- [Edit user returns to its origin](#edit-user-returns-to-its-origin)
- [Platform event log (persistence + clear)](#platform-event-log-persistence-clear)
- [force password change on next login (#232 / #233)](#force-password-change-on-next-login-232-233)
- [Functional Test Harness](#functional-test-harness)
- [Functional UI Sweep](#functional-ui-sweep)
- [GPU Utilisation Cache Logging](#gpu-utilisation-cache-logging)
- [gpuinfo-nvidia sidecar (logging + graceful no-hardware)](#gpuinfo-nvidia-sidecar-logging-graceful-no-hardware)
- [Group-Gated File Downloads](#group-gated-file-downloads)
- [group policy import/export bundle shape](#group-policy-importexport-bundle-shape)
- [Unified Group Policy Model](#unified-group-policy-model)
- [Group Sudo Access Control](#group-sudo-access-control)
- [Label capitalisation (Title Case)](#label-capitalisation-title-case)
- [live data honesty (no mock masquerade)](#live-data-honesty-no-mock-masquerade)
- [Mobile Responsive Portal](#mobile-responsive-portal)
- [Navigation patterns (edit pages -> parent + breadcrumbs)](#navigation-patterns-edit-pages---parent-breadcrumbs)
- [old portal cleanup](#old-portal-cleanup)
- [Portal UI Polish (2026-06-17 session)](#portal-ui-polish-2026-06-17-session)
- [profile name display](#profile-name-display)
- [Profile route (role-aware self-view)](#profile-route-role-aware-self-view)
- [Rename user (admin action on the profile)](#rename-user-admin-action-on-the-profile)
- [resource bars (limits + tooltips)](#resource-bars-limits-tooltips)
- [restart/stop progress feedback](#restartstop-progress-feedback)
- [Roles reference page](#roles-reference-page)
- [server lifecycle UX (inline spinners, no modal, real log)](#server-lifecycle-ux-inline-spinners-no-modal-real-log)
- [server status immediacy](#server-status-immediacy)
- [Servers host-relative resources](#servers-host-relative-resources)
- [Servers list layout](#servers-list-layout)
- [Servers resource cells](#servers-resource-cells)
- [dedicated Start-server page with live container-log feed](#dedicated-start-server-page-with-live-container-log-feed)
- [startup hydration](#startup-hydration)
- [TTL extend bar animation](#ttl-extend-bar-animation)
- [TTL progress bar behaviour matrix](#ttl-progress-bar-behaviour-matrix)
- ["Upgrade available" pill](#upgrade-available-pill)
- [version sync across subpackages](#version-sync-across-subpackages)
- [Volume reset confirmation](#volume-reset-confirmation)
- [Duoptimum Hub portal de-mock + fixes](#duoptimum-hub-portal-de-mock-fixes)

---

## activity reporting consistency

The Activity meter is a 7-DAY engagement metric (capped score + average active hours vs the daily target), not a live reading. It must render the same value on every surface that reports it - the Home servers widget, the Servers screen and the Users screen - whether or not the server is running. Regression (2026-06-18): the server-row builder gated the meter on the server being running, so an offline-but-active user read e.g. 30% on Users and "none" (a muted dash) on Servers and the Home widget.

### Consistency

- [x] **Same value on Servers and Users** - the server-list rows (`getServers`, used by Servers + the Home widget) and the user-list rows (`getUsers`, used by Users) derive `activity` / `activityHours` / `activityPct` from ONE shared helper, so the two builders cannot diverge
  - log: 2026-06-18 `liveSource.ts::activityFields(a, target)` spread into both row builders; was two separate expressions (one gated on `running`)
- [x] **Reported on every surface** - Home servers widget, Servers screen and Users screen show the identical meter for the same user
  - log: 2026-06-18 all three render `<ActivityMeter value hours pct>` from the same fields
- [x] **7-day metric, not gated on run state** - `activity` reflects the trailing-window engagement, never nulled because the server is offline / spawning; only live readings (CPU, memory, system) stay gated on `running`
  - log: 2026-06-18 dropped the `running ?` gate from the server-row activity; CPU/mem/system remain gated
- [x] **Shown when the server is stopped** - an offline user with a non-zero `activity_score` shows the meter (not a muted dash) on Servers and the Home widget, matching Users
  - log: 2026-06-18 confirmed live: admin `activity_score=31`, server offline -> was 30% on Users, dash on Servers; fixed
- [x] **Mock matches live** - the demo source applies the same rule (offline + spawning rows show the 7-day meter), so `/design-language` and the mock screens never contradict the rule
  - log: 2026-06-18 `mockSource.ts::mockActivity(p)` spread into `toServerRow` (offline + main) and `toUserRow`; offline branch was `activity: null`, main branch gated on `spawning`

### Edge cases

- [x] **Edge: never sampled** - a user with no activity samples reads `activity = 0` (a 0-lit meter), the same on all surfaces - not a dash on one and a meter on another
  - log: 2026-06-18 `clampPct(a?.activity_score ?? 0)` yields 0 (not null) in both builders
- [x] **Edge: spawning** - a coming-up server shows the 7-day meter (historical engagement exists independent of the in-progress spawn); live CPU/mem stay blank until ready
  - log: 2026-06-18 activity no longer gated on spawning in either source
- [ ] **Edge: pending signup (no hub user)** - a not-yet-authorised signup with no hub User row reads `activity = 0`; it appears on Users (pending bucket) only, not on Servers/Home
  - log: 2026-06-18 `getUsers` pushes pending rows with `activity: 0`; pending users have no server row by definition

### Tests

- [x] **Functional: launch -> stop -> observe** - a Playwright test creates a user, starts their lab, leaves it ~10s, samples activity while active, stops it, then asserts the Activity meter is present (not a dash) and identical across Servers, Users and the Home widget
  - log: 2026-06-18 `tests/functional/test_activity_consistency.py`; carries `@pytest.mark.acc_crit("activity-consistency::...")`; runs against a live stack (needs the rebuilt image to validate the fix)

## Activity map freshness (lightweight, activity-gated)

The portal's per-user activity map (status + CPU/memory) must reflect a lab's current state promptly, without a slow `/activity` request and without polling idle containers. Live `docker stats` is moved off the request path into a warm snapshot that is refreshed **lazily and only for recently-active users**. Backend: `container_stats_cache.py` (snapshot + `get_container_stats_with_refresh`), `docker_utils.py::stats_from_container` (shared stats math), `handlers/activity.py` (reads the snapshot). Verified against the code 2026-06-18.

### Endpoint latency

- [x] **No synchronous docker gather on the request path** - `/activity` no longer does `asyncio.gather(get_container_stats_async ...)` over active users; it reads the warm snapshot and returns instantly
  - log: 2026-06-18 replaced the blocking gather with `get_container_stats_with_refresh()` (was the operator's "~5-6s after I switched to portal")
- [x] **Status is request-fresh** - per-user active/idle status (`recently_active`) is computed live from `spawner.orm_spawner.last_activity` each request (no Docker), so the status pill is current the moment `/activity` returns
  - log: 2026-06-18 unchanged path; only the cpu/mem cells come from the snapshot
- [x] **Instant on navigation** - switching to a portal page paints the current status immediately (the snapshot read is non-blocking); cpu/mem fill from the snapshot (<= one interval old)
  - log: 2026-06-18 the navigation-time fix

### Lightweight + activity-gated refresh

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

### Snapshot correctness

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

### Tests

- [x] **stats_from_container** - cpu%/assigned cores/memory/image_id computed from a fake container, limited and unlimited paths, None on a stats error
  - log: 2026-06-18 `tests/test_container_stats_cache.py`
- [x] **Staleness + trigger gating** - `get_cached_container_stats` flags stale when never/expired; `get_container_stats_with_refresh` submits a refresh only when the active set is non-empty AND stale, and never when the active set is empty
  - log: 2026-06-18 `tests/test_container_stats_cache.py` (executor monkeypatched, no real docker)

### API

- `GET /hub/api/activity` -> per-user `{..., cpu_percent, cpu_cores, memory_mb, memory_percent, memory_total_mb, recently_active, ...}` (admin); cpu/mem sourced from the warm snapshot, status from `last_activity`

## activity scoring (target-hours normalisation + honest hours)

The activity score is the user's recent active time measured against a daily target (`JUPYTERHUB_ACTIVITYMON_TARGET_HOURS`, default 8h), not against the 24h clock. Samples are taken 24/7, so the decay-weighted active fraction is the share of the day active; the score normalises that against the target and caps at 100. A separate honest hours figure (`activity_hours`, real avg active hours/day, uncapped) drives the meter tooltip.

### Root cause (under-reporting: Natalia 33%)

- [x] **Identified** - `monitor.get_score` returned the raw decay-weighted active fraction (active / all 24/7 samples), so an 8h/day user maxed at 8/24 = 33%
  - log: 2026-06-17 root-caused; `monitor.py:get_score`
- [x] **Regression source** - the original `activity.html` normalised client-side (`normalized = activity_score / (targetHours/24)`, i.e. 33/0.333 ≈ 100); the React portal dropped that step and showed the raw 33%
  - log: 2026-06-17 confirmed against git `HEAD:services/jupyterhub/html_templates_enhanced/activity.html:74-76,231-235`
- [x] **Unused setting** - `JUPYTERHUB_ACTIVITYMON_TARGET_HOURS` was documented and passed to templates but never referenced by the scorer
  - log: 2026-06-17 now wired into `ActivityMonitor`

### Fix

- [x] **Normalise in the backend** - `get_score` returns `min(100, round((active_fraction*24 / target_hours) * 100))` so every consumer (portal, log buckets) agrees; the normalisation lives once, in the scorer
  - log: 2026-06-17 `monitor.py:get_score` via `_weighted_active_fraction`
- [x] **8h/day -> 100** - a user active the target hours scores 100, not 33
  - log: 2026-06-17 `test_eight_hours_a_day_scores_100_not_33`
- [x] **Proportional below target** - ~4h/day scores ~50
  - log: 2026-06-17 `test_half_target_scores_about_50`
- [x] **target_hours config** - read from env (1-24, default 8), echoed in the config log line
  - log: 2026-06-17 `test_target_hours_default`, `test_target_hours_env`
- [x] **Capped meter, honest tooltip** - the 0-100 score caps at 100 (old client was uncapped, could show 150%); the real uncapped hours live in `activity_hours` for the tooltip
  - log: 2026-06-17 `get_avg_active_hours` added
- [x] **Edge: no samples** - `get_score` returns `(None, 0)`, `get_avg_active_hours` returns `None`
  - log: 2026-06-17 `test_avg_active_hours_none_without_samples`
- [x] **Existing behaviour preserved** - all-active -> 100, all-inactive -> 0, recent-active-dominates still holds
  - log: 2026-06-17 prior tests green

### Honest hours tooltip (was: reword to avg hours over 3 days)

- [x] **Real hours exposed** - `/activity` returns `activity_hours` per user (decay-weighted avg active hours/day, uncapped), from `calculate_avg_active_hours`
  - log: 2026-06-17 `handlers/activity.py`, `helpers.calculate_avg_active_hours`
- [x] **Tooltip wording** - the meter tooltip reads "Active on average Nh/day over the last 3 days" (3 days = the 72h half-life window); falls back to "N% of the daily activity target" when hours are absent
  - log: 2026-06-17 `meters.activityTitle`, threaded to hero + servers table + drawer
- [x] **No fabrication** - hours come from real samples; never derived from a percentage
  - log: 2026-06-17 derived in the backend from the sample table
- [ ] **Runtime: heavy users read high** - on the live hub a full-time user shows ~100% with a truthful Nh/day tooltip
  - log: 2026-06-17 backend + frontend + tests done; on-screen confirm pends operator rebuild

### Servers-page activity tooltip (added 2026-06-17, #247)

- [ ] **Real uncapped %** - the activity meter tooltip on the Servers page shows the real activity %, which MAY exceed 100% (a user working more than the 8h/day target reads >100%, which is good); the displayed % is NOT clamped
  - log: 2026-06-17 criterion added - `activity_score` is capped at 100 for the meter fill, so the tooltip needs the uncapped figure (derive from `activity_hours / target_hours * 100`; target_hours must reach the frontend, or expose an uncapped score field on `/activity`)
- [ ] **Multiline** - the % and the existing "Active on average Nh/day" info on separate lines, not one super-long single line
  - log: 2026-06-17 criterion added
- [ ] **Reflected in the design language** - the activity-% tooltip convention appears on /design-language as a visual cue
  - log: 2026-06-17 criterion added (#252)
- [x] **Same tooltip on Servers, Users and the server resources widget** - the user-activity meter carries the identical multiline tooltip everywhere it appears (Servers list, Users list, and the "Server status" resources widget): uncapped `% of the daily activity target` + `Active on average Nh/day over the last 3 days`
  - log: 2026-06-17 added; `getUsers` now derives `activityHours`/`activityPct` like `getServers`; `Users.tsx` passes both to `ActivityMeter` (Servers already did)
- [x] **Same tooltip on the Home servers widget** - the Home "Active servers" preview activity meter carries the same multiline tooltip as the Servers list; it passes `hours`/`pct` from the shared `ServerRow`, not the bare `value`-only meter
  - log: 2026-06-17 added; `Home.tsx::ActiveServersPreview` activity column now `<ActivityMeter value hours pct />`

### API

- `GET /api/activity` -> each user gains `activity_hours: number | null` alongside `activity_score`
- Env `JUPYTERHUB_ACTIVITYMON_TARGET_HOURS` (1-24, default 8) - daily active hours that count as a 100% score

## Advanced menu ordering

The items in the Administration -> Advanced submenu are ordered alphabetically by label, so the menu stays predictable as leaves are added. Definition: `app/nav.ts` `NAV_ADMIN` Advanced `children`. Verified against the code 2026-06-18.

- [x] **Alphabetical by label** - Advanced children are listed A->Z by their `label`: Roles, Settings, Tokens
  - log: 2026-06-18 operator: "Advanced menu items must be ordered alphabetically"; reordered `children` in `nav.ts` (was Settings, Tokens, Roles)
- [x] **Case-insensitive, label-based** - ordering keys off the visible label, not the `id` or `path`
  - log: 2026-06-18 labels are Title Case; A->Z on the displayed text
- [x] **New leaves keep the order** - any item added to Advanced is inserted at its alphabetical position, not appended
  - log: 2026-06-18 comment in `nav.ts` records the rule for future additions
- [x] **Scope: Advanced only** - the rule applies to the Advanced submenu; top-level Administration items keep their deliberate workflow order (Servers, Users, Groups, Lab Setup, Events, Notifications, Advanced)
  - log: 2026-06-18 not alphabetised by design - top-level order is task-flow, not alphabetical

## API Keys Pool Group Config

### Overview

A new group configuration type that distributes a finite pool of API credentials to user containers so that no two running containers ever hold the same credential. It joins the existing group config family (env variables, GPU, Docker, compute, memory) and is resolved, applied, and logged through the same machinery in `duoptimum_hub_services`.

The pool is exclusive by design: each running container is assigned at most one credential per pool, the credential returns to the pool when the container stops, and the in-use set is rebuilt by inspecting the actual running containers rather than trusting lifecycle events alone.

### Definitions

- **Pool**: an ordered set of credentials defined on a single group config, with a fixed mode and fixed target environment variable names
- **Credential**: one pool entry, either a key-id/key-secret pair or a single API key, depending on pool mode
- **Slot**: a stable identifier for a credential within its pool, independent of list position, used to record and reconcile assignments
- **Assignment**: the binding of one slot to one running container for that container's lifetime
- **In-use set**: the set of slots currently held by running containers, derived by reconciliation
- **Mode**: `pair` (key-id + key-secret) or `single` (api key) - mutually exclusive per pool

### Configuration (admin)

- **AC-1** Given a group config editor, when an admin enables the API keys pool, then they select exactly one mode: `pair` or `single` (mutually exclusive)
- **AC-2** Given `pair` mode, when configuring target variables, then the admin specifies an environment variable name for the key id and an environment variable name for the key secret
- **AC-3** Given `single` mode, when configuring the target variable, then the admin specifies one environment variable name for the api key
- **AC-4** Given an enabled pool, when the admin adds credentials, then the list accepts an unlimited number of entries, each entry matching the pool mode (id+secret for `pair`, single value for `single`)
- **AC-5** Given a stored pool, when the admin reorders or edits the credential list, then each existing credential keeps its stable slot identity so in-flight assignments remain valid
- **AC-6** Given the group config persistence layer, when a pool is saved, then credential secrets are stored in the same protected store as other group config (`groups_config.sqlite`). The groups page and its API are admin-only and return credentials in full (the admin manages them, so they are shown unmasked in the editor); obfuscation applies only to the logs (AC-26/AC-28)

### Validation

- **AC-7** Given an enabled pool, when no mode is selected or both target-variable sets are empty, then validation fails with a clear message and the config is not saved
- **AC-8** Given `pair` mode, when either the key-id variable name or the key-secret variable name is missing, then validation fails
- **AC-9** Given `single` mode, when the api-key variable name is missing, then validation fails
- **AC-10** Given any target variable name, when it collides with a reserved name or reserved prefix (the same `reserved_env_var_names` / `reserved_env_var_prefixes` used elsewhere), then validation fails
- **AC-11** Given `pair` mode, when an entry is missing either the id or the secret, then validation fails (no half-credentials in the pool)

### Assignment at spawn

- **AC-12** Given a user in a group with an enabled pool, when their container spawns, then the pool assigns one free slot to that container and injects the credential into the configured environment variables (`pair` -> two variables; `single` -> one variable)
- **AC-13** Given an assignment, when the credential is injected, then no other running container in the same pool holds the same slot (exclusivity invariant)
- **AC-14** Given the assignment, when it is made, then it is recorded durably on the container itself in a stable, version-independent form (so it survives a hub restart and can be reconciled), in addition to any hub-side bookkeeping
- **AC-15** Given a user already holding a slot from a still-running container, when a duplicate spawn or reconciliation occurs, then the existing assignment is reused rather than allocating a second slot

### Release at stop

- **AC-16** Given a running container with an assignment, when the container stops cleanly, then its slot returns to the pool and becomes available for the next spawn
- **AC-17** Given a returned slot, when it re-enters the pool, then a subsequent spawn may receive it; assignments are per container lifetime and not sticky to a user across stop/start

### Resilience and reconciliation

The pool must never rely on stop events alone. Containers can be stopped while the hub is down (missed event), or were started by a previous or different hub version. The authoritative in-use set is therefore always derived from the running containers.

- **AC-18** Given the hub starts, when the startup reconciliation runs, then it enumerates running user containers, reads each container's recorded assignment, and rebuilds the in-use set from that observation - not from stale hub state
- **AC-19** Given a slot recorded as in-use but with no corresponding running container, when reconciliation runs, then that slot is returned to the pool
- **AC-20** Given a periodic reconciliation pass, when it runs at a fixed interval, then it re-derives the in-use set from running containers and converges the pool to match reality (self-healing against missed events)
- **AC-21** Given a container started by an older hub version with no recognizable assignment marker, when reconciliation runs, then it is treated as holding no pool slot - the pool does not crash, double-free, or guess; its already-injected environment is left untouched
- **AC-22** Given the assignment marker scheme, when the hub version changes, then the scheme is stable and backward-compatible so future reconciliation keeps working across upgrades

### Exhaustion

- **AC-23** Given a pool with all slots assigned, when another group member's container spawns, then the configured environment variables are still set but empty, and the container starts normally
- **AC-24** Given pool exhaustion at spawn, when the empty assignment is made, then a warning is logged stating the pool is exhausted, naming the pool and the user
- **AC-25** Given an exhausted pool, when a slot is later released and reconciliation runs, then it becomes available for the next spawn (no permanent starvation)

### Logging

- **AC-26** Given a credential assignment, when it succeeds, then an event is logged to the JupyterHub log naming the user and pool, showing only the last 4 characters of the id and/or secret and/or api key - never the full value
- **AC-27** Given pool exhaustion, when a container is assigned empty variables, then a warning-level event is logged
- **AC-28** Given any logging path, when an assignment or exhaustion is recorded, then full credential values never appear in logs or in container labels (log lines carry last-4 only; labels carry slot identity, not the secret). Full values are exposed only through the admin-only groups API/editor (AC-6)

### Multiple groups

- **AC-29** Given a user in several groups each defining a pool, when their container spawns, then each pool independently assigns one slot and injects its own configured variables
- **AC-30** Given two groups that set the same environment variable name (whether via a pool target variable or a plain group env var), when both would inject, then the group higher in the ordered group list wins and the shadowed value is not applied - this is the purpose of ordering groups by importance
- **AC-31** Given the resolved precedence in AC-30, when a higher-priority group's value shadows a lower one, then the shadowing is observable in the logs so an admin can see which group supplied the effective value

### Out of scope

- Credential rotation, expiry, or revocation against the upstream provider - the pool distributes static credentials supplied by the admin
- Validating that a credential is live or accepted by its target service
- Per-credential usage metering or quota beyond the one-container-one-slot exclusivity invariant

## background refresh + immediate update

The portal keeps lists/status current without manual navigation: mutations reflect at once (optimistic + immediate background refetch), and the live dashboard self-polls so a background change (a server coming up, status flips) shows on its own. Paradigm: when something happens in the background, a monitor watches and the affected view refreshes immediately on completion.

### Mutation-side (immediate effect on change)

- [x] **Immediate background refetch** - `invalidate()` uses `refetchType: 'all'` so a mutation refetches the affected list even when it is unmounted (RQ default only refetches active observers); navigating back shows fresh data, not stale-until-next-mount
  - log: 2026-06-17 `services/actions.ts::invalidate`
- [x] **Optimistic patch** - `patchQuery()` patches the query cache at once (e.g. `saveUserProfile` updates the `['users']` fullName immediately, like the Groups page's inline-edit immediacy); the PUT + invalidation reconcile, and a failure refetches to roll back
  - log: 2026-06-17 `actions.ts::patchQuery`, `ops.ts::saveUserProfile`
- [x] **Why it was slow** - the user list's name comes via `getUsers` which `Promise.all`s the fast `/users`+`/user-profiles` with the heavy `/activity`; without the optimistic patch the saved name only appeared after the slow refetch
  - log: 2026-06-17 root-caused

### Background polling (self-refresh)

- [x] **Adaptive poll on live queries** - `servers`, `hero`, `stats`, `resources` carry `refetchInterval`: FAST (2.5s) while a server is spawning, SLOW (15s) when stable
  - log: 2026-06-17 `hooks/queries.ts` `FAST_POLL`/`SLOW_POLL`, `serversSpawning`/`heroSpawning`
- [x] **No poll for slow data** - `users`/`groups`/`settings`/`tokens` are not polled (they change only on admin action)
  - log: 2026-06-17 deliberately left unpolled
- [x] **Paused when hidden** - `refetchIntervalInBackground: false` so a backgrounded tab stops polling (each `/activity` sample runs docker stats)
  - log: 2026-06-17
- [x] **Server-status-after-start heals** - root cause: the Start page navigates on the SSE `ready`, the hub's `/users/{user}` can still report `ready:false` for a few seconds, Home did ONE refetch that caught the mid-settle state, and nothing re-polled (no `refetchInterval`) so it stuck "Offline" until the 30s staleTime. Fast poll while spawning now flips it to active within ~2.5s
  - log: 2026-06-17 fixed via the adaptive poll; `statusOf` already spawner-authoritative
- [ ] **Runtime: status flips within ~2-3s of start** - confirm on the live hub the post-start Offline window is gone
  - log: 2026-06-17 code + build clean; on-screen confirm pends operator rebuild

### Prefetch (already present)

- [x] **Boot prefetch** - `App.tsx::prefetchCore` warms 12 list queries at app init; `persistCache` hydrates from localStorage so first paint is instant
  - log: 2026-06-17 pre-existing, confirmed
- [ ] **Edge: prefetch on nav hover** - optional Phase 3 (sider link `onMouseEnter` -> `prefetchQuery`) - not yet implemented
  - log: 2026-06-17 deferred

### Adversarial-critic fixes (2026-06-17)

- [x] **C1: settle window heals** - the original adaptive poll only fast-polled on `status==='spawning'`, but the post-spawn settle window (spawner present, not ready, no pending) mapped to `offline` and fell to the 15s poll. `statusOf` now reads that window as `spawning`, and `useSpawnProgress` invalidates servers/hero/stats/resources on the SSE `ready` - so the started server heals in ~2-3s, not up to 15s
  - log: 2026-06-17 `liveSource.statusOf`, `useSpawnProgress` ready effect
- [x] **H1/H3: /activity storm coalesced** - `refetchType:'all'` + the fact that getUsers/getServers/getStats/getServerHero all fetch `/activity` meant one mutation fired 3-4 concurrent docker-stat sweeps. A 1.5s in-flight coalescing cache on `fetchActivity` collapses them to one
  - log: 2026-06-17 `liveSource.fetchActivity` `_activityInFlight`
- [x] **H2: drop wasteful idle poll** - `stats`/`resources` no longer poll on a flat 15s interval (each dragged `/activity`); they refresh on mutation
  - log: 2026-06-17 `queries.ts`
- [x] **M1: optimistic patch live-only** - `saveUserProfile`'s `patchQuery` is guarded by `!isMock()` so it doesn't desync the mock cache
  - log: 2026-06-17
- [x] **M2: fullName matches backend** - optimistic `fullName` falls to `undefined` when both names blank (matching `getUsers`), no empty-string flicker
  - log: 2026-06-17 `\`${first} ${last}\`.trim() || undefined`
- [x] **M3: synchronous rollback** - the prior rows are snapshotted and restored synchronously on a failed write (not a refetch that shows the wrong value until it lands)
  - log: 2026-06-17

### Prefetch (already present)

- [x] **Boot prefetch** - `App.tsx::prefetchCore` warms 12 list queries at app init; `persistCache` hydrates from localStorage so first paint is instant
  - log: 2026-06-17 pre-existing, confirmed
- [ ] **Edge: prefetch on nav hover** - optional Phase 3 (sider link `onMouseEnter` -> `prefetchQuery`) - not yet implemented
  - log: 2026-06-17 deferred

### Out of scope (follow-up)

- [ ] **Slow/fast split** - decouple the light list fields from the heavy `/activity` so lists paint instantly and CPU/mem/activity cells fill in after (Phase 2); the coalescing cache mitigates the cost in the interim
  - log: 2026-06-17 planned, not yet implemented

## environment-stage badge

A small outlined rectangle in the portal header naming the deployment stage (DEV/STG/TST/PRD), coloured per stage, so operators can tell environments apart at a glance. Driven by `JUPYTERHUB_BRANDING_STAGE` -> `window.jhdata.stage` (frozen at hub start); empty = no badge. Frontend: `components/StageBadge.tsx`, rendered top-right in the `AppLayout` `oh-topbar` header row. Backend: `branding.py::setup_branding(stage=...)` -> `branding['stage']` -> `template_vars['branding_stage']` -> `portal.html`. Verified against the code 2026-06-18.

### Behaviour

- [x] **Env-driven** - the badge text and presence come from `JUPYTERHUB_BRANDING_STAGE`, read once at hub start
  - log: 2026-06-18 operator: "environment stage 'logo' ... env JUPYTERHUB_BRANDING_STAGE"; config `JUPYTERHUB_BRANDING_STAGE`, threaded through `setup_branding`
- [x] **None by default** - empty/unset env renders nothing (no element, no padding gap)
  - log: 2026-06-18 `StageBadge` returns null when `window.jhdata.stage` is falsy
- [x] **Top-right placement** - badge sits at the top-right of the portal header, to the right of the language + theme controls; all three render in the `oh-topbar` header row
  - log: 2026-06-18 was first item in `AppLayout` `actionsRender`
  - log: 2026-06-18 FIXED - `actionsRender` lands in the sider under `layout="side"` (ProLayout `Header` returns null), so it showed by the username at the sider foot; moved language + theme + stage into the `oh-topbar` row (badge rightmost); functional placement assertion added
- [x] **Outlined rectangle** - 1px border + text both in the stage colour (`currentColor`), transparent fill, square-ish corners (`--radius-sm`)
  - log: 2026-06-18 `.oh-stage-badge` in `global.css`
- [x] **Colour per stage** - DEV green, TST blue (accent/cyan per the design theme), STG orange, PRD red
  - log: 2026-06-18 `STAGE_TONE` maps to `--oh-green` / `--oh-cyan` / `--oh-orange` / `--oh-red`
- [x] **Unknown text grey** - any value not in {DEV,STG,TST,PRD} still renders, in neutral grey (`--oh-gray`)
  - log: 2026-06-18 `?? 'var(--oh-gray)'` fallback
- [x] **Case-insensitive match** - the stage key is matched uppercased, so `dev`/`Dev`/`DEV` all map to green
  - log: 2026-06-18 `raw.toUpperCase()` for the lookup
- [x] **Raw value displayed** - the badge shows the operator's text (CSS uppercases it for display), not a remapped label
  - log: 2026-06-18 renders `{raw}`; `text-transform: uppercase` in CSS
- [x] **Stripped server-side** - leading/trailing whitespace is trimmed before injection
  - log: 2026-06-18 `branding['stage'] = (stage or '').strip()`
- [x] **Injected via window.jhdata** - the value reaches the SPA through `portal.html` `window.jhdata.stage`, same channel as `admin_user`/`gpu_enabled`
  - log: 2026-06-18 `template_vars['branding_stage']` -> `stage: "{{ branding_stage }}"`
- [x] **Restart to change** - the value is frozen into `template_vars` at config load; changing the env takes effect on hub restart
  - log: 2026-06-18 read at module load, no live reload

### Env namespace

- [x] **Branding env namespace** - all branding env vars share the `JUPYTERHUB_BRANDING_*` prefix: STAGE, LOGO_URI, FAVICON_URI, FAVICON_BUSY_URI, LAB_MAIN_ICON_URI, LAB_SPLASH_ICON_URI
  - log: 2026-06-18 operator: "rename branding envs for logo, favicon etc to have _BRANDING like this one"; renamed in config, `settings_dictionary.yml`, Dockerfile, `compose.yml`, README, `custom-branding.md`, mock Settings page
- [x] **Settings + dictionary updated** - the renamed keys appear on the Settings page (data-driven from `settings_dictionary.yml`); STAGE added as an editable entry
  - log: 2026-06-18 `settings_dictionary.yml` + `mockSource.ts` Branding category

### Edge cases

- [x] **Edge: whitespace-only value** - a value that is only spaces trims to empty -> no badge
  - log: 2026-06-18 `.strip()` server-side; `?.trim()` client-side, then null
- [x] **Edge: lowercase stage** - `dev` matches green and displays `DEV`
  - log: 2026-06-18 uppercase match + CSS uppercase display
- [x] **Edge: long/custom text** - arbitrary text (e.g. `STAGING`) renders grey without breaking the header layout (`white-space: nowrap`)
  - log: 2026-06-18 grey fallback, nowrap badge
- [x] **Edge: auth pages** - login/signup screens have no app header, so the badge does not appear there (portal only)
  - log: 2026-06-18 badge lives in `AppLayout`, not the auth shell

### Tests

- [x] **Unit: stage normalization** - `setup_branding(stage=...)` returns `branding['stage']` stripped, `''` when unset; default-keys test includes `stage`
  - log: 2026-06-18 `duoptimum-hub-services/tests/test_branding.py::TestStage`; `make test`
- [x] **Functional: no badge by default** - default (signup) deployment has no stage env -> the header shows no `.oh-stage-badge`; also asserts the language + theme controls render in the `.oh-topbar` header row (right of the breadcrumb), not the sider
  - log: 2026-06-18 `tests/functional/test_branding_stage.py::test_no_stage_badge_by_default`; PASSED on the rebuilt image (default-mode suite, 26 passed)
- [x] **Functional: badge shows configured stage** - env-mode deployment with `JUPYTERHUB_BRANDING_STAGE=TST` shows a `TST` badge in the blue/accent tone, placed top-right (rightmost control: `badge.x > theme.x > lang.x`), not the sider
  - log: 2026-06-18 `tests/functional/test_branding_stage.py::test_stage_badge_shows_configured_stage` (envauth); `compose.functional-env.yml`; PASSED on the rebuilt image (env-mode suite, 3 passed)

### Configuration

- `JUPYTERHUB_BRANDING_STAGE` - environment-stage badge text; `DEV` / `STG` / `TST` / `PRD` recognised (coloured), any other text renders grey, empty/unset = no badge

## broadcast auto-close duration

The notifications broadcast composer picks an auto-close duration from five presets instead of an on/off toggle. The chosen value (milliseconds) flows to the lab Notification API via the broadcast payload.

- [x] **Five presets** - 30s, 1min, 10min, 30min, 1h, rendered as a segmented control
  - log: 2026-06-17 `AUTO_CLOSE_OPTIONS` (ms values) + antd `Segmented`; `pages/Notifications.tsx`
- [x] **Default 30s** - 30s is auto-selected on load
  - log: 2026-06-17 `useState(30000)`
- [x] **User-changeable** - the admin picks any preset before sending
  - log: 2026-06-17 `onChange={setAutoCloseMs}`
- [x] **Wired through** - `broadcast(message, variant, autoCloseMs, recipients)` sends `autoClose` (ms) in the POST body; the backend forwards it to the notification payload unchanged
  - log: 2026-06-17 `ops.broadcast` type `number | boolean`; backend `BroadcastNotificationHandler` passes `autoClose` through
- [x] **Correct unit** - values are milliseconds, what JupyterLab's `Notification` autoClose expects
  - log: 2026-06-17 30000 / 60000 / 600000 / 1800000 / 3600000

### API

- `POST /hub/api/notifications/broadcast` body `autoClose: number` (ms) - forwarded to each lab's notification ingest as `autoClose`

## last-known cache + non-blocking GPU + GPU-widget gating

The portal stays responsive across hub restarts: slow server-side aggregates (volume sizes, GPU inventory) persist their last-known snapshot and seed from it on boot, GPU detection never stalls startup, and the GPU widget is hidden when the platform has no GPU. `[x]` = implemented + verified by code-read / unit-check; `[ ]` = pending runtime confirmation (needs an image rebuild + restart). ESFO: every box below was re-verified against the code on 2026-06-17, not assumed.

### Persisted last-known cache (shared helper)

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

### Volume sizes (first consumer)

- [x] **Uses the helper** - volume_cache persists on refresh and seeds on boot via the shared helper
  - log: 2026-06-17 verified (volume_cache.py:21 import, :160 save_cached, :94 seed call)
- [x] **Seed only when no live data** - boot seed does not regress live in-memory data
  - log: 2026-06-17 verified by unit check (live cache not overwritten by disk)
- [x] **Non-blocking** - the fetch is deferred to the shared executor; startup only compiles templates + loads the seed
  - log: 2026-06-17 verified (configure_volume_cache compiles regex + _load_persisted; _fetch runs in get_executor)
- [ ] **Runtime: survives restart** - after a hub restart the portal shows last-known volume sizes immediately, not empty
  - log: 2026-06-17 pending deploy (logic verified, runtime needs rebuild)

### GPU inventory + non-blocking detection

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

### GPU widget global gating

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

### Prefetch all key pages

- [x] **Key-page data warmed at start** - prefetchCore warms servers/users/groups/events/stats/resources/hub-info plus tokens/lab-container/settings/sent-notifications
  - log: 2026-06-17 verified (App.tsx warm[] includes the four added keys; tsc green)
- [x] **No off-screen DOM prerender** - routes are statically bundled (no React.lazy), so only data is warmed, not hidden component trees
  - log: 2026-06-17 verified (router.tsx all static element imports; no lazy)

## Cert Provisioning

Hub provisions Traefik TLS at boot via `00_provision_certificates.sh`, reconciling the `/user-certs` overlay against the `/certs` runtime volume and choosing operator > persisted > auto. `/certs` is the dir Traefik scans; copying the overlay into the volume makes operator certs survive a failed host-bind mount across restarts.

- [x] **Runtime dir `/certs`** - `CERTIFICATE_TARGET_DIR` default `/certs`; Traefik file provider scans it (`watch=true`); hub writes here; backed by the `jupyterhub_certs` named volume
  - log: 2026-06-17 implemented + grep-verified no legacy path remains
- [x] **Overlay `/user-certs`** - `CERTIFICATE_USER_CERTS_DIR` default `/user-certs`; read-only host bind of `./certs`; optional - missing/empty means no operator certs
  - log: 2026-06-17 renamed from `/mnt/user_certs`
- [x] **No legacy `/mnt` cert paths** - no `/mnt/certs` or `/mnt/user_certs` in compose, Dockerfile, script, config, docs; historical JOURNAL entries exempt
  - log: 2026-06-17 swept both repos, clean
- [x] **Operator tier** - `/user-certs` has >=1 `*.yml`/`*.yaml` AND every `certFile`/`keyFile`/`caFile` resolves to an existing file -> source `operator-supplied`
  - log: 2026-06-17 verified by simulation
- [x] **Operator copy + rewrite** - delete top-level cert artifacts in `/certs`, `cp -a` overlay into `/certs` (subdirs included), sed-rewrite `/user-certs/` -> `/certs/` in copied yml so paths stay self-consistent
  - log: 2026-06-17 unchanged behaviour, paths migrated
- [x] **Persisted tier (symmetric)** - overlay empty/invalid AND `/certs` has >=1 yml whose every referenced file exists (recursive descent, `.pem` + subdirs accepted) -> keep `/certs` as-is, source `persisted`
  - log: 2026-06-17 rewritten from the old top-level-`*.crt`-only check; verified by simulation
- [x] **Auto tier** - operator + persisted both invalid -> `mkcert.sh` self-signed (CN `$CERTIFICATE_DOMAIN_NAME`, 2048-bit, 365d, no SAN) + default `certs.yml` into `/certs`, source `auto-generated`
  - log: 2026-06-17 unchanged, target path migrated
- [x] **Tier precedence** - operator > persisted > auto, evaluated in that order
  - log: 2026-06-17 verified
- [x] **All-or-nothing set** - a single missing reference rejects the whole tier's set and falls through to the next tier
  - log: 2026-06-17 verified
- [x] **Path resolution** - `resolve_under(dir,path)`: paths under `/user-certs` or `/certs` both remap under `dir`; other absolute pass through; bare/relative go under `dir`; used by operator (dir=`/user-certs`) and persisted (dir=`/certs`)
  - log: 2026-06-17 generalised from single-dir `resolve_user_path`
- [x] **Status banner** - startup logs `[Certificates]` source label, every yml present, per-cert subject/SAN/issuer/expiry (per-cert detail globs `*.crt` only, so `.pem` certs log the yml but not subject - cosmetic)
  - log: 2026-06-17 banner unchanged; `.pem` cosmetic gap noted
- [ ] **Resilience: failed host mount** - overlay fails to mount on restart (empty) + valid copy in `/certs` volume -> persisted serves the wildcard, not self-signed
  - log: 2026-06-17 logic verified by simulation; end-to-end pending live rebuild
- [x] **Resilience: `.pem` subdir recognised** - operator wildcard stored as `_.x/cert.pem` recognised by the persisted tier
  - log: 2026-06-17 the fix that closes the original clobber bug
- [x] **Resilience: no clobber** - a valid volume copy is never overwritten by auto-generate
  - log: 2026-06-17 falls out of the symmetric persisted check
- [x] **Direct-SSL mode** - `JUPYTERHUB_SSL_ENABLED=1` uses `/certs/server.crt` + `/certs/server.key`
  - log: 2026-06-17 path migrated
- [x] **Image bake** - Dockerfile `ENV CERTIFICATE_TARGET_DIR=/certs` + `CERTIFICATE_USER_CERTS_DIR=/user-certs`; `COPY templates/certs -> /certs`
  - log: 2026-06-17 added target env, migrated COPY
- [x] **Compose wiring** - `jupyterhub_certs:/certs` (hub + traefik), `./certs:/user-certs:ro` (hub overlay), provider dir `/certs`
  - log: 2026-06-17 migrated
- [x] **Functional test mount** - `tests/functional` compose mounts `certs:/certs`
  - log: 2026-06-17 migrated
- [x] **Wrapper certs.yml** - operator yml uses `/certs/...` paths; comment references the `/user-certs` overlay
  - log: 2026-06-17 reverted to `/certs`, comment updated
- [x] **Wrapper Traefik mount** - `./certs:/certs:ro` retained (host bind; Traefik reads `/certs`); deliberate, not changed
  - log: 2026-06-17 confirmed correct per operator
- [x] **Docs** - `docs/certificates.md` covers two dirs, three tiers, resilience rationale, path rules, reverse-proxy variant, logs, file reference
  - log: 2026-06-17 rewritten

- [x] **Edge: first boot, both empty** - empty overlay + empty volume -> auto-generate
  - log: 2026-06-17 verified by simulation
- [x] **Edge: yml present, cert/key missing** - operator invalid (logged) -> fall to persisted, else auto
  - log: 2026-06-17 covered by all-or-nothing
- [x] **Edge: cert/key present, no yml** - no yml in dir -> tier invalid -> fall through (yml required)
  - log: 2026-06-17 covered by the yml-count guard
- [ ] **Edge: corrupt / unparseable yml** - `yq` error -> `extract_paths` empty -> zero refs -> currently treated as valid (set copied/kept); Traefik then logs a parse error and keeps last-good
  - log: 2026-06-17 current behaviour documented; harden (reject yml yielding no refs)? confirm desired behaviour
- [x] **Edge: yml with no cert refs** - tls-options-only yml -> zero refs -> valid; loaded as Traefik config, no cert asserted (same semantics both tiers)
  - log: 2026-06-17 accepted as-is
- [x] **Edge: multiple yml files** - all loaded by the directory provider (multi-domain / split-CA)
  - log: 2026-06-17 unchanged
- [x] **Edge: subdir / `.pem` layout** - copied via `cp -a` and validated via recursive extract + resolve
  - log: 2026-06-17 verified by simulation

### Verification

- [x] **Unit/import tests** - `make test` = 556 (hub-services) + 63 (docker-proxy) pass
  - log: 2026-06-17 green
- [x] **Script syntax** - `bash -n` clean
  - log: 2026-06-17 ok
- [x] **Persisted simulation** - operator-valid; persisted recognises `.pem`-subdir wildcard; empty volume -> auto (no false-persist)
  - log: 2026-06-17 passed
- [ ] **Live end-to-end** - rebuild + restart: banner shows `operator-supplied`; a forced empty-overlay restart still serves the wildcard via persisted
  - log: 2026-06-17 pending user rebuild

### Env

- `CERTIFICATE_TARGET_DIR` (default `/certs`) - runtime dir Traefik scans
- `CERTIFICATE_USER_CERTS_DIR` (default `/user-certs`) - operator overlay
- `CERTIFICATE_DOMAIN_NAME` (default `localhost`) - CN for the auto-generated cert

## Compose Project Naming

Two explicit compose-project env vars replace the bare `COMPOSE_PROJECT_NAME` inside the hub: `JUPYTERHUB_COMPOSE_PROJECT_NAME` (the hub's own project - volume namespace + hub-infra labels) and `JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME` (the label stamped on spawned lab containers). They may differ; the lab var defaults to the hub project (empty suffix = same).

- [x] **Hub var read** - config reads `JUPYTERHUB_COMPOSE_PROJECT_NAME`, falling back to `COMPOSE_PROJECT_NAME` during transition; required non-empty (raises otherwise)
  - log: 2026-06-17 implemented (config:158); fallback keeps a not-yet-updated compose booting
- [x] **Volume namespacing unchanged** - per-user + shared + docker-proxy volume names stay on the hub var with the same value, so existing volumes still resolve (rename only, no re-namespacing)
  - log: 2026-06-17 verified - same value via compose mapping; would only change if the project name/suffix changed
- [x] **Lab var** - `JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME` is the `com.docker.compose.project` label on spawned labs; defaults to the hub project (empty = same), set to group labs under a different project
  - log: 2026-06-17 implemented (config:176 default, config:703 -> pre_spawn_hook compose_project)
- [x] **Hub-infra labels use the hub var** - the gpuinfo sidecar the hub self-starts is labelled with `JUPYTERHUB_COMPOSE_PROJECT_NAME`
  - log: 2026-06-17 (config:518 ensure_gpuinfo_sidecar)
- [x] **Configured in compose** - both vars passed to the hub in compose.yml (hub mapped from compose's `COMPOSE_PROJECT_NAME`; lab empty -> same project)
  - log: 2026-06-17 compose.yml:125-126
- [x] **Baked in Dockerfile** - both `ENV`s present (empty defaults)
  - log: 2026-06-17 Dockerfile:277,280
- [x] **In settings dictionary** - both on the Settings page (old `COMPOSE_PROJECT_NAME` entry renamed)
  - log: 2026-06-17 settings_dictionary.yml:11,15
- [ ] **Edge: stale wrapper compose** - wrapper compose.yml (gitignored download) still passes `COMPOSE_PROJECT_NAME`; the fallback boots the hub correctly until it is refreshed to pass `JUPYTERHUB_COMPOSE_PROJECT_NAME`
  - log: 2026-06-17 documented; fallback covers it, no boot failure
- [x] **Verified** - `python -m py_compile` config clean; `make test` 566 + 63 pass
  - log: 2026-06-17

## portal critic sweep (inconsistencies + illogical behaviour)

Findings from the 2026-06-17 two-agent critic sweep of every portal screen, deduplicated and prioritised. `[x]` = fixed + tsc-verified this session; `[ ]` = open. Runtime confirmation of every fix needs an image rebuild. Severity in the label.

### Fixed this session (code + tsc verified 2026-06-17)

- [x] **[HIGH] Duplicate `timeAgoShort`** - Home had a local long-form ("5 min ago") shadowing the shared short-form; deleted, now imports `lib/format`
  - log: 2026-06-17 fixed (Home.tsx import + removed local fn)
- [x] **[HIGH] `NaN%` segment widths on empty platform** - MetricCard segments divided by `total` (0 at first boot)
  - log: 2026-06-17 fixed (Home.tsx segPct guard)
- [x] **[HIGH] `undefined GB` in VolumeReset** - Size cell rendered `{v} GB` with no null guard
  - log: 2026-06-17 fixed (VolumeReset.tsx null -> muted dash)
- [x] **[MED] GPU row "none" text** - empty GPU row in ResourceBars printed the word "none"
  - log: 2026-06-17 fixed (meters.tsx -> dash)
- [x] **[MED] Tokens long-form time** - Tokens used `timeAgo` (".. ago") vs the short form everywhere else
  - log: 2026-06-17 fixed (Tokens.tsx -> timeAgoShort)
- [x] **[HIGH] Missing zebra rows** - Home active-servers preview, BulkResult, GroupsExport, SettingsReference tables had no alternating rows
  - log: 2026-06-17 fixed (rowClassName added to all four)
- [x] **[HIGH] GroupsExport opens with 0 selected** - `useState(data.map())` captured empty before data loaded
  - log: 2026-06-17 fixed (seed via useEffect once data arrives)
- [x] **[MED] GroupsExport reversed sort** - sorted ascending vs the Groups list's descending
  - log: 2026-06-17 fixed (b.priority - a.priority)
- [x] **[HIGH] Servers GPU column all-dashes in live** - per-server GPU is never collected -> column of dashes
  - log: 2026-06-17 fixed (column shown only when some row carries a gpu value)
- [x] **[HIGH] Users "Last seen" literal "never"** - rendered plain "never" not the muted dash convention
  - log: 2026-06-17 fixed (Users.tsx muted dash + "never signed in" title)
- [x] **[HIGH] `gpu_all` silently widens device-scoped groups** - seeded `true` even when specific devices granted
  - log: 2026-06-17 fixed (GroupPolicyTab default = gpu_device_ids empty)

### Open - HIGH

- [x] **[HIGH] Live error -> fake facts** - a failed live GET substituted mock fixtures (3x A100, version, lab image, curated settings) with no signal
  - log: 2026-06-17 FIXED for the platform-fact methods - getTotalResources / getHubInfo / getLabContainer / getSettings now return honest EMPTY on live error (no fake GPUs/version/image/settings); keepPreviousData holds the last real value on a transient error. List/feature fallbacks (groups/tokens/events) and the no-live-API delegations (effective-grants, settings-reference) left as intentional demo continuity; tsc+eslint green
- [x] **[HIGH] `PLATFORM.admin` mock drives live admin protections** - real JUPYTERHUB_ADMIN was unrecognised (task #182/#184)
  - log: 2026-06-17 FIXED - config exposes `admin_user`(JUPYTERHUB_ADMIN) -> window.jhdata; `isBuiltinAdmin = name === (adminUser() || PLATFORM.admin)`; tsc+eslint green
- [x] **[HIGH] Administrator switch reads persistent `user.admin`** - false for a post_auth_hook-promoted admin -> showed OFF for the real admin (task #182)
  - log: 2026-06-17 FIXED - `isAdminUser(name, user.admin)` = persistent OR name===admin_user; switch + save use the effective baseline
- [x] **[HIGH] Authorised switch shown/editable for admins** - admins are always authorised (task #184)
  - log: 2026-06-17 FIXED - Authorised hidden in UserConfig + invisible (muted "authorised") in the Users table for any effective admin; also switched Users from defaultChecked to controlled checked (fixes the desync MED)
- [x] **[HIGH] `statusOf` shows running server as Spawning** - `pending==='spawn'` checked before readiness; a stale pending masked a ready server (task #174)
  - log: 2026-06-17 FIXED (liveSource.statusOf checks ready first; pending only when not ready); tsc green
- [x] **[HIGH] Events row colour contradicts legend** - server event was green in the legend, cyan in the row (render only branched danger/warn)
  - log: 2026-06-17 FIXED (Events row reuses exported TONE_CLASS, matches the legend); the missing broadcast/group filter pills remain a separate MED item below
- [ ] **[HIGH] Settings signup toggle is a dead control** - uncontrolled defaultChecked wired only to a "(mock)" toast; no live persistence
  - log: 2026-06-17 found (Settings.tsx); fix = implement write or remove

### Open - MEDIUM

- [x] **[MED] Events missing broadcast/group filter pills** - counted in All but no scope pill, so counts never reconciled
  - log: 2026-06-17 FIXED (added Group + Broadcast scope pills with counts); tsc green
- [x] **[MED] Authorised toggle uncontrolled** - `defaultChecked` desynced from data after refetch (Users.tsx)
  - log: 2026-06-17 FIXED (controlled `checked={u.authorized}`); folded into the admin/authorised fix above
- [x] **[MED] Spawning bucketed as Active but sorted below Idle** - inconsistent counting vs ordering (Servers.tsx)
  - log: 2026-06-17 FIXED (STATUS_ORDER spawning=2, sorts just under active, consistent with the Active scope count); tsc green
- [x] **[MED] GPU section hidden but `gpu_access` round-trips on no-GPU host** - emit preserved gpu_access:true invisibly (GroupPolicyTab)
  - log: 2026-06-17 FIXED (emit forces gpu_access false when !gpuSupported()); tsc green
- [ ] **[MED] Policy emit fires on mount before seed** - a fast Save could PUT defaults (GroupPolicyTab); guard emit until cfg seeds
  - log: 2026-06-17 found
- [x] **[MED] GroupConfig editable Name never persisted** - dead input, change discarded on save
  - log: 2026-06-17 FIXED (Name now disabled/read-only with "cannot be changed" hint); tsc green
- [x] **[MED] Mock-mode Save skips validation** - the demo "saved" invalid data
  - log: 2026-06-17 FIXED in UserConfig (validateFields now runs before the mock short-circuit); GroupConfig/Profile share the pattern - DEFERRED (demo-only, low value)
- [x] **[MED] Live statusLabel has no time suffix** - mock shows "Active 1m", live showed just "Active"
  - log: 2026-06-17 FIXED (liveSource statusLabel appends timeAgoShort(last_activity); spawning stays bare); tsc green
- [ ] **[MED] Authorised defaults true on missing data** - `?? true` makes everyone authorised if native+activity silent (liveSource); unsafe default
  - log: 2026-06-17 found
- [x] **[MED] Notifications "active" includes spawning** - a spawning server has no extension to ingest -> guaranteed delivery failure
  - log: 2026-06-17 FIXED (recipient list restricted to active/idle ready servers); tsc green
- [x] **[MED] Dead "Require password change" toggle** - never read in NewUser/BulkUsers, contradictory defaults
  - log: 2026-06-17 FIXED (removed from both forms - NativeAuth has no forced-change flag, matching the earlier UserConfig removal); tsc green
- [ ] **[MED] Mock THRESHOLDS/IDLE_CULLER used as live** - time-left warn + session-info fallbacks are hardcoded UI constants applied to live data
  - log: 2026-06-17 found
- [ ] **[MED] Env-var / volume-mount editors no validation** - hint promises rules the UI doesn't enforce (GroupPolicyTab)
  - log: 2026-06-17 found
- [ ] **[MED] Settings live vs mock divergence** - live dumps all dictionary entries flat (state neutral, no toggle); mock is curated with states; align
  - log: 2026-06-17 found
- [ ] **[MED] Table row height Servers vs Users differ** (task #185)
  - log: 2026-06-17 found
- [ ] **[MED] Import / Export groups are mockActions** - Groups Import + GroupsExport export only toast "(mock)"; wire or hide
  - log: 2026-06-17 found

### Open - LOW (cosmetic / cleanup)

- [ ] **[LOW] Dead `error` ServerStatus** - no source produces it; drop from union or produce it on failed spawn
  - log: 2026-06-17 found
- [ ] **[LOW] Pending/credentials tables differ from ProTable density + zebra** (Users pending table, hand-rolled)
  - log: 2026-06-17 found
- [ ] **[LOW] Inline descriptive notes vs tooltip convention** - GroupConfig/UserConfig/NewUser/Profile inline "extra" notes
  - log: 2026-06-17 found
- [x] **[LOW] Empty states missing** - Tokens (no tokens / no apps) + Notifications past-history now show instructional empty text
  - log: 2026-06-17 FIXED (locale.emptyText on both Tokens tables + the Notifications history table); tsc green
- [x] **[LOW] SettingsReference mock var stale** - listed `JUPYTERHUB_NVIDIA_IMAGE` not the real `JUPYTERHUB_GPUINFO_NVIDIA_IMAGE`
  - log: 2026-06-17 FIXED (mockSource reference row -> JUPYTERHUB_GPUINFO_NVIDIA_IMAGE + sidecar image/description); tsc green
- [ ] **[LOW] Column-naming style mixed** - Servers terse (Vol/Sys/Mem) vs Users spelled-out; "Last activity" vs "Last seen" for the same concept
  - log: 2026-06-17 found

### Disposition of the remaining open items (2026-06-17)

Every HIGH and the clear MED/LOW are fixed + deployed. What is left is triaged, not ignored - each open box above falls into one of:

- **WON'T FIX (by design / defensive / risk > reward)**: the authorised `?? true` default is correct here because the hub runs `allow_all=True`; the policy emit-on-mount "race" is SUSPECT and a guard would break new-group creation; the dead `error` ServerStatus is harmless defensive code
- **NEEDS EYES (visual, can't verify from the shell)**: Servers vs Users row height (#185, content-driven); the pending/credentials table density; inline-note-vs-tooltip and column-naming are cosmetic + subjective - want the operator's preference before churning working UI
- **NEEDS A DECISION**: Groups Import / GroupsExport export are `mockAction`s - wire to a real endpoint or hide? operator's call
- **DEFERRED REFACTOR (low impact)**: Settings live-vs-mock curation; the time-warn / idle-culler UI thresholds read from constants (mem/vol/sys already read live); env-var / volume-mount editor validation
- **RUNTIME (needs the browser)**: profile-save "Failed to fetch" (#183) - code is correct; retry on the fresh bundle, then DevTools if it persists

None of the above blocks a workflow; the deployed build is functionally sound.

## design language (system-wide)

The portal's visual conventions, applied consistently across every screen. `[x]` = implemented + verified (code/build/render); `[ ]` = pending. Reference page: `/design-language`.

### Tables / lists

- [x] **Zebra rows** - every antd Table / ProTable / DragSortTable gets alternating row backgrounds, globally (no per-table wiring)
  - log: 2026-06-17 verified (global.css nth-child(even) + .oh-row-alt; all tables audited)
- [x] **Row hover = accent tint** - hovering any row subtly tints its background with the accent colour (overrides zebra + antd's grey hover), system-wide
  - log: 2026-06-17 implemented (global.css `.ant-table-tbody > tr:hover` accent 8%); build green
- [ ] **Two-line cells (sub-names)** - list rows show a primary name + a muted sub (username + first/last name) - NEEDS first/last in the list payload (task #186)
  - log: 2026-06-17 captured, next pass
- [ ] **Consistent row heights** - all list rows are the same height (the two-line shape unifies them) - task #186
  - log: 2026-06-17 captured, next pass (rows currently vary 51/69px)
- [ ] **Consistent margins** - uniform spacing/margins across screens - task #186
  - log: 2026-06-17 captured, next pass

### Icons

- [x] **Wireframe default, filled on demand** - icons render as line/wireframe by default; `filled` is opt-in
  - log: 2026-06-17 verified (Icon.tsx filled=false default -> stroke)
- [x] **Tones** - primary (blue, active/go-to), secondary (gray, neutral), dangerous (red, destructive), warning (yellow, caution)
  - log: 2026-06-17 verified (IconAction tone prop; demoed on /design-language)
- [x] **List icons wireframe; non-list filled** - list/table action icons stay wireframe (fill only for emphasis e.g. stop); non-list/button icons use the filled glyph when one is available
  - log: 2026-06-17 documented + demoed (design-language: non-list filled row + list wireframe row + note)

### Text colours

- [x] **Normal-text taxonomy** - five text colours, all from the defined palette vars: neutral (`--color-text`, body), link (`--color-accent`, e.g. a user-profile link), success (`--color-success`, green), warning (`--color-warning`, orange), dangerous (`--color-danger`, red); one utility class each (`.oh-text-*`)
  - log: 2026-06-17 added `.oh-text-neutral/link/success/warning/danger` (global.css) + demoed on /design-language ("Normal text" card); first consumer = the volume-reset "removed" red text; operator "add to design language normal text"
- [x] **Named palette (dim / normal / intense)** - a named colour palette borrowed from the tokens - green (success), cyan/blue (accent), red (danger), orange (warning), gray (text-subtle) - each as `--oh-<name>` with `-dim` (mixed toward surface) and `-intense` (mixed toward text) variants, referable by name; demoed as labelled squares on /design-language ("Palette" card). Magenta is not in the current tokens
  - log: 2026-06-18 added `:root --oh-*` (global.css) via `color-mix` on the source vars; operator "design palette of colours ... dim, normal, intense ... refer to them by name ... borrow from already defined"
- [x] **Activity meter tone by lit-bar count** - the 5-segment meter is a SINGLE tone across all lit bars, chosen by how many bars are lit: 1 bar pale red, 2-3 bars orange, 4-5 bars green (not a per-position gradient, and keyed off the lit count not a raw-value band) - so a fuller meter reads greener
  - log: 2026-06-18 `tone = lit<=1 ? 'low' : lit<=3 ? 'idle' : ''` on `ActivityMeter`/`ActivityMeterFill`, CSS `.oh-meter.low/.idle i.on`; operator "1 bar red, 2 both orange, 3 all orange, 4 all green, 5 all green" (corrected an interim per-segment-gradient reading)
- [x] **Activity meter red is pale** - the meter's red tone (1 lit bar) uses `--oh-red-dim` so the solid blocks read as soft as the thin danger / stop-button glyph (both still derive from `--color-danger`); orange = `--color-warning`, green = `--color-success`
  - log: 2026-06-18 `--oh-red-dim` on `.oh-meter.low i.on`; operator "activity red - make it the same pale colour as the stop button"

### Headers / chrome

- [x] **No page title headers** - the big page title + sub-line are removed (the breadcrumb names the page); only the optional right-aligned actions remain
  - log: 2026-06-17 implemented (PageHeader renders only actions; ~50px reclaimed on every page)
- [x] **Named edits are explicit** - editing a user profile / group is reached via an explicit named link (the username / group-name), never a whole-row click; row-click is reserved for read-only detail (Servers drawer)
  - log: 2026-06-17 verified (Users/Groups name-links to config; Servers row-click = report drawer)
- [x] **Label casing = Title Case** - button labels and header labels (page / card / section titles, table column headers, section tabs) Title-Case every principal word; minor words (a, an, the, and, or, of, to, in, on, at, by, for, with, vs...) stay lowercase unless first/last; acronyms (API, GPU, CPU, TLS, ID) and units (+7h, GB) preserved; sentence copy / form-field input labels / filter data-values stay sentence case. Detail in [acc-crit-label-capitalisation]
  - log: 2026-06-18 added (operator: "labels (buttons, headers) must have all capitalised parts; sweep"); demoed on /design-language Conventions card

### Navigation (system-wide)

- [x] **Sub-screen footer** - every screen reached from a list (Configure user, Configure group, Manage volumes) carries the standard footer: destructive action left, Cancel + a primary Save/Done/Ok right (`FormFooter`); never a dead-end with no way back
  - log: 2026-06-17 implemented - Manage volumes joined the pattern (Reset left, Cancel + Done right); UserConfig/GroupConfig already had it; cross-ref [acc-crit-volume-reset]
- [x] **Respect the navigation path / breadcrumbs** - a screen reachable from more than one parent records its origin in the nav state; the breadcrumb parent AND the Cancel/Done (close) target both reflect where the user actually came from, not a hardcoded route parent
  - log: 2026-06-17 implemented - nav `state.from` overrides the static breadcrumb parent (`Breadcrumbs.tsx`); Manage volumes from Home returns to Home, from Servers returns to Servers (was always /servers)
- [x] **Widget actions == list actions** - the Home "Active servers" widget renders the IDENTICAL row actions as the Servers list via the shared `rowActions` (start own -> Start page; start other -> inline spinner; enter/restart/stop; manage volumes), never a divergent widget-only set
  - log: 2026-06-17 implemented - extracted `components/ServerRowActions.tsx`, reused by Servers + the Home widget; cross-ref [acc-crit-server-lifecycle-ux]

### Values / feedback

- [x] **Tooltips, not static text** - precise values (exact GB / % / dates / breakdowns) live in a hover tooltip, never as wasteful static text under the control
  - log: 2026-06-17 documented (design-language note); cells use title tooltips for breakdowns
- [x] **Progress bars** - the standard bar is base-relative and drains blue -> amber -> red toward the cull; the GPU striped bars are the alternative (one labelled bar per device) for multi-device load
  - log: 2026-06-17 verified (TtlGadget + ResourceBars + GpuMeter; documented on /design-language)
- [x] **GPU device labels = mini names** - per-GPU bars label each device with its mini name (vendor/brand boilerplate stripped: "NVIDIA GeForce RTX 5090" -> "5090") instead of the bare index; full index + name stay in the hover tooltip
  - log: 2026-06-17 implemented (shortGpuName strips NVIDIA/GeForce/RTX/Generation; GpuMeter label uses it); typecheck clean, live render pending deploy

### Mobile

- [x] **Minimal home, desktop-parity actions** - below 768px the home is the server card (same actions as desktop) + admin servers widget + a Servers link (no Users); no sider panel, no collapse handle, no header hamburger
  - log: 2026-06-17 verified by headless render (no panel/handle/hamburger; full action set)
- [x] **Mobile Servers view** - the Servers screen on mobile is a card list mirroring the old JupyterHub admin info (user + admin, status, last activity, actions)
  - log: 2026-06-17 implemented (MobileServerList); runtime render pending the next deploy

### Visual cues to digest from the 2026-06-17 servers/resource batch (#252)

These conventions must be shown on `/design-language` as VISUAL CUES (live example elements), not "this -> that" before/after pairs.

- [ ] **Resource tooltip carries the live % + the assigned reference** - every CPU/memory bar tooltip quotes the usage % alongside the assigned ceiling (cores / GB assigned vs host)
  - log: 2026-06-17 criterion added (#245/#246/#252); cross-ref [acc-crit-resource-bars]
- [ ] **Activity % may exceed 100%** - the activity tooltip shows the real uncapped % (>100% = works more than the daily target), multiline
  - log: 2026-06-17 criterion added (#247/#252); cross-ref [acc-crit-activity-scoring]
- [ ] **List vs widget: status/last-activity separate in lists** - in lists, Status and Last activity are separate columns (the widget may club them); column order Status, Last activity, Activity; meters centered in their column
  - log: 2026-06-17 criterion added (#248/#252); cross-ref [acc-crit-servers-list-layout]
- [ ] **Names are links + carry first/last** - a user name in any list links to the user and shows the first/last name (no artificial click-friction)
  - log: 2026-06-17 criterion added (#249/#252)
- [x] **Admin lifecycle = inline spinner, not navigation** - starting/restarting another user's server spins the control in place; it does not route to a progress screen
  - log: 2026-06-17 criterion added (#243/#252); 2026-06-17 verified via shared `rowActions` (Servers list + Home widget) - own start -> Start page, other start -> inline `lf.start` spinner; cross-ref [acc-crit-server-lifecycle-ux]
- [ ] **Columns sized to content** - status / last-activity columns are just wide enough, not stretched
  - log: 2026-06-17 criterion added (#250/#252)

## docker policy access mode

The group-policy Docker section's enable toggle means "docker access granted". There is no separate "No docker access" choice (that is the toggle being off). When enabled, the only choice is HOW access is granted: Standard (raw socket) or Limited (per-user filtered proxy, the default), with Privileged orthogonal.

- [x] **No "none" option** - the radio offers only Standard and Limited; the redundant "No Docker access" entry is removed
  - log: 2026-06-17 `GroupPolicyTab.tsx` docker section
- [x] **Toggle grants** - `docker_active` (the section switch) being on = access granted; off = no docker, and both `docker_access`/`docker_limited` emit false
  - log: 2026-06-17 emission gated on `(on.docker ?? false)`
- [x] **Limited is the default** - when the section is enabled and Standard is not chosen, the mode is Limited; the quota panel shows for Limited
  - log: 2026-06-17 `dStd` is the only stored flag; limited = `!dStd`; quota panel gated on `!dStd`
- [x] **Emission coherence** - on -> exactly one of `docker_access`(std) / `docker_limited`(limited) is true; off -> both false; `docker_privileged` independent
  - log: 2026-06-17 `docker_access: on && dStd`, `docker_limited: on && !dStd`
- [x] **Legacy config migrates** - a stored config that was "active but neither mode" (the old none-while-on state) reads as Limited (the default), not a broken empty mode
  - log: 2026-06-17 init sets `dStd` from `docker_access`; not-standard reads as limited
- [x] **Privileged orthogonal** - the Privileged checkbox is independent of the access mode and unaffected by this change
  - log: 2026-06-17 `dPriv` unchanged
- [ ] **Runtime: edit + save round-trips** - on the live hub, a group with docker enabled saves as limited (or standard) and re-opens to the same mode
  - log: 2026-06-17 frontend + build clean; on-screen confirm pends operator rebuild

## drop the `/portal` URL segment

Serve the React SPA at the hub root (`/hub/...`) instead of `/hub/portal/...`, so the address bar and bookmarks carry no `portal` segment. The SPA's own routes become `/hub/servers`, `/hub/users`, etc.

### Implementation status (2026-06-17)

IMPLEMENTED and verified to the extent possible offline: backend `make test` 566+63 green, `py_compile` + pyflakes clean, portal `tsc -b` + `build:hub` clean, manifest entry is relative (`assets/index-*.js`) so `portal.html` resolves to `/hub/assets/*` matching the route. Decision taken: home client-route renamed to `/dashboard` (nav label stays "Home"); legacy server-rendered page handlers removed (the SPA owns those features). Login/signup are safe - `main.tsx` renders `<AuthApp/>` off `window.jhdata.authPage`, independent of the router/basename. Runtime asset resolution + deep-link routing against the live hub need the user's image rebuild to confirm on-screen. Revert = `git revert` of this change set (cohesive).

### Hard constraint (the reason `/portal` exists today)

JupyterHub registers its built-in page + API handlers BEFORE `c.JupyterHub.extra_handlers` and Tornado matches first-wins (`jupyterhub/app.py` ~1790-1794: `h.extend(default_handlers)` then `h.extend(self.extra_handlers)`). The portal handlers are `extra_handlers`, so they can only claim `/hub/<path>` that no built-in already owns. Built-ins that DO own a path (`jupyterhub/handlers/pages.py:772+`, `apihandlers`): `/hub/` (RootHandler), `/hub/home`, `/hub/admin`, `/hub/login`, `/hub/logout`, `/hub/token`, `/hub/spawn`, `/hub/spawn-pending`, `/hub/user-redirect`, `/hub/error`, `/hub/health`, `/hub/api/*`, `/hub/static/*`, `/hub/metrics`, `/hub/oauth_login`, `/hub/oauth2callback`.

Consequence: the SPA can serve at `/hub/<route>` for every route EXCEPT the reserved ones - and its current landing route `/home` collides with the built-in `/hub/home` (stock page wins on hard-refresh / deep-link), and bare `/hub/` is RootHandler.

### Decision required

- [ ] **Landing-route rename** - move the SPA's home view off the reserved `/home` path (recommended `/dashboard`, keep the nav LABEL "Home"); this is the one user-facing choice and the only thing blocking a clean drop
  - log: 2026-06-17 criterion added; alternatives: (b) accept stock hub home on a hard-refresh of the home view (poor), (c) override JupyterHub's RootHandler/HomeHandler (invasive, version-fragile, fights the framework - not recommended)

### Backend (duoptimum_hub_web)

- [ ] **Routes drop `/portal`** - `ASSETS_ROUTE` `/portal/assets/(.*)` -> `/assets/(.*)`, `BRAND_ROUTE` `/portal/brand/(.*)` -> `/brand/(.*)`, `PORTAL_ROUTE` `/portal/?(.*)` -> `/(.*)` (the SPA shell catch-all, still after built-ins so reserved paths win)
  - log: 2026-06-17 criterion added
- [ ] **PORTAL_URL** - `/hub/portal` -> the chosen landing (`/hub/dashboard`); `default_url = base_prefix + PORTAL_URL` so post-login + `/hub/` land on the portal
  - log: 2026-06-17 criterion added
- [ ] **Asset/brand precedence** - `/hub/assets/*` and `/hub/brand/*` matched before the `/(.*)` shell catch-all and do NOT collide with built-in `/hub/static/*`
  - log: 2026-06-17 criterion added
- [ ] **Shell still gets XSRF** - PortalHandler renders the shell for the catch-all so `window.jhdata.xsrf_token` is injected exactly as today
  - log: 2026-06-17 criterion added
- [x] **Old-path redirect (no /portal flash)** - `/hub/portal[/...]` 302s server-side to the hub-root SPA (`/portal/home` -> `/dashboard`) via `PortalRedirectHandler`, registered before the catch-all - so a stale `next`/bookmark/cached link never loads the shell at `/portal` and then client-redirects (the ~1s "portal" flash after login the operator hit)
  - log: 2026-06-17 implemented (`handlers.py::PortalRedirectHandler`, `LEGACY_PORTAL_ROUTE` before `PORTAL_ROUTE` in `portal_handlers`)
  - log: 2026-06-17 criterion added

### Frontend (duoptimum-hub-web)

- [ ] **Vite base** - `VITE_BASE` `/hub/portal/` -> `/hub/` (`.env.hub`); drives asset URLs + router base
  - log: 2026-06-17 criterion added
- [ ] **Router basename** - `portalBasename()` / `portalAssetBase()` drop the `/portal` suffix (read `window.jhdata.base_url` -> `<base>/hub` not `<base>/hub/portal`)
  - log: 2026-06-17 criterion added
- [ ] **Home route** - `/home` -> `/dashboard` in `router.tsx` (index redirect, `*` fallback), `nav.ts`, and every `navigate('/home')` / `to="/home"` (label stays "Home")
  - log: 2026-06-17 criterion added

### Edge cases

- [ ] **Reserved paths still work** - `/hub/login`, `/hub/logout`, `/hub/api/*`, `/hub/static/*`, `/hub/spawn`, `/hub/health` are served by JupyterHub built-ins, never the SPA catch-all
  - log: 2026-06-17 criterion added
- [ ] **Deep-link / refresh** - hard refresh on `/hub/servers`, `/hub/users`, `/hub/dashboard`, `/hub/servers/:name/starting` serves the shell (no 404, no stock page)
  - log: 2026-06-17 criterion added
- [ ] **Edge: `/hub/home` typed directly** - shows stock hub home (built-in, unavoidable while extra_handlers run after built-ins); the SPA never links there once the landing is `/dashboard`
  - log: 2026-06-17 criterion added
- [ ] **Edge: bare `/hub/`** - RootHandler redirects to `default_url` (the portal landing)
  - log: 2026-06-17 criterion added
- [ ] **Edge: wrapper Traefik** - the live stack routes the public root to `/hub`; dropping `/portal` is internal to the hub image and needs no wrapper change (the wrapper is a separate repo - do not edit)
  - log: 2026-06-17 criterion added
- [ ] **Mock/dev** - dev-proxy + mock (no shell) fall back to `BASE_URL`; `/dashboard` works there too
  - log: 2026-06-17 criterion added

### API / routes (after)

- `/hub/assets/(.*)` -> ImmutableStaticFileHandler (hashed bundle)
- `/hub/brand/(.*)` -> StaticFileHandler (public, no auth)
- `/hub/(.*)` -> PortalHandler (`@authenticated` shell; reserved paths already claimed by built-ins)
- `default_url = <base_prefix>/hub/dashboard`

## duoptimumhub service + image rename

The hub's Docker Compose service is renamed `jupyterhub` -> `duoptimumhub` and the published image `stellars/stellars-jupyterhub-ds` -> `stellars/duoptimumhub`, so the deployment matches the Duoptimum Hub branding and the DockerHub push targets the new repo. The hub's URL prefix (`/jupyterhub`, `JUPYTERHUB_BASE_URL`) and all `JUPYTERHUB_*` env vars are unchanged - only the compose service identity and the image tag move. Verified against the code 2026-06-18.

### Compose service rename

- [x] **Service key** - `compose.yml` hub service is `duoptimumhub` (was `jupyterhub`)
  - log: 2026-06-18 operator: "rename jupyterhub service to duoptimumhub"
- [x] **depends_on updated** - traefik and watchtower `depends_on` point at `duoptimumhub` (a stale `jupyterhub` reference would fail compose validation)
  - log: 2026-06-18 both blocks renamed
- [x] **Traefik identifiers** - router/service/middleware renamed `jupyterhub-rtr`/`jupyterhub-svc`/`jupyterhub-ratelimit` -> `duoptimumhub-*`, consistently in `compose.yml` and the wrapper override
  - log: 2026-06-18 the `routers.X.service` reference still matches the service definition
- [x] **URL path unchanged** - the router rule still matches `Path(/jupyterhub)`; the deploy prefix is a separate concern from the service name and was not touched
  - log: 2026-06-18 base_url stays `/jupyterhub`
- [x] **container_name** - the literal suffix is `-duoptimumhub` (`${COMPOSE_PROJECT_NAME:-…}-duoptimumhub`)
  - log: 2026-06-18 renamed; project-name default unchanged
- [x] **Hub bind/connect host** - `c.JupyterHub.hub_ip` and `hub_connect_url` in `config/jupyterhub_config.py` use `duoptimumhub`; the hub binds to, and CHP / spawned labs reach the hub by, the compose service name
  - log: 2026-06-18 the first rebuild crashed boot with `getaddrinfo ENOTFOUND jupyterhub` (hub_ip still hardcoded the old name); fixed both lines to `duoptimumhub`

### Image rename

- [x] **Image tag** - the hub image is `stellars/duoptimumhub` everywhere it is built, tagged, pulled or referenced: Makefile (`HUB_IMAGE`, build `--tag`, `tag`, push, success banners), `compose.yml`, the functional compose, `start.sh`, `start.bat`
  - log: 2026-06-18 operator: "change the image name ... to duoptimumhub ... so the dockerhub push won't blow up"; chose `stellars/duoptimumhub`
- [x] **README DockerHub badges** - image-size and pulls badges point at `stellars/duoptimumhub`
  - log: 2026-06-18 GitHub repo URLs left as-is (repo not renamed)
- [x] **Only the hub image** - the gpuinfo (`stellars/stellars-gpuinfo-nvidia`) and lab (`stellars/stellars-jupyterlab-ds`) images are unchanged (no `jupyterhub` token)
  - log: 2026-06-18 scope limited to the hub image

### Collaterals (verified independent)

- [x] **gpuinfo sidecar unaffected** - the hub finds the sidecar by its own DNS name (`gpuinfo-nvidia`) and joins the sidecar network by container id, never by the hub's compose service name; zero changes needed
  - log: 2026-06-18 `gpuinfo_sidecar.py` uses the Docker socket + URL host, not the service name
- [x] **Networks/volumes unchanged** - network and volume names derive from `COMPOSE_PROJECT_NAME`, not the service name
  - log: 2026-06-18 `${COMPOSE_PROJECT_NAME:-…}_network`, named volumes independent

### Tests + harness

- [x] **Functional harness renamed** - the service is `duoptimumhub` in all three harness compose files; `conftest.py` `BASE_URL`/`HUB_HOST` default to `duoptimumhub`; the Makefile `--wait`/`restart` targets name `duoptimumhub`
  - log: 2026-06-18 operator: "fix the tests and harness"
- [ ] **Functional suites pass post-rebuild** - `make test-functional` and `make test-functional-env` are green against the rebuilt `stellars/duoptimumhub:latest` image
  - log: 2026-06-18 needs the authorised one-time `make rebuild`

### Deployment surfaces

- [x] **Wrapper override + compose** - `../compose.yml` refreshed from the submodule; `../compose_override.yml` service + traefik + branding-env names renamed
  - log: 2026-06-18 operator: "copy current compose.yml to .. and fix ../compose-override.yml"
- [x] **Copier template** - `copier-stellars-jupyterhub-ds` override `.jinja` service key + traefik + image comment renamed; `tests/test_render.sh` assertions updated
  - log: 2026-06-18 operator: "fix the template - it refers to all the old setup and env names"

### Edge cases

- [x] **Edge: GitHub repo URLs preserved** - `github.com/.../stellars-jupyterhub-ds` and `copier-stellars-jupyterhub-ds` URLs are the repo, not the image, and are left unchanged
  - log: 2026-06-18 only `stellars/stellars-jupyterhub-ds` (image) renamed, not `…henson/stellars-jupyterhub-ds`
- [ ] **Edge: live recreate required** - a running stack must be recreated (`down`/`up`) to pick up the new service + container name; `make start` uses `--no-recreate` and will not rename a running container in place
  - log: 2026-06-18 operator action; not auto-applied
- [x] **Edge: historical docs untouched** - `CHANGELOG.md`, `docs/medium/*`, and journals keep the old names (they record past state)
  - log: 2026-06-18 append-only / published article content

## Edit user returns to its origin

Configuring a user (`UserConfig`, route `/users/:name`) is reachable from three places - the Home "Active servers" widget, the Servers list, and the Users list. Save, Cancel and Remove must return to the page the edit was opened from, and the breadcrumb parent must name that origin. Mechanism reuses the existing nav-origin pattern (the one `ManageVolumes` uses): the opening `<Link>` tags `state.from = {to, label}`; `UserConfig` reads `backTo = state.from?.to ?? '/users'`; `Breadcrumbs` prefers `state.from` over the static route parent. Verified against the code 2026-06-18.

### Return navigation

- [x] **From Home -> Home** - opening Configure-user from the Home servers widget returns to `/dashboard` on Save / Cancel / Remove
  - log: 2026-06-18 implemented - Home username `<Link>` tags `state.from = HOME_ORIGIN`
- [x] **From Servers -> Servers** - opening it from the Servers list returns to `/servers`
  - log: 2026-06-18 implemented - Servers username `<Link>` tags `state.from = SERVERS_ORIGIN`
- [x] **From Users -> Users** - opening it from the Users list returns to `/users`
  - log: 2026-06-18 implemented - Users is the canonical fallback (`?? '/users'`); the link carries no state, mirroring how `ManageVolumes` treats `/servers`
- [x] **Cancel returns to origin** - the footer Cancel navigates to `backTo`, not a hardcoded `/users`
  - log: 2026-06-18 was `navigate('/users')`, now `navigate(backTo)`
- [x] **Save returns to origin** - a successful save (mock and live paths) navigates to `backTo`
  - log: 2026-06-18 both branches changed to `navigate(backTo)`
- [x] **Remove returns to origin** - deleting the user (live mode) navigates to `backTo`
  - log: 2026-06-18 `navigate(backTo)`; mock mode unchanged (stays, list updates in place)

### Breadcrumb

- [x] **Parent names the origin** - the breadcrumb second crumb is Home / Servers / Users matching where the edit was opened, linking back there
  - log: 2026-06-18 `Breadcrumbs` already prefers `state.from` over `handle.parent`; the origin links now feed it
- [x] **Default parent is Users** - with no origin state the crumb falls back to the route's static parent (Users)
  - log: 2026-06-18 unchanged - `usersParent` on the `/users/:name` route handle

### Edge cases

- [x] **Edge: deep link / refresh** - landing on `/users/:name` directly (no `state.from`) returns to `/users` and shows Users as the parent
  - log: 2026-06-18 fallback `?? '/users'`; breadcrumb falls back to `handle.parent`
- [x] **Edge: Profile route (/profile)** - admin self-edit via `/profile` (no `:name`, no origin) keeps the prior behaviour, returning to `/users`
  - log: 2026-06-18 same fallback; out of scope to change, behaviour preserved
- [x] **Edge: single source of truth** - the same `from`-state shape (`{to, label}`) drives both the return navigation and the breadcrumb, so they can never disagree
  - log: 2026-06-18 one `state.from` read in `UserConfig` (return) and `Breadcrumbs` (parent)

## Platform event log (persistence + clear)

The portal's audit feed (Overview "Recent events" + the Events page) is backed by a persistent SQLite store, so events survive a hub restart; an admin can clear the whole log from the Events panel. Store: `duoptimum_hub_services/event_log.py` (`/data/event_log.sqlite`); handler: `handlers/events_data.py`; UI: `pages/Events.tsx`.

### Persistence

- [x] **Stored in SQLite, not memory** - events are written to `/data/event_log.sqlite` (the persistent `jupyterhub_data` volume), so they survive a hub restart / recreate
  - log: 2026-06-18 verified - `EventLogManager` SQLAlchemy store (was the operator's question "are events saved anywhere?")
- [x] **Bounded** - the table is pruned to the most recent 1000 rows on each record, so it never grows unbounded
  - log: 2026-06-18 `_MAX_ROWS = 1000`, prune-on-record
- [x] **Override path** - `STELLARS_EVENT_LOG_DB_PATH` overrides the DB location (tests point it at a temp file)
  - log: 2026-06-18 env override

### Clear action

- [x] **Clear button in the Events panel** - the Events toolbar has a danger-toned "Clear log" button (close icon), disabled when the feed is already empty
  - log: 2026-06-18 `Events.tsx` toolBarRender; operator "clear them - using action in the events panel - design that action button"
- [x] **Confirm before clearing** - clicking it opens a confirm modal ("Clear the event log? This permanently deletes every recorded event. This cannot be undone.") with a danger OK
  - log: 2026-06-18 `Modal.confirm` + danger okButtonProps
- [x] **Wipes the store** - confirming calls `DELETE /hub/api/events` -> `EventLogManager.clear()` (admin-only), emptying the table; the feed refetches empty
  - log: 2026-06-18 `clearEvents` op invalidates `['events']`; handler `delete` guarded on `current_user.admin`
- [x] **Admin-only** - both GET and DELETE on `/api/events` 403 for non-admins
  - log: 2026-06-18 `@web.authenticated` + admin check on both methods
- [x] **Log keeps working after a clear** - new events record normally into the emptied store
  - log: 2026-06-18 covered by `test_clear_empties_the_log`
- [ ] **Edge: clear is not itself audited** - clearing leaves the log empty (no "log cleared" marker is recorded); revisit if an audit trail of the clear is wanted
  - log: 2026-06-18 by design - literal "clear"; flag for the operator

### API

- `GET /hub/api/events` -> `{events: [{id, ts, type, text}]}` (admin, newest first, <=100)
- `DELETE /hub/api/events` -> `{cleared: <n>}` (admin) - empties the log

### Tests

- [x] **Store unit tests** - record/recent/prune/clear covered in `tests/test_event_log.py`
  - log: 2026-06-18 added `test_clear_empties_the_log` + `test_clear_empty_log_is_noop` (6 passing)
- [x] **Functional SPA test** - the harness drives the Events page end-to-end: an admin action records an event, the feed shows it, Clear log + confirm empties the feed and disables the button
  - log: 2026-06-18 `tests/functional/test_events.py::test_events_render_and_clear` (green in the signup setup)

## force password change on next login (#232 / #233)

An admin can require a user to change their password before they can use the platform. Enforcement is "no escape" at the spawner: a flagged user cannot start a lab by any route until the password is changed. All backend logic lives in the `duoptimum-hub-services` package.

### Storage (duoptimum_hub_services.user_profiles)

- [x] **must_change_password flag** - a Boolean column on the `user_profiles` table, default False
  - log: 2026-06-17 added; `get_must_change_password` / `set_must_change_password`
- [x] **Idempotent migration** - a pre-existing DB without the column gets it via `ALTER TABLE ... ADD COLUMN ... DEFAULT 0` (create_all never ALTERs); checked against the column list first
  - log: 2026-06-17 `_migrate_must_change_password`; covered by `test_migration_adds_column_to_legacy_db`
- [x] **Profile edits preserve the flag** - a name/email `save_profile` never clobbers must_change_password
  - log: 2026-06-17 `test_save_profile_preserves_must_change`

### Set / read (admin only)

- [x] **Admin-only set endpoint** - `POST /api/users/{user}/force-password-change {value}` sets/clears the flag; 403 for non-admin (a user must not clear their own gate)
  - log: 2026-06-17 `UserForcePasswordChangeHandler`, registered in config; handler count 26 -> 27
- [x] **Flag read via the profile** - `GET /api/users/{user}/profile` returns `must_change_password`; the frontend maps it to `UserProfile.mustChangePassword`
  - log: 2026-06-17 `_row_to_dict` + `liveSource.getUserProfile`

### Enforcement (no escape)

- [x] **Spawn hard-block** - `pre_spawn_hook` raises 403 with a clear message when the flag is set, so a flagged user - or an admin starting them - cannot get a lab by ANY route (the no-escape guarantee)
  - log: 2026-06-17 `hooks.py`; the message tells the user to change their password then start
- [x] **Fail-open on a store error** - if the flag cannot be read (profiles DB momentarily unreadable) the spawn is ALLOWED, never blocked - blocking-on-error would lock the whole platform out
  - log: 2026-06-17 try/except around the check; 605 backend tests pass (favicon/hook tests green)
- [x] **Clears on a successful change** - `DuoptimumHubAuthenticator.change_password` clears the flag on NativeAuth's success return, so a self-service change lets the user spawn again
  - log: 2026-06-17 success-gated override
- [ ] **Login auto-redirect (deferred)** - a flagged user is NOT yet auto-redirected to the change-password page on login; the spawn-block + the clear message enforce no-escape, but the funnel is manual. Intercepting the live login redirect was deliberately deferred (too risky to ship without a runtime auth round-trip test)
  - log: 2026-06-17 deferred - documented; revisit with an operator runtime test

### UI (#232 Configure-user)

- [x] **Toggle** - "Force password change on next login" switch on Configure-user (non-builtin users), initial state from `mustChangePassword`
  - log: 2026-06-17 `UserConfig.tsx`
- [x] **Hidden for admins** - the toggle only shows when the configured user is NOT an admin; flipping Administrator on hides it reactively (admins can always spawn, so the gate is meaningless for them) - gated on `liveAdmin`, mirroring the Authorised switch
  - log: 2026-06-17 `UserConfig.tsx` `!isBuiltinAdmin && !liveAdmin`
- [x] **Help is a tooltip on the control, not an inline note or (?) icon** - "The user cannot start their server until they set a new password" is a standard hover tooltip on the switch itself (native `title` on `<Switch>`, which antd forwards to the control), not an `extra` note and not a `Form.Item tooltip` (?) label icon
  - log: 2026-06-17 `extra=` -> `Form.Item tooltip=` (?) icon -> native `<Switch title=...>` per operator ("no (?) icon, normal standard tooltip on the control")
- [x] **Applied after the password set** - in `save()` the flag is applied AFTER any password set, so an admin setting a temp password + forcing a change leaves the gate ON (the password set clears it, the toggle re-sets it)
  - log: 2026-06-17 order enforced in `save()`; `setForcePasswordChange` ops, admin-only
- [x] **Reactive admin reveal** - flipping Administrator updates the dependent controls at once via `Form.useWatch` (admins are auto-authorised -> the Authorised switch yields to a note)
  - log: 2026-06-17 #232 reactive part

### Edge cases

- [x] **Admin set-password vs force flow** - an admin password set clears the flag; the Configure-user toggle (applied last) re-sets it, so "temp password + force change" works
  - log: 2026-06-17 ordering in `save()`
- [ ] **Runtime: end-to-end** - on the live hub: admin flags a user -> user cannot spawn (clear 403) -> user changes password -> spawn allowed; pends operator rebuild
  - log: 2026-06-17 backend + frontend + 605 tests + build green; on-screen confirm pends rebuild

### API

- `POST /api/users/{user}/force-password-change` body `{value: bool}` -> `{username, must_change_password}`; 403 non-admin
- `GET /api/users/{user}/profile` -> now includes `must_change_password: bool`

## Functional Test Harness

A standing functional regression harness that boots the built hub image in a fully isolated throwaway compose deployment and drives the running platform end-to-end (UI actions + multi-step scenarios) with a containerized Playwright runner. Purpose: validate future fundamental rebuilds; local-only (GitHub cannot run the DockerSpawner deployment); removes everything it creates on completion.

Legend: `[x]` implemented, `[ ]` planned (the test/scenario backlog). Each item is one functional test unless noted. Items needing the real `stellars-jupyterlab-ds` lab image (not the minimal singleuser one) are tagged `(real-lab)` and are out of scope for the default minimal run.

> 2026-06-18 SPA rebuild: the old `test_hub_ui` / `test_scenarios` drove the stock JupyterHub HTML (`#groups-table-body`, Bootstrap modals), dead against the React portal. The harness now drives the live SPA (visible text / antd `aria-label` / placeholders - no data-testids), authenticates by injecting the API session's hub cookies (a direct `/hub/login` self-redirects), and waits on the `.ant-layout` shell not `networkidle`. `make test-functional-all` (22 tests) green across all three setups on a GPU host.

### Setups (initial conditions, run one by one)

- [x] **Sequential multi-setup runner** - `make test-functional-all` boots each setup, runs its regime, cleans, moves to the next, and reports which passed (non-zero exit if any failed)
  - log: 2026-06-18 implemented (Makefile loop over signup / env / signup-open)
- [x] **Setup: signup-bootstrap** - fresh DB, signup off; admin via the bootstrap-signup window; runs the full SPA UI suite + container policy + GPU (when present)
  - log: 2026-06-18 18 passed (incl. GPU auto-detect: 3 GPUs)
- [x] **Setup: env-password admin** - signup off + `JUPYTERHUB_ADMIN_PASSWORD`, restart-to-provision; one focused login test
  - log: 2026-06-18 2 passed
- [x] **Setup: signup-open** - signup enabled, admin env-provisioned; a non-admin self-signs-up and the admin authorises via the SPA Users page
  - log: 2026-06-18 2 passed (`FUNCTEST_AUTH_MODE=signupopen`)
- [x] **Regime gating** - a conftest collection hook deselects (never skips) tests outside the run's regime, keyed off `FUNCTEST_AUTH_MODE` + GPU presence
  - log: 2026-06-18 signup / env / signupopen / gpu markers
- [x] **Coverage declaration + report** - every functional test declares the acc-crit it covers via `@pytest.mark.acc_crit("<doc-slug>::<label>", ...)`; a collected test with no declaration aborts the run, and the suite prints a `MET`/`UNMET` coverage report per criterion at conclusion
  - log: 2026-06-18 implemented (conftest `pytest_collection_modifyitems` enforcement + `pytest_terminal_summary` report; verified by collect-only across all three regimes)

### Harness infrastructure

- [x] **Isolated project** - runs under its own compose project `stellars-functest`, never the operator's
  - log: 2026-06-13 implemented
- [x] **Isolated network** - `stellars-functest_network`; spawned labs join only this network
  - log: 2026-06-13 implemented
- [x] **Namespaced volumes** - project-prefixed volumes; no shared `jupyterhub_*` names
  - log: 2026-06-13 implemented
- [x] **Dedicated admin** - `functestadmin`, distinct from any real `admin`
  - log: 2026-06-13 implemented
- [x] **No host port** - containerized runner reaches the hub by service name; operator `:8000` never bound
  - log: 2026-06-13 implemented
- [x] **Containerized runner** - Playwright runs in `mcr.microsoft.com/playwright/python`; no host browser deps
  - log: 2026-06-13 implemented
- [x] **Minimal spawn image** - `quay.io/jupyterhub/singleuser` pulled for spawn; hub image left intact
  - log: 2026-06-13 implemented
- [x] **Health gate** - runner waits on the HTTP health endpoint before tests (not the buggy compose pgrep healthcheck)
  - log: 2026-06-13 implemented
- [x] **Complete teardown** - on pass or fail, removes containers, spawned labs, network, all volumes, and pulled test images
  - log: 2026-06-13 implemented
- [x] **Idempotent clean target** - `make test-functional-clean` force-removes a leftover harness safely
  - log: 2026-06-13 implemented
- [x] **CI split** - pytest unit suites run as a GitHub `unit_tests` job; the harness is never wired into CI
  - log: 2026-06-13 implemented
- [ ] **Run isolation** - parallel/repeat runs do not collide (unique project suffix per run)
  - log: 2026-06-13 planned
- [ ] **Diagnostics on failure** - capture hub logs + Playwright trace/screenshot artifacts on failure
  - log: 2026-06-13 planned
- [ ] **Edge: interrupted run** - Ctrl-C / killed run still leaves zero trace (trap-based teardown)
  - log: 2026-06-13 planned
- [ ] **Edge: stale harness present** - a prior leftover deployment is cleaned before a new run starts
  - log: 2026-06-13 planned

### Fixtures

- [x] **base_url / admin_creds** - session fixtures from env
  - log: 2026-06-13 implemented
- [x] **admin_page / admin_portal** - admin page authenticated by injecting the `admin_api` session's hub cookies (no flaky form login); `admin_portal` wraps it with SPA navigation (`goto(route)` + `.ant-layout` ready wait)
  - log: 2026-06-13 implemented; 2026-06-18 reworked to cookie injection + SPA `Portal` helper
- [x] **clean_groups** - autouse fixture wiping all groups before/after each test (API), so tests are independent
  - log: 2026-06-13 implemented
- [x] **admin_api** - logged-in requests session for API-level setup/teardown
  - log: 2026-06-13 implemented
- [x] **signup_user** - factory that self-signs-up an arbitrary user via the NativeAuth form (the signup-open pending user)
  - log: 2026-06-18 implemented
- [ ] **seeded_groups** - fixture pre-creating a known set of groups for scenarios
  - log: 2026-06-13 planned
- [ ] **seeded_users** - fixture pre-creating non-admin users with set memberships
  - log: 2026-06-13 planned
- [ ] **api_client** - authenticated requests session for API-level assertions alongside the UI
  - log: 2026-06-13 planned

### Auth & bootstrap

- [x] **Login shell served** - `/hub/login` serves the SPA auth shell (`window.jhdata.authPage = "login"`), which renders the antd sign-in screen; the form login itself is exercised end-to-end by the `admin_api` fixture
  - log: 2026-06-13 implemented; 2026-06-18 reworked - the antd inputs use `id` not `name` and a direct `/hub/login` GET self-redirects, so render is asserted via the served shell
- [x] **Signup bootstrap window** - on a fresh DB (signup off, no env password) the first admin is created by signing up, then authenticates and reaches the hub
  - log: 2026-06-13 implemented (the harness default; env-password bootstrap cannot seed on a single fresh boot)
- [x] **Admin reaches the portal** - the authenticated admin loads the SPA app shell (`.ant-layout`), not bounced to login
  - log: 2026-06-18 implemented (`test_admin_reaches_portal`, cookie-injected session)
- [x] **Admin env-password login (mode 2)** - signup disabled + JUPYTERHUB_ADMIN_PASSWORD; `make test-functional-env` does the restart-to-provision and runs ONE focused test (`test_auth_env_mode`: env admin reaches the portal + signup form not served), not a full-suite re-run
  - log: 2026-06-13 implemented; 2026-06-18 strengthened to load the portal (was a trivial URL check)
- [x] **Signup enabled/disabled** - signup form present iff `JUPYTERHUB_SIGNUP_ENABLED=1`
  - log: 2026-06-18 implemented (`test_signup_form_served`, signup-open regime)
- [x] **Non-admin needs authorization** - a self-signed user lands in the pending queue (`is_authorized=False`), not authorised
  - log: 2026-06-18 implemented (signup-open: `signup_user` -> pending section)
- [x] **Admin authorizes user** - admin authorises a pending user through the SPA Users page; the pending queue empties and the backend reports `is_authorized=true`
  - log: 2026-06-18 implemented (`test_self_signup_then_admin_authorises`)
- [ ] **Logout** - logout returns to login and clears the session
  - log: 2026-06-13 planned
- [ ] **Wrong password rejected** - invalid login shows an error, no session
  - log: 2026-06-13 planned
- [ ] **Edge: failed-login lockout** - N failed attempts locks the account for the window
  - log: 2026-06-13 planned
- [ ] **Edge: admin password change ignores env** - after UI password change, env password no longer logs in
  - log: 2026-06-13 planned

### Hub pages & navigation

- [x] **SPA page-render smoke** - every major SPA screen mounts and shows its signature control: dashboard ("Active servers"), servers (user filter), users ("Inactive" pill), groups ("Add group"), events ("Clear log"), notifications ("Send broadcast"), settings ("Full reference"), lab setup ("Lab image"), design language
  - log: 2026-06-18 implemented (`test_hub_ui.py`, 9 page renders via SPA selectors)
- [x] **Groups page renders** - "Add group" button visible (SPA)
  - log: 2026-06-13 implemented; 2026-06-18 reworked to the SPA Groups page
- [x] **Settings / Notifications render** - signature controls visible (SPA)
  - log: 2026-06-13 implemented; 2026-06-18 reworked to SPA
- [ ] **Activity** - activity is folded into the dashboard / servers meters; there is no standalone `/activity` SPA page (the old 200-check is retired)
  - log: 2026-06-18 retired - covered indirectly by the dashboard/servers renders
- [ ] **Admin home renders** - admin home lists users + server controls
  - log: 2026-06-13 planned
- [ ] **Token page renders** - /hub/token page loads, can request a token
  - log: 2026-06-13 planned
- [ ] **Non-admin denied admin pages** - a non-admin user gets 403 on groups/settings/activity/notifications
  - log: 2026-06-13 planned
- [ ] **Nav links** - admin nav exposes the custom pages and they are reachable
  - log: 2026-06-13 planned

### Branding - hub

- [ ] **Custom logo** - `JUPYTERHUB_BRANDING_LOGO_URI` logo renders on hub login/home
  - log: 2026-06-13 planned
- [ ] **Custom favicon** - `JUPYTERHUB_BRANDING_FAVICON_URI` favicon served on hub pages
  - log: 2026-06-13 planned
- [ ] **file:// logo/favicon** - a `file://` URI is copied to the static dir and served
  - log: 2026-06-13 planned
- [ ] **External URL logo/favicon** - an `http(s)://` URI is passed through
  - log: 2026-06-13 planned
- [ ] **Default branding** - empty branding env yields stock JupyterHub assets
  - log: 2026-06-13 planned
- [ ] **Favicon CHP proxy route (real-lab)** - a lab session's favicon request routes back to the hub's custom favicon
  - log: 2026-06-13 planned

### Branding - lab container (injected env, asserted via docker inspect)

- [ ] **Main icon injected** - `JUPYTERLAB_MAIN_ICON_URI` present in the spawned container Env (file:// resolved to a hub static URL, else the URL passed through)
  - log: 2026-06-13 planned
- [ ] **Splash icon injected** - `JUPYTERLAB_SPLASH_ICON_URI` present in the container Env
  - log: 2026-06-13 planned
- [ ] **Busy favicon injected** - `JUPYTERHUB_BRANDING_FAVICON_BUSY_URI` resolved and reaches the lab
  - log: 2026-06-13 planned
- [ ] **System name rebrand** - `JUPYTERLAB_SYSTEM_NAME` injected into the container Env
  - log: 2026-06-13 planned
- [ ] **System name capitalize / color** - `JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME` and `JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR` injected
  - log: 2026-06-13 planned
- [ ] **Empty = no rebrand** - empty branding env leaves the lab env unset (no rebrand)
  - log: 2026-06-13 planned
- [ ] **Visual rebrand (real-lab)** - welcome page / MOTD / toolbar header badge reflect the system name
  - log: 2026-06-13 planned
- [ ] **Visual icons (real-lab)** - the lab shows the custom main/splash icons and busy favicon frames
  - log: 2026-06-13 planned

### Groups - management

- [x] **Create group** - "Add group" -> the NewGroup form -> Create -> the row appears on /groups
  - log: 2026-06-13 implemented; 2026-06-18 reworked to the SPA create flow (`test_group_create_badge_delete`)
- [x] **Name opens config** - the group-name link routes to `/groups/:name` (SPA, no modal)
  - log: 2026-06-13 implemented; 2026-06-18 SPA link
- [x] **Delete group** - the danger delete icon removes the row directly (no confirm modal in the SPA)
  - log: 2026-06-13 implemented; 2026-06-18 reworked to the SPA delete icon
- [x] **Reorder priority** - the move-up icon reorders the row above its neighbour (optimistic)
  - log: 2026-06-13 implemented; 2026-06-18 reworked to the SPA move-up action (`test_priority_reorder`)
- [ ] **Move down** - move-down reorders below its neighbour
  - log: 2026-06-13 planned
- [ ] **Priority persists** - reordered priority survives a page reload
  - log: 2026-06-13 planned
- [ ] **Description** - group description saves and displays
  - log: 2026-06-13 planned
- [ ] **Edit existing group** - reopening a saved group shows its persisted config
  - log: 2026-06-13 planned
- [ ] **Empty state** - no groups shows the "Add Group" empty message
  - log: 2026-06-13 planned
- [ ] **Edge: duplicate name** - creating a duplicate group name is rejected
  - log: 2026-06-13 planned
- [ ] **Edge: invalid name** - name not matching the pattern is rejected with a message
  - log: 2026-06-13 planned
- [ ] **Edge: cancel modal** - cancelling the add/config modal makes no change
  - log: 2026-06-13 planned

### Groups - membership

- [ ] **Add member** - chip-input adds a user to a group
  - log: 2026-06-13 planned
- [ ] **Remove member** - removing a chip removes membership
  - log: 2026-06-13 planned
- [ ] **Member count** - the row member count reflects membership
  - log: 2026-06-13 planned
- [ ] **Members tooltip** - hovering the count lists members
  - log: 2026-06-13 planned
- [ ] **Edge: unknown user** - adding a non-existent user is handled gracefully
  - log: 2026-06-13 planned
- [ ] **Edge: rename sync** - renaming a user in the admin panel keeps group membership
  - log: 2026-06-13 planned

### Policy config - per type (save + reopen + persist for each)

- [x] **Sudo** - enable section, member-sudo on/off; persists
  - log: 2026-06-13 implemented
- [x] **Downloads** - enable section, allow/block; persists
  - log: 2026-06-13 implemented
- [x] **Memory** - enable cap, set GB; persists
  - log: 2026-06-13 implemented
- [ ] **Memory swap** - swap-disabled toggle persists
  - log: 2026-06-13 planned
- [ ] **CPU** - enable cap, set cores; persists
  - log: 2026-06-13 planned
- [ ] **GPU all** - enable access, all-GPUs; persists
  - log: 2026-06-13 planned
- [ ] **GPU specific** - enable access, specific device ids; persists
  - log: 2026-06-13 planned
- [ ] **Env vars add** - enable section, add a var; persists
  - log: 2026-06-13 planned
- [ ] **Env vars remove** - remove a var row; persists
  - log: 2026-06-13 planned
- [ ] **Docker raw** - enable section, raw-socket access; persists
  - log: 2026-06-13 planned
- [ ] **Docker limited** - limited access + quotas (containers/volumes/networks/storage/cpu/mem); persists
  - log: 2026-06-13 planned
- [ ] **Docker dangerous flags** - allow-dangerous toggle persists with warning
  - log: 2026-06-13 planned
- [ ] **Docker compose project** - per-user compose-project enable + allow-override persist
  - log: 2026-06-13 planned
- [ ] **Docker hub-network** - hub-network-access toggle persists
  - log: 2026-06-13 planned
- [ ] **Docker privileged** - privileged toggle persists with warning
  - log: 2026-06-13 planned
- [ ] **API keys pair** - pair mode, id/secret var names + credentials; persists masked
  - log: 2026-06-13 planned
- [ ] **API keys single** - single mode, key var + credentials; persists masked
  - log: 2026-06-13 planned
- [ ] **Volume mounts** - add a volume->mountpoint; persists
  - log: 2026-06-13 planned
- [ ] **Section fold/unfold** - toggling a section active flag shows/hides its body
  - log: 2026-06-13 planned

### Policy config - validation (save rejected with message)

- [ ] **Reserved env var** - a reserved name (e.g. PATH / JUPYTERHUB_*) is rejected, `#config-error` shown
  - log: 2026-06-13 planned
- [ ] **Reserved api-keys target** - reserved pool target var rejected
  - log: 2026-06-13 planned
- [ ] **GPU incoherent** - access on, not-all, no device ids -> rejected
  - log: 2026-06-13 planned
- [ ] **Docker mutual exclusivity** - raw + limited in one group -> rejected
  - log: 2026-06-13 planned
- [ ] **Docker negative quota** - negative quota -> rejected
  - log: 2026-06-13 planned
- [ ] **Mem/CPU zero-when-enabled** - enabled with zero/blank value -> rejected
  - log: 2026-06-13 planned
- [ ] **Volume protected mountpoint** - mounting over /etc, /home etc. -> rejected
  - log: 2026-06-13 planned
- [ ] **Volume duplicate** - duplicate mountpoint or volume -> rejected
  - log: 2026-06-13 planned
- [ ] **API keys incomplete** - enabled pool missing mode/var/credentials -> rejected
  - log: 2026-06-13 planned

### Policy display

- [x] **Badges from policy_summary** - after an API config change the SPA row renders the server-sourced policy tag(s) (`CappedTags`)
  - log: 2026-06-13 implemented; 2026-06-18 SPA assertion (`test_group_create_badge_delete`, `test_multi_policy_badges`)
- [x] **No badges when inactive** - a group with no active policy shows the empty marker (no `.ant-tag`)
  - log: 2026-06-18 implemented (asserted before the first policy is set)
- [x] **Multiple badges** - a group with three active policies renders >= 3 inline tags (cap 4)
  - log: 2026-06-18 implemented (`test_multi_policy_badges`)
- [ ] **Hover tooltip** - the tag detail tooltip lists the valued policy line (hover; not asserted)
  - log: 2026-06-13 implemented (stock UI); 2026-06-18 the SPA tooltip is hover-only, not yet asserted
- [ ] **Badge per type** - each policy type shows its expected badge text
  - log: 2026-06-13 planned

### Policy resolution scenarios (multi-group)

- [ ] **Priority-wins (sudo/downloads)** - higher-priority configuring group wins (real-lab spawn assert)
  - log: 2026-06-13 planned
- [ ] **Biggest-wins (mem/cpu)** - largest enabled cap wins across groups
  - log: 2026-06-13 planned
- [ ] **OR-grant (gpu/docker)** - any granting group grants
  - log: 2026-06-13 planned
- [ ] **Section-off ignored** - an inactive section does not configure
  - log: 2026-06-13 planned
- [ ] **Env precedence** - higher-priority group env var wins; pool var vs plain var precedence
  - log: 2026-06-13 planned
- [ ] **Volume union** - mounts union across groups; conflict priority-wins
  - log: 2026-06-13 planned

### Spawn & lab lifecycle

- [x] **Spawn creates the container** - starting a server creates `jupyterlab-functestadmin`, inspected for policy effects (test_container_policy); the lab UI itself does not load under the minimal image, so no separate always-skip smoke
  - log: 2026-06-13 implemented (replaced the always-skip spawn smoke)
- [ ] **Spawn with overlay** - spawn-config overlay makes the minimal image spawn reliably
  - log: 2026-06-13 planned
- [ ] **Stop server** - stop returns to a stopped state
  - log: 2026-06-13 planned
- [ ] **Restart server** - one-click restart preserves the container
  - log: 2026-06-13 planned
- [ ] **Sudo applied (real-lab)** - resolved sudo reaches the lab as JUPYTERLAB_SUDO_ENABLE
  - log: 2026-06-13 planned
- [ ] **Env applied (real-lab)** - group env vars present in the lab environment
  - log: 2026-06-13 planned
- [ ] **Volume mounted (real-lab)** - group volume mounted at the configured path
  - log: 2026-06-13 planned
- [ ] **Edge: spawn failure surfaces** - an un-spawnable image shows a spawn error, not a hang
  - log: 2026-06-13 planned

### Spawned container - end-to-end policy application (docker inspect/exec)

The resolved policy *is* the container's create-time config (Env / Mounts /
HostConfig), set by DockerSpawner before the app starts - so these are
inspectable via the host docker socket regardless of the lab image.

- [x] **Container created** - spawning a member of a configured group creates `jupyterlab-<user>` (running)
  - log: 2026-06-13 planned; done (test_container_policy)
- [x] **Env: sudo** - container Env has `JUPYTERLAB_SUDO_ENABLE=<resolved>`
  - log: 2026-06-13 planned; done (test_container_policy)
- [x] **Env: group vars** - configured group env vars present in container Env
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **Env: reserved stripped** - reserved names never injected
  - log: 2026-06-13 planned
- [ ] **Env: GPU flags** - `ENABLE_GPU_SUPPORT` / `NVIDIA_VISIBLE_DEVICES` / `CUDA_VISIBLE_DEVICES` match the gpu policy
  - log: 2026-06-13 planned
- [ ] **Env: api-keys** - pool target vars present; two running containers never hold the same credential
  - log: 2026-06-13 planned
- [x] **Mounts: group volume** - the configured volume -> mountpoint appears in Mounts
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **Mounts: per-user volumes** - home/workspace/cache mounted
  - log: 2026-06-13 planned
- [ ] **Mounts: docker socket** - raw access mounts `/var/run/docker.sock`; limited mounts the proxy subpath + sets `DOCKER_HOST`
  - log: 2026-06-13 planned
- [x] **Limit: memory** - `HostConfig.Memory == cap` bytes; `MemorySwap` per swap policy
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **Limit: cpu** - `NanoCpus` / `CpuQuota` == ceil(cores)
  - log: 2026-06-13 planned
- [ ] **Privileged** - `HostConfig.Privileged` true only when granted
  - log: 2026-06-13 planned
- [ ] **Network** - attached to the test network; limited-docker hub-network visibility per flag
  - log: 2026-06-13 planned
- [x] **Labels: compose project** - `com.docker.compose.project` stamped on the lab
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **Labels: api-keys slot** - durable slot label present per pool
  - log: 2026-06-13 planned
- [ ] **Exec: sudo reality** - `exec` confirms sudo availability matches the policy
  - log: 2026-06-13 planned
- [ ] **Exec: mountpoint reality** - `exec` confirms the group mountpoint exists / is writable
  - log: 2026-06-13 planned
- [ ] **Negative: no group** - a member of no group gets defaults (no extra mounts, default sudo)
  - log: 2026-06-13 planned
- [ ] **Edge: leaving a group unmounts** - re-spawn after removal drops the group volume
  - log: 2026-06-13 planned

### Group policy -> container effect matrix (configured value -> asserted on the spawned container)

The core of the harness: for each policy value an admin can set on a group, spawn a member and assert the concrete effect on the container (via `docker inspect`/`exec`). Positive, negative, and boundary values each get a test.

- [ ] **sudo on** -> `JUPYTERLAB_SUDO_ENABLE=1` in Env
  - log: 2026-06-13 planned
- [x] **sudo off** -> `JUPYTERLAB_SUDO_ENABLE=0`
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **sudo unconfigured** -> platform default value
  - log: 2026-06-13 planned
- [x] **mem 4G** -> `HostConfig.Memory == 4*1024^3`
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **mem 4G + no-swap** -> `MemorySwap == Memory`
  - log: 2026-06-13 planned
- [ ] **mem disabled** -> no memory limit
  - log: 2026-06-13 planned
- [ ] **cpu 2** -> `NanoCpus == 2e9` (or CpuQuota/Period)
  - log: 2026-06-13 planned
- [ ] **cpu 2.5** -> ceil to 3 cores
  - log: 2026-06-13 planned
- [ ] **gpu all (gpu host)** -> `device_requests` Count -1, `NVIDIA_VISIBLE_DEVICES=all`
  - log: 2026-06-13 planned
- [ ] **gpu specific [0,2]** -> DeviceIDs [0,2], `NVIDIA_VISIBLE_DEVICES=0,2`, CUDA by uuid
  - log: 2026-06-13 planned
- [ ] **gpu none** -> `NVIDIA_VISIBLE_DEVICES=void`, no device_requests
  - log: 2026-06-13 planned
- [x] **env FOO=bar** -> `FOO=bar` in Env
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **env reserved (PATH)** -> not injected
  - log: 2026-06-13 planned
- [ ] **docker raw** -> `/var/run/docker.sock` mounted, no DOCKER_HOST
  - log: 2026-06-13 planned
- [ ] **docker limited** -> `DOCKER_HOST` set, proxy subpath mount, no raw socket
  - log: 2026-06-13 planned
- [ ] **docker privileged** -> `HostConfig.Privileged=true`
  - log: 2026-06-13 planned
- [x] **volume vol->/mnt/x** -> Mounts contains the named volume at /mnt/x
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **api-keys pool** -> target var(s) set, durable slot label present
  - log: 2026-06-13 planned
- [ ] **downloads block** -> per-user CHP block routes registered (lab-extension effect out of scope minimal)
  - log: 2026-06-13 planned

#### Combinations + multi-group resolution (asserted on the container)

- [ ] **All-policies group** -> one spawn reflects sudo+env+mem+cpu+gpu+docker+volumes+api-keys simultaneously
  - log: 2026-06-13 planned
- [ ] **Priority-wins** -> two groups configuring sudo/downloads: the higher-priority value lands in the container
  - log: 2026-06-13 planned
- [ ] **Biggest-wins** -> two groups capping mem/cpu: the larger cap lands in the container
  - log: 2026-06-13 planned
- [ ] **OR-grant** -> two groups, only one grants gpu/docker: the grant lands
  - log: 2026-06-13 planned
- [ ] **Section toggled off** -> turning a section off then re-spawning drops that effect from the container
  - log: 2026-06-13 planned
- [ ] **Membership change** -> adding/removing the user from a group changes the next spawn's container config
  - log: 2026-06-13 planned

### Server lifecycle control

- [ ] **Spawn via UI** - start server from the UI
  - log: 2026-06-13 planned
- [ ] **Spawn via API** - start server via the API
  - log: 2026-06-13 planned
- [ ] **Stop** - stop removes the container
  - log: 2026-06-13 planned
- [ ] **Restart preserves container** - restart keeps the same container (no recreate)
  - log: 2026-06-13 planned
- [ ] **Concurrent users** - two users spawn distinct containers
  - log: 2026-06-13 planned
- [ ] **Edge: re-spawn picks up new policy** - changing the group then re-spawning re-applies config
  - log: 2026-06-13 planned

### Idle culling

- [ ] **Idle culled** - an idle server is stopped after a short test timeout
  - log: 2026-06-13 planned
- [ ] **Active not culled** - an active server survives the interval
  - log: 2026-06-13 planned
- [ ] **Extension delays cull** - a granted extension delays culling
  - log: 2026-06-13 planned
- [ ] **Culled container removed** - the lab container is gone after culling
  - log: 2026-06-13 planned

### Logs

- [ ] **Resolution log** - the hub log shows the per-spawn groups/policy resolution line
  - log: 2026-06-13 planned
- [ ] **Policy apply logs** - api-keys assignment / docker-proxy / downloads-route lines appear per policy
  - log: 2026-06-13 planned
- [ ] **Spawn failure logged** - a failed spawn logs the cause
  - log: 2026-06-13 planned
- [ ] **Lab logs retrievable** - the spawned container logs are fetchable and show startup
  - log: 2026-06-13 planned

### Activity reporting

- [ ] **Active server reported** - a running server appears in activity data within the sample interval
  - log: 2026-06-13 planned
- [ ] **Resource stats** - CPU/memory for the running lab report back to the hub
  - log: 2026-06-13 planned
- [ ] **Stopped drops out** - a stopped server leaves the active set
  - log: 2026-06-13 planned
- [ ] **Manual sample** - a manual sample updates the data immediately
  - log: 2026-06-13 planned

### Limits enforcement (real effect)

- [ ] **Memory OOM** - in-container stress beyond the cap is OOM-limited
  - log: 2026-06-13 planned
- [ ] **CPU throttle** - in-container CPU beyond the cap is throttled
  - log: 2026-06-13 planned
- [ ] **Volume quota warning** - exceeding the volume/container-size threshold raises the activity warning
  - log: 2026-06-13 planned

### GPU auto-detection (GPU host only)

- [x] **Auto-detect enables on GPU host** - `make test-functional` auto-detects a host GPU, sets `JUPYTERHUB_GPU_ENABLED=2`, and the test asserts the hub `[GPU debug]` line reports `detected=1 enabled=1` with GPUs enumerated
  - log: 2026-06-13 implemented (runs for real on a GPU host)
- [x] **Deselected on CPU host** - no GPU -> the gpu test is deselected (not collected), no skip noise and no CUDA pull
  - log: 2026-06-13 implemented (conftest pytest_collection_modifyitems)
- [ ] **GPU policy spawn (GPU host)** - a gpu-access group member spawns with `device_requests` and `NVIDIA_VISIBLE_DEVICES` set
  - log: 2026-06-13 planned
- [ ] **Specific-GPU selection (GPU host)** - a device-id subset reaches the container env
  - log: 2026-06-13 planned

### Self-service

- [ ] **Manage volumes list** - the volume reset UI lists home/workspace/cache
  - log: 2026-06-13 planned
- [ ] **Manage volumes reset** - selected volume reset works (server stopped)
  - log: 2026-06-13 planned
- [ ] **Restart server (self)** - user restarts own running server
  - log: 2026-06-13 planned
- [ ] **Session extend** - idle session extend updates the remaining time
  - log: 2026-06-13 planned
- [ ] **Edge: manage volumes blocked while running** - reset refused while the server runs
  - log: 2026-06-13 planned

### Notifications broadcast

- [ ] **Page renders form** - message field, type selector, auto-close toggle
  - log: 2026-06-13 planned
- [ ] **Char limit** - 140-char limit + live counter
  - log: 2026-06-13 planned
- [ ] **Broadcast no servers** - sending with no active servers reports zero deliveries
  - log: 2026-06-13 planned
- [ ] **Broadcast delivery (real-lab)** - active lab with the extension receives the toast; per-user status shown
  - log: 2026-06-13 planned
- [ ] **Edge: extension missing** - server without the extension reports "not installed"
  - log: 2026-06-13 planned

### Settings

- [ ] **Settings list** - settings render from the dictionary
  - log: 2026-06-13 planned
- [ ] **Edit setting** - changing a setting persists
  - log: 2026-06-13 planned
- [ ] **Hidden secrets** - admin-password-style settings absent from the page
  - log: 2026-06-13 planned

### Activity monitor

- [ ] **Activity data** - the activity page shows user rows / data
  - log: 2026-06-13 planned
- [ ] **Resource stats** - CPU/memory/status columns populate
  - log: 2026-06-13 planned
- [ ] **Reset** - reset clears activity samples
  - log: 2026-06-13 planned
- [ ] **Manual sample** - trigger a sample updates the data
  - log: 2026-06-13 planned

### Lab-extension features (real-lab; out of scope for the minimal run)

- [ ] **Download blocked** - a download-blocked user gets 403 on the download surfaces
  - log: 2026-06-13 planned
- [ ] **Download toast** - a blocked attempt pushes a notification toast
  - log: 2026-06-13 planned
- [ ] **Download allowed** - an allowed user downloads normally
  - log: 2026-06-13 planned
- [ ] **Favicon proxy** - custom favicon served through the per-user CHP route
  - log: 2026-06-13 planned
- [ ] **Inline view allowed** - inline image/media still served to a blocked user
  - log: 2026-06-13 planned

### Abuse protection & ops

- [x] **Health endpoint** - /hub/health returns 200 JSON
  - log: 2026-06-13 implemented
- [ ] **Rate limit** - exceeding the ingress rate returns 429 (needs Traefik; out of scope minimal)
  - log: 2026-06-13 planned
- [ ] **Concurrent spawn limit** - spawn-storm protection caps simultaneous spawns
  - log: 2026-06-13 planned
- [ ] **Idle culler** - an idle server is culled after the timeout
  - log: 2026-06-13 planned

### Teardown verification

- [x] **No containers left** - after a run, no `stellars-functest` or spawned `jupyterlab-functestadmin` containers remain
  - log: 2026-06-13 implemented
- [x] **No network left** - `stellars-functest_network` removed
  - log: 2026-06-13 implemented
- [x] **No volumes left** - project + spawned per-user volumes removed
  - log: 2026-06-13 implemented
- [x] **Pulled images removed** - singleuser + Playwright images removed (unless KEEP_IMAGES)
  - log: 2026-06-13 implemented
- [x] **Hub image intact** - the image under test is not removed
  - log: 2026-06-13 implemented
- [ ] **Teardown asserted in-suite** - a final check confirms zero trace (or a separate verify step)
  - log: 2026-06-13 planned

### API (endpoints the harness exercises)

- `GET /hub/health` -> 200 JSON (unauthenticated)
- `GET /hub/api/admin/groups` -> groups list + `policy_summary`
- `POST /hub/api/admin/groups/create` -> create
- `PUT /hub/api/admin/groups/{name}/config` -> save policy; 400 on reserved/invalid
- `POST /hub/api/admin/groups/reorder` -> priority
- `DELETE /hub/api/admin/groups/{name}/delete` -> delete
- `POST /hub/api/notifications/broadcast` -> broadcast; `GET /hub/api/notifications/active-servers`
- `DELETE /hub/api/users/{name}/manage-volumes`; `POST /hub/api/users/{name}/restart-server`

## Functional UI Sweep

Completeness gates for `docs/portal-ui-catalogue.md`, the hub-portal inventory feeding a future rebuild. These criteria do not test the running portal; they assert the catalogue itself is complete and at the right fidelity - every hub screen mapped to its actions, capabilities, conditionals, messages, navigation, dynamic behaviour and API, with no JupyterLab UI and no CSS/DOM detail.

### Scope gates

- [x] **Hub only** - catalogue covers hub-served screens; no JupyterLab in-session UI
  - log: 2026-06-14 added, satisfied (catalogue Coverage map lists hub screens, lab out of scope)
- [x] **Functional fidelity** - entries describe routes, actions, endpoints, states; no CSS selectors, class names or DOM structure
  - log: 2026-06-14 added, satisfied (CSS/DOM-level agent output stripped during synthesis)
- [x] **Single source** - one master doc, one section per screen plus a shared global-layer section
  - log: 2026-06-14 added, satisfied
- [x] **Provenance** - catalogue names the source files (templates, handlers, config) it was built from
  - log: 2026-06-14 added, satisfied

### Per-screen completeness

Every screen section must carry, where applicable: route, purpose, actions (+ target endpoint), inputs/validation, conditionals (role/state gating), messages, navigation, modals, dynamic behaviour, API. A label is omitted only when genuinely N/A.

- [x] **Route present** - each screen states its URL path(s)
  - log: 2026-06-14 added, satisfied
- [x] **Actions enumerated** - every button/link/form submit listed with what it does and the endpoint it hits
  - log: 2026-06-14 added, satisfied
- [x] **Inputs + validation** - form fields, limits and validation rules captured (char limits, name regex, reserved/protected rejections)
  - log: 2026-06-14 added, satisfied
- [x] **Conditionals** - role gating (admin vs user vs anon) and state gating (server running/stopped/pending, bootstrap window) captured per screen
  - log: 2026-06-14 added, satisfied
- [x] **Messages** - error/success/info text and the trigger condition captured
  - log: 2026-06-14 added, satisfied
- [x] **Navigation** - outbound links per screen captured
  - log: 2026-06-14 added, satisfied
- [x] **Modals** - confirmation/config dialogs and what they guard captured
  - log: 2026-06-14 added, satisfied
- [x] **Dynamic behaviour** - JS-driven polling, timers, redirects, auto-close, spinners, live counters captured
  - log: 2026-06-14 added, satisfied
- [x] **API** - method, path, payload shape and error codes captured for screens that call endpoints
  - log: 2026-06-14 added, satisfied

### Screen inventory (every hub screen accounted for)

- [x] **Auth + landing** - login, native-login, signup, logout, change-password, change-password-admin, authorization-area, oauth, accept-share, error, 404, message, token
  - log: 2026-06-14 added, satisfied
- [x] **Spawn + home + self-service** - home, named-servers, manage-volumes, restart, extend-session, spawn, spawn_pending, stop_pending, not_running
  - log: 2026-06-14 added, satisfied
- [x] **Groups + policy** - groups page with layout regions, actions, all nine policy types, badges, tooltip, validation, persistence, API
  - log: 2026-06-14 added, satisfied
- [x] **Admin platform** - admin, settings, activity, notifications
  - log: 2026-06-14 added, satisfied
- [x] **Global layer** - page.html base, navigation map, branding, dark mode, mobile.js, session-timer.js, shared messaging
  - log: 2026-06-14 added, satisfied

### Capability depth gates

- [x] **Branding fully mapped** - every branding env var (logo, favicon, favicon-busy, lab main/splash icons, base url), file:// vs URL handling, and the favicon CHP proxy mechanism captured
  - log: 2026-06-14 added, satisfied
- [x] **Navigation role matrix** - which nav items each role sees (anonymous/user/admin) captured, not just the link list
  - log: 2026-06-14 added, satisfied
- [x] **Policy types complete** - all nine (env, gpu, docker, cpu, mem, sudo, downloads, api-keys, volume-mounts), each with config inputs, badge, tooltip detail, cross-group resolve rule and apply effect
  - log: 2026-06-14 added, satisfied
- [x] **Badge/tooltip provenance** - documented as server-computed `policy_summary` consumed verbatim by the client, not recomputed in the browser
  - log: 2026-06-14 added, satisfied
- [x] **Self-service flows** - manage-volumes, restart, extend-session each carry their poll loops, timeouts and reload behaviour
  - log: 2026-06-14 added, satisfied
- [x] **Spawn lifecycle** - spawn -> spawn_pending (EventSource + lab-ready fallback) -> not_running/stop_pending state machine captured
  - log: 2026-06-14 added, satisfied
- [x] **Bootstrap window** - first-admin signup-window behaviour and its gating env vars captured on the signup screen
  - log: 2026-06-14 added, satisfied

### Edge cases

- [x] **Edge: empty states** - no-groups, no-volumes-yet, no-active-servers, no-tokens captured as distinct UI states
  - log: 2026-06-14 added, satisfied
- [x] **Edge: failure paths** - spawn-failed (Relaunch), broadcast partial-failure, validation 400/409, restart timeout captured
  - log: 2026-06-14 added, satisfied
- [x] **Edge: external state drift** - home drift detector reloading on externally-stopped server, spawn-pending fallback poll on mid-spawn hub restart captured
  - log: 2026-06-14 added, satisfied
- [x] **Edge: admin-acting-for-user** - admin spawning/managing another user's server and volumes captured
  - log: 2026-06-14 added, satisfied
- [x] **Edge: mobile vs desktop divergence** - device-specific controls (mobile start/stop interception, status strip, card views, inline extend panel) captured where behaviour differs
  - log: 2026-06-14 added, satisfied
- [x] **Edge: one-time secrets** - token "you won't see it again" card and api-keys masked-on-read noted as non-recoverable display states
  - log: 2026-06-14 added, satisfied

### Sign-off

- [x] **No orphan screens** - every template in `html_templates_enhanced/*.html` maps to a catalogue section or is explicitly out of scope
  - log: 2026-06-14 added, satisfied (24 templates + 2 static JS accounted for in Coverage map)
- [x] **No orphan handlers** - custom page/API handlers referenced by a catalogued screen appear in that screen's API list
  - log: 2026-06-14 added, satisfied
- [ ] **Rebuild-ready** - a developer can rebuild any single screen from its section without reading the source
  - log: 2026-06-14 criterion added, pending owner review

## GPU Utilisation Cache Logging

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

## gpuinfo-nvidia sidecar (logging + graceful no-hardware)

The GPU-info sidecar logs its lifecycle so an operator can see it start, serve and what hardware it detected. A failure to start the container is an acceptable outcome - it means no NVIDIA hardware - and the hub degrades to GPU-off without stalling or alarming.

### Logging

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

### Graceful no-hardware (container fail = no GPU = OK)

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

### Lifecycle (tied to the hub)

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

## Group-Gated File Downloads

Best-effort, hub-side blocking of browser file downloads from spawned labs. Section-gated and priority-wins: a group whose File Downloads section (`downloads_active`) is on explicitly configures member downloads to allow or block (`downloads_allow`); among a user's configuring groups the highest-priority one wins; if no group configures it, the platform default `JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS` applies. For a blocked user, `pre_spawn_hook` overlays per-user CHP routes (favicon-route mechanism) onto the lab's download surfaces, sending them to hub guard handlers that 403 genuine downloads and reverse-proxy inline content. Every block fires a throttled "blocked by policy" toast and an audit log line. This is policy + notification + audit, NOT exfiltration prevention - the lab user is root with open egress, so a terminal/kernel transfer over an encrypted channel is out of reach by design.

### Platform setting

- [x] **Default policy** - `JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS` (`0`/`1`, default `0`) is the fallback applied only when no group configures downloads; dormant (no routes/handlers) when the default is allow AND no group configures it - zero change for existing deployments
  - log: 2026-06-12 implemented (v3.11.5) - read in `config/jupyterhub_config.py`, threaded into `make_pre_spawn_hook` and `schedule_startup_downloads_callback`
  - log: 2026-06-12 reworked to default-fallback (section-gated/priority-wins) - a configuring group overrides it and can block even when default is allow
- [x] **Settings page** - listed in `settings_dictionary.yml` (Abuse Protection category) so it shows on the admin Settings page
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Startup log** - hub prints the policy state (BLOCK/ALLOW) once at config load
  - log: 2026-06-12 implemented (v3.11.5)

### Group config (admin)

- [x] **Section** - foldable "File Downloads" section with header switch `config-downloads-active` (default off), following the `*_active` section pattern
  - log: 2026-06-12 implemented (v3.11.5) - `groups.html`
- [x] **Value control** - when the section is on, toggle `config-downloads-allow` chooses allow (1) or block (0) for members
  - log: 2026-06-12 added - `groups.html`
- [x] **Persistence** - `downloads_active: False`, `downloads_allow: True` in `default_config()`; section folded off persists data and restores on re-enable; legacy rows default off (no inference - section off = not configured)
  - log: 2026-06-12 implemented (v3.11.5) - `groups_config.py`
  - log: 2026-06-12 added `downloads_allow` value field
- [x] **API accept** - `GroupsConfigHandler.put` accepts boolean body keys `downloads_active` and `downloads_allow`
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Badge** - groups table shows `Downloads on` or `Downloads off` (reflecting the configured value) when `downloads_active` is on; no badge when the section is off
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Section-gated** - a group with `downloads_active` false does NOT configure downloads (its `downloads_allow` is ignored); only sections explicitly on are considered
  - log: 2026-06-12 added - `group_resolver.py`
- [x] **Priority-wins** - among configuring groups the highest-priority `downloads_allow` wins (priority-descending walk, first configuring group decides) - not OR, not biggest-wins
  - log: 2026-06-12 reworked from grant-style OR to section-gated priority-wins
- [x] **Resolved value** - `resolve_group_config` returns `downloads_allow` as `True`/`False` when some group configures it, else `None`; the hook applies the platform default when `None`
  - log: 2026-06-12 added - covered by `TestDownloadsAllow`
- [x] **No admin exemption** - admins follow the same resolution as any user (no implicit bypass)
  - log: 2026-06-12 implemented (v3.11.5) - confirmed with operator

### Enforcement (hub overlay)

- [x] **Vector inventory** - verified against the deployed image: block surfaces are `files/` (download / open-to-save), `nbconvert/` (download / open-to-save), `jupyterlab-export-markdown-extension/export/` (POST, always attachment), `jupyterlab-share-files-extension/public/share/` (GET, unauthenticated public link). Not vectors: export-svg-as-png (client-side), jupyterlab_zip (POST create only), jupyter-archive (absent)
  - log: 2026-06-12 implemented (v3.11.5) - probed inside the running container source
  - log: 2026-06-12 corrected - the JupyterLab Download button saves client-side via `<a download>` against `files/<path>` with NO `?download` arg, so jupyter_server serves it 200 inline and the browser writes it to disk - the query arg alone never fired (Playwright-confirmed as `konrad.jelen`)
- [x] **Route overlay** - for blocked users `pre_spawn_hook` registers one CHP route per surface to the hub, recorded in `app.proxy.extra_routes` so `check_routes()` does not reap them
  - log: 2026-06-12 implemented (v3.11.5) - `hooks.py` `_register_download_block`
- [x] **Survivor re-registration** - `schedule_startup_downloads_callback` re-applies block routes for labs still running after a hub restart
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Grant change removes routes** - a user resolved as allowed has any stale block routes deleted on next spawn (`_unregister_download_block`); symmetric add/remove
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Allowed = no overlay** - users resolved to allow get no routes; traffic flows browser -> CHP -> container with zero added hops
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Group blocks regardless of default** - a configuring group resolving to block overlays routes even when the platform default is allow; a group resolving to allow removes them even when the default is block
  - log: 2026-06-12 added - hook gates on `block_file_downloads or downloads_allow is not None`
- [x] **Pure-download block** - `DownloadBlockHandler` 403s the export-markdown and share-files prefixes unconditionally (no auth, so it also blocks the unauthenticated public share link); GET/POST/HEAD
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Download-intent block** - `FilesGuardHandler._is_download_request` 403s `files/`/`nbconvert/` when the request is a save / open vector: a truthy `?download` arg, OR `Sec-Fetch-Dest` of `empty` (fetch / `<a download>`), `document` (top-level navigation / open-in-tab), or absent (non-browser / plain-HTTP - fail-closed)
  - log: 2026-06-12 implemented (v3.11.5) - originally download-arg only
  - log: 2026-06-12 reworked to `Sec-Fetch-Dest` discriminator - empirically captured per vector via Playwright over HTTPS (img=image, fetch=empty, open-tab=document, `<a download>` saves with no arg); the query arg alone missed the Download button
- [x] **Inline pass-through** - `files/`/`nbconvert/` requests whose `Sec-Fetch-Dest` is an inline subresource render (`image`, `video`, `audio`, `font`, `style`, `script`, `object`, `embed`, `iframe`, `frame`, `track`, `manifest`) reverse-proxy to the container, forwarding the `Range` header and relaying status/headers/body (markdown/notebook images, embedded media, in-lab viewers keep working)
  - log: 2026-06-12 implemented (v3.11.5)
  - log: 2026-06-12 narrowed from "any non-download request" to the inline-dest allowlist
- [x] **Defense in depth** - if a proxied inline response unexpectedly carries `Content-Disposition: attachment`, it is converted to a 403 before any body reaches the client
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Owner isolation** - `FilesGuardHandler` is a plain `tornado.web.RequestHandler` (hub login cookie is scoped to `/hub/` and never reaches `/user/...`, so `@web.authenticated` there loops to login); isolation holds because the inline proxy forwards the request's `/user/{u}/` cookie to that user's own container and the browser only sends that cookie to the user's own prefix
  - log: 2026-06-12 implemented (v3.11.5) - was `@web.authenticated` owner-or-admin
  - log: 2026-06-12 reworked - `@web.authenticated` at `/user/...` caused an `ERR_TOO_MANY_REDIRECTS` login loop; switched to forwarded-cookie isolation
- [x] **Block response** - 403 with an HTML page for top-level navigation (Accept: text/html), JSON `{"error":"downloads_blocked"}` otherwise
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Audit log** - every block logs username, path, and the trigger (`via=pure-download|download-arg|sec-fetch-dest=<v>|attachment-header`)
  - log: 2026-06-12 implemented (v3.11.5)
  - log: 2026-06-12 added the `sec-fetch-dest=<v>` trigger

### Must not break

- [x] **Contents API untouched** - `/user/{u}/api/contents/*` never intercepted; browse, open, edit, save, rename, upload work for blocked users
  - log: 2026-06-12 implemented (v3.11.5) - not in the overlaid prefix set
- [x] **Kernels and terminals untouched** - `/api/kernels`, `/api/terminals`, websockets unaffected
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Lab UI untouched** - `/lab`, `/static/`, extension assets, settings/themes unaffected
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Export format listing untouched** - the `nbconvert` POST (inline render) and format metadata are not blocked; only download-arg GETs are
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Favicon overlay coexistence** - block routes and the favicon route coexist in `extra_routes` without prefix collision
  - log: 2026-06-12 implemented (v3.11.5)

### Notification

- [x] **Toast on block** - hub pushes a warning toast to the blocked user's lab via the notifications-extension ingest endpoint (temp 5-min token), naming the file
  - log: 2026-06-12 implemented (v3.11.5) - `notify_blocked` reuses the broadcast pattern
- [x] **Fire and forget** - notification is scheduled on the IO loop and never delays or alters the 403
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Throttle** - at most one toast per user per 10 s; further blocks in the window are counted and the next toast carries the aggregate ("N downloads blocked")
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Extension absent / server down** - block is still enforced; notify failure is logged and swallowed
  - log: 2026-06-12 implemented (v3.11.5)

### Lifecycle

- [x] **Group change** - adding/removing a user from a configuring group, or toggling `downloads_active`/`downloads_allow`, takes effect at the user's next server start
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Feature toggle** - flipping the platform default requires a hub restart; the survivor callback applies the new state to running labs (dormant default off + no configuring group -> `check_routes()` reaps leftover routes since they are no longer in `extra_routes`)
  - log: 2026-06-12 implemented (v3.11.5)

### Edge cases

- [x] **Edge: user in no groups** - no group configures -> platform default applies
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: configuring groups disagree** - highest-priority configuring group wins regardless of the others
  - log: 2026-06-12 added
- [x] **Edge: higher-priority section OFF, lower-priority ON** - the lower-priority group (the only one configuring) decides
  - log: 2026-06-12 added
- [x] **Edge: `?download=0` / falsy** - not treated as a download; passes through (`_is_download_arg`)
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: burst of blocked clicks** - one throttled toast, not a storm
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: default allow, no group configures** - no routes, no handlers; downloads work for everyone
  - log: 2026-06-12 implemented (v3.11.5)
- [ ] **Edge: group deleted while member's lab runs** - lab keeps spawn-time behaviour until restart, then re-resolves
  - log: 2026-06-12 criterion holds by construction (routes set at spawn / survivor callback); not separately tested

### Tests

- [x] **Resolver tests** - `TestDownloadsAllow`: no group configures -> None, section-off -> None, single allow/block, higher-priority wins, higher-off+lower-on decides, only-matched-groups-count
  - log: 2026-06-12 reworked to tri-state priority-wins - `tests/test_group_resolver.py`
- [x] **Discriminator tests** - `TestIsDownloadArg` / `TestIsDownloadRequest` / `TestFilenameFromPath` cover the block/allow decision and toast naming; `TestIsDownloadRequest` asserts inline dests allowed, empty/document/absent blocked, `?download` wins
  - log: 2026-06-12 implemented (v3.11.5) - `tests/test_downloads_guard.py`
  - log: 2026-06-12 added `TestIsDownloadRequest` for the `Sec-Fetch-Dest` discriminator (build-gated by the Dockerfile pytest step)
- [ ] **Live end-to-end** - post-rebuild probe as `konrad.jelen`: Download button (`<a download>`, no arg) -> 403 + toast + audit, `?download=1` -> 403, open-in-tab -> 403, inline markdown image -> 200 via proxy, export-markdown POST -> 403, granting group -> downloads succeed; contents API / kernels / terminals unaffected
  - log: 2026-06-12 pending operator-initiated hub rebuild (Playwright already confirmed the per-vector `Sec-Fetch-Dest` values the discriminator keys off)

### Documentation

- [x] **README** - Groups section documents the File Downloads switch, the allow/block value, the priority-wins/default-fallback rule, and the platform default env var; states it is browser-download policy with notification, not full DLP
  - log: 2026-06-12 implemented (v3.11.5)

### Out of scope

- Exfiltration via terminal/kernel egress, `git push`, the contents API, or any encrypted channel - structurally unblockable while the lab stays usable (root + sudo + needed egress)
- Upload blocking; per-path or per-filetype allowlists; named servers (one server per user here)

### API

- Blocked vectors (blocked users): `GET|HEAD /user/{u}/files/*` and `/nbconvert/*` when `?download` is truthy OR `Sec-Fetch-Dest` ∈ {`empty`, `document`, absent}, `POST /user/{u}/jupyterlab-export-markdown-extension/export/*`, `GET /user/{u}/jupyterlab-share-files-extension/public/share/*` -> `403` (HTML or `{"error":"downloads_blocked"}`); inline `files/`/`nbconvert/` with a media `Sec-Fetch-Dest` -> proxied 200/206
- `PUT /hub/api/admin/groups/{group}/config` body gains optional booleans `downloads_active`, `downloads_allow`
- Env: `JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS` (`0`/`1`, default `0`) - platform default when no group configures

## group policy import/export bundle shape

The group policy export/import bundle uses the hierarchy group -> policy[] -> members instead of one flat per-group `config` dict. Each policy is a named section carrying its own settings. The hub still stores and validates a single flat config, so this is purely the on-disk bundle shape, folded on export and unfolded on import.

- [x] **Folded export** - export emits `{groups:[{name, description, priority, policies:[{key, label, settings}]}]}`; each policy carries only the flat keys it owns
  - log: 2026-06-17 `toPolicies` in `lib/policyShape.ts`; `GroupsExport.tsx`
- [x] **Nine sections in backend order** - env_vars, gpu, docker, cpu, mem, sudo, downloads, api_keys, volume_mounts; key ownership matches the backend POLICY_TYPES
  - log: 2026-06-17 `SECTIONS` table
- [x] **Unfolded import** - import merges every section's `settings` back into the flat config the hub PUTs
  - log: 2026-06-17 `fromPolicies`; `Groups.tsx` import maps `policies` -> `config`
- [x] **Round-trips** - an exported bundle re-imports through the same flat config the editor PUTs (hub coerces + validates)
  - log: 2026-06-17 fold/unfold are inverse over the owned keys
- [x] **Legacy bundles still import** - a file with a flat `config` (older export) is still accepted
  - log: 2026-06-17 import uses `policies` when present, else `config`
- [x] **Edge: malformed file** - non-JSON / shapeless file shows "Import failed: …" and writes nothing; same file re-pickable
  - log: 2026-06-17 parse guarded before any write (unchanged)
- [x] **Edge: api_keys nested object** - the `api_keys_pool` nested object travels whole inside the api_keys policy's settings
  - log: 2026-06-17 single-key section

## Unified Group Policy Model

One policy-type registry is the single source for every group permission (default, set-rule, validate, cross-group resolve), and at spawn a user's groups collapse into one effective policy object the hook reads. The legacy resolver and per-field validator are deleted, gated on a frozen golden snapshot proving the new engine reproduces them (v3.11.6 -> 3.12.0).

### Registry + engine

- [x] **Single source** - `POLICY_TYPES` is the only place each type's default, coerce, validate, and resolve live
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **default_config from registry** - `default_config()` is assembled from each type's `default`, no hand-listed field bag
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **resolve_policies drop-in** - same signature and output key set as the deleted `resolve_group_config`; the three hook call sites switch with no behaviour change
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Registry-driven save** - `GroupsConfigHandler.put` coercion and validation loop over `POLICY_TYPES`; no per-field if-chain remains
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **ctx carries non-config inputs** - `gpu_available`, reserved env names/prefixes flow via a context object, not globals
  - log: 2026-06-13 criterion added; done (v3.12.0)

### Per-type set-rule + resolve-rule

- [x] **env_vars** - reserved names stripped to `skipped_env_vars`; priority-first-wins on name; inactive section contributes nothing
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **gpu** - OR-grant; all-GPUs wins else device-id union; hardware-gated; grant with neither all nor ids falls back to all
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **docker** - OR-grant access/limited/privileged; max quota across granting groups; raw supersedes limited (clears limited + its flags)
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **mem** - biggest-enabled-GB wins; swap policy follows the winning cap; disabled group does not un-cap
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **cpu** - biggest-enabled-cores wins; disabled group does not un-cap
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **sudo** - section-gated priority-wins; `None` when unconfigured (hook applies platform default)
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **downloads** - section-gated priority-wins; `None` when unconfigured (hook applies platform default)
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **api_keys** - priority-ordered pool list; reserved target names rejected at save
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **volume_mounts** - union keyed by mountpoint; priority-wins on conflict; protected-mountpoint blacklist re-checked at resolve
  - log: 2026-06-13 criterion added; done (v3.12.0)

### Models own apply + lifecycle (the controller layer)

- [x] **Policy is a model class** - each permission is a `Policy` subclass (`EnvVarsPolicy`, `GpuPolicy`, ...) owning default/coerce/validate/resolve/summarize/apply/on_hub_startup; `POLICY_TYPES` is a list of instances
  - log: 2026-06-13 criterion added; done
  - log: 2026-06-13 evolved from the function-registry to model classes (operator "each policy type a model, not a hybrid frankenstack")
- [x] **apply imposes the resolved value** - each model's `apply(spawner, resolved, actx)` mutates the spawner / registers routes / assigns slots; moved verbatim from the old monolithic `pre_spawn_hook`
  - log: 2026-06-13 criterion added; done
- [x] **Thin hook** - `pre_spawn_hook` = resolve -> `apply_policies` loop -> non-policy steps only (compose labels, favicon, lab icons, aggregate log); no per-feature branches
  - log: 2026-06-13 criterion added; done
- [x] **Unified startup** - one `schedule_policy_startup(actx)` -> `run_hub_startup` loops each model's `on_hub_startup`; replaces the three per-feature startup callbacks; favicon stays separate (non-policy)
  - log: 2026-06-13 criterion added; done
- [x] **ApplyContext** - spawn-time hub config (proxy dirs, compose project, gpu uuid map, sudo/downloads defaults, reconcile interval) threaded to apply/startup via one frozen context built once in `make_pre_spawn_hook`
  - log: 2026-06-13 criterion added; done
- [x] **api_keys / docker controllers unchanged** - `PoolManager` and proxy `register_user` logic preserved, now invoked from `ApiKeysPolicy`/`DockerPolicy`; dead `schedule_*` functions removed
  - log: 2026-06-13 criterion added; done
- [x] **Apply regression guard** - `tests/test_policy_apply.py` FakeSpawner asserts exact spawner state per model (gpu/docker/mem/cpu/sudo/env/volumes/api-keys/downloads); resolve golden + all prior suites still green (506 tests)
  - log: 2026-06-13 criterion added; done
- [x] **api_keys restart persistence** - in-use set is label-derived; a lab surviving a hub restart keeps its slot; `ApiKeysPolicy.on_hub_startup` rebuilds in-use before any new spawn assigns
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **api_keys label at create** - the slot label is stamped on the container via `extra_create_kwargs` at create (the one gap that would reintroduce collisions)
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: collision after restart** - two labs running, hub restarts, a third spawn must not re-hand-out either surviving slot
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: exhausted pool** - more containers than credentials sets the target vars empty and logs a warning, never reuses a live slot
  - log: 2026-06-13 criterion added; done (v3.12.0)

### Migration + no-regression

- [x] **Golden frozen** - `tests/golden/policy_resolution.json` captures the old resolver outputs across the scenario matrix
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Golden green** - new engine output deep-equals the frozen golden for every scenario
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Old path deleted** - `resolve_group_config` and per-field `GroupConfigValidator` methods removed; no shim, no fallback; importers updated
  - log: 2026-06-13 criterion added; done (v3.12.0)

### Bundle round-trip (import/export foundation)

- [x] **Bundle shape** - a group serializes to `{group_name, description, priority, policies}`
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Round-trip** - export then import a bundle through the registry coerce path deep-equals the source config
  - log: 2026-06-13 criterion added; done (v3.12.0)

### UI

- [x] **Name opens config** - clicking the group name opens its configuration modal (edit icon dropped)
  - log: 2026-06-13 implemented (group name is a clickable config link, cog button removed)
- [x] **Hover tooltip** - hovering the group name lists the group's active policies, rendered from the server-provided `policy_summary` detail lines (no policy-display logic in the browser)
  - log: 2026-06-13 criterion added; done (v3.12.0)
  - log: 2026-06-13 GC removed the unconsumed `ui.summarize`; then redesigned per operator - `summarize` restored as a consumed display facet on each `PolicyType`, served by `GroupsDataHandler` as `policy_summary`, client renders verbatim
- [x] **Single-source badges + tooltip** - each `PolicyType.summarize(config)` returns `{badge, detail}`; `summarize_config` feeds `GroupsDataHandler.policy_summary`; the group table badges and tooltip both render it, so neither drifts from the registry
  - log: 2026-06-13 criterion added; done (v3.12.0)

### Edge cases

- [x] **Edge: zero matched groups** - resolve returns all defaults / `None` for section-gated types
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: section off with stale data** - an inactive section contributes nothing while its stored data persists
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: legacy row missing active flags** - `infer_active_flags` still applies; legacy groups keep working
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: conflicting priorities** - higher-priority group wins for priority-type keys; ties keep the higher-priority (earlier) group
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: reserved env-var name** - rejected at save with the stable `reserved_env_var_names` JSON error
  - log: 2026-06-13 criterion added; done (v3.12.0)

### Gate

- [x] **Tests green** - `uv run pytest` passes including golden, per-type, driver, restart, round-trip
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Version bumped** - root `pyproject.toml` 3.11.6 -> 3.12.0
  - log: 2026-06-13 criterion added; done (v3.12.0)

### API

Admin-only group config endpoints; the PUT body is coerced and validated through the registry.

- `GET /api/admin/groups` -> `{groups: [{name, description, priority, member_count, members, config, policy_summary}], shared_volume}`, priority-descending; `policy_summary` = `[{key, badge, detail}]` per active policy (registry-sourced display facet)
- `GET /api/admin/groups/{name}/config` -> `{group_name, description, priority, config}`
- `PUT /api/admin/groups/{name}/config` body = partial policy dict (any registry keys) -> saved `{group_name, description, priority, config}`
  - 403 non-admin
  - 400 `{error: 'reserved_env_var_names', message, rejected: [...]}` - env_vars or api-keys target name reserved (structured)
  - 400 `{error: '<code>', message}` coherence failure, first wins: `invalid_gpu_selection`, `invalid_docker_selection`, `invalid_cpu_limit`, `invalid_mem_limit`, `invalid_api_keys_pool`, `invalid_volume_mounts`
  - 400 bare message - malformed shape (`env_vars`/`gpu_device_ids`/`volume_mounts` not a list, `api_keys_pool` not an object)
- Bundle (import/export foundation) = `{group_name, description, priority, policies}` where `policies` is the config dict; import re-coerces each slice through the registry

## Group Sudo Access Control

A foldable "Sudo Access" group config section that explicitly sets whether members get sudo in their lab. When the section is on, the group configures sudo (enable or disable); `pre_spawn_hook` injects `JUPYTERLAB_SUDO_ENABLE=0|1` into the spawned container, which the image consumes. Resolution is section-gated and priority-wins: among the groups that configure it, the highest-priority group's value applies; if no group configures it, the platform default `JUPYTERHUB_LAB_SUDO_ENABLE` applies. Hub-side only - the hub injects the env var; enforcing sudo from it is the image's job.

### Platform default

- [x] **Default env** - `JUPYTERHUB_LAB_SUDO_ENABLE` (compose, `0`/`1`, default `1`) sets the value used when no group configures sudo
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Settings page** - listed in `settings_dictionary.yml` so it appears on the admin Settings page
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Compose default** - `JUPYTERHUB_LAB_SUDO_ENABLE=1` present in `compose.yml` jupyterhub service environment
  - log: 2026-06-12 implemented (v3.11.5)

### Group config (admin)

- [x] **Section** - foldable "Sudo Access" section in the group modal with a section-active switch `config-sudo-active` (default off), following the `*_active` section pattern
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Value control** - when the section is on, a toggle `config-sudo-enable` chooses enable (1) or disable (0) for members
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Persistence** - `default_config()` carries `sudo_active: False` and `sudo_enable: True`; data persists when the section is folded off and restores when re-enabled (same as other `*_active` sections)
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **No inference** - brand-new feature; legacy rows default to `sudo_active: False` (not configured -> platform default applies), no `infer_active_flags` entry
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **API accept** - `GroupsConfigHandler.put` accepts boolean body keys `sudo_active` and `sudo_enable`
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Badge** - groups table shows `Sudo on` or `Sudo off` when `sudo_active` is set (reflecting the configured value); no badge when the section is off
  - log: 2026-06-12 implemented (v3.11.5)

### Resolution

- [x] **Section-gated** - a group with `sudo_active` false does NOT configure sudo (its `sudo_enable` is ignored); only sections explicitly on are considered
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Priority-wins** - among groups with `sudo_active` on, the highest-priority group's `sudo_enable` wins (groups resolved in descending priority order; first configuring group decides) - not OR, not biggest-wins
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Resolved value** - resolver returns `sudo_enable` as `True`/`False` when configured by some group, or `None` when no group configures it
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Default fallback** - the spawn-time value is the resolved `sudo_enable` when not `None`, else `JUPYTERHUB_LAB_SUDO_ENABLE` (resolver stays pure; the hook applies the default)
  - log: 2026-06-12 implemented (v3.11.5)

### Spawn injection

- [x] **Always set** - `pre_spawn_hook` always sets `spawner.environment['JUPYTERLAB_SUDO_ENABLE']` to `'1'` or `'0'` (never left unset) so the container gets an explicit value every spawn
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Disable wins when configured** - a higher-priority group setting `sudo_enable=false` yields `JUPYTERLAB_SUDO_ENABLE=0` even if a lower-priority group enables it and even if the platform default is `1`
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Log line** - the existing pre_spawn resolution log line includes the resolved sudo value (configured vs default) for audit
  - log: 2026-06-12 implemented (v3.11.5)

### Edge cases

- [x] **Edge: user in no groups** - no group configures sudo -> platform default applies
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: all configuring groups agree** - any number of groups with the same value resolves to that value
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: configuring groups disagree** - highest-priority configuring group wins regardless of the others
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: section on, value unset in stored row** - defaults to `sudo_enable: True` from `default_config()`
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: higher-priority group section OFF, lower-priority ON** - the lower-priority group (the only one configuring) decides
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: membership change** - takes effect on the member's next server start (consistent with other group settings)
  - log: 2026-06-12 implemented (v3.11.5)

### Tests

- [x] **Resolver tests** - `TestSudoAccess`: no groups -> None; single configuring group -> its value; section-off group -> None; two configuring groups -> higher priority wins; higher-priority-off + lower-priority-on -> lower-priority value
  - log: 2026-06-12 implemented (v3.11.5)

### Documentation

- [x] **README** - Groups section documents the Sudo Access switch, the value toggle, the priority-wins/default-fallback rule, and the master default env var
  - log: 2026-06-12 implemented (v3.11.5)

### Out of scope

- Enforcing sudo inside the container from the env var - the image owns that; the hub only injects `JUPYTERLAB_SUDO_ENABLE`
- Per-user (non-group) sudo overrides
- Runtime sudo change without a server restart

### API

- `PUT /hub/api/admin/groups/{group}/config` body gains optional booleans `sudo_active`, `sudo_enable`
- Env into container: `JUPYTERLAB_SUDO_ENABLE` (`0`/`1`)
- Platform env: `JUPYTERHUB_LAB_SUDO_ENABLE` (`0`/`1`, default `1`)

## Label capitalisation (Title Case)

Button labels and header labels across the portal use Title Case - every principal word capitalised, minor words lowercase unless first/last. This is a system-wide design-language rule (cross-ref [acc-crit-design-language]); the live reference is the `/design-language` Conventions card. The trigger was the Events "Clear log" button, which should read "Clear Events". Verified against the code 2026-06-18.

### The rule

- [x] **Title Case principal words** - capitalise the first word and every principal word of a label
  - log: 2026-06-18 rule defined; e.g. "Add user" -> "Add User", "Manage volumes" -> "Manage Volumes"
- [x] **Minor words stay lowercase** - a, an, the, and, or, but, nor, of, to, in, on, at, by, for, from, with, vs, per, as, into stay lowercase UNLESS first or last word
  - log: 2026-06-18 e.g. "Force Password Change on Next Login", "Add a Group"
- [x] **Acronyms preserved** - JSON, API, CPU, GPU, TLS, URL, ID, NAS, CIFS, MLflow, TTL kept as-is (never "Api"/"Gpu")
  - log: 2026-06-18 e.g. "New API Token", "Single API Key"
- [x] **Units / tokens / numbers preserved** - "+7h", "24h", "30s", "GB", ".txt", "30%" unchanged
  - log: 2026-06-18 e.g. "Download .txt", "Choose JSON File(s)…"

### Scope (Title-Cased)

- [x] **Button labels** - every button's visible text, and Modal action buttons (`okText`/`cancelText`) that are action labels
  - log: 2026-06-18 swept (e.g. Clear Events, Stop All, Start Server, Remove User, Bulk Add)
- [x] **Page / card / section headers** - `PageHeader` titles, `Card` / `CardHeadLink` titles, `oh-section-title`
  - log: 2026-06-18 swept (e.g. Active Servers, Recent Events, New User, Export Groups, Effective Policies)
- [x] **Table column headers** - the `title` of list/table columns
  - log: 2026-06-18 swept (e.g. Last Activity, Time Left, Mount Point, Key Secret)
- [x] **Section / mode tabs** - tab and segmented labels that name a section or mode (not a data value)
  - log: 2026-06-18 swept (e.g. Add User, Create Group, Single API Key)

### Out of scope (left sentence case / unchanged)

- [x] **Form-field input labels** - `Form.Item` labels (First name, Last name, Email, Change password) stay sentence case - they are field prompts, not button/header labels
  - log: 2026-06-18 excluded per the operator's "(buttons, headers)" scope
- [x] **Sentence copy** - descriptions, `sub` lines, notices, alerts, tooltips and confirm-modal prompts ("Stop all running servers?", "Clear the event log?") stay sentence case
  - log: 2026-06-18 excluded - these are sentences, not labels
- [x] **Filter data-values** - Segmented/Radio option values that are data (statuses All/Active/Idle/Offline/Culled/Unauthorised, time ranges Last 24h / Last 7 days, percentages, durations, language names) stay as-is
  - log: 2026-06-18 excluded - they are values, not labels
- [x] **Dynamic / cell content** - table cell values and interpolated runtime strings unaffected
  - log: 2026-06-18 excluded

### Edge cases

- [x] **Same string, two roles** - a literal that appears both as a button AND as a sentence/tooltip is Title-Cased only in the label occurrence, not globally
  - log: 2026-06-18 swept per-occurrence with context, never a blind global replace
- [x] **Demo / reference pages** - `/design-system` (dev kitchen-sink) showcase headings were left as-is; `/design-language` carries the canonical Conventions rule + a Title-Case example row
  - log: 2026-06-18 DesignSystem.tsx out of scope; DesignLanguage.tsx Conventions card documents the rule

### Verification

- [x] **Frontend gates** - `npx tsc -b`, `npm run lint`, `npm run build:hub` all clean after the sweep
  - log: 2026-06-18 run from duoptimum-hub-web after the sweep

## live data honesty (no mock masquerade)

In live mode the portal must never present fabricated mock data as if it were real. A live `DataSource` method either returns real hub data, returns an honest empty/disabled state, or the surface is hidden - it never silently delegates to `mockSource` for content a user reads as fact. Mock mode (the design pages) keeps full mock data so the UI demos whole.

### Effective grants (per-user resolved policy)

- [x] **Real resolve endpoint** - `getEffectiveGrants(user)` calls `GET /api/users/{user}/effective-grants`, not `mockSource`
  - log: 2026-06-17 FIXED - was `getEffectiveGrants: mockSource.getEffectiveGrants` (liveSource.ts:606); now a real async method
- [x] **Backend resolves across the user's groups** - `EffectiveGrantsHandler` loads the user's ORM groups, runs `resolve_policies`, then `effective_grants(matched, resolved)`
  - log: 2026-06-17 added `handlers/effective_grants.py`, `policy.effective_grants`
- [x] **Source attribution** - each grant cites the highest-priority group that granted it (`from`), resolved by walking the priority-descending matched configs
  - log: 2026-06-17 `winner()` helper in `effective_grants`
- [x] **Honest empty** - a user whose groups grant nothing special returns `[]` (runs on platform defaults), not fabricated CPU/memory rows
  - log: 2026-06-17 mock fabricated "8 cores"/"16 GB" for everyone; real version emits a row only when a group sets it
- [x] **GPU hardware-gated** - the GPU grant appears only when `gpu_available` (resolver gates `gpu_access` on it); `gpu_available` threaded into `stellars_config`
  - log: 2026-06-17 added `'gpu_available': bool(gpu_enabled)` to tornado_settings
- [x] **Grant value formatting** - memory `N GB` (`(no swap)` annotated), CPU `N cores`, GPU `all devices` or `GPU 0, 1`, sudo `enabled`/`disabled`, docker `socket`/`limited`/`privileged` (privileged annotated onto the same row)
  - log: 2026-06-17 `num()` drops trailing `.0`
- [x] **Unique icon keys** - the full grant fanout uses distinct `key`s (gpu/memory/cpu/shield/box) so the React row keys never collide; docker+privileged collapse to one `box` row
  - log: 2026-06-17 covered by `test_unique_keys_for_react`
- [x] **Self-or-admin** - non-admin may read only their own grants (403 otherwise), same rule as the profile handler
  - log: 2026-06-17 `_authorize`
- [x] **Failure falls to honest empty** - a fetch error returns `[]`, never the mock grants
  - log: 2026-06-17 `catch { return [] }`
- [x] **Edge: unknown user** - handler returns 404 when the ORM user does not exist
  - log: 2026-06-17 implemented
- [x] **Edge: biggest-wins attribution** - when two groups set memory/cpu, the row cites the highest-priority group at the winning (max) value
  - log: 2026-06-17 covered by `test_biggest_wins_with_attribution`
- [ ] **Runtime: konrad sees real grants** - on the live hub the Home / UserConfig grants reflect his actual group policy with correct source, not the mock list
  - log: 2026-06-17 backend + frontend done; on-screen confirm pends operator rebuild

### Activity report download

- [x] **Real report** - the Servers "Report" action downloads a real CSV of the servers currently in scope (one row per server, the same activity / CPU / memory / volume / time-left numbers the table shows), client-side from already-fetched data
  - log: 2026-06-17 FIXED - was `mockAction('Downloaded activity report')`; now `downloadCsv` from `filtered`, real success toast, disabled when scope is empty
- [x] **Edge: empty scope** - the Report button is disabled when no server is in scope (nothing to export)
  - log: 2026-06-17 implemented

### Group policy import / export

- [x] **Export uses real configs** - "Export N groups" downloads `{groups:[{name, description, priority, config}]}` built from the live `/admin/groups` configs (raw flat `config` now carried on `GroupRow`), client-side, real success toast
  - log: 2026-06-17 FIXED - was `mockAction('Exported N groups as JSON')`; `downloadJson`, importable shape
- [x] **Import writes via real endpoints** - the Import file-picker parses the bundle and `importGroups` creates each group (409 already-exists falls through) then PUTs `/admin/groups/{name}/config`; one toast + one `['groups']` invalidation for the batch
  - log: 2026-06-17 FIXED - was `mockAction('Import groups from JSON')`; real create + config PUT, mock-toast only in mock mode
- [x] **Round-trips** - an exported bundle re-imports through the same flat-config shape the editor PUTs (hub coerces + validates)
  - log: 2026-06-17 export/import share `{name, description, priority, config}`
- [x] **Edge: malformed file** - a non-JSON / shapeless file shows "Import failed: ..." and writes nothing; the same file can be re-picked (input value cleared)
  - log: 2026-06-17 parse guarded before any write

### General rule

- [x] **Audit remaining mock delegations** - an adversarial sweep found 11 live-mode mock-masquerades; every `mockSource.*` in `liveSource` is now removed - on a 403/404/500/network error each method returns honest-empty/neutral, never fabricated content
  - log: 2026-06-17 adversarial sweep + fix pass; the `mockSource` import is gone from `liveSource.ts`

### Adversarial mock sweep (2026-06-17) - all fixed

- [x] **getGroups / getGroupConfig** - catch returned `mockSource` (fabricated ~15 groups / a policy config that would PUT back on save); now `[]` / `undefined`
  - log: 2026-06-17 fixed
- [x] **getTokens** - catch fabricated 5 tokens incl. a fake `admin:users`-scoped one; now `[]`
  - log: 2026-06-17 fixed
- [x] **getUserVolumes** - catch fabricated home/workspace/cache sizes; now `[]`
  - log: 2026-06-17 fixed
- [x] **getEvents** - catch fabricated a named event feed as the real activity log; now `[]`
  - log: 2026-06-17 fixed
- [x] **getSessionInfo** - catch fabricated a per-user TTL driving the extend control; now an honest neutral from real idle-culler config
  - log: 2026-06-17 fixed
- [x] **getGroupCorpus / getUserCorpus** - catch injected fixture names into pickers; now `[]`
  - log: 2026-06-17 fixed
- [x] **getSettingsReference** - was hardwired to mock (no live attempt) despite a real `/settings`; now fetches `/settings` (env name + live value + description), honest-empty on error
  - log: 2026-06-17 wired to the real endpoint
- [x] **Servers "View spawn log"** - was `mockAction('Tail live spawn log')`; now opens the real Start-server page (`/servers/{user}/starting`)
  - log: 2026-06-17 fixed (#238)
- [x] **Verified honest (no change)** - getTotalResources, getHubInfo, getUserProfile, getLabContainer, getSettings, getEffectiveGrants, getSentNotifications already return honest-empty/last-known
  - log: 2026-06-17 confirmed by the sweep
- [ ] **AppLayout language toast** - `mockAction('Language: ...')` fires in both modes; client-only (no i18n backend) - lowest priority, left as-is
  - log: 2026-06-17 noted, deliberately not changed

### API

- `GET /api/users/{user}/effective-grants` -> `{grants: [{key, label, value, from}]}`; 403 not-self-not-admin, 404 unknown user

## Mobile Responsive Portal

Below a mobile breakpoint the Duoptimum Hub portal switches to a JupyterHub-style minimal home: status plus the few controls that make sense on a phone. The lab itself (JupyterLab) is not mobile-friendly, so the portal never navigates into the user server on mobile.

- [x] **Breakpoint** - below a mobile width (target < 768px) the portal renders the mobile layout; the desktop layout is unchanged at/above it
  - log: 2026-06-17 implemented + code-verified (useIsMobile `(max-width: 767px)`; Home returns MobileHome when mobile, else desktop unchanged)
- [x] **Mobile home content** - shows server status (pill + time-left) and exactly these controls: Start (launch), Stop, Extend TTL
  - log: 2026-06-17 implemented (MobileHome.MyServerCard: StatusPill + Start|Stop + TtlGadget time-left/Extend)
- [x] **No lab navigation on mobile** - no Open-lab / Enter-session affordance anywhere on mobile; the portal never links into the user server UI
  - log: 2026-06-17 verified by code (MobileHome does not import userServerUrl; no Open-lab control)
- [x] **Allowed mobile actions (closed set)** - launch server, stop server, extend session TTL; nothing else for a regular user
  - log: 2026-06-17 verified (regular user sees only MyServerCard = Start/Stop/Extend)
- [x] **No Restart on mobile** - restart is a desktop action; mobile exposes only Start/Stop/Extend
  - log: 2026-06-17 confirmed by user ("no other mobile actions"); no Restart button in MobileHome
- [x] **Admin extras** - admin additionally sees the servers widget below the home card, plus a link to the Servers screen and a link to the Users screen
  - log: 2026-06-17 implemented (MobileServersWidget + Servers/Users Links, gated on role==='admin')
- [x] **No other admin mobile actions** - beyond the two links and the widget, no admin actions on mobile (no groups / tokens / settings / notifications inline)
  - log: 2026-06-17 verified (MobileHome renders only the widget + two links for admin)
- [x] **Servers/Users via link** - the Servers and Users screens are reached as links (navigation), not embedded inline on the mobile home
  - log: 2026-06-17 verified (react-router Link to /servers + /users; widget is read-only, not the inline screens)
- [x] **Edge: resize / rotate across breakpoint** - layout swaps without losing query state (shared TanStack cache)
  - log: 2026-06-17 verified by code (useIsMobile subscribes to matchMedia change -> live swap; single QueryClient so cache is shared across layouts)
- [ ] **Edge: deep link to a desktop-only route on mobile** - degrade gracefully (redirect to mobile home or show a brief "desktop only" note), never a broken screen
  - log: 2026-06-17 NOT handled - desktop routes (Servers/Users/etc.) still render their ProTable on mobile (horizontally scrollable, not broken, but no deliberate degrade); follow-up
- [x] **Edge: TTL/extend on mobile** - the extend control works on mobile (touch-friendly hours input); the bar follows the same base-relative behaviour as desktop
  - log: 2026-06-17 verified (TtlGadget reused: InputNumber hours popover + base-relative pct, identical to desktop)
- [x] **Look good on a phone (runtime)** - visual polish, spacing, touch targets confirmed on an actual narrow viewport
  - log: 2026-06-17 VISUALLY CONFIRMED via Playwright headless render at 390px (mock build): clean single column, big Start button, Offline status pill, read-only Active-servers list, full-width Servers/Users links, JupyterHub-5 chip - looks good. Screenshot reviewed.

### Open questions

- Which actions, if any, are allowed on the admin Servers screen on mobile (view-only vs the same Start/Stop/Extend per row)? - widget is read-only; the Servers screen itself is reached via link and renders its desktop table for now
- Should Restart be available on mobile for one's own running server, or is Stop+Start the only path? - RESOLVED: no Restart on mobile (user: "no other mobile actions")

## Navigation patterns (edit pages -> parent + breadcrumbs)

Every form / sub screen reached from a list must offer a way back to its parent and show a breadcrumb that names that parent - never a dead end and never a wrong parent. Two shapes: a screen with ONE parent returns to that fixed canonical route (matching its breadcrumb `parent` route handle); a screen reachable from MORE THAN ONE place records its origin in `state.from = {to, label}` and both the return target and the breadcrumb parent honour it. Mechanism: `react-router` route handles (`{crumb, parent}`) + `Breadcrumbs.tsx` (prefers `state.from` over the static parent) + `FormFooter` (Cancel + Save/Done/Ok). Cross-ref [acc-crit-edit-returns-to-origin] (UserConfig), [acc-crit-design-language] (the system-wide nav rules), [acc-crit-volume-reset]. Verified against the code 2026-06-18.

### Single-parent edit / sub pages

- [x] **Configure group -> Groups** - `/groups/:name` Save / Cancel / Delete return to `/groups`; breadcrumb parent Groups
  - log: 2026-06-18 verified (GroupConfig `navigate('/groups')` x3 + `FormFooter onCancel`; router `groupsParent`)
- [x] **New user -> Users** - `/users/new` Save / Cancel return to `/users`; breadcrumb parent Users
  - log: 2026-06-18 verified (NewUser FormFooter + `navigate('/users')`)
- [x] **New group -> Groups** - `/groups/new` Save / Cancel return to `/groups`; breadcrumb parent Groups
  - log: 2026-06-18 verified (NewGroup FormFooter + `navigate('/groups')`)
- [x] **Bulk add -> Users / result** - `/users/bulk` Cancel returns to `/users`; submit advances to `/users/bulk/result`; breadcrumb parent Users
  - log: 2026-06-18 verified (BulkUsers)
- [x] **Bulk result -> Users** - `/users/bulk/result` Done returns to `/users`; breadcrumb parent Users
  - log: 2026-06-18 verified (BulkResult `navigate('/users')`)
- [x] **Export groups -> Groups** - `/groups/export` Cancel returns to `/groups`; breadcrumb parent Groups
  - log: 2026-06-18 verified (GroupsExport)
- [x] **Full reference -> Settings** - `/settings/reference` (read-only) has no footer; the breadcrumb parent Settings is the way back
  - log: 2026-06-18 verified (router parent Settings -> /settings; read-only page, no footer by design)

### Multi-origin pages (honour state.from)

- [x] **Configure user** - `/users/:name` returns to its origin (Home / Servers / Users) via `state.from`, Users as the canonical fallback; breadcrumb parent matches
  - log: 2026-06-18 implemented this session; full matrix in [acc-crit-edit-returns-to-origin]
- [x] **Manage volumes** - `/servers/:name/volumes` returns to its origin (Home or Servers) via `state.from`, Servers as the canonical fallback; breadcrumb parent matches
  - log: 2026-06-17 implemented (ManageVolumes `backTo = state.from?.to ?? '/servers'`); cross-ref [acc-crit-volume-reset]
- [x] **Start server** - `/servers/:name/starting` returns to Home for your own server, Servers for another user's
  - log: 2026-06-18 verified (Starting `navigate(isOwn ? '/dashboard' : '/servers')`); cross-ref [acc-crit-start-server-page]

### Breadcrumb rules

- [x] **Crumb from the route handle** - each page declares `handle.crumb`; the breadcrumb shows "Duoptimum Hub / [parent] / crumb"
  - log: 2026-06-18 verified (Breadcrumbs reads the deepest matched handle)
- [x] **Origin beats static parent** - when `state.from` is present it overrides the route's static `parent` so the crumb names where the user actually came from
  - log: 2026-06-17 implemented (Breadcrumbs `origin ?? handle.parent`)
- [x] **Parent crumb is a link** - the parent crumb navigates back to the parent list; the current page crumb is bold, not a link
  - log: 2026-06-18 verified (Breadcrumbs builds `<Link to={parent.to}>` + bold current)
- [x] **Single source of truth** - the same `state.from` drives BOTH the breadcrumb parent and the footer return target, so they can never disagree
  - log: 2026-06-18 verified (UserConfig + ManageVolumes read the one `state.from`)

### Edge cases

- [x] **Edge: deep link / refresh** - landing on a sub page directly (no `state.from`) returns to the canonical parent and shows it as the breadcrumb parent
  - log: 2026-06-18 fallback routes (`?? '/users'`, `?? '/servers'`) + static route parent
- [x] **Edge: never a dead end** - every list-reachable screen has either a footer Cancel/Done or a parent breadcrumb link back
  - log: 2026-06-18 audited the edit/sub pages (see lists above)
- [x] **Edge: rename changes the route** - renaming a user on `/users/:name` navigates to `/users/:newName` (the renamed profile), carrying the origin state forward
  - log: 2026-06-18 implemented with the rename action (`navigate('/users/'+newName, { state })`) - cross-ref [acc-crit-rename-user]

### Functional tests

- [x] **Origin round-trip** - a Playwright test opens Configure user from the Users list and asserts the breadcrumb parent link is Users and Cancel returns to /users
  - log: 2026-06-18 `tests/functional/test_navigation.py::test_configure_user_returns_to_users` (acc_crit `navigation-patterns::Origin round-trip`); Servers/Home origins covered by code + the design-language nav rules
- [x] **Single-parent round-trip** - tests open New user (-> Users) and New group (-> Groups) and assert the breadcrumb parent link + that Cancel returns to the parent list
  - log: 2026-06-18 `test_navigation.py::test_new_user_returns_to_users` + `test_new_group_returns_to_groups`

## old portal cleanup

Remove the dead remnants of the pre-React portal now that `duoptimum-hub-web` serves the portal via `PortalHandler` and the React SPA owns the former server-rendered routes. Surgical, not blanket: many `html_templates_enhanced/*.html` are still rendered by stock JupyterHub and MUST stay.

### Removed (confirmed dead)

- [x] **Dead page templates** - `activity.html`, `settings.html`, `groups.html`, `notifications.html` deleted from `html_templates_enhanced/`; referenced only by their own unregistered handlers
  - log: 2026-06-17 `git rm`; verified no other `render_template` refs
- [x] **Dead page handlers** - `ActivityPageHandler`, `SettingsPageHandler`, `NotificationsPageHandler`, `GroupsPageHandler` classes removed; their API data handlers kept
  - log: 2026-06-17 removed from the 4 handler modules + `handlers/__init__.py` imports/`__all__`
- [x] **Handler count test** - `test_imports` expectation 30 -> 26
  - log: 2026-06-17 updated + suite green (592 passed)
- [x] **Orphaned import** - `import os` dropped from `groups.py` (only the removed page handler used it)
  - log: 2026-06-17
- [x] **Static mock prototype** - the `mock/` static HTML prototype tree (368K) deleted; unreferenced by any build/serve path
  - log: 2026-06-17 `git rm -r mock/`; grep confirmed no Dockerfile/compose/config/script refs
- [x] **Stale comments** - config `template_vars` comments naming `GroupsPageHandler` updated to the live consumers
  - log: 2026-06-17 `config/jupyterhub_config.py`

### Kept (still live - must not remove)

- [x] **Stock-rendered templates kept** - `error.html`, `404.html`, `logout.html`, `oauth.html`, `spawn*.html`, `stop_pending.html`, `not_running.html`, `my_message.html`, `change-password*.html`, `authorization-area.html`, `accept-share.html`, `page.html` base - rendered by stock JupyterHub / NativeAuth
  - log: 2026-06-17 left in place
- [x] **Static assets kept** - `custom.css`, `session-timer.js`, `mobile.js` - referenced by `page.html`
  - log: 2026-06-17
- [x] **API data handlers kept** - the `*DataHandler` classes serving the SPA stay registered
  - log: 2026-06-17

### Held for a rebuild-verified pass (confirmed dead, not removed blind)

- [ ] **Shadowed auth/redirect templates** - enhanced `login.html`, `signup.html`, `native-login.html`, `home.html`, `token.html`, `admin.html` are shadowed by the duoptimum-hub-web wheel / remapped in `auth.py`; deleting them is auth-critical and wants an image rebuild to verify before removal
  - log: 2026-06-17 left in place pending a rebuild-verified sweep; flagged to the operator
- [x] **package-lock name** - `duoptimum-hub-web/package-lock.json` already carries the correct name (no longer `mock-antd`)
  - log: 2026-06-17 verified after `make install`

## Portal UI Polish (2026-06-17 session)

Running checklist for the rapid UI feedback pass: TTL animation, GPU labels + rich tooltip, list tooltips, resource tooltips, upgrade pill, footer, list sub-names. Status is honest - `[x]` = in code + verified (tests/typecheck), `[ ]` = pending; backend-dependent items are flagged. Nothing here is live until the next image rebuild.

### TTL extend

- [x] **Extend refetches the bar** - `extendSession` invalidates `['hero', user]` so the bar refetches; backend persists `cull_at` and `remaining_seconds_for` reads it
  - log: 2026-06-17 fixed + verified (backend round-trip read end-to-end, invalidate confirmed); a "still 50%" rebuild predates this fix
- [ ] **Animate the increase** - on extend the bar should animate up to the new remaining, not snap
  - log: 2026-06-17 antd `Progress` transitions on percent change by default - expected free once the refetch lands; confirm visually after rebuild

### GPU labels + tooltip

- [x] **Mini name as bar label** - per-GPU bar labels show the stripped name ("5090") not the index
  - log: 2026-06-17 implemented (shortGpuName + GpuMeter)
- [x] **Full name fits before the bar (single line)** - the device-name label column is wide enough for the full short name ("A500 Embedded GPU"), single line, never wrapped/truncated, bar flexes after it
  - log: 2026-06-17 pending - needs `.oh-gpurow` layout: name `white-space:nowrap` + natural width, bar `flex:1`
  - log: 2026-06-17 fixed - `.oh-gpurow > small` was 8px (index-sized) so names wrapped/collided; now `width:112px` left-aligned, `nowrap` + ellipsis guard, `flex:1` bar after it (global.css:80)
- [x] **Rich multiline GPU tooltip** - hover shows full info, one field per line, like the old design: full name, UUID, memory total, current utilisation, memory used, temperature, wattage
  - log: 2026-06-17 pending; PARTIAL data only - name/uuid/mem-total/utilisation/mem-used are available (uuid in inventory, dropped by gpu_cache so must be threaded); **temperature + wattage are NOT queried by the sidecar** (`_GPU_QUERY`), so they need: sidecar `_GPU_QUERY += temperature.gpu,power.draw` + schema + image rebuild, then gpu_cache + activity entry + GpuDevice type + tooltip
  - log: 2026-06-17 complete - `gpuTip` renders name/UUID/memory used+total/utilisation/temp/power, one field per line (meters.tsx)
  - [x] **Sub: extend sidecar** - add `temperature.gpu`, `power.draw` to `_GPU_QUERY` + schema (`gpuinfo-nvidia`, separate image)
  - [x] **Sub: thread fields** - keep uuid/temp/power through `gpu_cache` -> activity gpu entry -> `GpuDevice` -> tooltip
- [x] **Standard (native) tooltip, not a styled popup** - the GPU tooltip is the SAME native browser `title` tooltip the CPU/memory/volume/system cells use, so every resource tooltip reads identically - not a bespoke antd `Tooltip` popup
  - log: 2026-06-17 first tightened the antd Tooltip, then (operator: "must be standard, not a different design") converted `gpuTip` to a plain `\n`-joined string on the `title` attribute of the GpuMeter row + GpuInventory chip; removed the antd `Tooltip` wrapper + import

### List + resource tooltips

- [ ] **Multiline list tooltips** - long tooltips on Servers, Users and Groups lists wrap to a sensible max-width multiline box, not one ridiculously long line
  - log: 2026-06-17 pending (tooltip `overlayStyle` max-width + normal white-space); names/labels themselves stay single-line (multiline name breaks the row visuals)
- [x] **Resource widget tooltips** - on the resources tracker widget EVERY progress bar carries the detail tooltip, not just the % value
  - log: 2026-06-17 done - `title={r.tip}` added to the `.oh-res-bar` spans (CPU/Memory) so the bar itself shows the breakdown; GPU per-device bars/chips already carry their own native `title`; the value span keeps its tip too

### Upgrade pill

- [x] **Desktop pill** - gold "Upgrade available" left of the status pill on the Server status card, running servers only
  - log: 2026-06-17 implemented + running-gated
- [x] **Mobile pill** - same pill on the mobile MyServerCard header, running only
  - log: 2026-06-17 implemented (MobileHome), typecheck clean
- [x] **Recency check** - `docker image ls` newest local image for the repo vs the running container's image created time (`image_upgrade_available`, 6 unit tests); unknown -> no pill
  - log: 2026-06-17 implemented + tested

### Dashboard freshness

- [x] **Refresh server status on return** - returning to the dashboard after starting the lab (the start page navigates out into the lab) must redraw the server control, servers widget and servers list with current status, not a stale "offline" from the hydrated cache for ~10s
  - log: 2026-06-17 fixed - `Home()` invalidates `['hero',user]`, `['servers']`, `['stats']`, `['resources']`, `['session',user]` on mount so they refetch immediately (staleTime 30s otherwise trusts the hydrated stale value); the refetch resolves in ~1s instead of waiting out the stale window

### Misc

- [x] **Footer label** - bottom stack chip reads "Ant Design" not "Ant Design Pro"
  - log: 2026-06-17 done (AppLayout VersionFooter)
- [x] **First/last name in users list** - the users list shows the profile first/last name as a sub-name under the username
  - log: 2026-06-17 pending (#186) - `getUsers` does not surface profile first/last; also depends on the profile save actually persisting (#183 "Failed to fetch"); user reports the saved name does not appear -> both needed
  - log: 2026-06-17 done - new bulk `GET /api/user-profiles` (admin) via `UserProfilesListHandler` + `UserProfileManager.get_all_profiles()`; `liveSource.getUsers` fetches it and sets `UserRow.fullName = "First Last"`; `Users.tsx` already renders `oh-name-hint`; mock already had names so parity holds. #183: save path (handler/route/XSRF) verified correct - the "Failed to fetch" was a stale bundle, not a code bug; the real symptom was this missing display link

### Verification

- [x] **Backend + frontend green** - `make test` 564, docker-proxy 63, portal `tsc --noEmit` clean as of this session
  - log: 2026-06-17
- [ ] **Live** - rebuild + hard refresh; confirm TTL animates up on extend, GPU names fit, tooltips wrap, pill shows
  - log: 2026-06-17 pending user rebuild

## profile name display

A user's display name (first + last) edited on the Profile / Configure-user page must show everywhere it appears once saved. The backend store + API are correct (verified live: DB holds the new name, `GET /api/user-profiles` returns it); the bug was a frontend cache that never refetched after the save. `services/ops.ts::saveUserProfile`; display in `pages/Users.tsx` (`fullName` hint) + the profile form.

- [x] **Save invalidates the table** - `saveUserProfile` invalidates `['users']` (the Users table reads `fullName` from `/user-profiles` under that key) in addition to `['user-profile', name]` and `['user', name]`
  - log: 2026-06-17 FIXED - was `[['user-profile', name], ['user', name]]` only, so a saved last-name change never refreshed the list; the persisted query cache also kept it stale across reloads
- [x] **Form refetches** - `['user-profile', name]` invalidation refetches the edit form so its own fields/header reflect the save
  - log: 2026-06-17 verified (key already present)
- [x] **List refetches on mount** - `Users.tsx` force-invalidates `['users']` on mount (mirroring `Home.tsx`), so returning to the list after a save shows the new name immediately instead of repainting the persisted cache (trusted-as-fresh under the 30s staleTime) for ~2 min
  - log: 2026-06-17 FIXED - root cause of the residual ~2-min staleness: unlike Home, Users had no mount-time refetch, so the hydrated cache held the old name until the query was next re-observed while stale
- [x] **Backend correct** - PUT `/users/{name}/profile` persists first/last/email; bulk `GET /api/user-profiles` returns `{profiles: {username: {first_name,last_name,email}}}`
  - log: 2026-06-17 verified live (user_profiles.sqlite has 'Konrad','Jelenski'; API 200)
- [x] **Admin tag spacing** - the Users cell renders the username Link and the "admin" Tag in a flex row with a gap, so they no longer run together as "konrad.jelenadmin"
  - log: 2026-06-17 FIXED - inner `<div>` was bare (Tag has no left margin); now `display:flex; gap:6`
- [x] **Full name shown as hint** - `fullName` renders as the muted `oh-name-hint` line under the username (Users table + pending list)
  - log: 2026-06-17 present
- [ ] **Runtime: saved name refreshes the list** - on the live hub, saving a last name updates the Users table `fullName` without a manual reload
  - log: 2026-06-17 invalidation fixed; on-screen confirm pends operator rebuild

### Edge cases

- [x] **Edge: empty profile** - no first/last set -> no `fullName` hint rendered (the `{u.fullName && ...}` guard)
  - log: 2026-06-17 verified
- [x] **Edge: self vs admin save** - both the user's own Profile page and the admin Configure-user page call the same `saveUserProfile`, so both invalidate `['users']`
  - log: 2026-06-17 verified (Profile.tsx + UserConfig.tsx)
- [ ] **Edge: rename + profile** - a username rename (`renameUser`) and a profile edit are separate ops; the rename already invalidates `USER_KEYS(name)`; the display name (fullName) is independent of the username
  - log: 2026-06-17 noted; no cross-dependency

## Profile route (role-aware self-view)

The Profile nav link (`/profile`) opens the current user's own profile. It is role-aware: an admin gets the full Configure-user screen scoped to themselves; a plain user gets the self-service Profile page. `duoptimum-hub-web/src/router.tsx::ProfileRoute`, `pages/UserConfig.tsx`, `pages/Profile.tsx`.

### Routing

- [x] **Admin -> Configure-user (self)** - an admin's `/profile` renders `UserConfig`, which falls back to `useRole().username` when there is no `:name` param, so it is the same screen as `/users/{self}`
  - log: 2026-06-17 `ProfileRoute` + `name = paramName || username`
- [x] **Non-admin -> self-service Profile** - a plain user's `/profile` renders `Profile.tsx` (own name/email/password only), NOT `UserConfig`
  - log: 2026-06-17 `ProfileRoute` role switch; fixes the sweep HIGH where a non-admin saw admin-only controls + a 403 on the admin-only `/users` fetch
- [x] **Breadcrumb** - the crumb is "Profile" for both roles (PageHeader title/sub are ignored by design, so the breadcrumb is the visible label)
  - log: 2026-06-17 `router.tsx` crumb

### Admin self-view (UserConfig)

- [x] **Builtin admin controls hidden** - for the platform admin viewing self, Remove-user, Administrator and Authorised are hidden and the built-in-admin notice shows (`isBuiltinAdmin`)
  - log: 2026-06-17 pre-existing UserConfig guards apply to self
- [x] **Force-password hidden** - the force-password toggle is hidden for an admin target (`!liveAdmin`), so it never shows on an admin's own profile
  - log: 2026-06-17 cross-ref [acc-crit-force-password-change]

### Non-admin self-view (Profile.tsx)

- [x] **No admin controls** - only username (read-only), first/last name, email and password; no Administrator/Authorised/Remove/Groups
  - log: 2026-06-17 `Profile.tsx` unchanged self-service page
- [x] **Self password change with challenge** - changing the password requires the current password (`changeOwnPassword` -> `/change-password`), not the admin no-challenge endpoint
  - log: 2026-06-17 the sweep flagged that routing self through UserConfig's admin `setUserPassword` would 403 + skip the current-password challenge
- [x] **No admin-only fetch** - the page reads only self-allowed endpoints (`/users/{self}/profile`), never the admin-only `/users` list
  - log: 2026-06-17 avoids the 403 a non-admin hit in the broken interim
- [x] **Cancel/save stay put** - save and cancel return via `navigate(-1)`, not `/users` (which `RequireAdmin` would bounce a non-admin off)
  - log: 2026-06-17 `Profile.tsx` navigation

### Edge cases

- [x] **Edge: no dead code** - `Profile.tsx` and `changeOwnPassword` are live again (used by the non-admin branch), not orphaned
  - log: 2026-06-17 the interim `/profile`->`UserConfig`-always change had orphaned both
- [ ] **Runtime: both roles** - on the live hub, an admin's Profile shows the Configure screen and a plain user's shows the self-service page with a working current-password change
  - log: 2026-06-17 code + tsc/eslint/build green; on-screen confirm pends operator rebuild

## Rename user (admin action on the profile)

An admin can rename a user from the Configure-user screen via an action attached to the Username input (the design-language input-with-attached-action pattern, like Change password / Generate). The rename is destructive-adjacent: it goes through a confirmation popup, is only possible while the user's server is stopped, and warns that the renamed user's existing volumes do NOT follow the rename (an admin must migrate them separately). On success the screen navigates to the renamed user's profile. Backend is the stock JupyterHub admin rename (`PATCH /users/{name}` with `{name}`) plus the existing sync listener (`events.py::sync_nativeauth_on_rename`). Frontend `ops.renameUser`. Verified against the code 2026-06-18.

### Control + placement

- [ ] **Adjacent to the Username input** - the Rename action sits attached to the Username field as a `Space.Compact` input + button (the same pattern as the Change-password / Generate row), not a separate panel
  - log: 2026-06-18 to implement (UserConfig Username Form.Item)
- [x] **Admin role only** - the Rename control renders / is usable only for an admin; a plain user (self-service Profile page) never sees it
  - log: 2026-06-18 UserConfig is admin-only (`/users/:name` under RequireAdmin); gated on role
- [x] **Hidden for the built-in admin** - the platform admin account (`JUPYTERHUB_ADMIN`) cannot be renamed (like it cannot be removed/de-authorised)
  - log: 2026-06-18 gated on `isBuiltinAdmin`

### Rules

- [x] **Enabled only when the server is stopped** - the Rename button is disabled while the user's server is running/spawning; a tooltip says to stop it first
  - log: 2026-06-18 gated on the server status (`useServerHero(name).status === 'offline'`)
- [x] **Confirmation popup** - clicking Rename opens a confirmation dialog before any write; cancelling makes no change
  - log: 2026-06-18 Modal.confirm with a danger OK
- [x] **Volumes-not-migrated warning** - the confirmation states that the user's existing volumes (home / workspace / cache) stay attached to the OLD name and will NOT follow the rename; an admin must migrate them separately
  - log: 2026-06-18 the operator's explicit warning text
- [x] **Back to the renamed profile** - on a successful rename the screen navigates to `/users/{newName}` (the renamed user's Configure screen)
  - log: 2026-06-18 navigate to the new name; origin state carried forward
- [x] **No-op guards** - Rename is disabled when the new name is blank or unchanged from the current name
  - log: 2026-06-18 disabled unless `newName.trim()` and `!= current`

### Backend (existing, reused)

- [x] **Rename endpoint records the actor** - the write goes through a custom admin endpoint `POST /users/{name}/rename` (not the stock PATCH) so the recorded event can name the acting admin; the rename itself is the orm `user.name = newName` + commit, identical to what stock does
  - log: 2026-06-18 `UserRenameHandler` added + route registered; `ops.renameUser` repointed from stock PATCH to the custom endpoint
- [x] **NativeAuth UserInfo synced** - the rename event listener updates the NativeAuthenticator `UserInfo.username` so authorisation + password survive the rename
  - log: 2026-06-18 `events.py::sync_nativeauth_on_rename` (verified); covered by the new unit test
- [x] **Activity + profile synced** - the listener renames the user's ActivityMonitor samples and display profile (first/last/email) to the new name
  - log: 2026-06-18 `rename_activity_user` + `UserProfileManager.rename_user` (both already unit-tested; orchestration covered)
- [x] **Event recorded** - the rename records a `user` event so it shows in the Events feed
  - log: 2026-06-18 `record_event` in the listener (base text "<old> renamed to <new>")
- [x] **Event names the actor (who renamed whom)** - the rename event identifies the acting admin AND both names, e.g. "<admin> renamed <old> to <new>"; the actor is taken from the authenticated request (server-trusted), never the client
  - log: 2026-06-18 operator: "event about user rename (and who did rename who)"; implemented via a `rename_actor` contextvar set by `UserRenameHandler` and read by the listener (falls back to "<old> renamed to <new>" with no actor); covered by `test_rename_event_names_the_actor`
- [x] **Volumes are NOT renamed** - the Docker per-user volumes (`jupyterlab-{encoded}_home` etc.) are keyed on the old encoded name and are intentionally left untouched by the rename (hence the UI warning)
  - log: 2026-06-18 no volume rename in the listener - the documented platform behaviour the warning surfaces

### Post-rename + collateral (renamer's responsibility)

- [x] **Logs in with the new name** - after the rename the user authenticates with the NEW username; the credentials carry over because the NativeAuth `UserInfo` row (username + password hash + authorisation) is moved by the listener
  - log: 2026-06-18 operator: "when user is renamed, they will log in using this new name"; UserInfo username synced -> old name no longer logs in, new name does
- [x] **DB rows keyed on username are synced** - every platform store keyed on the username moves to the new name automatically: JupyterHub's own user row (the hub), NativeAuth `users_info`, ActivityMonitor samples, the display-profile row
  - log: 2026-06-18 operator "(db changes too)"; the rename listener fans out to all three platform DBs; the hub renames its own row
- [x] **Renamer owns the remaining collateral** - the acting admin is responsible for everything the rename does NOT move automatically - chiefly the Docker per-user volumes (keyed on the old encoded name) - and the confirm dialog states this explicitly so it is a conscious choice
  - log: 2026-06-18 operator: "the renamer must take care of all collateral"; volumes are the known non-migrated item (cross-ref the volumes warning above)
- [x] **No silent half-rename** - if any sync step fails the failure is logged; the rename never half-applies the auth row silently (UserInfo move is the auth-critical step, asserted in the unit test)
  - log: 2026-06-18 listener wraps each sync; UserInfo move covered by test_rename_sync

### Edge cases

- [x] **Edge: rename to an existing username** - the endpoint returns 409; the error toast surfaces and the screen stays put (no navigation)
  - log: 2026-06-18 `UserRenameHandler` 409 on `find_user(new_name)`; `ops.run` error toast; navigate only on success
- [x] **Edge: server running** - Rename stays disabled; no write is attempted
  - log: 2026-06-18 server-stopped gate (`serverStopped` from `useServerHero`)
- [x] **Edge: mock mode** - the demo shows the success toast and does NOT navigate (the renamed mock user does not exist), matching Remove-user mock behaviour
  - log: 2026-06-18 `if (!isMock()) navigate(...)`
- [x] **Edge: user creation is not a rename** - the `set` listener fires on the INITIAL name-set (user creation) with SQLAlchemy's `NO_VALUE` sentinel as oldvalue (not None); it must early-return so creation records no spurious rename event and never binds the sentinel into the username lookups
  - log: 2026-06-18 functional run exposed live log spam + a bogus creation event (`type 'LoaderCallableStatus' is not supported`); guard changed to `if not isinstance(oldvalue, str) or oldvalue == value`; covered by `test_create_user_records_no_rename_event`

### Tests

- [x] **Unit: rename sync orchestration** - renaming an ORM user fires the listener: NativeAuth UserInfo username updated + authorisation preserved, a rename event recorded, the event names the actor when set, a same-value set records nothing, and user creation (NO_VALUE oldvalue) records no rename event
  - log: 2026-06-18 `tests/test_rename_sync.py` (4 tests, in-memory JH + NativeAuth orm); `make test`-runnable
- [x] **Functional: SPA rename flow** - a Playwright test renames a stopped user from the Configure screen (confirm dialog -> rename), asserts navigation to the new profile and the actor-named rename event in the feed; carries `@pytest.mark.acc_crit("rename-user::...")`
  - log: 2026-06-18 `tests/functional/test_rename_user.py` added; collects + declares acc_crit (runs against a live stack in the harness)

### API

- `POST /hub/api/users/{name}/rename` body `{ "name": "<newName>" }` (admin) -> renames via the orm + records the actor event; returns `{ "name": "<newName>" }`; 400 blank/unchanged, 404 no such user, 409 name clash

## resource bars (limits + tooltips)

The CPU/Memory/GPU progress bars on the "Server Status" panel (the server card's right half), the Servers table, and the Home "Host Status" widget (renamed from "Total resources usage"; the server card's status+controls half is titled "Server Control"). Each bar must read 0-100% against the right reference (a quota-limited user's bar measures against THEIR ceiling, not the host) and every bar must carry a hover tooltip with the precise breakdown. Backend `docker_utils.get_container_stats`; frontend `liveSource` (`getServerHero`/`getServers`/`getTotalResources`) + `components/meters.tsx` (`ResourceBars`).

### CPU bar reference

- [x] **Quota detected two ways** - `get_container_stats` reads BOTH `HostConfig.NanoCpus` (DockerSpawner `cpu_limit`) and `HostConfig.CpuQuota`/`CpuPeriod` (the cpu-quota-* cgroup groups); either yields `cpu_cores` + `cpu_cores_limited=True`
  - log: 2026-06-17 FIXED - was NanoCpus-only, so a quota-group user (konrad: CpuQuota=3200000 -> 32 cores) reported `cpu_cores=64` host, `limited=False`
- [x] **CpuPeriod default** - a quota set without an explicit period uses the kernel cfs default 100000 (so 3200000/100000 = 32)
  - log: 2026-06-17 implemented (`cpu_period = hostcfg.get('CpuPeriod') or 100000`)
- [x] **No limit -> host cores** - absent any limit, `cpu_cores` = `online_cpus`, `cpu_cores_limited=False`
  - log: 2026-06-17 retained
- [x] **Bar is usage/assignment** - the CPU bar value = `cpu_percent / cpu_cores` clamped 0-100 (`cpuBarPct`), parallel to the memory bar's usage/limit; docker's `cpu_percent` is cores-used x 100, so a multi-core container previously overflowed past 100%
  - log: 2026-06-17 implemented (`liveSource.cpuBarPct`, applied in getServers + getServerHero)
  - log: 2026-06-18 superseded for the Servers widget+page by [[acc-crit-servers-host-relative-resources]] (those cells are counters not bars - CPU counter now % of host, counter COLOUR = % of assigned); this usage/assignment bar is retained for the Server Status hero only
- [x] **CPU tooltip names the ceiling** - `cpuTip` = "N cores assigned" (limited) or "N cores host (no limit)"
  - log: 2026-06-17 present; now reads "32 cores assigned" for konrad

### Memory bar reference

- [x] **Bar is usage/limit** - `memory_percent` = usage / container memory limit; a 256 GiB-limited user reads against 256 GiB, not host RAM
  - log: 2026-06-17 verified live (konrad memory_total_mb=262144 reflected) - was already correct
  - log: 2026-06-18 superseded for the Servers widget+page by [[acc-crit-servers-host-relative-resources]] (those cells are counters not bars - MEM counter now shows GB used, counter COLOUR = % of assigned); usage/limit retained for the Server Status hero
- [x] **memory_limited flag** - the service exposes whether the bar's denominator is an explicit per-user limit or the host fallback, parallel to `cpu_cores_limited`; from `HostConfig.Memory > 0`
  - log: 2026-06-17 added so the tooltip can name "assigned" vs "host (no limit)" - previously the hero tooltip said "of host RAM" unconditionally (the reported bug)
- [x] **Memory tooltip names the ceiling honestly** - "N GB used of M GB assigned" when `memory_limited`, else "of M GB host (no limit)"; Servers also annotates "(over warning threshold)" on a `memory_max_usage_mb` breach
  - log: 2026-06-17 FIXED - hero was "X GB of host RAM" regardless; both paths now flag-driven (`getServers`, `getServerHero`)
- [x] **Usage excludes page cache** - `memory_mb`/`memory_percent` use `mem_usage_excluding_cache(memory_stats)` = cgroup `usage` minus `total_inactive_file` (v1) / `inactive_file` (v2), the exact figure `docker stats` and Docker Desktop show; the raw `usage` counts reclaimable file cache, so an idle file-heavy container over-reported tens of GB
  - log: 2026-06-18 FIXED (regression) - operator caught Host Status reading "143 of 256 GB" while Docker Desktop showed 41 GB; root cause `stats_from_container` used raw `usage` (page cache included); `docker_utils.mem_usage_excluding_cache` added + used, summed host now 41.7 GB matching Docker; `tests/test_docker_resource_assignment.py` +5 cases

### Granular assigned-resource service design

- [x] **Pure, tested helpers** - `derive_cpu_assignment(hostcfg, online_cpus)`, `derive_memory_assignment(hostcfg, stats_limit_bytes)` and `mem_usage_excluding_cache(memory_stats)` in `docker_utils` are pure functions, unit-tested independently of Docker (13 cases), so the assignment + usage logic is granular and verifiable, not inlined in the socket call
  - log: 2026-06-17 operator "make sure the service that calculates it is properly designed and granular" - extracted both; `tests/test_docker_resource_assignment.py`, 600 backend pass
- [x] **Edge: nano-cpus wins over quota; zero mem limit = unlimited** - explicit `NanoCpus` takes precedence over a cfs quota; `HostConfig.Memory == 0` reads as host fallback, not a 0-byte ceiling
  - log: 2026-06-17 covered by `test_cpu_nano_cpus_wins_over_quota`, `test_memory_zero_limit_is_unlimited`
- [x] **Exposed on /activity** - per-user `memory_limited` added (default `False`, set from the stats passthrough in `handlers/activity.py`)
  - log: 2026-06-17

### Colour ramp (mem + cpu, both Total and the widget)

- [x] **Calm to 50%** - the CPU/memory fill keeps the default accent up to and including 50% (`meters.barColor` returns undefined)
  - log: 2026-06-17 operator "only past 50% mark start slowly changing colours"
- [x] **Gradual ramp past 50%** - 50-75% blends accent -> warning, 75-90% blends warning -> danger, and >=90% saturates to full danger via `color-mix` (smooth, design-token based, no hardcoded RGB) so a near-full bar reads strong red, not pale orange
  - log: 2026-06-17 `meters.barColor`
  - log: 2026-06-18 operator "~95% must be much more red, not pale red" - was linear 75-100% so 93% gave only 72% danger; now full `--color-danger` at >=90%, ramp steepened across 75-90
  - log: 2026-06-18 functional coverage added - `tests/functional/test_resource_bars.py::test_bar_at_90pct_uses_danger_token` asserts the `/design-language` 90% bar fill uses `var(--color-danger)` (== the Stop-button red); PASSED (default-mode suite)
- [x] **Smooth recolour** - the fill transitions width + background ~0.4s so a value change eases rather than jumps
  - log: 2026-06-17 inline transition on the bar fill
- [x] **CPU/memory only** - the ramp rides the standard fill bar; GPU rows (labelled striped per-GPU bars) and the activity meter keep their own colours
  - log: 2026-06-17 applied only on the `<i style=width>` branch in `ResourceBars`
- [x] **Both surfaces** - one helper in `meters.tsx`, used by the "Server status" panel and the "Host status" widget alike
  - log: 2026-06-17

### Tooltips on every bar

- [x] **Bar + value carry the tip** - `ResourceBars` puts `title={r.tip}` on BOTH the `.oh-res-bar` span and the value readout, so hovering the bar itself (not only the %) shows the breakdown
  - log: 2026-06-17 verified (meters.tsx)
- [x] **Host status tips populated** - the Home "Host status" rows pass `tip` for CPU (`cpuTip`) and Memory (`memTip`); previously they passed none so the bars had no tooltip
  - log: 2026-06-17 FIXED - added `cpuTip` to `getTotalResources`, passed `total.cpuTip`/`total.memTip` in Home.tsx
- [x] **Host status tips quote % used** - both Host CPU and Memory tooltips lead with a `N% used` line (the bar value) followed by the absolute breakdown (`~N of H cores ...` / `N of M GB ...`), multiline like the per-server widget
  - log: 2026-06-17 added - `getTotalResources` now derives `cpuBar`/`memBar` and prefixes both tips; memTip also names the host total GB
- [x] **Host memory denominator is host RAM** - the Host memory bar + tooltip divide by `activity.memory_host_total_mb` (real host RAM), NOT `active[0].memory_total_mb` (which is the first user's cgroup ceiling when that user is mem-limited, and would over-report the host %)
  - log: 2026-06-17 adversarial-sweep finding - `getTotalResources` was using the first active user's ceiling; fixed to `memory_host_total_mb` (matching getServers/getServerHero)
  - log: 2026-06-18 FIXED (regression) - backend `_host_total_memory_mb()` returned None because `import psutil` always failed (psutil not in the hub image), so the frontend kept falling back to `active[0].memory_total_mb` (256 GB cap); now reads `/proc/meminfo` MemTotal directly -> 503 GB real host RAM, psutil only a secondary fallback
- [x] **Mock parity** - the demo (`mockSource`) matches live: `getTotalResources` returns `cpuTip`/`memTip` leading with `N% used`, and the activity meter carries `activityHours` (so the tooltip's "Active on average Nh/day" line shows in demo too)
  - log: 2026-06-17 adversarial-sweep finding - mock lacked both; added to `toServerRow`/`toUserRow`/`getServerHero`/`getTotalResources`
- [x] **Per-server memory tooltip leads with % used** - the per-server memory tooltip leads with `N% used` (the bar value), matching CPU and the Host tooltips, then the absolute `X of Y GB assigned/host` line and the `% of host` line; previously it led with `X GB used`
  - log: 2026-06-17 operator "unify memory to lead with % used too" - `getServers` + `getServerHero` (live), `toServerRow` + `getServerHero` (mock), and the `/design-language` example
- [x] **Total CPU is host-relative** - the aggregate CPU bar = total cores-used / host cores (largest assigned-core count among active servers), not a clamped sum that always pegged ~100%
  - log: 2026-06-17 implemented; tip reads "~N of H cores in use across M servers"
- [x] **GPU tooltips native** - per-GPU bars carry the standard browser `title` (name/UUID/memory/util/temp/power), not a bespoke antd popup
  - log: 2026-06-17 verified (gpuTip returns a \n-joined string)
- [x] **GPU rows always show striped bars** - a GPU row with devices renders one labelled striped bar per device whether or not live utilisation is sampled; absent utilisation the bars render at zero fill (empty striped track), never collapsing to inventory chips
  - log: 2026-06-18 operator "it must ALWAYS be there" - striped bars were gated on `r.gpus` (utilisation) since 6aee137, falling back to `GpuInventory` chips when the sidecar reported devices but no load; `ResourceBars` now always renders `GpuMeter gpus={utils ?? devices.map(d => d.utilizationPct ?? 0)}` (covers server hero, host status, mock in one place); `GpuInventory` now unused
- [x] **Multiline tooltips** - the Servers memory/volume/system tooltips are `\n`-joined (one fact per line) like the GPU tooltip, not a single long " / "-joined string; the desktop table's native `title` breaks on `\n` and the mobile drawer's inline `detail` uses `white-space: pre-line`
  - log: 2026-06-17 operator (repeat) "tooltips weirdly long, must be multiline broken nicely" - memTip/volTip/sysTip switched to `[...].filter(Boolean).join('\n')`; Metric detail div got `pre-line`

### Edge cases

- [x] **Edge: just-started container** - empty `precpu_stats` -> get_container_stats try/except returns None -> bars show "-" rather than 500
  - log: 2026-06-17 verified (whole body guarded)
- [x] **Edge: no active servers (totals)** - `getTotalResources` returns cpu/mem 0 with the real GPU inventory still surfaced
  - log: 2026-06-17 verified
- [ ] **Runtime: konrad CPU bar reads against 32 cores** - on the live hub the CPU bar + tooltip reflect his 32-core quota, not 64 host
  - log: 2026-06-17 backend confirmed live (`cpu_cores=32` after fix pending rebuild); on-screen confirm pends operator rebuild
- [x] **Edge: GPU absent** - `gpuSupported()` false (live `window.jhdata.gpu_enabled` false) -> GPU rows hidden entirely, not a "-" row
  - log: 2026-06-17 default tightened to false in live mode (was `?? true`)

### Tooltip percentages (added 2026-06-17)

The bars are 0-100% but the tooltips must also quote the live usage %, not only the assigned ceiling, on BOTH the server-resources widget and the servers-list per-user cells (identical tooltip text on both surfaces).

- [ ] **CPU tooltip shows % used** - in addition to "N cores assigned" / "N cores host (no limit)", the CPU tooltip quotes the live usage % (the bar value)
  - log: 2026-06-17 criterion added (#245)
- [ ] **Servers-list CPU cell = same tooltip as the widget** - the per-user CPU cell on the Servers list uses the exact same tooltip text as the server-resources CPU bar
  - log: 2026-06-17 criterion added (#245, #10); currently the list cell tip differs
- [ ] **Memory tooltip shows % of assigned + % of total** - alongside the assigned info ("X GB used of Y GB assigned/host"), the memory tooltip states the % of the assigned that is used AND the % of the host total it is
  - log: 2026-06-17 criterion added (#246)
- [ ] **Edge: unlimited memory** - when not limited (host fallback), "% of assigned" and "% of total" coincide; show one clearly rather than a redundant duplicate
  - log: 2026-06-17 criterion added (#246)
- [ ] **Reflected in the design language** - the "tooltip carries the live % + the assigned reference" rule appears on /design-language as a visual cue
  - log: 2026-06-17 criterion added (#252)

## restart/stop progress feedback

During a server restart or stop the progress modal must clearly read as "something is happening": the bar creeps (it no longer sits at a static full bar that looks done) and a rotating funny "loading…" line plays underneath, sourced from a ready package.

- [x] **Creeping bar** - while busy the bar eases toward (never reaching) 90%, so it reads as ongoing work instead of a static 100% that looks complete
  - log: 2026-06-17 creep interval in `ServerLifecycle.tsx` (was indeterminate-at-100, which looked finished)
- [x] **Active style** - the bar keeps antd's `status="active"` shimmer while busy
  - log: 2026-06-17
- [x] **Rotating flavour line** - a random message rotates every ~1.6s below the bar
  - log: 2026-06-17 `getRandomMessage()` from the `loading-messages` package
- [x] **Ready package** - flavour text comes from the `loading-messages` npm package (MIT, 305 messages), not a hand-rolled list
  - log: 2026-06-17 added as a dependency; resolved via `make install`; no docker-specific package exists, this is the closest maintained one
- [x] **Untyped shim** - a `declare module 'loading-messages'` ambient type lets TS import the untyped package
  - log: 2026-06-17 `src/vite-env.d.ts`
- [x] **Settle** - on success the bar jumps to 100% (success colour) and the modal auto-closes; the flavour line and timers stop
  - log: 2026-06-17 intervals cleared on leaving `busy`
- [x] **Edge: error** - on failure the bar shows the exception state and the flavour line is hidden; modal stays open with Close
  - log: 2026-06-17 flavour rendered only in `busy` phase

## Roles reference page

A read-only reference page under Advanced documenting the two IMPLICIT platform roles (admin, user) and the access each is granted across every page and action. Roles are not assigned by name - the platform derives them from JupyterHub's `admin` flag (admin) vs a regular authenticated, authorised account (user). Page: `Roles.tsx`, route `/roles`, nav under Administration -> Advanced. Verified against the code 2026-06-18.

### Placement + access

- [x] **Under Advanced** - the page is a leaf in the Administration -> Advanced submenu, beside Settings and Tokens
  - log: 2026-06-18 added to `nav.ts` NAV_ADMIN Advanced children (`/roles`, shield icon)
- [x] **Admin-only** - the route is under RequireAdmin; a plain user never reaches it
  - log: 2026-06-18 `/roles` inside the RequireAdmin block in `router.tsx`
- [x] **Read-only reference** - no writes, no footer; pure documentation (like Settings reference)
  - log: 2026-06-18 static curated data, no mutations

### Roles are implicit (documented here, not on the page)

The roles are implicit - NOT assigned by name. The platform derives the role from JupyterHub's `admin` flag (admin) versus a regular authenticated, authorised account (user). A guest role is planned for the future but is not added now. This explanation lives in this acc-crit, not as on-page prose.

- [x] **Implicit model captured in acc-crit** - the implicit-role explanation is recorded here (above), not as an inline Notice on the page
  - log: 2026-06-18 operator removed the on-page intro text ("remove that text") and asked for it as acc-crit ("all that -> acc crit"); the page conveys the derivation only through the definitions table
- [x] **Role definitions single panel** - the role definitions live in ONE panel ("Role definitions") holding a single table, not per-role prose cards
  - log: 2026-06-18 operator: "it was supposed to be panel with table with rows" / "make it as table in the panel (single panel)"; replaced the two `Card` prose blocks with one `Card` + `Table<RoleDef>`
- [x] **Role table columns** - columns are Role, Description, How assigned, Who; descriptions terse (technical-documentation style); Who is a terse example audience, not names
  - log: 2026-06-18 operator: "role name; description; how assigned; who (examples - not names, just terse description)"; `roleColumns`
- [x] **Admin row** - terse: full read/write/create/remove across fleet, users, groups, platform; assigned = holds JupyterHub's `admin` flag (JUPYTERHUB_ADMIN at login, or toggled on Users); who = operators, maintainers
  - log: 2026-06-18 `ROLES[0]`
- [x] **User row** - terse: own server + profile only, no fleet/user/group rights; assigned = authenticated, authorised account without the admin flag; who = data scientists, notebook authors, learners
  - log: 2026-06-18 `ROLES[1]`
- [x] **Guest not on the page** - guest is documented as a planned future role here only; it is NOT shown on the page and NOT added as a current role
  - log: 2026-06-18 operator: "in the future we will have guest also" / "but don't add guest"; not in the definitions table

### Access matrix (every page + function, per role)

- [x] **One row per capability** - the matrix lists each page AND each action (server lifecycle, user admin, groups/policy, platform), grouped by area
  - log: 2026-06-18 operator: "list each function each page"; `CAPS` grouped by area (Pages / Server / Users / Groups / Platform)
- [x] **Per-capability description** - every capability row carries a terse description column stating the read/write/list/create/remove rights it entails, not only the few rows that needed a caveat
  - log: 2026-06-18 operator: "provide short explanation (description colum) - terse style" / "also focus on read, write, list, remove, create rights"; added the required `desc` field to every `Cap` and a Description column
- [x] **A column per role** - Admin and User columns, one access cell each
  - log: 2026-06-18 two role columns
- [x] **Access level per cell, not just yes/no** - each cell shows the level: Full / Self only / View / Denied (the operator's "access level or deny or etc")
  - log: 2026-06-18 `Level` = full|self|view|none, rendered as coloured pills
- [x] **Colour-coded pills** - access levels render as pills on the shared palette (green full, amber self-only, blue view, red denied), per the design-language state=colour rule
  - log: 2026-06-18 `AccessPill` (color-mix tints of success/warning/accent/danger)
- [x] **Accurate to the code** - the matrix reflects the real gating: RequireAdmin page gating + the handlers' self-or-admin rules (e.g. start/stop = self for user, full for admin; rename/groups/broadcast = admin only)
  - log: 2026-06-18 sourced from `router.tsx` RequireAdmin + ops/handlers; cross-ref [acc-crit-rename-user], [acc-crit-navigation-patterns]
- [x] **Notes for nuance** - rows whose access needs a caveat (own-only, admin-can-enter-any, rename needs stopped server) carry a muted sub-note
  - log: 2026-06-18 `note` sub-line under the capability
- [x] **Zebra rows** - the matrix tables use the mandatory alternating-row striping
  - log: 2026-06-18 `rowClassName` oh-row-alt (design-language)

### Verification

- [x] **Frontend gates** - `npx tsc -b`, `npm run lint`, `npm run build:hub` clean with the new page + route + nav
  - log: 2026-06-18 all green

## server lifecycle UX (inline spinners, no modal, real log)

Server start/restart/stop show progress with an INLINE spinner on the control (no modal popup): the op fires, a background monitor polls the real hub status until the transition lands, then the affected views refresh immediately. A spawning server shows a rotating spinner (not the old ekg/activity glyph), and the spawn log opens the real Start-server page.

### Restart / Stop (no modal, inline spinner)

- [x] **No modal** - the restart/stop progress modal (creeping bar + flavour text) is removed; `ServerLifecycle` is a context provider with no popup UI
  - log: 2026-06-17 `app/ServerLifecycle.tsx` rewritten; `loading-messages` dep removed (its only use was the modal)
- [x] **Inline spinner** - while restarting/stopping, the control shows a spinner in place of its icon (hero buttons via antd `loading`; row actions via `IconAction busy`)
  - log: 2026-06-17 `ServerHero.tsx` `loading={busy===...}`, `IconAction` gained a `busy` prop, `Servers.tsx` row actions pass `busy={mode===...}`
- [x] **Background monitor + immediate refresh** - the op's `run()` toasts + invalidates on POST; `pollUntil` then monitors the real status until the transition lands, then invalidates servers/hero/resources/stats so the views update at once
  - log: 2026-06-17 `runOp` in `ServerLifecycle.tsx`
- [x] **Conflicting controls disabled** - other lifecycle buttons disable while a transition is in flight (the busy map)
  - log: 2026-06-17 `disabled={busy}`
- [x] **Failure surfaces as a toast** - a failed POST shows the op's error toast (no stuck modal); busy clears
  - log: 2026-06-17 `run()` error toast + `clearBusy` in catch

### Spawning (rotating spinner, real log)

- [x] **Rotating spinner, not ekg** - a spawning server's row shows an antd `Spin`, not the activity/ekg icon
  - log: 2026-06-17 `Servers.tsx` rowActions spawning branch
- [x] **Real spawn log** - "View spawn log" navigates to the real Start-server page (`/servers/{user}/starting`, live progress + container-log tail), not a `(mock)` toast
  - log: 2026-06-17 was `mockAction('Tail live spawn log')`; now `nav(.../starting)` - #238 mock removed
- [x] **Per-row probe/refresh on ready** - the servers list fast-polls (2.5s) while any server is spawning, so a spawning row flips to active within ~2.5s of ready; `statusOf` reads the post-spawn settle window as spawning so the fast poll engages
  - log: 2026-06-17 adaptive poll + `statusOf` settle fix (see acc-crit-background-refresh)
- [ ] **Runtime: spinner + heal** - on the live hub a spawning row shows the spinner and flips to active within ~2-3s of ready
  - log: 2026-06-17 code + build clean; on-screen confirm pends operator rebuild

### Starting / restarting ANOTHER user's server - inline, no nav (#243, supersedes #237)

Starting or restarting another user's server from the Servers widget or list must NOT navigate to the start/progress screen. It behaves exactly like Stop/Restart already do: an inline spinner on the play (or restart) button until the server is up, then an immediate row refresh.

- [ ] **No start-screen navigation** - starting another user's server does not route to `/servers/{user}/starting`
  - log: 2026-06-17 criterion added (#243) - reverses the earlier #237 decision (which routed admin starts to the start screen)
- [ ] **Inline play spinner** - the play button shows the SAME inline spinner pattern as the stop button (`IconAction busy` / hero `loading`) while the server starts
  - log: 2026-06-17 criterion added (#243)
- [ ] **Restart same** - restarting another user's server is also inline-spinner + refresh, no navigation
  - log: 2026-06-17 criterion added (#243)
- [ ] **Background monitor + immediate refresh on ready** - the existing `runOp`/`pollUntil` monitor drives the start too; the row flips to active immediately when the server is up (reuse the start op, add a `start` mode to the lifecycle busy map)
  - log: 2026-06-17 criterion added (#243)
- [ ] **Self-start unchanged** - a user starting their OWN server keeps the start page (this only changes starting someone ELSE's server); confirm the self path still shows progress
  - log: 2026-06-17 criterion added (#243) - clarify scope vs the dedicated start page
- [ ] **Reflected in the design language** - the "admin start = inline spinner, not a nav" cue is on /design-language
  - log: 2026-06-17 criterion added (#252)

## server status immediacy

After a server starts or stops, the hub status (hero + table) must reflect the new state immediately, not ~10s later. The authoritative signal is the spawner state from `/users/{user}` (`ready`/`pending`), not the activity sampler's `server_active`/`recently_active`, which lags by one ~10s sample.

- [x] **Spawner is authoritative for presence** - `statusOf` derives status from `srv.ready` / `srv.pending`, dropping the stale `|| a.server_active` OR that kept a just-stopped server showing active
  - log: 2026-06-17 `liveSource.statusOf` rewritten
- [x] **Hero fetches the spawner** - `getServerHero` now fetches `/users/{user}` and derives status from `servers['']`, so it no longer trusts only the lagging activity snapshot
  - log: 2026-06-17 `getServerHero` Promise.all includes the raw user
- [x] **Start reflects immediately** - a just-started (ready) server reads active/idle at once
  - log: 2026-06-17 `srv.ready ? (recently_active ? active : idle)`
- [x] **Stop reflects immediately** - a just-stopped server reads offline at once, not active-for-10s
  - log: 2026-06-17 spawner absence wins over the stale sample
- [x] **Spawning shown** - `srv.pending === 'spawn'` reads as spawning
  - log: 2026-06-17
- [x] **Resources still keyed on the sample** - CPU/memory stay keyed on `server_active` (they only exist once stats are sampled), while presence comes from the spawner
  - log: 2026-06-17 deliberate split
- [ ] **Runtime: no 10s lag** - on the live hub the status flips within one refresh of start/stop
  - log: 2026-06-17 code done + builds; on-screen confirm pends operator rebuild

## Servers host-relative resources

On the Servers widget (Home) and the Servers page table the per-server CPU/MEM cell is a numeric COUNTER (no progress bar): CPU shows the server's total CPU usage in the docker/top convention (100% = one core, so 1300% means the server is saturating ~13 cores) and MEM shows the absolute GB used. The counter's COLOUR encodes the server's usage as a % of its own ASSIGNED quota. The Server Status hero widget is unchanged and remains the only surface showing % of assigned (with its bars). Tooltips reveal the full breakdown.

### Supersedes

- replaces, for the Servers widget + Servers page only, the per-server "bar = usage/assignment" rule in [[acc-crit-resource-bars]] (CPU "Bar is usage/assignment", Memory "Bar is usage/limit") - the Servers list cells are counters, not bars; that usage/assignment BAR is retained for the Server Status hero
- replaces the Servers-page cell display + tooltip rules in [[acc-crit-servers-resource-cells]] (Mem tooltip breakdown, Mem over-quota, CPU assigned cores) with the host-relative counter + quota-colour + full-breakdown-tooltip rules below

### CPU counter - total cores used (100% per core)

- [ ] **CPU counter = cores-used %** - the per-server CPU cell shows the raw `cpu_percent` in the docker/top convention (100% = one core), e.g. 1300% means the server is saturating ~13 cores; NOT clamped to 100 and NOT divided by host cores
  - log: 2026-06-18 criterion added (operator "CPU and MEM need to show % of total (host) ... all servers CPU % add up to 100%"); 2026-06-18 corrected "bar" -> "counter"
  - log: 2026-06-18 CHANGED from "% of host" to total cores-used % (operator "1300% means server saturated 13 cores capacity; other platforms measure it like this") - values no longer sum to 100%
- [ ] **No host-count denominator** - the counter is the raw cores-used %, so it needs no host CPU-core count from the backend (`cpu_percent` is already on `/api/activity`)
  - log: 2026-06-18 replaced the earlier "host CPU count denominator" criterion - no longer needed after the cores-used % change

### MEM counter - absolute GB

- [ ] **MEM counter = absolute GB** - the per-server MEM cell shows the actual GB used (e.g. "19.2 GB"), never a % and no bar; the MEM counters across active servers sum to the host total GB used
  - log: 2026-06-18 criterion added (operator "in Mem we don't show % but the actual GB used"); 2026-06-18 corrected "bar" -> "counter"
- [ ] **Host RAM in tooltip, not on the cell** - the host total (`memory_host_total_mb`) and the % of host appear in the tooltip; the cell itself stays a raw GB figure
  - log: 2026-06-18 criterion added

### Counter colour - % of assigned (quota)

- [ ] **Colour encodes quota usage, not the displayed value** - both the CPU and MEM counter COLOUR is driven by the server's usage as a % of its ASSIGNED quota, independent of the host-relative value the counter shows
  - log: 2026-06-18 criterion added (the key non-obvious design point: counter value = host share, counter colour = quota usage)
- [ ] **Reached quota -> danger** - at >= 100% of the assigned quota the counter colours danger (`--color-danger`, the Stop-button red)
  - log: 2026-06-18 criterion added (operator "if someone reached quota - we show in dangerous colour")
- [ ] **>= 75% and < quota -> warning** - between 75% and 100% of assigned the counter colours warning
  - log: 2026-06-18 criterion added (operator ">=75% of quota and still < quota - warning colour")
- [ ] **< 75% -> normal** - below 75% of assigned the counter keeps the normal text colour
  - log: 2026-06-18 criterion added
- [ ] **CPU quota source** - the CPU quota % uses `cpu_percent / cpu_cores` (the assigned-core ceiling already on `/api/activity`)
  - log: 2026-06-18 criterion added
- [ ] **MEM quota source** - the MEM quota % uses `memory_percent` (usage / assigned limit already on `/api/activity`)
  - log: 2026-06-18 criterion added

### Tooltips reveal all

- [ ] **CPU tooltip full breakdown** - the CPU tooltip lists usage in cores, the assigned ceiling, the % of assigned used, and the quota-crossing state
  - log: 2026-06-18 criterion added (operator "tooltip reveals all, incl crossing the quota info")
- [ ] **MEM tooltip full breakdown** - the MEM tooltip lists GB used, the assigned ceiling, the % of assigned used, the % of host total, and the quota-crossing state
  - log: 2026-06-18 criterion added
- [ ] **Quota-crossing line** - when usage is >= 75% the tooltip states "over warning threshold"; when >= 100% it states the quota is reached/exceeded
  - log: 2026-06-18 criterion added
- [ ] **Multiline** - tooltips are `\n`-joined (one fact per line), consistent with the existing servers tooltips
  - log: 2026-06-18 criterion added

### Column header tooltips

Explanatory tooltips on the CPU/MEM column headers of BOTH the Servers page table and the Servers widget on Home, so the host-relative figures are not misread; distinct from the per-cell value tooltips above (which break down a single server).

- [ ] **CPU header tooltip** - hovering the CPU column header explains it measures total CPU usage where 100% = one core (e.g. 1300% = ~13 cores)
  - log: 2026-06-18 criterion added (operator "explanatory tooltips over servers page table columns, specifically CPU and MEM to indicate what they measure")
  - log: 2026-06-18 reworded - measures "% of total system used by the server", not "share of host CPU" (operator correction)
  - log: 2026-06-18 reworded again - CPU now shown as total cores-used % (100% per core); tooltip explains the per-core convention (operator "1300% means server saturated 13 cores")
- [ ] **MEM header tooltip** - hovering the MEM column header explains it measures the actual memory used in GB
  - log: 2026-06-18 criterion added
- [ ] **Both surfaces** - the explanatory CPU/MEM header tooltips appear on both the Servers page table and the Home Servers widget
  - log: 2026-06-18 criterion added (operator "that tooltip must be on servers page and widget")

### Server Status hero unchanged

- [ ] **Hero keeps bars at % of assigned** - the Server Status hero widget keeps its CPU/MEM bars showing usage as a % of the server's ASSIGNED quota (`cpuBarPct` / `memory_percent`); it is the ONLY surface showing % of assigned and must not switch to host-relative counters
  - log: 2026-06-18 criterion added (operator "the only place where we see the % of assigned - is the Server Status widget")

### CPU progressbars (Host Status + Server Status widgets)

CPU is reported the same docker/top way (cores-used; 100% = one core) on the progressbar widgets, just expressed as a 0-100 bar fill plus a tooltip that reveals both the % of total host compute and the % of total assigned compute.

- [ ] **Server Status hero CPU bar capped at assigned cores** - the hero CPU bar FILL is the % of the server's ASSIGNED cores (`cpuBarPct`, 0-100) - the one CPU bar capped at its assignment
  - log: 2026-06-18 criterion added (operator "the Server Status has progressbar capped at its assigned cores")
- [ ] **Host Status CPU bar = % of host compute** - the aggregate CPU bar FILL is total cores-used / host cores (0-100% of total host compute)
  - log: 2026-06-18 criterion added
- [ ] **CPU bar tooltips show both percentages** - both CPU bar tooltips reveal cores used plus BOTH the % of total host compute and the % of total assigned compute (each 0-100)
  - log: 2026-06-18 criterion added (operator "in the tooltips we must show the % of total too ... 0-100% of total CPU compute and total assigned compute")
- [ ] **Memory bars unchanged** - the change is CPU-only; the hero memory bar stays % of assigned and the Host memory bar stays % of host RAM
  - log: 2026-06-18 criterion added (operator "i mean CPU progressbars")
- [ ] **Edge: host CPU count approximated** - the host-core denominator is the largest assigned-core count among active servers (an unlimited server's assignment IS the host count); a fully cpu-limited fleet would under-state the host denominator until a real host CPU count is exposed
  - log: 2026-06-18 criterion added - reuses the existing getTotalResources approximation; no backend host-CPU-count was added

### Edge cases

- [ ] **Edge: unlimited quota** - when a server has no CPU/MEM limit the assigned ceiling is the host capacity, so the colour ramps against host cores / host RAM and the tooltip says "no limit"
  - log: 2026-06-18 criterion added
- [ ] **Edge: no quota configured** - when the platform quota env is 0/unset the colour never reaches warning/danger from that quota and the tooltip omits the quota clause
  - log: 2026-06-18 criterion added
- [ ] **Edge: server stopped** - the CPU/MEM counters read the muted dash when the server is not running (no host-relative figure invented)
  - log: 2026-06-18 criterion added
- [ ] **Edge: host RAM unknown** - when the host RAM total is unavailable the MEM tooltip's "% of host" line is omitted rather than fabricated; the GB figure (which needs no host total) still shows (see the no-fallback memory rule in [[acc-crit-resource-bars]])
  - log: 2026-06-18 criterion added; 2026-06-18 narrowed to host RAM only (CPU no longer uses a host-core denominator after the cores-used % change)
- [ ] **Edge: data not yet sampled** - before the first stats sample lands the counters show the muted dash, never a 0
  - log: 2026-06-18 criterion added

### Data sources (/api/activity per-user fields)

- `cpu_percent`, `cpu_cores`, `cpu_cores_limited` - usage (cores x 100), assigned cores, whether limited
- `memory_mb`, `memory_percent`, `memory_total_mb`, `memory_limited` - GB used, % of assigned, assigned ceiling, whether limited
- `memory_host_total_mb` - host RAM total (for the MEM tooltip's % of host)
- NEEDED: host CPU-core count (CPU counter denominator) - to be added to the payload

## Servers list layout

The Servers page table column structure, ordering, alignment, widths, and the user-name + time-left columns. Distinct from the Server widget (which intentionally clubs status + last-activity); the LIST keeps them as separate columns. `duoptimum-hub-web/src/pages/Servers.tsx`.

### Columns and order

- [ ] **Status and Last activity are separate columns** - the list does NOT club last-activity into the status label (unlike the widget); Status is its own column, Last activity its own
  - log: 2026-06-17 criterion added (#248)
- [ ] **Column order** - Status, then Last activity, then Activity tracker (left to right)
  - log: 2026-06-17 criterion added (#248)
- [ ] **Status column just wide enough** - the Status column is sized to its content, not over-wide
  - log: 2026-06-17 criterion added (#250)
- [ ] **Last activity column just wide enough** - same: sized to content, not over-wide
  - log: 2026-06-17 criterion added (#250)

### Activity column

- [ ] **Activity meter centered** - the activity tracker is centered within its column, not left-aligned
  - log: 2026-06-17 criterion added (#248)
- [ ] **Activity tooltip: real uncapped %** - the tooltip shows the REAL activity % which MAY exceed 100% (>100% is desirable - the user works more than the 8h/day target); not clamped
  - log: 2026-06-17 criterion added (#247); cross-ref [acc-crit-activity-scoring]
- [ ] **Activity tooltip multiline** - the % plus the existing info (avg active hours/day) on separate lines, not one super-long single line
  - log: 2026-06-17 criterion added (#247)

### Row actions

- [x] **No "View spawn log" action** - the spawning-row actions are the spinner + Cancel spawn only; the "View spawn log" icon (which navigated to the Start page) is removed - not needed
  - log: 2026-06-17 removed from `rowActions` spawning branch; `nav` still used by the offline-start branch

### User name column

- [ ] **Name is a link to the user** - the username links to the user config page (same target as the Users page), no artificial click-friction
  - log: 2026-06-17 criterion added (#249)
- [ ] **First + last name shown** - the cell shows the user's first and last name exactly like the Users page (name under / alongside the username), from the same profile source
  - log: 2026-06-17 criterion added (#249)

### Time-left column

- [ ] **Tooltip: hours over standard TTL** - the Time-left tooltip states how many hours over the standard (base) TTL the session currently is (the extension beyond the base timeout)
  - log: 2026-06-17 criterion added (#251)
- [ ] **Edge: not extended** - when the session is at or under the base TTL, the tooltip does not claim a negative over-hours (shows none / "within standard TTL")
  - log: 2026-06-17 criterion added (#251)

### Reflected in the design language

- [ ] **Visual cues on /design-language** - the column-separation, ordering, alignment, and name-as-link conventions are shown on the design-language page as visual cues (not before/after examples)
  - log: 2026-06-17 criterion added (#252); cross-ref [acc-crit-design-language]

## Servers resource cells

The Servers table enriches every resource cell with a full breakdown and its quota so an admin reads usage-vs-limit at a glance. Data comes from the `/api/activity` payload (per-user `memory_mb`/`memory_total_mb`, `volume_breakdown`, `container_size_rw_mb`/`container_size_rootfs_mb`, `last_activity`) plus the aggregate quotas (`memory_max_usage_mb`, `volume_max_total_size_mb`, `container_max_extra_space_mb`). Absent values render as the muted dash, never a fabricated zero.

- [x] **Mem column label** - the Memory column header reads "Mem"
  - log: 2026-06-17 implemented (Servers.tsx column title)
- [x] **Mem tooltip breakdown** - tooltip shows used vs configured per-user limit vs total host RAM (e.g. "19.2 GB used / 32 GB limit / 64 GB host")
  - log: 2026-06-17 implemented in liveSource.getServers memTip (code+typecheck verified; runtime render pending deploy)
  - log: 2026-06-18 cell display reworked by [[acc-crit-servers-host-relative-resources]] (counters, not bars: CPU = % of host, MEM = GB used; counter colour = % of assigned; tooltip reveals all incl quota-crossing)
- [x] **Mem over-quota** - cell flags (warn colour) when used exceeds the configured per-user limit; tooltip states it is over
  - log: 2026-06-17 implemented (memOver + " (over limit)" clause)
- [ ] **CPU assigned cores** - CPU cell/tooltip also shows how many cores are assigned to the user (per-user limit), not only % of host
  - log: 2026-06-17 NOT done - assigned cores not in current activity payload, must be exposed backend-side first (task #179)
- [x] **Volumes tooltip breakdown** - tooltip lists per-volume sizes (home / workspace / cache) and the total; shows the quota when the total is exceeded
  - log: 2026-06-17 implemented in liveSource.getServers volTip from volume_breakdown (code+typecheck; runtime pending deploy)
- [x] **Volumes over-quota** - cell flags (warn colour) when total exceeds the volume quota; tooltip states the quota
  - log: 2026-06-17 implemented (volumesOver + "quota exceeded" clause)
- [x] **System size breakdown** - tooltip shows base image size, writable layer size, and the quota (e.g. "base 3.1 GB + writable 1.4 GB / 10 GB quota")
  - log: 2026-06-17 implemented (base = rootfs - rw) in sysTip (code+typecheck; runtime pending deploy)
- [x] **System over-quota** - cell flags (warn colour) when writable layer exceeds the extra-space quota; tooltip states the quota
  - log: 2026-06-17 implemented (systemOver + " (over)" clause)
- [x] **Last activity column** - a "Last activity" column sits immediately after Status, showing time-ago of the last activity, shortened per design language ("2m", "3h", "2d")
  - log: 2026-06-17 implemented (Servers.tsx column + lastActivityISO + timeAgoShort; mock populated)
- [x] **GPU column gating** - the GPU column is shown only when the platform has GPU (window.jhdata.gpu_enabled), hidden entirely otherwise
  - log: 2026-06-17 implemented under task #173 (gpuSupported() spread; runtime pending deploy)
- [x] **Edge: server stopped** - resource cells (cpu/mem/system/last-activity) read the muted dash when the server is not running; volumes still show last-known size
  - log: 2026-06-17 verified by code: cpu/mem/system gated on running/non-null -> dash; volumesGB from last-known; lastActivityISO null when not running -> dash
- [x] **Edge: data not yet sampled** - before the first stats/volume sample lands, cells show the muted dash (or last-known for volumes), never a 0
  - log: 2026-06-17 verified by code: null-guards render muted dash; volumes seed from persisted last-known
- [x] **Edge: no quota configured** - when a quota env is 0/unset, the cell never flags over-quota and the tooltip omits the quota clause
  - log: 2026-06-17 verified by code: every over/quota clause guarded on max > 0
- [x] **Edge: no last activity** - users with no recorded activity show the muted dash in the Last activity column
  - log: 2026-06-17 verified by code: timeAgoShort on null/undefined -> muted dash render

### Data sources (existing /api/activity per-user fields)

- `memory_mb`, `memory_percent`, `memory_total_mb` - mem used / % host / host total
- `volume_size_mb`, `volume_breakdown` (suffix -> MB) - volumes total + per-mount
- `container_size_rw_mb`, `container_size_rootfs_mb` - writable layer + full rootfs (base = rootfs - rw)
- `last_activity` (ISO) - last activity timestamp
- aggregate quotas: `memory_max_usage_mb`, `volume_max_total_size_mb`, `container_max_extra_space_mb`
- MISSING: per-user assigned CPU cores (needs to be added to the payload for the CPU-cores criterion)

## dedicated Start-server page with live container-log feed

Starting your OWN server leaves the lightweight modal behind and navigates to a dedicated page that shows a spawn progress bar plus a rolling 10-15 line tail of the freshly-started container's logs, then redirects into the lab when it is ready. Restart/stop keep the small popup (they settle in seconds). Supersedes the start-page items under "Live QA - round 3" in `duoptimum-hub-web/acc-crit-portal-fixes.md`.

Two data sources: the **progress bar** rides the hub spawn-progress SSE (`GET /hub/api/users/{name}/server/progress`, no backend change); the **log feed** is the actual container stdout/stderr via a new backend tail endpoint (the SSE `message` field is spawn-progress text, not container logs).

### Implementation status (2026-06-17)

Code-complete; backend `make test` 566+63 green, portal `tsc -b` + `build:hub` clean. The visual "must look polished" criteria below are coded to spec but await the user's image rebuild for on-screen confirmation (no live verify possible here). Elegant architecture per directive: two focused hooks own the data, the page is composition + presentation only, and the start path is unified (no duplicate modal-vs-page logic).

- Backend: `ServerLogsHandler` (`handlers/server.py`) - `GET /api/users/{name}/server/logs?tail=N`, admin-or-self, tail capped at 200, 404 before the container exists; exported + route-registered; handler count test 27->29
- Frontend data: `hooks/useSpawnProgress.ts` (spawn POST + progress SSE + bounded status-poll fallback + mock ramp) and `hooks/useContainerLogTail.ts` (1.5s poll while spawning, stops on unmount, mock sample)
- Frontend page: `pages/Starting.tsx` at route `servers/:name/starting` (not admin-gated; backend enforces admin-or-self) - centered branded card, progress bar, terminal-styled log panel (`.oh-termlog` in global.css), redirect-on-ready (own -> lab, admin-other -> Servers), failure -> error + Back
- Start path unified: ServerHero, MobileHome, Servers, Home(preview) Start buttons now navigate to the page; `ServerLifecycle` trimmed to restart/stop only (the duplicated start/SSE/modal path removed)

### Page + navigation

- [ ] **Start -> dedicated page** - clicking Start on your own server navigates to `/servers/:name/starting` (no modal); restart/stop keep the lightweight popup
  - log: 2026-06-17 criterion added
- [ ] **Progress bar** - a progress bar bound to the spawn SSE advances with the hub's reported spawn progress (0-100)
  - log: 2026-06-17 criterion added
- [ ] **Auto-navigate on ready** - on the SSE `ready` event the page redirects into the running server (`userServerUrl`); there is NO Close/Continue button on the success path
  - log: 2026-06-17 criterion added
- [ ] **Failure path** - on `failed` (or stream drop without ready) the page shows the error + a Back-to-portal action; no auto-redirect
  - log: 2026-06-17 criterion added
- [ ] **Admin starting another user's server** - lands on the page; on ready returns to the parent screen (Servers), never auto-enters someone else's lab (consistent with the open-someone-else confirm rule)
  - log: 2026-06-17 criterion added

### Live container-log feed

- [ ] **Rolling tail** - the page shows the last 10-15 lines of the freshly-started container's logs, in a fixed-height monospaced panel that scrolls with new lines (newest at bottom)
  - log: 2026-06-17 criterion added; source = docker logs tail of jupyterlab-{name}
- [ ] **Live update** - the feed refreshes while spawning (poll ~1-2s or stream) so the user watches the container come up, not a frozen snapshot
  - log: 2026-06-17 criterion added
- [ ] **Stops on ready/redirect** - polling/stream stops when the page redirects or unmounts (no leaked timer/EventSource)
  - log: 2026-06-17 criterion added
- [ ] **Admin-or-self only** - the log endpoint is authorised to the server owner or an admin; a non-owner non-admin gets 403
  - log: 2026-06-17 criterion added
- [ ] **Bounded** - only a tail (N lines, capped) is returned; never the full log; never secrets echoed by the entrypoint beyond what the container itself prints
  - log: 2026-06-17 criterion added

### Look and feel (must look polished)

- [ ] **Centered, branded** - a single centered card with the Duoptimum Hub mark and the server name as a clear title ("Starting konrad.jelen's lab"), generous standard panel padding, no raw full-width sprawl
  - log: 2026-06-17 criterion added
- [x] **Terminal-styled log panel** - the log feed reads like a real terminal: monospaced, dark subdued panel, soft rounded corners, dim line text, fixed height (~10-15 rows) that scrolls, not a plain bulleted list
  - log: 2026-06-17 implemented (`.oh-termlog` in global.css)
- [x] **Wide enough, no line-wrap** - the panel is wide enough for real log lines and never breaks a line mid-content; long lines scroll horizontally
  - log: 2026-06-17 fixed (operator: lines were breaking) - start card `max-width` 560px -> 820px, `.oh-termlog` `overflow: auto`, `.oh-termlog-line` `white-space: pre` (no wrap)
- [ ] **Smooth progress** - the progress bar animates smoothly (antd Progress, accent blue), with a short human status line above it ("Pulling image...", "Starting server...") sourced from the latest SSE message
  - log: 2026-06-17 criterion added
- [ ] **No layout shift / no flicker** - the card and log panel reserve their space from first paint; new log lines append without the page jumping; the redirect on ready is clean, not a flash
  - log: 2026-06-17 criterion added
- [ ] **On-brand + design-language consistent** - colours, spacing, pills and typography match the rest of the portal (cross-check `/design-language`); dark-mode correct; tasteful, calm, not busy
  - log: 2026-06-17 criterion added
- [ ] **Graceful states look intentional** - waiting/placeholder, failure and "logs unavailable" states are styled (muted, centered, an icon), never raw error text
  - log: 2026-06-17 criterion added
- [ ] **Subtle motion** - a light spinner/pulse while spawning conveys liveness without being noisy; stops on ready
  - log: 2026-06-17 criterion added

### Edge cases

- [ ] **Edge: SSE unsupported / drops** - progress falls back to status polling (`isRunning`); the log feed still tails independently
  - log: 2026-06-17 criterion added
- [ ] **Edge: navigate away mid-spawn** - spawn continues server-side; returning to the page reflects current state (re-attaches SSE + log tail)
  - log: 2026-06-17 criterion added
- [ ] **Edge: container not created yet** - before the container exists, the log panel shows a muted "waiting for container..." placeholder, not an error
  - log: 2026-06-17 criterion added
- [ ] **Edge: logs unavailable** - if docker logs can't be read (permissions, container gone), the panel shows a muted notice and the progress bar still drives readiness
  - log: 2026-06-17 criterion added
- [ ] **Edge: very chatty container** - the tail is line-capped so a noisy container can't blow up the DOM/memory (keep last N only)
  - log: 2026-06-17 criterion added
- [ ] **Edge: spawn succeeds before page mounts** - if the server is already ready on mount, skip the wait and redirect immediately
  - log: 2026-06-17 criterion added
- [ ] **Mock parity** - in mock mode the page animates progress and shows a canned 10-15 line log sample so the demo shows the flow (no hub)
  - log: 2026-06-17 criterion added

### API

- existing: `GET /hub/api/users/{name}/server/progress` (SSE) - drives the progress bar; `_xsrf` as query param (EventSource can't set headers)
- NEW: `GET /api/users/{name}/server/logs?tail=15` -> `{lines: string[]}` (admin-or-self) - tails the spawned container (`docker logs --tail N jupyterlab-{name}`); 403 non-owner, 404 no container, capped tail
- existing: status poll (`GET /hub/api/users/{name}`) - SSE fallback for readiness

### Open decisions

- Log transport: simple short-poll of the tail endpoint (~1-2s) vs a streaming endpoint; poll is simpler and adequate for a 10-15 line tail - default to poll unless streaming is wanted
- Whether restart should also use this page or keep the popup (current: popup; restart settles in seconds)

## startup hydration

A single startup-hydration step warms every cache and fires the deferred checks ONCE at boot, so a (re)started hub shows a populated portal immediately instead of an empty one until an admin first opens the Activity page. Everything runs on the IOLoop after the hub is serving (best-effort, never blocks boot) and is consolidated behind one entry point. Module: `hydrate.py::schedule_startup_hydration`; wired in `config/jupyterhub_config.py` Section 5. Verified against the code 2026-06-18.

### Consolidation

- [x] **Single entry point** - one `schedule_startup_hydration(...)` call replaces the previously scattered startup work (lazy refresher starts in the `/activity` handler + the separate favicon and policy callbacks)
  - log: 2026-06-18 operator: "sweep this initial hydration and consolidate"; `hydrate.py`, config Section 5 one call
- [x] **Deferred, never blocks boot** - hydration is registered via `IOLoop.current().add_callback` and runs after the hub is serving; the synchronous boot work (bounded GPU probe, sidecar self-start, branding) stays where it is
  - log: 2026-06-18 mirrors `schedule_policy_startup` / `schedule_startup_favicon_callback` pattern
- [x] **Best-effort** - each hydration step is wrapped so a failure (docker unreachable, etc.) is logged and skipped, never crashing boot or the IOLoop
  - log: 2026-06-18 per-step try/except in `_hydrate`
- [x] **Shared with the handler (fallback)** - the `/activity` handler calls the same `start_activity_refreshers(...)`, so a direct `/activity` hit still works if hydration was skipped; the refreshers are idempotent
  - log: 2026-06-18 `start_activity_refreshers` is the single code path; refresher `start()` is `if periodic_callback is not None: return`

### Cache hydration (populate right away)

- [x] **Activity refreshers started at boot** - volume sizes + container sizes refreshers start at hydration; each `start()` submits an immediate first refresh, so the caches warm without waiting for the first request
  - log: 2026-06-18 `start_activity_refreshers`; `start()` does `get_executor().submit(_refresh_*)`
- [x] **GPU utilisation gated on hardware** - the GPU-utilisation refresher is started only when the host has GPUs (`gpu_list` enumerated at boot); GPU-less hosts skip it (no pointless sidecar polling)
  - log: 2026-06-18 `if gpu_list:` in `start_activity_refreshers`
- [x] **Live stats warmed for survivors** - servers that survived the restart get a live-stats sample triggered at hydration, so the activity map shows CPU/memory immediately
  - log: 2026-06-18 `_warm_survivor_stats` enumerates `spawner.active` users -> `get_container_stats_with_refresh(active)`
- [x] **Periodic refresh continues** - after the immediate warm, each refresher keeps its normal PeriodicCallback cadence (volume 3600s, container size 300s, GPU util 30s, stats activity-gated 10s)
  - log: 2026-06-18 unchanged intervals; only the START moved to boot

### Pick up running servers (restart survivors)

- [x] **Survivor caches rehydrated** - the warmed size/volume/stats caches reflect already-running labs at boot, not only after the first `/activity` poll
  - log: 2026-06-18 refreshers enumerate running `jupyterlab-*` containers; stats warmed for active spawners
- [x] **Survivor CHP favicon routes** - per-user favicon routes for already-running servers are re-registered (pre_spawn_hook only fires on new spawns)
  - log: 2026-06-18 folded into hydration via `schedule_startup_favicon_callback`
- [x] **Survivor policy re-imposed** - each policy model's `on_hub_startup` runs for survivors (docker-proxy re-bind, download-block route re-registration, api-keys reconcile)
  - log: 2026-06-18 folded into hydration via `schedule_policy_startup` (skipped when no `policy_actx`)

### Image-update check (immediate)

- [x] **Image snapshot warmed at boot** - the slow `docker image ls` scan that backs "update available" is built at hydration, so the per-container check is immediate from the first `/activity` request instead of lazily on first access
  - log: 2026-06-18 `_check_image_updates` calls `_image_snapshot_get()`
- [x] **Configured lab image reported** - hydration logs whether the configured lab image is up to date, has a newer local build, or is not present yet
  - log: 2026-06-18 `_check_image_updates` compares the tag's target id vs the repo's newest

### Edge cases

- [x] **Edge: no survivors** - with nothing running, stats warming is a no-op (no docker calls); refreshers still start and find an empty fleet
  - log: 2026-06-18 `_warm_survivor_stats` only calls the cache when the active set is non-empty
- [x] **Edge: docker unreachable** - image snapshot + stats warming degrade to empty/last-known and log a warning; hydration completes
  - log: 2026-06-18 `_image_snapshot_get` is best-effort; step wrapped in try/except
- [x] **Edge: GPU-less host** - GPU-utilisation refresher is not started; no error
  - log: 2026-06-18 `gpu_list` empty -> skipped
- [x] **Edge: runs once** - hydration is a one-time boot callback; the refreshers' idempotent `start()` means a later `/activity` hit does not double-start them
  - log: 2026-06-18 one `add_callback`; `start()` guards on `periodic_callback`

### Tests

- [x] **Unit: shared helper + gating** - `start_activity_refreshers` starts volume + container-size refreshers always and GPU utilisation only when `gpu_list` is non-empty; the hydration entry is importable + callable
  - log: 2026-06-18 `tests/test_hydrate.py`; `make test`-runnable
- [ ] **Functional: restart with a running lab** - start a lab, restart the hub, then confirm the portal shows the survivor's sizes/stats and the update state without a manual `/activity` visit
  - log: 2026-06-18 needs a hub-restart harness step; pends (the current functional harness boots a fresh hub, no restart-with-survivors flow yet)

## TTL extend bar animation

Extending the idle-session TTL must move the progress bar immediately on click and animate smoothly to the **computed post-extend target %**, with no overshoot, no snap-back and no delayed flash. The bar and the time-left counter animate on click in lockstep, then settle when the refetched value lands - landing on the same % it animated to, so there is no jump.

- [x] **Immediate animate to target** - on Extend the bar starts moving on click (optimistic boost) toward the post-extend target %, not 2-3s later
  - log: 2026-06-17 `TtlGadget.apply` sets boost synchronously; `meters.tsx`
- [x] **Target = computed post-extend %, not 100%** - the boost target is `pctFor(min(ceiling, timeLeft + addedHours))` through the same two-phase formula (base scale below base, ceiling scale when extended), NOT a hard-coded 100%; so an already-extended session animates to its true partial % and never overshoots to full
  - log: 2026-06-18 FIXED - was `shownPct = boost ? 100 : pct`; overshot to 100% then snapped down to the real ceiling-scaled % (operator: 56h +7h animated to 100% then flickered to 63h). Now `boostPct` captured at click from the optimistic remaining against the invariant ceiling
- [x] **No snap-back on settle** - because the ceiling is invariant across an extend, the optimistic target equals the refetched %, so when the value lands the bar is already there (no visible jump)
  - log: 2026-06-18 added with the target-% fix
- [x] **Hold until refetch** - the boost (bar held at the target) holds until the refetched `timeLeftMin` actually changes, so the bar never snaps back to the old value mid-flight
  - log: 2026-06-17 was a fixed 1s timer that fired before the 2-3s refetch; now gated on the value landing
- [x] **Minimum fill window** - the boost lasts at least `ANIMATION.ttlExtendMs` so the growth is always visible even if the refetch is fast
  - log: 2026-06-17 `minFillDone` ref
- [x] **3s duration** - the fill/glow animation runs over 3s
  - log: 2026-06-17 `ANIMATION.ttlExtendMs` 1000 -> 3000 (`services/config.ts`), threaded to CSS via `--oh-ttl-anim`
- [x] **Time counter climbs with the bar** - during the boost the shown minutes count UP from the captured baseline to the post-extend target over the SAME `ttlExtendMs` duration and CSS-`ease` easing as the bar fill, so the number climbs in lockstep with the bar; on settle it lands on the live refetched value
  - log: 2026-06-17 originally the shown minutes FROZE during the boost and revealed the new value only on settle (`displayMin` held)
  - log: 2026-06-18 changed to a synchronized count-up (operator "animate the time-left counter to climb alongside the bar"): a `requestAnimationFrame` tween in `TtlGadget` drives `displayMin` from `baselineMin` to `boostTargetMin` via `EASE` (cubic-bezier(.25,.1,.25,1), matching the bar's CSS `ease`); cancels on reject/unmount; `meters.tsx`
- [x] **Edge: extend rejected** - if `onExtend` rejects, the boost drops immediately (bar returns to the real %)
  - log: 2026-06-17 `.catch(() => setBoost(false))`
- [x] **Edge: value never changes** - a safety cap (`ttlExtendMs + 6s`) ends the boost so it can never stick
  - log: 2026-06-17 safety timeout in `apply`
- [x] **Edge: extend across the base crossover** - extending a session from below base up past base animates to the post-extend ceiling-scaled % (a one-time scale-switch drop is the operator-chosen two-phase model, not the bug); within the banked regime (both endpoints > base) the bar grows monotonically
  - log: 2026-06-18 documented - the target-% boost makes the crossover land on the true % with no overshoot

## TTL progress bar behaviour matrix

The idle-session TTL bar (`TtlGadget`, `components/meters.tsx`) reads ~100% when time is ample and drains as the session is used, shifting blue -> orange -> red as the cull nears; the used-up remainder is the gray trail. Extend opens a popover to type the hours to add, capped at the configured ceiling. A fresh session reads ~100% and drains; an EXTENDED session (time banked above base) drains against the extension ceiling (base + max_extension) so the user sees it running out, then rescales to full at the standard baseline. Verified against the code 2026-06-17, warn threshold = 60 min (`THRESHOLDS.timeLeftWarnMin`).

### Rules (verified in meters.tsx)

- [x] **Two-phase pct** - below base: `min(100, timeLeft/base)`; extended (timeLeft > base): `timeLeft / ceiling` where `ceiling = timeLeft + maxAddHours*60` (= base + max_extension), so the extended bar drains instead of pinning at 100%
  - log: 2026-06-17 reworked (operator: extended must visibly drain) - was `min(100, timeLeft/base)` capped
- [x] **Rescale to base at the baseline** - the moment timeLeft falls to base the scale switches to base (full again), then drains normally below; a visible snap-to-full at the baseline crossover (operator-chosen model)
  - log: 2026-06-17 implemented (meters.tsx ceilingMin branch)
- [x] **Colour bands** - danger (red) at `timeLeftMin <= 20` (warn/3); warning (amber) at `<= 60`; accent (blue) above
  - log: 2026-06-17 verified (color ternary, warn=60)
- [x] **Readout matches the bar tone** - the remaining-time text and the clock icon take the SAME colour the bar shows at that moment (accent / warning / danger), driven by one shared `barTone` so the readout and the bar can never disagree
  - log: 2026-06-18 added (operator: "time and clock icon -> use the same colour that the ttl progressbar has at the same time"); `barTone` set on `.oh-ttl-val` (icon inherits via currentColor) and the time `<b>` (overrides the `.oh-ttl-val b` text-colour rule); colour transitions over .4s
- [x] **Readout follows the boost** - during an extend boost the bar is forced accent; the readout is too (same `barTone`), so the whole gadget reads accent while the optimistic fill plays
  - log: 2026-06-18 `barTone = boost ? accent : color`, the exact strokeColor expression
- [x] **Extend = hours input** - Extend opens a popover with an InputNumber (min 1, max = round(maxAddHours)); apply clamps and calls onExtend
  - log: 2026-06-17 verified (Popover + InputNumber + apply clamp)
- [x] **At ceiling disables Extend** - `atCeiling = maxAddHours <= 0` -> Extend button disabled
  - log: 2026-06-17 verified (atCeiling)
- [x] **Hidden when stopped** - the gadget is only rendered for a running server
  - log: 2026-06-17 verified (ServerHero `{running && <TtlGadget/>}` + MobileHome MyServerCard)

### Behaviour matrix (base = 240 min)

Each row is demonstrated live on `/design-language` (TTL behaviour matrix row).

- [x] **Full** - timeLeft 240, maxAdd 12 -> pct 100, blue, Extend enabled (max 12h)
  - log: 2026-06-17 verified by code + design-language demo
- [x] **Ample** - timeLeft 180, maxAdd 12 -> pct 75, blue, Extend enabled
  - log: 2026-06-17 verified
- [x] **Warn** - timeLeft 45, maxAdd 12 -> pct 19, amber, Extend enabled
  - log: 2026-06-17 verified (45 <= 60, > 20)
- [x] **Low / danger** - timeLeft 12, maxAdd 12 -> pct 5, red, Extend enabled
  - log: 2026-06-17 verified (12 <= 20)
- [x] **Extended-drains** - timeLeft 300 (> base 240), maxAdd 6 -> ceiling 300+360=660, pct 45 (drains against the ceiling, NOT capped at 100), blue, Extend enabled (max 6h)
  - log: 2026-06-17 reworked (operator: extended must visibly drain) - was pct 100 capped
- [x] **At ceiling** - timeLeft 180, maxAdd 0 -> pct 75, blue, Extend DISABLED
  - log: 2026-06-17 verified (atCeiling true)
- [x] **Stopped** - server offline -> gadget not rendered at all
  - log: 2026-06-17 verified (running-gate)

### Extension flow

- [x] **Extend caps at allowance** - typed hours clamped to [1, round(maxAddHours)] before onExtend
  - log: 2026-06-17 verified (apply: Math.max(1, Math.min(maxH, round(hours))))
- [ ] **Runtime: extend round-trips** - clicking Extend issues the real `POST /users/{name}/extend-session` and the bar/clock refresh to the new remaining time
  - log: 2026-06-17 pending deploy (onExtend -> extendSession wired; live round-trip needs the running hub)
- [x] **Runtime: visual drain + colour shift** - the matrix renders blue -> amber -> red with the base-relative cap and the at-ceiling disable
  - log: 2026-06-17 VISUALLY CONFIRMED via Playwright headless render of /design-language (6 gadgets): full=100% blue, ample=75% blue, warn=amber, low=red, extended(5h>base)=full bar capped not overflowing, at-ceiling=Extend disabled. Screenshot reviewed. (Live drain over wall-clock + extend round-trip on a running session still observable on the deployed hub.)

### Replenish laws (SSOT: idle_culler.py, mirrored in the bar)

- [x] **Activity floor = base** - an active server retains at least base; activity replenishes remaining up to base, never above (`calc_remaining` activity_floor = base - idle)
  - log: 2026-06-17 verified (test_remaining_keeps_active_server_at_base)
- [x] **No replenish above base** - while extended (remaining > base) an active server is NOT topped up; the banked time drains via the deadline until it falls to base
  - log: 2026-06-17 added test_remaining_extended_not_inflated_by_activity
- [x] **Drains to base then replenishes** - once remaining falls below base, an active server is topped back to exactly base ("max becomes base again") and normal replenish resumes
  - log: 2026-06-17 added test_remaining_below_base_active_replenishes_to_base
- [x] **Ceiling cap** - no extend sequence banks lifetime past base + max_extension; the deadline never sits more than ceiling ahead of now
  - log: 2026-06-17 verified (test_remaining_clamped_to_ceiling, test_extend_caps_at_ceiling)

### Extended TTL must visibly drain (operator 2026-06-17)

The backend already drains banked extension down to base; the BAR now shows it. Operator-chosen model: scale the extended bar to the extension ceiling so it drains (gray trail growing), then rescale to the standard baseline at the crossover (snaps full again, against the standard baseline not the extended scale).

- [x] **Drains while extended** - when remaining > base the bar shrinks against the ceiling as time passes (the user sees time running out), no longer pinned at 100%
  - log: 2026-06-17 implemented (meters.tsx `ceilingMin` two-phase pct)
- [x] **Gray leftover** - the drained portion above the current remaining shows as the standard gray trail (antd Progress trailColor)
  - log: 2026-06-17 implemented
- [x] **Full again at the standard TTL** - at the standard baseline the bar rescales to base and reads full again (against the standard baseline, not the extended scale); below base it drains normally
  - log: 2026-06-17 implemented (operator-chosen: visible snap-to-full at the baseline crossover)

### Extend refetches the bar

- [x] **Extend invalidates hero** - `extendSession` invalidates `['hero', user]` (plus session, servers) so the bar refetches and grows after a successful extend
  - log: 2026-06-17 FIXED - was `['session', user]` + `['servers']` only; the bar reads from the hero query so an extend updated the backend but only a toast showed, the bar never moved
- [x] **Runtime: extend grows the bar** - on a running session, Extend visibly animates the bar to the post-extend remaining; below base it fills toward base, when banked above base it grows against the ceiling (never pinned at a false 100%)
  - log: 2026-06-17 invalidation fixed; 2026-06-18 boost target corrected from 100% to the computed post-extend %

### Staged extend animation

On Extend the gadget plays a three-step animation instead of a single jump (`TtlGadget` boost state + `.oh-ttl-boost` in global.css). The bar animates to the **computed post-extend target %** (against the invariant ceiling), never a blanket 100%.

- [x] **Step 1 - bar moves to target, time held** - on click the bar animates immediately toward `boostPct = pctFor(min(ceiling, timeLeft + addedHours))` (the same two-phase formula) while the time text holds its pre-extend value
  - log: 2026-06-17 implemented as `shownPct=100`; 2026-06-18 FIXED to the computed target `boostPct` so an extended session animates to its true partial % (operator: 56h +7h overshot to 100% then snapped to 63h); `displayMin` freezes the shown minutes during the fill
- [x] **Step 2 - grow to new limit over a configured duration** - the bar visibly fills to the new ceiling (not a snap) with a brief accent glow, like the old design
  - log: 2026-06-17 implemented, then (operator: "not properly animated ... make it 1s") forced a visible fill - `.oh-ttl-boost .ant-progress-bg { transition: width var(--oh-ttl-anim) ease }` overrides antd's quick default; boost window + `oh-ttl-pulse` glow share the same duration
- [x] **Duration is package-config** - the fill duration lives in `duoptimum-hub-web/src/services/config.ts` (`ANIMATION.ttlExtendMs`, default 1000), NOT a Docker env (too granular); it drives the JS hold timer and, via the `--oh-ttl-anim` CSS var on the bar, the CSS transition + glow from one place
  - log: 2026-06-17 added `ANIMATION` config; `meters.tsx` reads it for the timer + sets `--oh-ttl-anim`; `global.css` uses `var(--oh-ttl-anim, 1s)`
- [x] **Step 3 - time text updates, no snap** - once the refetched `timeLeftMin` lands the bar settles on the real % (which equals the target it already animated to, ceiling being invariant, so no jump) and the clock text reveals the new remaining time
  - log: 2026-06-17 implemented; 2026-06-18 the settle now lands on the same % as the boost target, eliminating the snap-back flicker
- [x] **Clock icon before the time** - the clock glyph renders immediately left of the remaining-time text in the gadget
  - log: 2026-06-17 present (`Icon name="clock"` before `<b>` in `.oh-ttl-val`)
- [x] **Edge: partial extend below base** - extending only part-way (remaining still < base) animates to the base-scaled target % and settles there; no overshoot to 100%
  - log: 2026-06-18 fixed by the target-% boost (was: filled to 100% then settled back)
- [x] **Edge: extend while banked (> base)** - both endpoints above base -> the bar grows monotonically against the ceiling (the operator's reported case: 56h -> 63h), no overshoot/snap
  - log: 2026-06-18 the regression this fix closes
- [ ] **Runtime: animation on the live hub** - the three-step sequence is visible end-to-end on a real extend round-trip
  - log: 2026-06-17 coded; 2026-06-18 target-% fix coded; visual confirm pends rebuild

### Test harness

- [x] **Python SSOT matrix runs all scenarios** - `test_ttl_matrix.py` + `test_idle_culler.py` cover progress pct, ceiling, available hours, extend (add/cap/maxed), remaining (activity floor, replenish, ceiling, floor), cull
  - log: 2026-06-17 extended with the two replenish-law scenarios; `make test` green
- [ ] **No JS test harness for the bar** - the portal has no vitest setup; the `TtlGadget` pct formula mirrors `calc_progress_pct` verbatim and is covered in Python; a JS unit test would need a new harness
  - log: 2026-06-17 gap documented

### Home server-controls additions

- [x] **Uptime on the TTL line** - the TtlGadget shows "up Xh" inline (next to the remaining-time clock) for a running server
  - log: 2026-06-17 implemented - `server_started` (spawner `orm_spawner.started`) added to the activity payload -> `getServerHero.startedISO` -> `TtlGadget uptimeLabel={timeAgoShort(startedISO)}`; mock + typecheck clean
- [x] **Upgrade-available pill** - a gold "Upgrade available" pill shows left of the status pill on the Server status card when a newer lab image is available locally than the running container's
  - log: 2026-06-17 implemented - `lab_image_id` (cached ~5min) vs the container's running image id (`container.attrs['Image']`, reused from the stats inspect); `image_upgrade_available` pure helper (5 unit tests); surfaced as `lab_image_upgrade_available` -> `hero.upgradeAvailable`
- [x] **Edge: image id unknown** - local image absent / docker unreachable -> `lab_image_id` None -> no upgrade offered (never a false pill)
  - log: 2026-06-17 covered by test_image_upgrade (None cases)
- [ ] **Edge: re-tag to older** - if the local tag is moved to an OLDER image the pill still shows (different-id heuristic; watchtower only pulls forward so this is theoretical)
  - log: 2026-06-17 documented limitation - a created-time compare would close it at the cost of extra docker inspects; left out by design

## "Upgrade available" pill

The home/server "Upgrade available" pill tells a user that a stop/start would land their lab on a newer image. Detection compares image IDs (not `Created` times): the running container's image is frequently pruned right after a rebuild - the very moment an upgrade exists - so its timestamp is unreadable; the reliable signal is that the configured lab image tag now resolves to a different id than the one the container runs. Backend `docker_utils.newer_lab_image_available` + pure `image_upgrade_available`; surfaced as `/activity` `lab_image_upgrade_available` -> `hero.upgradeAvailable`.

### Detection algorithm

- [x] **Ref from settings** - the compared ref is the configured lab image (`stellars_config['lab_image']` = `JUPYTERHUB_LAB_IMAGE`), passed per-container to `newer_lab_image_available(image_ref, container_image_id)`
  - log: 2026-06-17 verified (activity.py:164,176)
- [x] **No tag -> :latest** - a ref with no tag on its final path segment gets an implicit `:latest` (docker's own default); a `@sha256` digest is stripped (`_normalize_ref`)
  - log: 2026-06-17 implemented (`_normalize_ref`)
- [x] **Tag supplied -> use it** - a ref that already carries a tag (`repo:3.8.5`, `repo:latest`) is compared on that exact tag, not coerced
  - log: 2026-06-17 implemented (`_normalize_ref` leaves a tagged ref unchanged)
- [x] **Compare resolved-tag id vs running id** - `tag_to_id[ref]` (the id the tag currently points to) is compared to the running container's `container.attrs['Image']`; differ -> candidate upgrade
  - log: 2026-06-17 implemented; verified live (konrad running `0ee110` vs `:latest` `1c4b02` -> True)
- [x] **Guard: tag must be the repo's newest** - the candidate only fires when the resolved tag id equals the repo's newest-by-`Created` image id, so a deliberate re-tag of the lab tag to an OLDER image never offers a false upgrade
  - log: 2026-06-17 implemented (`image_upgrade_available(latest_tag_id, container_image_id, newest_repo_id)`)
- [x] **ID comparison, not Created** - the running image's `Created` is NOT read (it is gone from the store after a rebuild+prune); only ids are compared, with `Created` used solely to pick the repo's newest image
  - log: 2026-06-17 root-caused on the live host - `docker image inspect <running id>` returned "No such image"; the prior Created-vs-Created compare could never fire

### Created parsing (why the old code never fired)

- [x] **ISO-8601 string parse** - docker-py returns image `Created` as an ISO-8601 string with nanosecond precision + trailing `Z` (`2026-06-17T11:20:48.755861714Z`), not an epoch int; `_parse_created` normalises `Z`->`+00:00`, trims ns->us, and `datetime.fromisoformat`s it
  - log: 2026-06-17 FIXED - the old `if not isinstance(created, int): continue` skipped EVERY image, so `newest_by_repo` was always empty and the pill was dead for every user
- [x] **Epoch fallback** - an int/float `Created` (older docker clients) is accepted as-is
  - log: 2026-06-17 covered (`isinstance(created, (int, float))`)
- [x] **Unparseable -> None** - a malformed/empty `Created` yields None and the image is skipped for the newest-by-repo calc (never crashes the snapshot)
  - log: 2026-06-17 covered (try/except ValueError)

### Snapshot + caching

- [x] **One snapshot, dict lookups** - `docker image ls -a` is snapshotted to `(tag_to_id, newest_id_by_repo)` and cached `_IMAGE_TTL` = 300s so the polled `/activity` endpoint does a dict lookup, not a socket call per user
  - log: 2026-06-17 retained (cache shape changed from `(created_by_id, newest_by_repo)`)
- [x] **Dangling/untagged skipped** - tags whose repo is `<none>` are not indexed
  - log: 2026-06-17 verified (`repo == '<none>'` skip)

### Display

- [x] **Running server only** - the pill shows only for an active server (the upgrade check runs on the container stats path, default `lab_image_upgrade_available: False`)
  - log: 2026-06-17 verified (activity.py only sets it inside the active-users stats merge)
- [x] **Label is "Update available"** - the user-facing pill label reads "Update available" (capital U); internal identifiers (`upgradeAvailable`, `lab_image_upgrade_available`) keep "upgrade"
  - log: 2026-06-18 renamed (operator "upgrade available -> update available ... with capital U") in `ServerHero.tsx` + `MobileHome.tsx`; also the /design-language reference text
- [ ] **Pill desktop + mobile** - `hero.upgradeAvailable` renders a gold "Update available" pill on the "Server Control" card (desktop) and the mobile MyServerCard
  - log: 2026-06-17 backend confirmed live (pill=True for konrad); on-screen render pends operator rebuild
- [x] **Tooltip says stop/start, not restart** - the pill tooltip reads "A newer lab image is available locally - stop your server and start a new one to update"; a Docker restart reuses the existing container/image so it would NOT update
  - log: 2026-06-17 corrected from "restart ... to upgrade" in `ServerHero.tsx` + `MobileHome.tsx`; 2026-06-18 verb "upgrade"->"update" with the label rename
- [ ] **Runtime: pill clears after upgrade** - after stop/start onto the new image the running id == tag id -> pill disappears on the next `/activity` refresh
  - log: 2026-06-17 logic verified (`newer_lab_image_available(ref, latest_id)` -> False); live confirm pends rebuild

### Edge cases

- [x] **Edge: running image pruned/gone** - the running id is not inspectable/listed (rebuilt+pruned); pill still fires because the comparison never looks the running image up - it only needs the tag's current id and the running id (already held from the stats inspect)
  - log: 2026-06-17 this is THE live case (konrad) - now returns True
- [x] **Edge: running the current tag** - running id == tag id -> no pill
  - log: 2026-06-17 verified live (False when container runs `:latest`'s id)
- [x] **Edge: re-tag to older** - the lab tag points at an image that is NOT the repo's newest -> guard rejects -> no false pill
  - log: 2026-06-17 covered (test_no_upgrade_when_tag_retagged_to_older)
- [x] **Edge: docker unreachable** - snapshot is empty -> `tag_to_id.get(ref)` None -> no pill (conservative)
  - log: 2026-06-17 covered (except -> empty snapshot; test_no_upgrade_when_tag_unknown)
- [x] **Edge: container image id unknown** - stats returned no `image_id` -> no pill
  - log: 2026-06-17 covered (test_no_upgrade_when_container_unknown)
- [ ] **Edge: pinned non-latest tag with a newer sibling tag** - operator pins `:3.8.5` while a newer `:latest`/`:3.9.0` exists; the pinned tag is not the repo's newest so no pill - acceptable, since a restart spawns the pinned tag, not the sibling
  - log: 2026-06-17 documented; consequence of the newest-repo guard, intended for the watchtower `:latest` deployment

### API / functions

- `newer_lab_image_available(image_ref, container_image_id) -> bool` - resolves the ref, snapshots images, delegates to the pure helper
- `image_upgrade_available(latest_tag_id, container_image_id, newest_repo_id) -> bool` - pure: `latest_tag_id and container_image_id and latest_tag_id != container_image_id and latest_tag_id == newest_repo_id`
- `_image_snapshot_get() -> (tag_to_id, newest_id_by_repo)` - cached ~5min
- `_normalize_ref(image_ref) -> "repo:tag"` - implicit `:latest`, strips `@digest`
- `_parse_created(created) -> epoch float | None` - ISO-8601 string or epoch int

## version sync across subpackages

`make increment_version` bumps the patch version of the root project and every in-repo package baked into the hub image in lockstep, by setting the new version absolutely (not matching the old string) so a drifted subpackage is pulled back into sync rather than skipped.

- [x] **Root + three subpackages** - sets the version on `pyproject.toml`, `duoptimum-hub-web/pyproject.toml`, `duoptimum-hub-services/pyproject.toml`, `duoptimum-docker-proxy/pyproject.toml`, and `duoptimum-hub-web/package.json`
  - log: 2026-06-17 `VERSIONED_PYPROJECTS` loop + package.json sed; `Makefile`
- [x] **Image packages only** - the three subpackages are exactly the wheels the hub image installs (Dockerfile lines 174-176); `duoptimum hub`, `jupyter hub services`, and `the other one` = docker-proxy
  - log: 2026-06-17 confirmed against `Dockerfile.jupyterhub`
- [x] **gpuinfo-nvidia excluded** - the GPU-info sidecar is a separate image with its own version; intentionally not synced
  - log: 2026-06-17 left at its own version, documented in the Makefile comment
- [x] **Absolute set fixes drift** - uses `s/^version = "[^"]*"$/.../` so hub-services (was 3.8.0) and any drifted package jump to the new root version, not just packages already in sync
  - log: 2026-06-17 prior recipe matched the old string and silently skipped drifted packages
- [x] **Single version line** - each pyproject has exactly one `[project] version` line and package.json one `"version"`, so the absolute sed touches only the intended line
  - log: 2026-06-17 verified before changing the recipe
- [x] **package-lock.json tracks the bump** - `increment_version` also rewrites the lockfile's own version (root `.version` + `packages[""].version`) so it never drifts from package.json; the image build runs `npm ci` (`Dockerfile.jupyterhub:61`) which aborts with EUSAGE on a package.json/lock version mismatch
  - log: 2026-06-17 found via adversarial review - the prior recipe bumped package.json only, leaving the lockfile at 4.0.0 while package.json was 4.0.1 (a committed build-breaker); fixed with an `awk` first-two-`"version"`-fields rewrite + a one-time lockfile resync
- [x] **Edge: transitive deps named like the project version** - the lockfile holds many `"version"` lines; the bump targets only the first two (root + `packages[""]`, always the first two in lockfileVersion 3) so a transitive dep that happens to share the project version is not corrupted
  - log: 2026-06-17 `awk 'BEGIN{n=0} /"version":/ && n<2 {...; n++}'`; 6 transitive 4.0.0 deps left untouched
- [x] **Edge: no helper script** - manifest set is an inline Make variable + a bash `for` loop in the recipe, no external script
  - log: 2026-06-17 per the inline-metadata convention

## Volume reset confirmation

After an admin/user resets selected volumes, the panel reports what was done and offers a clean way back. The list paints volume names instantly with sizes filling in (see [acc-crit-resource-bars] for the names/sizes split). `duoptimum-hub-web/src/components/VolumeReset.tsx`, `pages/ManageVolumes.tsx`.

### After reset (same screen, no separate view)

- [x] **Stays on the volumes screen** - resetting does NOT switch to a separate confirmation view; the same table + buttons remain and the removed rows are marked in place
  - log: 2026-06-17 reworked (operator: "stay on the same one with the same buttons") - dropped the `done` early-return; `removed` suffixes marked in the table
- [x] **"removed" in red, not a pill** - each removed volume reads "removed" in dangerous (red) text in its Size cell, never an antd Tag/pill
  - log: 2026-06-17 `oh-text-danger` in the Size column; cross-ref [acc-crit-design-language] text colours
- [x] **Removed rows non-selectable** - a removed volume's checkbox is disabled so it cannot be re-selected; Reset re-disables when nothing is selected
  - log: 2026-06-17 `getCheckboxProps` disabled on removed suffixes
- [x] **Irreversibility warning** - the top notice is a WARNING (not the info/activity "EKG" glyph) stating that removing volumes is irreversible - the selected volumes and all their contents are permanently deleted
  - log: 2026-06-17 reworked (operator: "warning that selecting and removing the volumes is irreversible; not the current EKG message") - Notice type warning, was info

### Close behaviour

- [x] **Cancel + Done footer** - the dedicated Manage-volumes page uses the standard config footer (Reset destructive on the left; Cancel + a primary Done on the right), matching Configure-user / Configure-group; both Cancel and Done leave the screen
  - log: 2026-06-17 implemented - `VolumeReset` renders `FormFooter` in page mode (when `onClose` is set); the Configure-user Volumes TAB keeps the bare Reset button (UserConfig owns that footer)
- [x] **Returns to the true origin** - Cancel / Done return to where the screen was opened from per the nav-origin state - Home if opened from Home, Servers if opened from the Servers list - not a hardcoded /servers
  - log: 2026-06-17 implemented - `ManageVolumes` reads `location.state.from` (`backTo`); Home hero / widget + Servers list all tag the origin; was the reported bug (Home -> volumes closed to Servers); cross-ref [acc-crit-design-language] "Respect the navigation path"
- [x] **Edge: reached from the user-config Volumes tab vs the dedicated Manage-volumes page** - Close returns to whichever parent opened it (the tab keeps its own footer; the page returns to its origin), not a dead-end empty panel
  - log: 2026-06-17 implemented - page mode renders the footer; tab mode (no `onClose`) renders just the Reset action

### Audit

- [x] **Event logged on reset** - a successful reset records a `volume` event on the event log (`record_event`), surfaced in Recent events and on the Events page with the disk icon and a `warn` tone; hub log keeps its `[Manage Volumes]` lines too
  - log: 2026-06-17 added; `handlers/volumes.py` after the removal loop, only when >=1 volume actually removed
- [x] **Event names actor and owner** - text names the actor; when an admin resets another user's volumes it names both ("<b>admin</b> reset <b>alice</b> volumes: home, workspace"), all HTML-escaped
  - log: 2026-06-17 added
- [x] **No UI notify** - the event log + hub log are the record; no extra toast/notification is sent on reset
  - log: 2026-06-17 per request - event log only
- [ ] **Edge: all requested volumes already gone** - when nothing is actually removed (all not-found) no event is recorded
  - log: 2026-06-17 added; guarded on non-empty `reset_volumes`

### Already in place (keep)

- [x] **Names instant, sizes fill in** - the table paints volume names at once and sizes show "updating…" then fill (split fast names / slow sizes)
  - log: 2026-06-17 shipped (#242)
- [x] **Reset gated on stopped server** - reset is disabled while the server runs (backend also rejects)
  - log: 2026-06-17 pre-existing

## Duoptimum Hub portal de-mock + fixes

Master fix-list for the autonomous sweep that makes the hub-served portal fully wired and free of mocks. Detail/evidence per action lives in `portal-action-audit.md`; this file tracks each fix to done. `[x]` = implemented + tsc/eslint (or py_compile/tests) clean; `[ ]` = pending. Final runtime verification needs an image rebuild (operator).

### Round 2 - operator punch-list (2026-06-16)

Reroute the reset-volumes action to a dedicated page, make every server widget state-aware, make group priority a true contiguous rank with up/down + set-position controls, and surface real per-GPU utilisation sampled from a CUDA subcontainer.

#### BLOCKER: stale nginx mock portal shadows the live portal

Root cause of "everything is mock": a leftover standalone container `duoptimum-hub-portal` (`nginx:alpine`, compose project `deploy`, file `mock-antd/deploy/compose.portal.yml`) is still running and serving the **old mock build**. Its Traefik router (`portal-rtr`, priority 1000) claims `Host(jupyterhub.lab.stellars-tech.eu) && PathPrefix(/portal)`. Visiting `/portal` therefore hits the retired mock SPA, not the hub-served live portal at `/hub/portal`. Proof: the nginx bundle contains the mock banner string "every action is simulated" (mock build) with the old wording "data is pulled live from the hub"; the hub-baked bundle tree-shakes that string out (live build, `isMock()` statically false).

- [ ] **Retire the nginx /portal container** - `docker compose -f mock-antd/deploy/compose.portal.yml down` (removes the mock container + its `/portal` Traefik route); the live portal stays at `/hub/portal` (hub `default_url`)
  - log: 2026-06-16 diagnosed; teardown is a deployment action - operator-gated
- [ ] **Delete the obsolete deploy assets** - remove `mock-antd/deploy/compose.portal.yml` + `nginx.conf` once teardown confirmed (plan's "Retire" step)
  - log: 2026-06-16 criterion added
- [ ] **Single portal URL** - after teardown, `/portal` 404s (or redirects); the only portal is the hub-served live one
  - log: 2026-06-16 criterion added

#### Server lifecycle popups (start / restart / stop)

Every lifecycle action shows a progress popup tied to the real hub state, and disables conflicting controls while in flight. Verify against the existing functional tests (`docs/acc-crit-functional-test-harness.md`, `docs/acc-crit-functional-ui-sweep.md`, Playwright specs) and extend them.

- [x] **Start popup** - clicking Start server opens a modal with a progress bar that reflects the spawn progressing, not a fire-and-forget toast
  - log: 2026-06-16 fixed (app/ServerLifecycle.tsx provider + Modal/Progress)
- [x] **Start progress source** - progress driven by the hub's spawn-progress SSE (`GET /api/users/{name}/server/progress`, `_xsrf` in query since EventSource can't set headers), with a status-poll fallback if the stream ends without a ready event
  - log: 2026-06-16 fixed (ServerLifecycle.start; xsrfToken exported from client.ts)
- [x] **Start resolve** - popup shows done at 100% when the server is ready and offers Open lab (+ Close)
  - log: 2026-06-16 fixed (phase 'done' footer)
- [x] **Restart popup** - Restart opens an indeterminate "Restarting container…" popup; closes/done when the server is running again (status poll)
  - log: 2026-06-16 fixed (ServerLifecycle.restart)
- [x] **Stop popup** - Stop opens a "Stopping server…" popup; while busy, play/restart/stop are disabled; done when status is offline
  - log: 2026-06-16 fixed (ServerLifecycle.stop + busyOf disabling)
- [x] **In-flight disabling** - a `busy` map disables every conflicting action on that user's row/hero during a transition (no double-fire)
  - log: 2026-06-16 fixed (busyOf consumed by ServerHero + Servers rowActions)
- [x] **Mock parity** - in mock mode the start popup animates to done (no hub) so the demo shows the flow
  - log: 2026-06-16 fixed (ServerLifecycle isMock branch)
- [x] **Edge: spawn failure** - SSE `failed` / failed status poll -> error phase, exception bar, Close (no hang)
  - log: 2026-06-16 fixed
- [x] **Edge: stop/restart failure** - op throw -> error phase, controls re-enabled (busy cleared)
  - log: 2026-06-16 fixed
- [ ] **Use functional tests** - drive/verify these flows with the existing functional test harness, extending the specs rather than inventing parallel ones
  - log: 2026-06-16 pending - needs a live hub; tsc/eslint/build/Playwright-smoke green here, runtime verify on cutover
- [ ] **Edge: already running** - Start no-op; the stopped/running button split already prevents Start on a running server (verify on cutover)

#### TTL gadget - drain bar + working Extend

- [ ] **Full = blue** - at ample time the bar reads 100% in standard blue (antd Progress)
  - log: 2026-06-16 criterion added
- [ ] **Drain + colour** - fill shrinks proportionally as time is used and shifts blue -> orange -> red as it approaches the cull
  - log: 2026-06-16 criterion added
- [ ] **Gray remainder** - the used-up portion shows as a gray track behind the coloured fill
  - log: 2026-06-16 criterion added
- [ ] **Extend works** - the Extend button issues the real `POST /users/{name}/extend-session` and the bar/clock refresh to the new remaining time (behaviour per `docs/acc-crit-functional-ui-sweep.md` / session handler `session.py`)
  - log: 2026-06-16 criterion added
- [ ] **Extend = hours input** - Extend is not a fixed +2h click; the admin types the number of hours (validated, capped at the remaining allowance up to `max_extension_hours`), then applies
  - log: 2026-06-16 criterion added
- [ ] **Edge: at extension ceiling** - Extend disabled / no-op when `max_extension_hours` reached
- [ ] **Edge: server stopped** - TTL gadget hidden or inert when no running server

#### Dedicated reset-volumes page

- [x] **Dedicated page** - resetting a user's volumes opens a dedicated Manage-volumes page, never the full Configure-user screen
  - log: 2026-06-16 fixed (ManageVolumes.tsx; ServerHero + Servers navigate to `/servers/{name}/volumes`)
- [x] **Reuse, not duplicate** - one shared `VolumeReset` component reused by the dedicated page and Configure-user's Volumes tab
  - log: 2026-06-16 fixed (components/VolumeReset.tsx; UserConfig volumesTab now reuses it)
- [x] **Route** - `/servers/:name/volumes` (admin), crumb "Manage volumes", parent Servers
  - log: 2026-06-16 fixed (router.tsx)
- [x] **Content** - per-user volume table (volume, mount, description, size) with checkbox selection + "Reset selected" (danger)
  - log: 2026-06-16 fixed (VolumeReset.tsx)
- [x] **Stopped-only** - reset enabled only when the user's server is stopped; running -> button + checkboxes disabled + warning notice
  - log: 2026-06-16 fixed (VolumeReset resolves running state from useServers)
- [x] **Edge: server running** - reset disabled, warning shown; backend also rejects (defence in depth)
  - log: 2026-06-16 fixed (VolumeReset running gate)
- [x] **Edge: no resettable volumes** - empty table, reset disabled (no selection)
  - log: 2026-06-16 fixed (disabled unless selection)
- [x] **Edge: direct nav to unknown/missing user** - graceful empty/loading, no crash
  - log: 2026-06-16 fixed (empty volumes + running=false fallback)

#### Server widgets - state-aware actions (Home ServerHero + Servers table)

- [x] **Stopped set** - a stopped/offline server shows exactly: Start, Manage volumes
  - log: 2026-06-16 fixed (ServerHero + Servers.rowActions offline)
- [x] **Running set** - a running (active/idle) server shows exactly: Go to server (open lab), Restart, Stop
  - log: 2026-06-16 verified (ServerHero running branch + Servers.rowActions default)
- [x] **Manage-volumes target** - both widgets' Manage-volumes navigates to the dedicated page, not Configure-user
  - log: 2026-06-16 fixed (ServerHero + Servers -> `/servers/{name}/volumes`)
- [x] **Servers table parity** - offline rows always offer Manage volumes (no longer gated on a non-null volume size)
  - log: 2026-06-16 fixed (Servers.rowActions)
- [x] **Spawning unchanged** - spawning rows keep view-spawn-log / cancel
  - log: 2026-06-16 verified (unchanged)
- [x] **Edge: non-admin on own Home** - Manage volumes shown only for admins (current gating preserved)
  - log: 2026-06-16 verified (ServerHero role === 'admin')

#### Save user / group -> confirm + return to list

- [x] **Save user returns** - saving in Configure-user shows a success confirmation (per-write toasts) and navigates to the Users list
  - log: 2026-06-16 fixed (UserConfig.save -> navigate('/users'))
- [x] **Save group returns** - saving in Configure-group shows a success confirmation and navigates to the Groups list
  - log: 2026-06-16 fixed (GroupConfig.save -> navigate('/groups'))
- [x] **Edge: save error** - on failure stay on the form with the error, do not navigate
  - log: 2026-06-16 fixed (navigate only after the try-body completes)

#### Groups list - contiguous priority rank

- [x] **# = row number** - the # column is the current 1-based row position (top = 1), always
  - log: 2026-06-16 fixed (Groups.tsx PositionCell renders i+1)
- [x] **Renumber on any change** - after create, delete, drag-reorder, move up/down or set-position, stored priorities are rewritten to a contiguous sequence matching row order (top = highest), no gaps, no ties
  - log: 2026-06-16 fixed (groups.py GroupsDataHandler normalises on every fetch; reorder ops persist contiguous priorities)
- [x] **Move up / down** - each row has up and down actions that swap it with its neighbour and persist the new contiguous priorities; disabled at the ends
  - log: 2026-06-16 fixed (Groups.tsx move() + arrowup/arrowdown IconActions)
- [x] **Set position** - clicking the # opens a popover to type an arbitrary position; value clamped to 1..N then the whole list renormalised
  - log: 2026-06-16 fixed (Groups.tsx PositionCell popover + setPosition())
- [x] **New group placement** - a created group (priority 0) lands at the bottom; the normaliser gives it a unique contiguous priority on next fetch (no 0-tie)
  - log: 2026-06-16 fixed (groups.py normaliser)
- [x] **Edge: set-position out of range** - clamped to [1, N], not rejected
  - log: 2026-06-16 fixed (PositionCell apply clamps)
- [x] **Edge: set-position non-integer / empty** - rounded / falls back to current rank, no-op if unchanged
  - log: 2026-06-16 fixed (PositionCell apply Math.round + null fallback)
- [x] **Edge: filter active** - up/down + set-position disabled while a search filter is applied (acts on true full order otherwise)
  - log: 2026-06-16 fixed (Groups.tsx disabled on `q`)
- [x] **Edge: single group** - up/down disabled; position is 1
  - log: 2026-06-16 fixed (move() bounds + disabled at ends)
- [x] **GroupConfig position consistent with list** - the Configure-group page shows "Position" (1-based rank, 1 = top) matching the Groups list, not the raw stored priority; editing it moves the group to that position and renormalises
  - log: 2026-06-16 fixed (GroupConfig.tsx uses useGroups to derive rank; save reorders the full list)

#### Real per-GPU utilisation

- [x] **Real utilisation** - the Home Total-resources GPU bar shows live per-GPU utilisation %, one striped bar per device, not inventory chips and not a fabricated 0%
  - log: 2026-06-16 fixed (gpu_cache.py, activity.py, liveSource.ts, meters.tsx, types.ts); supersedes the host-blocked note - `utilization.gpu` confirmed real on this WSL2 host (container sample returned 0/3/0 %)
- [x] **Tooltip** - each striped GPU bar's tooltip shows the device name and its current utilisation % (e.g. "GPU 1 GeForce RTX 5090 - 3%")
  - log: 2026-06-16 fixed (meters.tsx GpuMeter takes devices for names)
- [x] **Sampled via subcontainer** - `GpuUtilizationRefresher` samples `nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader,nounits` in an ephemeral CUDA container on a periodic background tick (default 30s, `JUPYTERHUB_GPU_UTIL_UPDATE_INTERVAL`), cached; no per-request container spin; gated on a non-empty inventory
  - log: 2026-06-16 fixed (gpu_cache.py mirrors volume_cache pattern; live sampler test green)
- [x] **Snapshot field** - `/activity` `gpus[]` gains `utilization` (int %) + `memory_used_mb` per device, merged by index onto the static inventory
  - log: 2026-06-16 fixed (activity.py)
- [x] **Fallback** - when utilisation can't be sampled (no GPU, nvidia error), the bar falls back to inventory chips (current behaviour), never a fake 0%
  - log: 2026-06-16 fixed (liveSource: gpus undefined -> ResourceBars renders GpuInventory)
- [ ] **Edge: WSL2** - confirmed working on this host; still falls back gracefully if a future host returns N/A
- [ ] **Edge: stale sample** - the refresher interval is bounded; a stale sample is shown until refreshed rather than blanking

#### Native login + signup served as the antd portal

Today the hub renders the stock NativeAuth `login.html` / `signup.html`; the portal's own `Login.tsx` / `Signup.tsx` are unused. Turn the stock pages off and serve the antd screens, wired to NativeAuth's real POST endpoints. Larger change - touches the public (unauthenticated) serving path, so it needs its own handler (the portal handler is `@authenticated`).

- [x] **antd login screen** - `/hub/login` renders the antd Login, served by a new `DuoptimumHubAuthenticator`. (First attempt overrode `login.html`, but NativeAuth's `LoginHandler._render` renders `native-login.html` and the enhanced stock copy won the template path - so the override never took.) The authenticator swaps the login handler to render uniquely-named `duoptimum_login.html` (`window.jhdata.authPage='login'`); `main.tsx` renders `AuthApp` instead of the router app. Verified live: `<title>Sign in - Duoptimum Hub</title>`, antd form renders, zero console errors
  - log: 2026-06-16 fixed + verified live (auth.py DuoptimumHubAuthenticator/DuoptimumLoginHandler, duoptimum_login.html, AuthApp.tsx, main.tsx); rebuilt + restarted + Playwright against the live URL green
- [x] **antd signup screen** - `DuoptimumSignUpHandler` renders uniquely-named `duoptimum_signup.html` (`authPage='signup'`); `BootstrapAdminSignUpHandler` rebased onto it so the bootstrap-admin flow is antd too. Live `/hub/signup` currently 404s because `JUPYTERHUB_SIGNUP_ENABLED=0` (signup disabled, handler 404s before render) - correct; renders antd when signup is enabled
  - log: 2026-06-16 fixed (auth.py DuoptimumSignUpHandler, duoptimum_signup.html, config bootstrap rebase); wiring confirmed in the running hub
- [x] **Real login POST** - the antd form does a native browser POST of `username`/`password`/`_xsrf` to `{base}hub/login?next=…` (NativeAuth login logic unchanged - lockout-safe), redirecting on success
  - log: 2026-06-16 fixed (AuthApp postForm)
- [x] **Real signup POST** - native POST of `username`/`signup_password`/`signup_password_confirmation`/`email`/`_xsrf` to `{base}hub/signup` (exact NativeAuth field names); the re-rendered `result_message`+`alert` surface as an antd notice
  - log: 2026-06-16 fixed (AuthApp + signup.html passes result_message/alert into jhdata)
- [x] **Public serving** - login/signup load the bundle + logo unauthenticated: brand assets get a public route (`/portal/brand/*`), assets are already public, the templates are served by NativeAuth's own (public) handlers
  - log: 2026-06-16 fixed (__init__ BRAND_ROUTE; entry chunk via template_vars duoptimum_entry_js/css)
- [x] **Errors** - failed login shows `login_error`; signup shows the NativeAuth `result_message`; both rendered as an antd Alert/Notice in the form
  - log: 2026-06-16 fixed (AuthApp reads authError/authMessage/authAlert)
- [x] **Lockout safety** - each template includes a `<noscript>` stock fallback form posting to the same endpoint, so a bundle/JS failure can never block login
  - log: 2026-06-16 fixed (login.html/signup.html noscript)
- [ ] **Edge: bootstrap admin window** - first-admin signup through the antd screen - verify by enabling signup (NativeAuth logic unchanged via DuoptimumSignUpHandler, so expected to work)
- [ ] **Edge: logout** - logout returns to the antd login - verify in a browser session
- [x] **Runtime verify (login)** - deployed; live Playwright confirms the antd sign-in renders with no console errors
  - log: 2026-06-16 verified live after rebuild + restart

#### Functional E2E harness - needs porting to the portal

- [ ] **Port `tests/functional/` to the antd portal** - the harness (`test_hub_ui.py`, `test_scenarios.py`, etc.) drives the OLD stock admin UI (`/hub/groups` with `#add-group-modal`, `.btn-config`, `.btn-move-up`, `input[name='username']`) which the portal REPLACED. Running it as-is yields wholesale false negatives. Rewrite the specs against the antd portal (`/hub/portal/*` routes, antd selectors / `get_by_role`, the new `duoptimum_login` sign-in) before it can gate cutover
  - log: 2026-06-16 criterion added - harness obsolete vs portal; not run (would mislead)

#### Groups members tooltip

- [x] **Members tooltip** - hovering the Groups list Members count shows the member names
  - log: 2026-06-16 fixed (Groups.tsx Tooltip; GroupRow.memberNames from backend `members`)
- [x] **Cap at 10** - more than 10 members shows the first 10 then "+N more"
  - log: 2026-06-16 fixed (slice(0,10) + "+N more")
- [x] **Wrap nicely** - the tooltip wraps (normal white-space, break-word, maxWidth 320) rather than one long line
  - log: 2026-06-16 fixed (Groups.tsx tooltip styles)
- [x] **Edge: no members** - tooltip reads "No members"
  - log: 2026-06-16 fixed

#### Round 2 - small polish

- [x] **Users default filter = All** - the Users list scope defaults to "All", not "Authorized"
  - log: 2026-06-16 fixed (Users.tsx)
- [x] **Effective-policy / catalogue chips blue** - group-policy tags render in accent blue, not gray (confirmed already accent in `CappedTags`; the gray seen was the stale mock /portal)
  - log: 2026-06-16 verified (CappedTags accent=true default)
- [x] **Users list refresh after delete** - deleting a user invalidates `['users']` so the list drops the row (confirmed `deleteUser` -> `USER_KEYS` already includes `['users']`; the stale row seen was the mock /portal's static fixture)
  - log: 2026-06-16 verified (ops.ts deleteUser invalidation)

#### Performance + persistent cache

Make repeat portal loads near-instant: paint from cache, revalidate only what changed.

- [x] **Persistent query cache** - the TanStack Query cache is saved to localStorage (dehydrate/hydrate, no new dep) and rehydrated before first render, so a full reload paints last-known data immediately
  - log: 2026-06-16 fixed (app/persistCache.ts, App.tsx)
- [x] **Background revalidate** - hydrated queries are stale (past staleTime 30s) so each refetches on mount; only changed data re-renders (keepPreviousData avoids blanks)
  - log: 2026-06-16 fixed (App.tsx defaults + persistence)
- [x] **gcTime raised** - in-memory cache kept warm 30 min (was 5) so within-session revisits never refetch cold
  - log: 2026-06-16 fixed (App.tsx gcTime 30m)
- [x] **Secrets excluded** - token queries are never persisted to localStorage
  - log: 2026-06-16 fixed (persistCache EXCLUDE=['tokens'])
- [x] **Self-healing cache** - blob namespaced by data mode + version, dropped after 24h or on parse error
  - log: 2026-06-16 fixed (persistCache KEY + MAX_AGE)
- [ ] **Initial bundle size** - consider route-level code-splitting to shrink the cold-load JS (deferred: the cutover smoke test asserts a single manifest entry; revisit with chunking)
  - log: 2026-06-16 criterion added (deferred, cutover-risk noted)

#### Round 2 API

- `GET /servers/:name/volumes` - frontend route only; reuses existing `GET /users/{name}/manage-volumes` + `DELETE .../manage-volumes`
- `POST /admin/groups/reorder` - existing; now called after create / delete / move / set-position with a full contiguous `[{name, priority}]`
- `GET /activity` `gpus[]` - add `utilization:int` (+ `memory_used_mb:int`) per device, sampled + cached

### Done (frontend, validated)

- [x] **Banner** - ReadonlyBanner renders only in mock mode; never claims "simulated" on the live portal
  - log: 2026-06-16 fixed (ReadonlyBanner.tsx)
- [x] **Groups # column** - shows row rank (top = 1), not the raw duplicated priority value
  - log: 2026-06-16 fixed (Groups.tsx)
- [x] **Group priority direction** - GroupConfig says "higher number wins" (matches server + Groups list)
  - log: 2026-06-16 fixed (GroupConfig.tsx)
- [x] **Docker access exclusivity** - Standard and Limited are mutually exclusive in the policy UI
  - log: 2026-06-16 fixed (GroupPolicyTab.tsx)
- [x] **Servers default filter** - defaults to "all"
  - log: 2026-06-16 fixed (Servers.tsx)

### Frontend - wire to existing backend (no hub change)

- [x] **Group input = autocomplete** - `Combo` rewritten as an AutoComplete chip input; removing a chip no longer reopens a popup (UserConfig/NewUser/BulkUsers/GroupConfig members)
  - log: 2026-06-16 fixed (Combo.tsx)
- [x] **State-aware server controls** - stopped: "Start server" (+ "Reset volumes" for admins); running: Open lab / Restart / Stop. Hero + Active-servers widget done; Servers list row already correct
  - log: 2026-06-16 fixed (ServerHero.tsx, Home.tsx)
- [x] **Email not fabricated** - UserConfig no longer shows `{name}@lab...`; blank until persistence exists
  - log: 2026-06-16 fixed (UserConfig.tsx)
- [x] **GroupConfig empty fields** - `form.setFieldsValue` in the cfg `useEffect` (name/description/priority)
  - log: 2026-06-16 fixed (GroupConfig.tsx)
- [x] **Policy editor real read** - `getGroupConfig` returns the hub's real flat `config`; GroupPolicyTab seeds all 9 sections from it (env vars, GPU all/per-device, mem, cpu, docker access/limited/quotas/flags/privileged, volume mounts, api-keys pool, downloads, sudo) - no seeded constants. GPU devices now come from the real host inventory; volume mounts are a free-form {volume,mountpoint} table (dropped the fabricated `jupyterhub_datasets`/`scratch`)
  - log: 2026-06-16 fixed (liveSource.ts, mockSource.ts, GroupPolicyTab.tsx, types.ts)
- [x] **Policy editor real write** - GroupPolicyTab emits the flat config on change; `GroupConfig.save` sends it via `saveGroupConfig(name, description, config)` -> `PUT /admin/groups/{name}/config` (body `{description, ...flatConfig}`). Verified field-for-field: the exact emitted body round-trips through the hub's `coerce_config` + `validate_all` with zero mismatches, all 9 sections, api-keys slot preserved
  - log: 2026-06-16 fixed (ops.ts, GroupConfig.tsx); needs operator runtime check on cutover (security-grant writes; no rebuild here)
- [x] **Policy section toggles persist** - section switches drive the active/access flags in the emitted config (env_vars_active/gpu_access/docker_active/...), persisted on Save - no `mockAction`
  - log: 2026-06-16 fixed (GroupPolicyTab.tsx)
- [x] **Policy JSON download/export** - Download exports the live editor config as `{name}.policy.json` (client-side); Upload parses a JSON file and re-seeds the editor (Save then PUTs it)
  - log: 2026-06-16 fixed (GroupConfig.tsx)
- [x] **Notifications "Selected users"** - recipient-mode state + autocomplete picker fed by live `useServers`; `broadcast` passes `recipients` (backend filters). Live sent-history is honestly empty (no backend store yet)
  - log: 2026-06-16 fixed (Notifications.tsx, ops.ts, liveSource.ts)
- [x] **Command palette quick actions** - Open/Restart my server call real ops with the current user; hardcoded `jupyterlab-alice` mock action removed
  - log: 2026-06-16 fixed (nav.ts, CommandPalette.tsx)
- [x] **Tokens stale comment** - header no longer says "mocked" (code is live)
  - log: 2026-06-16 fixed (Tokens.tsx)
- [x] **Page-size switcher** - `showSizeChanger: { showSearch: false }` -> plain non-searchable dropdown (Servers list)
  - log: 2026-06-16 fixed (Servers.tsx)
- [x] **Home caching** - QueryClient `placeholderData: keepPreviousData` + `gcTime` 5min; revisits render cached data instantly while revalidating
  - log: 2026-06-16 fixed (App.tsx)
- [x] **Home lazy-load panels** - panels are independent queries that render as each resolves; combined with keepPreviousData the fast ones paint first
  - log: 2026-06-16 satisfied (Home.tsx independent queries + App.tsx cache)
- [x] **Remove inline notes + mock-info copy** - stripped the descriptive `oh-note` "Note:" blocks from the real portal pages (LabContainer volumes note, UserHome membership note); kept functional result/constraint `Notice`s; left the internal `/design-*` reference pages
  - log: 2026-06-16 fixed (LabContainer.tsx, Home.tsx)

### Frontend - decide: wire or remove (currently mock, no real backend)

- [x] **Require-password-change switch** - removed; it was an unbound, unwireable control (NativeAuth has no forced-change flag) that misled admins into thinking it did something
  - log: 2026-06-16 removed (UserConfig.tsx)
- [ ] **Spawn-log tail / activity-report** - remove buttons or build endpoints (Servers)
- [ ] **Lab Container image pull / add-remove mount** - remove or build endpoints
- [ ] **Groups import JSON** - wire (parse + create) or remove
- [ ] **Language switch** - apply real i18n or remove the control

### Backend additions needed

- [x] **Expose GPU inventory** - real `stellars_config['gpu_list']` (cached at startup, no per-request container spin) added to the `/activity` response as `gpus:[{index,name,memory_mb}]`; Home Total-resources bar now shows the real device count + names + total memory, not the mock 4-GPU utilisation. ServerHero drops the per-server GPU row in live (per-server GPU not tracked) instead of a fake 0%
  - log: 2026-06-16 fixed (handlers/activity.py, liveSource.ts, meters.tsx, types.ts, Home.tsx, ServerHero.tsx); py_compile + 92 hub-services tests + tsc + eslint + 3 Playwright tests green
- [x] **GPU device picker (policy editor)** - GroupPolicyTab's per-device picker now reads the real host inventory (`useTotalResources().gpuDevices`), not hardcoded `GPU_DEVICES`; empty list -> "No GPUs detected"
  - log: 2026-06-16 fixed (GroupPolicyTab.tsx)
- [x] **Lab Container real config** - the page is now a read-only view of real deployment facts: the spawn image (`JUPYTERHUB_LAB_IMAGE`) and the standard per-user volumes (home/workspace/cache + mounts/descriptions), both surfaced via the `/activity` snapshot (`lab_image` + `lab_volumes` from `stellars_config`). Dropped the fabricated `jupyterhub_datasets`/`scratch` mounts and the non-wireable Set-image / Add-mount / Remove-mount mockActions; a notice points shared/extra volumes to the per-group Volume mounts policy
  - log: 2026-06-16 fixed (jupyterhub_config.py, handlers/activity.py, LabContainer.tsx, datasource.ts, liveSource.ts, mockSource.ts, queries.ts, types.ts); py_compile + 53 hub-services tests + tsc + eslint + 3 Playwright tests green; needs operator rebuild to serve the live fields
- [x] **First/last name + email persistence** - new `UserProfileManager` store (mirrors `groups_config.sqlite`; path env-overridable for tests) + `UserProfileHandler` (GET/PUT `/api/users/{name}/profile`, admin-or-self) wired into `extra_handlers`; profile follows user rename/delete via the `events.py` listeners. Frontend: `UserProfile` type, `getUserProfile`/`saveUserProfile`, `useUserProfile`, and Profile + Configure-user now load and persist first/last name + email (no more fabricated `{name}@lab...`)
  - log: 2026-06-16 fixed (user_profiles.py, handlers/user_profile.py, events.py, jupyterhub_config.py, test_imports.py, test_user_profiles.py, Profile.tsx, UserConfig.tsx, ops.ts, datasource/live/mock, queries.ts, types.ts); 512 hub-services tests (6 new) + tsc + eslint + 3 Playwright green; needs operator rebuild to serve
- [x] **Settings read API** - `SettingsDataHandler` (GET `/api/settings`, admin) returns the live settings (57 entries / 11 categories from `settings_dictionary.yml` + env), shared loader with the stock `SettingsPageHandler`; `liveSource.getSettings` groups them by category (env-var name as tooltip). Read-only by design - the running env is not runtime-writable, so no write API
  - log: 2026-06-16 fixed (handlers/settings.py, handlers/__init__.py, jupyterhub_config.py, test_imports.py, liveSource.ts); py_compile + 512 hub-services tests + tsc + eslint + 3 Playwright green; needs operator rebuild to serve
- [ ] **GPU utilisation %** - device count is now real (inventory above); per-GPU load is still not sampled. Extend the Activity Monitor to sample host GPU usage into the precomputed snapshot, then `gpus` (utilisation array) drives the segmented meter instead of the inventory chips. Note WSL2 caveat: `nvidia-smi --query-gpu=utilization.gpu` is often N/A on this host, so utilisation may stay unavailable regardless
- [ ] **Central precomputed status (confirmed appropriate)** - reuse/extend the existing samplers (`activity/monitor.py`, `container_size_cache.py`, `volume_cache.py`); serve last snapshot without a blocking refresh. Keep users/groups/auth as live DB reads (no precompute)
- [x] **Events feed** - real platform event log: new `EventLogManager` store (SQLite `events` table id/ts/type/text, pruned to 1000 rows; path env-overridable) + bulletproof `record_event(type,text)` helper that never raises; `EventsDataHandler` (GET `/api/events`, admin -> `{events: recent(100)}`) wired into `extra_handlers`. Instrumented the real lifecycle paths: user create/delete/rename (`events.py` listeners), group create/delete + policy update (`handlers/groups.py`), broadcast sent (`handlers/notifications.py`). `liveSource.getEvents` maps rows via an `EVENT_ICON` map (server/user/group/policy/broadcast/cull); event `text` is escaped server-side (`html.escape`) before the `<b>` wrap since the feed renders HTML
  - log: 2026-06-16 fixed (event_log.py, handlers/events_data.py, handlers/__init__.py, jupyterhub_config.py, events.py, handlers/groups.py, handlers/notifications.py, test_imports.py, test_event_log.py, liveSource.ts); 516 hub-services tests (4 new) + tsc + eslint + 3 Playwright green; needs operator rebuild to serve
- [~] **Notification sent-history** - already honest in live: `liveSource.getSentNotifications` returns `[]` (no fabricated history); the mock-mode list is demo-only. A real persistence store is a future enhancement, not a live mock
  - log: 2026-06-16 confirmed honest in live (liveSource.ts)

### Live QA - round 3 (start UX, TTL, versions, perf)

Server-start experience graduates from a modal to a dedicated page with a live spawn-log tail; plus TTL-bar, version-banner and preload fixes found during live testing.

- [ ] **Start -> dedicated page** - starting your OWN server navigates to a start page (e.g. `/servers/:name/starting`), no modal; restart/stop keep the lightweight popup (they settle in seconds)
  - log: 2026-06-16 proposed + criteria captured; not yet implemented
- [ ] **Progress + spawn-log tail** - the page shows a progress bar bound to the spawn SSE plus a rolling tail of the last ~10 progress messages (the SSE `message` field - that IS the spawn log; no new backend needed)
  - log: 2026-06-16 criterion added
- [ ] **Auto-navigate on ready** - on the SSE `ready` event the page redirects to the running server (`userServerUrl`); there is NO Close button on the success path
  - log: 2026-06-16 criterion added
- [ ] **Failure path** - on `failed` (or stream drop without ready), the page shows the error + a Back-to-portal action; no auto-redirect
  - log: 2026-06-16 criterion added
- [ ] **Admin starting another user's server** - lands on the page but on ready returns to the parent screen, never auto-enters someone else's server (consistent with the open-someone-else confirm rule)
  - log: 2026-06-16 criterion added
- [ ] **Edge: SSE unsupported / drops** - fall back to status polling (`isRunning`) as today; still tail the last message
  - log: 2026-06-16 criterion added
- [ ] **Edge: navigate away mid-spawn** - spawn continues server-side; returning reflects current state
  - log: 2026-06-16 criterion added
- [x] **Start popup: no Close on success** - success auto-resolves (navigate own / auto-close other); Close shows only on error (interim, until the start page lands)
  - log: 2026-06-16 done (ServerLifecycle.tsx footer)
- [x] **TTL bar base-relative** - the drain bar measures remaining against the BASE timeout, not the extension ceiling, so a fresh 24h session reads ~100% not ~50%; the extend cap uses available-hours (ceiling gap)
  - log: 2026-06-16 root-caused (wrapper sets MAX_EXTENSION_MINUTES=2880 -> max_extension_hours=48 used as the bar denominator); 2026-06-17 verified (meters.tsx:169 pct = timeLeftMin/baseMin; SessionInfo.baseMin from timeout_seconds)
- [x] **TTL hidden when server stopped** - no progress bar rendered when the server is offline
  - log: 2026-06-17 verified (ServerHero.tsx:54 `{running && <TtlGadget/>}`)
- [x] **Volume reset spinner** - the Reset button shows a loading state while the delete is in flight so the user sees activity
  - log: 2026-06-17 verified (VolumeReset.tsx:16 busy state, :51 `loading={busy}` + "Resetting…")
- [x] **Duoptimum Hub version** - footer + sidebar badge show the build-stamped package version (tracks `package.json`/`pyproject`; `make increment_version` syncs all three), not a hardcoded 1.0.0
  - log: 2026-06-17 verified (vite.config.ts:25 __APP_VERSION__ from package.json 3.12.2; AppLayout.tsx:141 + VersionBadge.tsx:4)
- [x] **JupyterHub version banner** - the footer banner reads live from `/hub/api/info` (5.5.0). CORRECTION: the "JupyterHub 3" the user kept seeing was NOT a stale bundle - it was a hardcoded `STACK_CHIPS` tech-chip `{k:'JupyterHub', v:'3'}` in AppLayout. Fixed to derive the major from the live hub version (5.5.0 -> "5")
  - log: 2026-06-16 mis-attributed to stale bundle; 2026-06-17 ROOT-CAUSED + fixed (AppLayout.tsx VersionFooter hubMajor from hub.version); supersedes the stale-bundle claim
- [x] **Preload core lists** - servers/users/groups/events/stats prefetched at portal start so navigation paints immediately instead of empty-then-lazy (complements the localStorage query cache)
  - log: 2026-06-17 verified (App.tsx prefetchCore warm[] - servers/users/groups/events/stats/resources/hub-info + tokens/lab-container/settings/sent-notifications)

### API (new/changed endpoints)

- GPU inventory: delivered inside the existing `GET /activity` payload as `gpus:[{index,name,memory_mb}]` (admin) - no separate endpoint; reuses the startup-cached `gpu_list`
- `GET|PUT /api/users/{name}/profile` -> `{username,first_name,last_name,email}` (admin or self) - DONE
- Lab Container: delivered inside the existing `GET /activity` payload as `lab_image` + `lab_volumes:[{suffix,mount,description}]` (admin) - no separate endpoint
- `GET /api/settings` -> `{settings:[{category,name,value,description}]}` (admin, read-only) - DONE; no write API (running env not runtime-writable)
- existing, to consume: `GET /api/notifications/active-servers`; `PUT /api/admin/groups/{name}/config` (full body)

### Notes

- The backend group-policy model (`groups_config.py` + `policy/registry.py`) already supports full read+write for all nine sections; the gap is purely the React data layer
- A live GPU inventory already exists (`gpu.py::enumerate_gpus` -> `stellars_config['gpu_list']`); it is just never exposed to the portal
