# Acceptance Criteria - Duoptimum Hub

Consolidated acceptance criteria for the Duoptimum Hub portal and platform - one section per feature, scope or design, assembled from the individual `acc-crit-*.md` documents that remain the editable source of record. Each section keeps its original checklist items, log lines and edge cases.

Cross-document conflicts found during consolidation are tracked in [concerns.md](concerns.md) and have not yet been actioned.

## Contents

- [Activity reporting consistency](#activity-reporting-consistency)
- [Activity map freshness (lightweight, activity-gated)](#activity-map-freshness-lightweight-activity-gated)
- [Activity scoring (target-hours normalisation + honest hours)](#activity-scoring-target-hours-normalisation-honest-hours)
- [Advanced menu ordering](#advanced-menu-ordering)
- [API Keys Pool Group Config](#api-keys-pool-group-config)
- [Background refresh + immediate update](#background-refresh-immediate-update)
- [Environment-stage badge](#environment-stage-badge)
- [Broadcast auto-close duration](#broadcast-auto-close-duration)
- [Last-known cache + non-blocking GPU + GPU-widget gating](#last-known-cache-non-blocking-gpu-gpu-widget-gating)
- [Cert Provisioning](#cert-provisioning)
- [Compose Project Naming](#compose-project-naming)
- [Portal Critic Sweep (Inconsistencies + Illogical Behaviour)](#portal-critic-sweep-inconsistencies-illogical-behaviour)
- [Design Language (System-Wide)](#design-language-system-wide)
- [Docker Policy Access Mode](#docker-policy-access-mode)
- [Drop the `/portal` URL Segment](#drop-the-portal-url-segment)
- [Duoptimumhub Service + Image Rename](#duoptimumhub-service-image-rename)
- [Edit User Returns to Its Origin](#edit-user-returns-to-its-origin)
- [Platform Event Log (Persistence + Clear)](#platform-event-log-persistence-clear)
- [Force Password Change on Next Login (#232 / #233)](#force-password-change-on-next-login-232-233)
- [Functional Test Harness](#functional-test-harness)
- [Functional UI Sweep](#functional-ui-sweep)
- [GPU Utilisation Cache Logging](#gpu-utilisation-cache-logging)
- [gpuinfo-nvidia sidecar (logging + graceful no-hardware)](#gpuinfo-nvidia-sidecar-logging-graceful-no-hardware)
- [Group-Gated File Downloads](#group-gated-file-downloads)
- [Group Policy Import/Export Bundle Shape](#group-policy-importexport-bundle-shape)
- [Unified Group Policy Model](#unified-group-policy-model)
- [Group Sudo Access Control](#group-sudo-access-control)
- [Label Capitalisation (Title Case)](#label-capitalisation-title-case)
- [Live Data Honesty (no mock masquerade)](#live-data-honesty-no-mock-masquerade)
- [Mobile Responsive Portal](#mobile-responsive-portal)
- [Navigation patterns (edit pages -> parent + breadcrumbs)](#navigation-patterns-edit-pages---parent-breadcrumbs)
- [Old portal cleanup](#old-portal-cleanup)
- [Portal UI Polish (2026-06-17 session)](#portal-ui-polish-2026-06-17-session)
- [Profile name display](#profile-name-display)
- [Profile route (role-aware self-view)](#profile-route-role-aware-self-view)
- [Rename user (admin action on the profile)](#rename-user-admin-action-on-the-profile)
- [Resource bars (limits + tooltips)](#resource-bars-limits-tooltips)
- [Restart/stop progress feedback](#restartstop-progress-feedback)
- [Roles reference page](#roles-reference-page)
- [Server lifecycle UX (inline spinners, no modal, real log)](#server-lifecycle-ux-inline-spinners-no-modal-real-log)
- [Server Status Immediacy](#server-status-immediacy)
- [Servers List Layout](#servers-list-layout)
- [Servers Resource Cells](#servers-resource-cells)
- [Dedicated Start-server Page with Live Container-log Feed](#dedicated-start-server-page-with-live-container-log-feed)
- [Startup Hydration](#startup-hydration)
- [TTL Extend Bar Animation](#ttl-extend-bar-animation)
- [TTL Progress Bar Behaviour Matrix](#ttl-progress-bar-behaviour-matrix)
- ["Upgrade Available" Pill](#upgrade-available-pill)
- [Version Sync Across Subpackages](#version-sync-across-subpackages)
- [Volume Reset Confirmation](#volume-reset-confirmation)

---

## Activity reporting consistency

The Activity meter is a 7-DAY engagement metric (capped score + average active hours vs the daily target), not a live reading. It must render the same value on every surface that reports it - the Home servers widget, the Servers screen and the Users screen - whether or not the server is running.

### Consistency

- [x] **Same value on Servers and Users** - the server-list rows (`getServers`, used by Servers + the Home widget) and the user-list rows (`getUsers`, used by Users) derive `activity` / `activityHours` / `activityPct` from ONE shared helper, so the two builders cannot diverge
- [x] **Reported on every surface** - Home servers widget, Servers screen and Users screen show the identical meter for the same user
- [x] **7-day metric, not gated on run state** - `activity` reflects the trailing-window engagement, never nulled because the server is offline / spawning; only live readings (CPU, memory, system) stay gated on `running`
- [x] **Shown when the server is stopped** - an offline user with a non-zero `activity_score` shows the meter (not a muted dash) on Servers and the Home widget, matching Users
- [x] **Mock matches live** - the demo source applies the same rule (offline + spawning rows show the 7-day meter), so `/design-language` and the mock screens never contradict the rule

### Edge cases

- [x] **Edge: never sampled** - a user with no activity samples reads `activity = 0` (a 0-lit meter), the same on all surfaces - not a dash on one and a meter on another
- [x] **Edge: spawning** - a coming-up server shows the 7-day meter (historical engagement exists independent of the in-progress spawn); live CPU/mem stay blank until ready
- [ ] **Edge: pending signup (no hub user)** - a not-yet-authorised signup with no hub User row reads `activity = 0`; it appears on Users (pending bucket) only, not on Servers/Home

### Tests

- [x] **Functional: launch -> stop -> observe** - a Playwright test creates a user, starts their lab, leaves it ~10s, samples activity while active, stops it, then asserts the Activity meter is present (not a dash) and identical across Servers, Users and the Home widget


## Activity map freshness (lightweight, activity-gated)

The portal's per-user activity map (status + CPU/memory) must reflect a lab's current state promptly, without a slow `/activity` request and without polling idle containers. Live `docker stats` is moved off the request path into a warm snapshot that is refreshed lazily and only for recently-active users. Backend: `container_stats_cache.py` (snapshot + `get_container_stats_with_refresh`), `docker_utils.py::stats_from_container` (shared stats math), `handlers/activity.py` (reads the snapshot).

### Endpoint latency

- [x] **No synchronous docker gather on the request path** - `/activity` no longer does `asyncio.gather(get_container_stats_async ...)` over active users; it reads the warm snapshot and returns instantly
- [x] **Status is request-fresh** - per-user active/idle status (`recently_active`) is computed live from `spawner.orm_spawner.last_activity` each request (no Docker), so the status pill is current the moment `/activity` returns
- [x] **Instant on navigation** - switching to a portal page paints the current status immediately (the snapshot read is non-blocking); cpu/mem fill from the snapshot (<= one interval old)

### Lightweight + activity-gated refresh

- [x] **No always-on timer** - there is no background `PeriodicCallback`; the refresh fires only when `/activity` is polled and the snapshot is stale
- [x] **Only active users are sampled** - the refresh samples `docker stats` ONLY for users in the recently-active set (`recently_active`, the kernel `last_activity` signal the platform already uses); idle-but-running containers are never polled
- [x] **Idle-but-running keeps its last value** - a running container that is not recently active retains its last snapshot entry (not refreshed, not pruned), so its cell still shows the last sampled cpu/mem (~0 once idle)
- [x] **Zero docker calls when all idle** - when no user is recently active the refresh is not even triggered (`active_encoded` empty -> no submit, no `/containers/json` list)
- [x] **At most once per interval** - a `refreshing` guard + the staleness check mean overlapping polls collapse to a single in-flight refresh per interval
- [x] **Interval is env-configurable** - `JUPYTERHUB_ACTIVITYMON_STATS_INTERVAL` (default 10s) sets how fresh an active user's cpu/mem cell is

### Snapshot correctness

- [x] **Keyed by encoded username** - the snapshot is keyed by the escapism-encoded username (the `jupyterlab-<encoded>` suffix); the handler maps each active user via `encode_username_for_docker(user.name)`
- [x] **Stopped containers pruned** - on a refresh that runs, entries whose encoded username is not among the running containers are dropped
- [x] **Shared stats math** - cpu%/cores(+limited)/memory(+limited)/image_id come from `docker_utils.stats_from_container`, the single source used by both the ad-hoc `get_container_stats` and the refresher (no duplicated formula)
- [x] **Edge: docker unreachable** - any docker failure in a fetch leaves the prior snapshot intact and never raises into `/activity` (the fetch returns None, the response still finishes)
- [x] **Edge: cold start** - before the first refresh lands the snapshot is empty, so an active user's cpu/mem is briefly absent (status still shown) and fills on the next poll; never a blocking wait

### Tests

- [x] **stats_from_container** - cpu%/assigned cores/memory/image_id computed from a fake container, limited and unlimited paths, None on a stats error
- [x] **Staleness + trigger gating** - `get_cached_container_stats` flags stale when never/expired; `get_container_stats_with_refresh` submits a refresh only when the active set is non-empty AND stale, and never when the active set is empty

### API

- `GET /hub/api/activity` -> per-user `{..., cpu_percent, cpu_cores, memory_mb, memory_percent, memory_total_mb, recently_active, ...}` (admin); cpu/mem sourced from the warm snapshot, status from `last_activity`


## Activity scoring (target-hours normalisation + honest hours)

The activity score is the user's recent active time measured against a daily target (`JUPYTERHUB_ACTIVITYMON_TARGET_HOURS`, default 8h), not against the 24h clock. Samples are taken 24/7, so the decay-weighted active fraction is the share of the day active; the score normalises that against the target and caps at 100. A separate honest hours figure (`activity_hours`, real avg active hours/day, uncapped) drives the meter tooltip.

### Root cause (under-reporting: Natalia 33%)

- [x] **Identified** - `monitor.get_score` returned the raw decay-weighted active fraction (active / all 24/7 samples), so an 8h/day user maxed at 8/24 = 33%
- [x] **Regression source** - the original `activity.html` normalised client-side (`normalized = activity_score / (targetHours/24)`, i.e. 33/0.333 ≈ 100); the React portal dropped that step and showed the raw 33%
- [x] **Unused setting** - `JUPYTERHUB_ACTIVITYMON_TARGET_HOURS` was documented and passed to templates but never referenced by the scorer

### Fix

- [x] **Normalise in the backend** - `get_score` returns `min(100, round((active_fraction*24 / target_hours) * 100))` so every consumer (portal, log buckets) agrees; the normalisation lives once, in the scorer
- [x] **8h/day -> 100** - a user active the target hours scores 100, not 33
- [x] **Proportional below target** - ~4h/day scores ~50
- [x] **target_hours config** - read from env (1-24, default 8), echoed in the config log line
- [x] **Capped meter, honest tooltip** - the 0-100 score caps at 100 (old client was uncapped, could show 150%); the real uncapped hours live in `activity_hours` for the tooltip
- [x] **Edge: no samples** - `get_score` returns `(None, 0)`, `get_avg_active_hours` returns `None`
- [x] **Existing behaviour preserved** - all-active -> 100, all-inactive -> 0, recent-active-dominates still holds

### Honest hours tooltip (was: reword to avg hours over 3 days)

- [x] **Real hours exposed** - `/activity` returns `activity_hours` per user (decay-weighted avg active hours/day, uncapped), from `calculate_avg_active_hours`
- [x] **Tooltip wording** - the meter tooltip reads "Active on average Nh/day over the last 3 days" (3 days = the 72h half-life window); falls back to "N% of the daily activity target" when hours are absent
- [x] **No fabrication** - hours come from real samples; never derived from a percentage
- [ ] **Runtime: heavy users read high** - on the live hub a full-time user shows ~100% with a truthful Nh/day tooltip

### Servers-page activity tooltip (added 2026-06-17, #247)

- [ ] **Real uncapped %** - the activity meter tooltip on the Servers page shows the real activity %, which MAY exceed 100% (a user working more than the 8h/day target reads >100%, which is good); the displayed % is NOT clamped
- [ ] **Multiline** - the % and the existing "Active on average Nh/day" info on separate lines, not one super-long single line
- [ ] **Reflected in the design language** - the activity-% tooltip convention appears on /design-language as a visual cue
- [x] **Same tooltip on Servers, Users and the server resources widget** - the user-activity meter carries the identical multiline tooltip everywhere it appears (Servers list, Users list, and the "Server status" resources widget): uncapped `% of the daily activity target` + `Active on average Nh/day over the last 3 days`
- [x] **Same tooltip on the Home servers widget** - the Home "Active servers" preview activity meter carries the same multiline tooltip as the Servers list; it passes `hours`/`pct` from the shared `ServerRow`, not the bare `value`-only meter

### API

- `GET /api/activity` -> each user gains `activity_hours: number | null` alongside `activity_score`
- Env `JUPYTERHUB_ACTIVITYMON_TARGET_HOURS` (1-24, default 8) - daily active hours that count as a 100% score


## Advanced menu ordering

The items in the Administration -> Advanced submenu are ordered alphabetically by label, so the menu stays predictable as leaves are added. Definition: `app/nav.ts` `NAV_ADMIN` Advanced `children`. Verified against the code 2026-06-18.

- [x] **Alphabetical by label** - Advanced children are listed A->Z by their `label`: Roles, Settings, Tokens
- [x] **Case-insensitive, label-based** - ordering keys off the visible label, not the `id` or `path`
- [x] **New leaves keep the order** - any item added to Advanced is inserted at its alphabetical position, not appended
- [x] **Scope: Advanced only** - the rule applies to the Advanced submenu; top-level Administration items keep their deliberate workflow order (Servers, Users, Groups, Lab Setup, Events, Notifications, Advanced)


## API Keys Pool Group Config

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


## Background refresh + immediate update

The portal keeps lists/status current without manual navigation: mutations reflect at once (optimistic + immediate background refetch), and the live dashboard self-polls so a background change (a server coming up, status flips) shows on its own. Paradigm: when something happens in the background, a monitor watches and the affected view refreshes immediately on completion.

### Mutation-side (immediate effect on change)

- [x] **Immediate background refetch** - `invalidate()` uses `refetchType: 'all'` so a mutation refetches the affected list even when it is unmounted (RQ default only refetches active observers); navigating back shows fresh data, not stale-until-next-mount
- [x] **Optimistic patch** - `patchQuery()` patches the query cache at once (e.g. `saveUserProfile` updates the `['users']` fullName immediately, like the Groups page's inline-edit immediacy); the PUT + invalidation reconcile, and a failure refetches to roll back
- [x] **Why it was slow** - the user list's name comes via `getUsers` which `Promise.all`s the fast `/users`+`/user-profiles` with the heavy `/activity`; without the optimistic patch the saved name only appeared after the slow refetch

### Background polling (self-refresh)

- [x] **Adaptive poll on live queries** - `servers`, `hero`, `stats`, `resources` carry `refetchInterval`: FAST (2.5s) while a server is spawning, SLOW (15s) when stable
- [x] **No poll for slow data** - `users`/`groups`/`settings`/`tokens` are not polled (they change only on admin action)
- [x] **Paused when hidden** - `refetchIntervalInBackground: false` so a backgrounded tab stops polling (each `/activity` sample runs docker stats)
- [x] **Server-status-after-start heals** - root cause: the Start page navigates on the SSE `ready`, the hub's `/users/{user}` can still report `ready:false` for a few seconds, Home did ONE refetch that caught the mid-settle state, and nothing re-polled (no `refetchInterval`) so it stuck "Offline" until the 30s staleTime. Fast poll while spawning now flips it to active within ~2.5s
- [ ] **Runtime: status flips within ~2-3s of start** - confirm on the live hub the post-start Offline window is gone

### Prefetch (already present)

- [x] **Boot prefetch** - `App.tsx::prefetchCore` warms 12 list queries at app init; `persistCache` hydrates from localStorage so first paint is instant
- [ ] **Edge: prefetch on nav hover** - optional Phase 3 (sider link `onMouseEnter` -> `prefetchQuery`) - not yet implemented

### Adversarial-critic fixes (2026-06-17)

- [x] **C1: settle window heals** - the original adaptive poll only fast-polled on `status==='spawning'`, but the post-spawn settle window (spawner present, not ready, no pending) mapped to `offline` and fell to the 15s poll. `statusOf` now reads that window as `spawning`, and `useSpawnProgress` invalidates servers/hero/stats/resources on the SSE `ready` - so the started server heals in ~2-3s, not up to 15s
- [x] **H1/H3: /activity storm coalesced** - `refetchType:'all'` + the fact that getUsers/getServers/getStats/getServerHero all fetch `/activity` meant one mutation fired 3-4 concurrent docker-stat sweeps. A 1.5s in-flight coalescing cache on `fetchActivity` collapses them to one
- [x] **H2: drop wasteful idle poll** - `stats`/`resources` no longer poll on a flat 15s interval (each dragged `/activity`); they refresh on mutation
- [x] **M1: optimistic patch live-only** - `saveUserProfile`'s `patchQuery` is guarded by `!isMock()` so it doesn't desync the mock cache
- [x] **M2: fullName matches backend** - optimistic `fullName` falls to `undefined` when both names blank (matching `getUsers`), no empty-string flicker
- [x] **M3: synchronous rollback** - the prior rows are snapshotted and restored synchronously on a failed write (not a refetch that shows the wrong value until it lands)

### Out of scope (follow-up)

- [ ] **Slow/fast split** - decouple the light list fields from the heavy `/activity` so lists paint instantly and CPU/mem/activity cells fill in after (Phase 2); the coalescing cache mitigates the cost in the interim


## Environment-stage badge

A small outlined rectangle in the portal header naming the deployment stage (DEV/STG/TST/PRD), coloured per stage, so operators can tell environments apart at a glance. Driven by `JUPYTERHUB_BRANDING_STAGE` -> `window.jhdata.stage` (frozen at hub start); empty = no badge. Frontend: `components/StageBadge.tsx`, rendered top-right in the `AppLayout` `oh-topbar` header row. Backend: `branding.py::setup_branding(stage=...)` -> `branding['stage']` -> `template_vars['branding_stage']` -> `portal.html`.

### Behaviour

- [x] **Env-driven** - the badge text and presence come from `JUPYTERHUB_BRANDING_STAGE`, read once at hub start
- [x] **None by default** - empty/unset env renders nothing (no element, no padding gap)
- [x] **Top-right placement** - badge sits at the top-right of the portal header, to the right of the language + theme controls; all three render in the `oh-topbar` header row
- [x] **Outlined rectangle** - 1px border + text both in the stage colour (`currentColor`), transparent fill, square-ish corners (`--radius-sm`)
- [x] **Colour per stage** - DEV green, TST blue (accent/cyan per the design theme), STG orange, PRD red
- [x] **Unknown text grey** - any value not in {DEV,STG,TST,PRD} still renders, in neutral grey (`--oh-gray`)
- [x] **Case-insensitive match** - the stage key is matched uppercased, so `dev`/`Dev`/`DEV` all map to green
- [x] **Raw value displayed** - the badge shows the operator's text (CSS uppercases it for display), not a remapped label
- [x] **Stripped server-side** - leading/trailing whitespace is trimmed before injection
- [x] **Injected via window.jhdata** - the value reaches the SPA through `portal.html` `window.jhdata.stage`, same channel as `admin_user`/`gpu_enabled`
- [x] **Restart to change** - the value is frozen into `template_vars` at config load; changing the env takes effect on hub restart

### Env namespace

- [x] **Branding env namespace** - all branding env vars share the `JUPYTERHUB_BRANDING_*` prefix: STAGE, LOGO_URI, FAVICON_URI, FAVICON_BUSY_URI, LAB_MAIN_ICON_URI, LAB_SPLASH_ICON_URI
- [x] **Settings + dictionary updated** - the renamed keys appear on the Settings page (data-driven from `settings_dictionary.yml`); STAGE added as an editable entry

### Edge cases

- [x] **Edge: whitespace-only value** - a value that is only spaces trims to empty -> no badge
- [x] **Edge: lowercase stage** - `dev` matches green and displays `DEV`
- [x] **Edge: long/custom text** - arbitrary text (e.g. `STAGING`) renders grey without breaking the header layout (`white-space: nowrap`)
- [x] **Edge: auth pages** - login/signup screens have no app header, so the badge does not appear there (portal only)

### Tests

- [x] **Unit: stage normalization** - `setup_branding(stage=...)` returns `branding['stage']` stripped, `''` when unset; default-keys test includes `stage`
- [x] **Functional: no badge by default** - default (signup) deployment has no stage env -> the header shows no `.oh-stage-badge`; also asserts the language + theme controls render in the `.oh-topbar` header row (right of the breadcrumb), not the sider
- [x] **Functional: badge shows configured stage** - env-mode deployment with `JUPYTERHUB_BRANDING_STAGE=TST` shows a `TST` badge in the blue/accent tone, placed top-right (rightmost control: `badge.x > theme.x > lang.x`), not the sider

### Configuration

- `JUPYTERHUB_BRANDING_STAGE` - environment-stage badge text; `DEV` / `STG` / `TST` / `PRD` recognised (coloured), any other text renders grey, empty/unset = no badge


## Broadcast auto-close duration

The notifications broadcast composer picks an auto-close duration from five presets instead of an on/off toggle. The chosen value (milliseconds) flows to the lab Notification API via the broadcast payload.

- [x] **Five presets** - 30s, 1min, 10min, 30min, 1h, rendered as a segmented control
- [x] **Default 30s** - 30s is auto-selected on load
- [x] **User-changeable** - the admin picks any preset before sending
- [x] **Wired through** - `broadcast(message, variant, autoCloseMs, recipients)` sends `autoClose` (ms) in the POST body; the backend forwards it to the notification payload unchanged
- [x] **Correct unit** - values are milliseconds, what JupyterLab's `Notification` autoClose expects

### API

- `POST /hub/api/notifications/broadcast` body `autoClose: number` (ms) - forwarded to each lab's notification ingest as `autoClose`


## Last-known cache + non-blocking GPU + GPU-widget gating

The portal stays responsive across hub restarts: slow server-side aggregates (volume sizes, GPU inventory) persist their last-known snapshot and seed from it on boot, GPU detection never stalls startup, and the GPU widget is hidden when the platform has no GPU. `[x]` = implemented + verified by code-read / unit-check; `[ ]` = pending runtime confirmation (needs an image rebuild + restart).

### Persisted last-known cache (shared helper)

- [x] **Helper exists** - `persisted_cache.py` exposes `save_cached(name, data)` + `load_cached(name)`
- [x] **Atomic write** - snapshot written via tempfile + `os.replace` so a crash mid-write cannot corrupt the seed
- [x] **Shape** - file is `{timestamp: iso, data}` on the data volume (`JUPYTERHUB_DATA_DIR`, default `/data`)
- [x] **TTL-gated load** - a snapshot older than `JUPYTERHUB_CACHED_DATA_TTL_MINUTES` (default 1440 = 24h) is ignored on boot, returns None
- [x] **Best-effort** - missing or corrupt file returns None and never raises (cannot block startup)
- [x] **Configurable TTL in minutes** - `JUPYTERHUB_CACHED_DATA_TTL_MINUTES` read in minutes, multiplied to seconds
- [x] **Env baked, not in compose** - the TTL env is in the Dockerfile + settings dictionary only

### Volume sizes (first consumer)

- [x] **Uses the helper** - volume_cache persists on refresh and seeds on boot via the shared helper
- [x] **Seed only when no live data** - boot seed does not regress live in-memory data
- [x] **Non-blocking** - the fetch is deferred to the shared executor; startup only compiles templates + loads the seed
- [ ] **Runtime: survives restart** - after a hub restart the portal shows last-known volume sizes immediately, not empty

### GPU inventory + non-blocking detection

- [x] **Self-start sidecar** - the hub starts the `gpuinfo-nvidia` sidecar itself; `ensure_gpuinfo_sidecar` returns a bool (True running / False unavailable)
- [x] **Skip probe when sidecar down** - when self-start returns False, detection skips the live probe entirely (no DNS/connect stall)
- [x] **Bounded probe** - the boot probe is ~6x0.5s (max ~3s), not the old 20x1.0s (~20s)
- [x] **Persist fresh inventory** - a successful probe saves the inventory as last-known
- [x] **Seed from last-known** - an empty/skipped probe seeds gpu_list from the persisted inventory (within TTL)
- [x] **Mode semantics** - mode 0 never probes; mode 2 collapses to on/off from inventory; mode 1 stays forced-on with empty list when sidecar down
- [x] **Runtime: no 20s boot stall** - boot logs show the sidecar self-start line and no ~20s GPU gap

### GPU widget global gating

- [x] **Authoritative flag exposed** - `gpu_enabled` is injected into the portal shell `window.jhdata` (template_var)
- [x] **Frontend accessor** - `gpuSupported()` reads `window.jhdata.gpu_enabled`, defaults true in mock/dev
- [x] **Widgets gated** - ResourceBars (Home + ServerHero), the Servers GPU column, and the GroupPolicy GPU section render only when supported
- [x] **Mock keeps GPU on** - design pages still demo GPU (no jhdata -> default true)
- [ ] **Runtime: no-GPU host hides every GPU surface** - on a GPU-less deployment no GPU widget appears anywhere

### Prefetch all key pages

- [x] **Key-page data warmed at start** - prefetchCore warms servers/users/groups/events/stats/resources/hub-info plus tokens/lab-container/settings/sent-notifications
- [x] **No off-screen DOM prerender** - routes are statically bundled (no React.lazy), so only data is warmed, not hidden component trees


## Cert Provisioning

Hub provisions Traefik TLS at boot via `00_provision_certificates.sh`, reconciling the `/user-certs` overlay against the `/certs` runtime volume and choosing operator > persisted > auto. `/certs` is the dir Traefik scans; copying the overlay into the volume makes operator certs survive a failed host-bind mount across restarts.

- [x] **Runtime dir `/certs`** - `CERTIFICATE_TARGET_DIR` default `/certs`; Traefik file provider scans it (`watch=true`); hub writes here; backed by the `jupyterhub_certs` named volume
- [x] **Overlay `/user-certs`** - `CERTIFICATE_USER_CERTS_DIR` default `/user-certs`; read-only host bind of `./certs`; optional - missing/empty means no operator certs
- [x] **No legacy `/mnt` cert paths** - no `/mnt/certs` or `/mnt/user_certs` in compose, Dockerfile, script, config, docs; historical JOURNAL entries exempt
- [x] **Operator tier** - `/user-certs` has >=1 `*.yml`/`*.yaml` AND every `certFile`/`keyFile`/`caFile` resolves to an existing file -> source `operator-supplied`
- [x] **Operator copy + rewrite** - delete top-level cert artifacts in `/certs`, `cp -a` overlay into `/certs` (subdirs included), sed-rewrite `/user-certs/` -> `/certs/` in copied yml so paths stay self-consistent
- [x] **Persisted tier (symmetric)** - overlay empty/invalid AND `/certs` has >=1 yml whose every referenced file exists (recursive descent, `.pem` + subdirs accepted) -> keep `/certs` as-is, source `persisted`
- [x] **Auto tier** - operator + persisted both invalid -> `mkcert.sh` self-signed (CN `$CERTIFICATE_DOMAIN_NAME`, 2048-bit, 365d, no SAN) + default `certs.yml` into `/certs`, source `auto-generated`
- [x] **Tier precedence** - operator > persisted > auto, evaluated in that order
- [x] **All-or-nothing set** - a single missing reference rejects the whole tier's set and falls through to the next tier
- [x] **Path resolution** - `resolve_under(dir,path)`: paths under `/user-certs` or `/certs` both remap under `dir`; other absolute pass through; bare/relative go under `dir`; used by operator (dir=`/user-certs`) and persisted (dir=`/certs`)
- [x] **Status banner** - startup logs `[Certificates]` source label, every yml present, per-cert subject/SAN/issuer/expiry (per-cert detail globs `*.crt` only, so `.pem` certs log the yml but not subject - cosmetic)
- [ ] **Resilience: failed host mount** - overlay fails to mount on restart (empty) + valid copy in `/certs` volume -> persisted serves the wildcard, not self-signed
- [x] **Resilience: `.pem` subdir recognised** - operator wildcard stored as `_.x/cert.pem` recognised by the persisted tier
- [x] **Resilience: no clobber** - a valid volume copy is never overwritten by auto-generate
- [x] **Direct-SSL mode** - `JUPYTERHUB_SSL_ENABLED=1` uses `/certs/server.crt` + `/certs/server.key`
- [x] **Image bake** - Dockerfile `ENV CERTIFICATE_TARGET_DIR=/certs` + `CERTIFICATE_USER_CERTS_DIR=/user-certs`; `COPY templates/certs -> /certs`
- [x] **Compose wiring** - `jupyterhub_certs:/certs` (hub + traefik), `./certs:/user-certs:ro` (hub overlay), provider dir `/certs`
- [x] **Functional test mount** - `tests/functional` compose mounts `certs:/certs`
- [x] **Wrapper certs.yml** - operator yml uses `/certs/...` paths; comment references the `/user-certs` overlay
- [x] **Wrapper Traefik mount** - `./certs:/certs:ro` retained (host bind; Traefik reads `/certs`); deliberate, not changed
- [x] **Docs** - `docs/certificates.md` covers two dirs, three tiers, resilience rationale, path rules, reverse-proxy variant, logs, file reference
- [x] **Edge: first boot, both empty** - empty overlay + empty volume -> auto-generate
- [x] **Edge: yml present, cert/key missing** - operator invalid (logged) -> fall to persisted, else auto
- [x] **Edge: cert/key present, no yml** - no yml in dir -> tier invalid -> fall through (yml required)
- [ ] **Edge: corrupt / unparseable yml** - `yq` error -> `extract_paths` empty -> zero refs -> currently treated as valid (set copied/kept); Traefik then logs a parse error and keeps last-good
- [x] **Edge: yml with no cert refs** - tls-options-only yml -> zero refs -> valid; loaded as Traefik config, no cert asserted (same semantics both tiers)
- [x] **Edge: multiple yml files** - all loaded by the directory provider (multi-domain / split-CA)
- [x] **Edge: subdir / `.pem` layout** - copied via `cp -a` and validated via recursive extract + resolve

### Verification

- [x] **Unit/import tests** - `make test` = 556 (hub-services) + 63 (docker-proxy) pass
- [x] **Script syntax** - `bash -n` clean
- [x] **Persisted simulation** - operator-valid; persisted recognises `.pem`-subdir wildcard; empty volume -> auto (no false-persist)
- [ ] **Live end-to-end** - rebuild + restart: banner shows `operator-supplied`; a forced empty-overlay restart still serves the wildcard via persisted

### Env

- `CERTIFICATE_TARGET_DIR` (default `/certs`) - runtime dir Traefik scans
- `CERTIFICATE_USER_CERTS_DIR` (default `/user-certs`) - operator overlay
- `CERTIFICATE_DOMAIN_NAME` (default `localhost`) - CN for the auto-generated cert

## Compose Project Naming

Two explicit compose-project env vars replace the bare `COMPOSE_PROJECT_NAME` inside the hub: `JUPYTERHUB_COMPOSE_PROJECT_NAME` (the hub's own project - volume namespace + hub-infra labels) and `JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME` (the label stamped on spawned lab containers). They may differ; the lab var defaults to the hub project (empty suffix = same).

- [x] **Hub var read** - config reads `JUPYTERHUB_COMPOSE_PROJECT_NAME`, falling back to `COMPOSE_PROJECT_NAME` during transition; required non-empty (raises otherwise)
- [x] **Volume namespacing unchanged** - per-user + shared + docker-proxy volume names stay on the hub var with the same value, so existing volumes still resolve (rename only, no re-namespacing)
- [x] **Lab var** - `JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME` is the `com.docker.compose.project` label on spawned labs; defaults to the hub project (empty = same), set to group labs under a different project
- [x] **Hub-infra labels use the hub var** - the gpuinfo sidecar the hub self-starts is labelled with `JUPYTERHUB_COMPOSE_PROJECT_NAME`
- [x] **Configured in compose** - both vars passed to the hub in compose.yml (hub mapped from compose's `COMPOSE_PROJECT_NAME`; lab empty -> same project)
- [x] **Baked in Dockerfile** - both `ENV`s present (empty defaults)
- [x] **In settings dictionary** - both on the Settings page (old `COMPOSE_PROJECT_NAME` entry renamed)
- [ ] **Edge: stale wrapper compose** - wrapper compose.yml (gitignored download) still passes `COMPOSE_PROJECT_NAME`; the fallback boots the hub correctly until it is refreshed to pass `JUPYTERHUB_COMPOSE_PROJECT_NAME`
- [x] **Verified** - `python -m py_compile` config clean; `make test` 566 + 63 pass

## Portal Critic Sweep (Inconsistencies + Illogical Behaviour)

Findings from the 2026-06-17 two-agent critic sweep of every portal screen, deduplicated and prioritised. `[x]` = fixed + tsc-verified this session; `[ ]` = open. Runtime confirmation of every fix needs an image rebuild. Severity in the label.

### Fixed this session (code + tsc verified 2026-06-17)

- [x] **[HIGH] Duplicate `timeAgoShort`** - Home had a local long-form ("5 min ago") shadowing the shared short-form; deleted, now imports `lib/format`
- [x] **[HIGH] `NaN%` segment widths on empty platform** - MetricCard segments divided by `total` (0 at first boot)
- [x] **[HIGH] `undefined GB` in VolumeReset** - Size cell rendered `{v} GB` with no null guard
- [x] **[MED] GPU row "none" text** - empty GPU row in ResourceBars printed the word "none"
- [x] **[MED] Tokens long-form time** - Tokens used `timeAgo` (".. ago") vs the short form everywhere else
- [x] **[HIGH] Missing zebra rows** - Home active-servers preview, BulkResult, GroupsExport, SettingsReference tables had no alternating rows
- [x] **[HIGH] GroupsExport opens with 0 selected** - `useState(data.map())` captured empty before data loaded
- [x] **[MED] GroupsExport reversed sort** - sorted ascending vs the Groups list's descending
- [x] **[HIGH] Servers GPU column all-dashes in live** - per-server GPU is never collected -> column of dashes
- [x] **[HIGH] Users "Last seen" literal "never"** - rendered plain "never" not the muted dash convention
- [x] **[HIGH] `gpu_all` silently widens device-scoped groups** - seeded `true` even when specific devices granted

### Open - HIGH

- [x] **[HIGH] Live error -> fake facts** - a failed live GET substituted mock fixtures (3x A100, version, lab image, curated settings) with no signal; FIXED for platform-fact methods - getTotalResources / getHubInfo / getLabContainer / getSettings now return honest EMPTY on live error (no fake GPUs/version/image/settings); keepPreviousData holds the last real value on a transient error
- [x] **[HIGH] `PLATFORM.admin` mock drives live admin protections** - real JUPYTERHUB_ADMIN was unrecognised; FIXED - config exposes `admin_user`(JUPYTERHUB_ADMIN) -> window.jhdata; `isBuiltinAdmin = name === (adminUser() || PLATFORM.admin)`
- [x] **[HIGH] Administrator switch reads persistent `user.admin`** - false for a post_auth_hook-promoted admin -> showed OFF for the real admin; FIXED - `isAdminUser(name, user.admin)` = persistent OR name===admin_user
- [x] **[HIGH] Authorised switch shown/editable for admins** - admins are always authorised; FIXED - Authorised hidden in UserConfig + invisible (muted "authorised") in the Users table for any effective admin
- [x] **[HIGH] `statusOf` shows running server as Spawning** - `pending==='spawn'` checked before readiness; FIXED (liveSource.statusOf checks ready first; pending only when not ready)
- [x] **[HIGH] Events row colour contradicts legend** - server event was green in the legend, cyan in the row; FIXED (Events row reuses exported TONE_CLASS, matches the legend)
- [ ] **[HIGH] Settings signup toggle is a dead control** - uncontrolled defaultChecked wired only to a "(mock)" toast; no live persistence

### Open - MEDIUM

- [x] **[MED] Events missing broadcast/group filter pills** - counted in All but no scope pill, so counts never reconciled; FIXED (added Group + Broadcast scope pills with counts)
- [x] **[MED] Authorised toggle uncontrolled** - `defaultChecked` desynced from data after refetch (Users.tsx); FIXED (controlled `checked={u.authorized}`)
- [x] **[MED] Spawning bucketed as Active but sorted below Idle** - inconsistent counting vs ordering; FIXED (STATUS_ORDER spawning=2, sorts just under active)
- [x] **[MED] GPU section hidden but `gpu_access` round-trips on no-GPU host** - emit preserved gpu_access:true invisibly; FIXED (emit forces gpu_access false when !gpuSupported())
- [ ] **[MED] Policy emit fires on mount before seed** - a fast Save could PUT defaults (GroupPolicyTab); guard emit until cfg seeds
- [x] **[MED] GroupConfig editable Name never persisted** - dead input, change discarded on save; FIXED (Name now disabled/read-only with "cannot be changed" hint)
- [x] **[MED] Mock-mode Save skips validation** - the demo "saved" invalid data; FIXED in UserConfig (validateFields now runs before the mock short-circuit)
- [x] **[MED] Live statusLabel has no time suffix** - mock shows "Active 1m", live showed just "Active"; FIXED (liveSource statusLabel appends timeAgoShort(last_activity); spawning stays bare)
- [ ] **[MED] Authorised defaults true on missing data** - `?? true` makes everyone authorised if native+activity silent (liveSource); unsafe default
- [x] **[MED] Notifications "active" includes spawning** - a spawning server has no extension to ingest -> guaranteed delivery failure; FIXED (recipient list restricted to active/idle ready servers)
- [x] **[MED] Dead "Require password change" toggle** - never read in NewUser/BulkUsers, contradictory defaults; FIXED (removed from both forms - NativeAuth has no forced-change flag)
- [ ] **[MED] Mock THRESHOLDS/IDLE_CULLER used as live** - time-left warn + session-info fallbacks are hardcoded UI constants applied to live data
- [ ] **[MED] Env-var / volume-mount editors no validation** - hint promises rules the UI doesn't enforce (GroupPolicyTab)
- [ ] **[MED] Settings live vs mock divergence** - live dumps all dictionary entries flat (state neutral, no toggle); mock is curated with states; align
- [ ] **[MED] Table row height Servers vs Users differ**
- [ ] **[MED] Import / Export groups are mockActions** - Groups Import + GroupsExport export only toast "(mock)"; wire or hide

### Open - LOW (cosmetic / cleanup)

- [ ] **[LOW] Dead `error` ServerStatus** - no source produces it; drop from union or produce it on failed spawn
- [ ] **[LOW] Pending/credentials tables differ from ProTable density + zebra** (Users pending table, hand-rolled)
- [ ] **[LOW] Inline descriptive notes vs tooltip convention** - GroupConfig/UserConfig/NewUser/Profile inline "extra" notes
- [x] **[LOW] Empty states missing** - Tokens (no tokens / no apps) + Notifications past-history now show instructional empty text
- [x] **[LOW] SettingsReference mock var stale** - listed `JUPYTERHUB_NVIDIA_IMAGE` not the real `JUPYTERHUB_GPUINFO_NVIDIA_IMAGE`; FIXED
- [ ] **[LOW] Column-naming style mixed** - Servers terse (Vol/Sys/Mem) vs Users spelled-out; "Last activity" vs "Last seen" for the same concept

### Disposition of remaining open items (2026-06-17)

Every HIGH and the clear MED/LOW are fixed + deployed. What is left is triaged, not ignored - each open box falls into one of:

- **WON'T FIX (by design / defensive / risk > reward)**: the authorised `?? true` default is correct here because the hub runs `allow_all=True`; the policy emit-on-mount "race" is SUSPECT and a guard would break new-group creation; the dead `error` ServerStatus is harmless defensive code
- **NEEDS EYES (visual, can't verify from the shell)**: Servers vs Users row height (#185, content-driven); the pending/credentials table density; inline-note-vs-tooltip and column-naming are cosmetic + subjective
- **NEEDS A DECISION**: Groups Import / GroupsExport export are `mockAction`s - wire to a real endpoint or hide?
- **DEFERRED REFACTOR (low impact)**: Settings live-vs-mock curation; the time-warn / idle-culler UI thresholds read from constants
- **RUNTIME (needs the browser)**: profile-save "Failed to fetch" (#183)

## Design Language (System-Wide)

The portal's visual conventions, applied consistently across every screen. `[x]` = implemented + verified (code/build/render); `[ ]` = pending. Reference page: `/design-language`.

### Tables / lists

- [x] **Zebra rows** - every antd Table / ProTable / DragSortTable gets alternating row backgrounds, globally (no per-table wiring)
- [x] **Row hover = accent tint** - hovering any row subtly tints its background with the accent colour (overrides zebra + antd's grey hover), system-wide
- [ ] **Two-line cells (sub-names)** - list rows show a primary name + a muted sub (username + first/last name) - NEEDS first/last in the list payload (task #186)
- [ ] **Consistent row heights** - all list rows are the same height (the two-line shape unifies them) - task #186
- [ ] **Consistent margins** - uniform spacing/margins across screens - task #186

### Icons

- [x] **Wireframe default, filled on demand** - icons render as line/wireframe by default; `filled` is opt-in
- [x] **Tones** - primary (blue, active/go-to), secondary (gray, neutral), dangerous (red, destructive), warning (yellow, caution)
- [x] **List icons wireframe; non-list filled** - list/table action icons stay wireframe (fill only for emphasis e.g. stop); non-list/button icons use the filled glyph when one is available

### Text colours

- [x] **Normal-text taxonomy** - five text colours, all from the defined palette vars: neutral (`--color-text`, body), link (`--color-accent`, e.g. a user-profile link), success (`--color-success`, green), warning (`--color-warning`, orange), dangerous (`--color-danger`, red); one utility class each (`.oh-text-*`)
- [x] **Named palette (dim / normal / intense)** - a named colour palette borrowed from the tokens - green (success), cyan/blue (accent), red (danger), orange (warning), gray (text-subtle) - each as `--oh-<name>` with `-dim` (mixed toward surface) and `-intense` (mixed toward text) variants, referable by name; demoed as labelled squares on /design-language ("Palette" card). Magenta is not in the current tokens
- [x] **Activity meter tone by lit-bar count** - the 5-segment meter is a SINGLE tone across all lit bars, chosen by how many bars are lit: 1 bar pale red, 2-3 bars orange, 4-5 bars green (not a per-position gradient, and keyed off the lit count not a raw-value band)
- [x] **Activity meter red is pale** - the meter's red tone (1 lit bar) uses `--oh-red-dim` so the solid blocks read as soft as the thin danger / stop-button glyph; orange = `--color-warning`, green = `--color-success`

### Headers / chrome

- [x] **No page title headers** - the big page title + sub-line are removed (the breadcrumb names the page); only the optional right-aligned actions remain
- [x] **Named edits are explicit** - editing a user profile / group is reached via an explicit named link (the username / group-name), never a whole-row click; row-click is reserved for read-only detail (Servers drawer)
- [x] **Label casing = Title Case** - button labels and header labels (page / card / section titles, table column headers, section tabs) Title-Case every principal word; minor words (a, an, the, and, or, of, to, in, on, at, by, for, with, vs...) stay lowercase unless first/last; acronyms (API, GPU, CPU, TLS, ID) and units (+7h, GB) preserved; sentence copy / form-field input labels / filter data-values stay sentence case. Detail in [acc-crit-label-capitalisation]

### Navigation (system-wide)

- [x] **Sub-screen footer** - every screen reached from a list (Configure user, Configure group, Manage volumes) carries the standard footer: destructive action left, Cancel + a primary Save/Done/Ok right (`FormFooter`); never a dead-end with no way back
- [x] **Respect the navigation path / breadcrumbs** - a screen reachable from more than one parent records its origin in the nav state; the breadcrumb parent AND the Cancel/Done (close) target both reflect where the user actually came from, not a hardcoded route parent
- [x] **Widget actions == list actions** - the Home "Active servers" widget renders the IDENTICAL row actions as the Servers list via the shared `rowActions` (start own -> Start page; start other -> inline spinner; enter/restart/stop; manage volumes), never a divergent widget-only set

### Values / feedback

- [x] **Tooltips, not static text** - precise values (exact GB / % / dates / breakdowns) live in a hover tooltip, never as wasteful static text under the control
- [x] **Progress bars** - the standard bar is base-relative and drains blue -> amber -> red toward the cull; the GPU striped bars are the alternative (one labelled bar per device) for multi-device load
- [x] **GPU device labels = mini names** - per-GPU bars label each device with its mini name (vendor/brand boilerplate stripped: "NVIDIA GeForce RTX 5090" -> "5090") instead of the bare index; full index + name stay in the hover tooltip

### Mobile

- [x] **Minimal home, desktop-parity actions** - below 768px the home is the server card (same actions as desktop) + admin servers widget + a Servers link (no Users); no sider panel, no collapse handle, no header hamburger
- [x] **Mobile Servers view** - the Servers screen on mobile is a card list mirroring the old JupyterHub admin info (user + admin, status, last activity, actions)

### Visual cues to digest from the 2026-06-17 servers/resource batch (#252)

These conventions must be shown on `/design-language` as VISUAL CUES (live example elements), not "this -> that" before/after pairs.

- [ ] **Resource tooltip carries the live % + the assigned reference** - every CPU/memory bar tooltip quotes the usage % alongside the assigned ceiling (cores / GB assigned vs host)
- [ ] **Activity % may exceed 100%** - the activity tooltip shows the real uncapped % (>100% = works more than the daily target), multiline
- [ ] **List vs widget: status/last-activity separate in lists** - in lists, Status and Last activity are separate columns (the widget may club them); column order Status, Last activity, Activity; meters centered in their column
- [ ] **Names are links + carry first/last** - a user name in any list links to the user and shows the first/last name (no artificial click-friction)
- [x] **Admin lifecycle = inline spinner, not navigation** - starting/restarting another user's server spins the control in place; it does not route to a progress screen
- [ ] **Columns sized to content** - status / last-activity columns are just wide enough, not stretched

## Docker Policy Access Mode

The group-policy Docker section's enable toggle means "docker access granted". There is no separate "No docker access" choice (that is the toggle being off). When enabled, the only choice is HOW access is granted: Standard (raw socket) or Limited (per-user filtered proxy, the default), with Privileged orthogonal.

- [x] **No "none" option** - the radio offers only Standard and Limited; the redundant "No Docker access" entry is removed
- [x] **Toggle grants** - `docker_active` (the section switch) being on = access granted; off = no docker, and both `docker_access`/`docker_limited` emit false
- [x] **Limited is the default** - when the section is enabled and Standard is not chosen, the mode is Limited; the quota panel shows for Limited
- [x] **Emission coherence** - on -> exactly one of `docker_access`(std) / `docker_limited`(limited) is true; off -> both false; `docker_privileged` independent
- [x] **Legacy config migrates** - a stored config that was "active but neither mode" (the old none-while-on state) reads as Limited (the default), not a broken empty mode
- [x] **Privileged orthogonal** - the Privileged checkbox is independent of the access mode and unaffected by this change
- [ ] **Runtime: edit + save round-trips** - on the live hub, a group with docker enabled saves as limited (or standard) and re-opens to the same mode

## Drop the `/portal` URL Segment

Serve the React SPA at the hub root (`/hub/...`) instead of `/hub/portal/...`, so the address bar and bookmarks carry no `portal` segment. The SPA's own routes become `/hub/servers`, `/hub/users`, etc.

### Implementation status (2026-06-17)

IMPLEMENTED and verified to the extent possible offline: backend `make test` 566+63 green, `py_compile` + pyflakes clean, portal `tsc -b` + `build:hub` clean, manifest entry is relative (`assets/index-*.js`) so `portal.html` resolves to `/hub/assets/*` matching the route. Decision taken: home client-route renamed to `/dashboard` (nav label stays "Home"); legacy server-rendered page handlers removed (the SPA owns those features). Login/signup are safe - `main.tsx` renders `<AuthApp/>` off `window.jhdata.authPage`, independent of the router/basename. Runtime asset resolution + deep-link routing against the live hub need the user's image rebuild to confirm on-screen. Revert = `git revert` of this change set (cohesive).

### Hard constraint (the reason `/portal` exists today)

JupyterHub registers its built-in page + API handlers BEFORE `c.JupyterHub.extra_handlers` and Tornado matches first-wins (`jupyterhub/app.py` ~1790-1794: `h.extend(default_handlers)` then `h.extend(self.extra_handlers)`). The portal handlers are `extra_handlers`, so they can only claim `/hub/<path>` that no built-in already owns. Built-ins that DO own a path (`jupyterhub/handlers/pages.py:772+`, `apihandlers`): `/hub/` (RootHandler), `/hub/home`, `/hub/admin`, `/hub/login`, `/hub/logout`, `/hub/token`, `/hub/spawn`, `/hub/spawn-pending`, `/hub/user-redirect`, `/hub/error`, `/hub/health`, `/hub/api/*`, `/hub/static/*`, `/hub/metrics`, `/hub/oauth_login`, `/hub/oauth2callback`.

Consequence: the SPA can serve at `/hub/<route>` for every route EXCEPT the reserved ones - and its current landing route `/home` collides with the built-in `/hub/home` (stock page wins on hard-refresh / deep-link), and bare `/hub/` is RootHandler.

### Decision required

- [ ] **Landing-route rename** - move the SPA's home view off the reserved `/home` path (recommended `/dashboard`, keep the nav LABEL "Home"); this is the one user-facing choice and the only thing blocking a clean drop

### Backend (duoptimum_hub_web)

- [ ] **Routes drop `/portal`** - `ASSETS_ROUTE` `/portal/assets/(.*)` -> `/assets/(.*)`, `BRAND_ROUTE` `/portal/brand/(.*)` -> `/brand/(.*)`, `PORTAL_ROUTE` `/portal/?(.*)` -> `/(.*)` (the SPA shell catch-all, still after built-ins so reserved paths win)
- [ ] **PORTAL_URL** - `/hub/portal` -> the chosen landing (`/hub/dashboard`); `default_url = base_prefix + PORTAL_URL` so post-login + `/hub/` land on the portal
- [ ] **Asset/brand precedence** - `/hub/assets/*` and `/hub/brand/*` matched before the `/(.*)` shell catch-all and do NOT collide with built-in `/hub/static/*`
- [ ] **Shell still gets XSRF** - PortalHandler renders the shell for the catch-all so `window.jhdata.xsrf_token` is injected exactly as today
- [x] **Old-path redirect (no /portal flash)** - `/hub/portal[/...]` 302s server-side to the hub-root SPA (`/portal/home` -> `/dashboard`) via `PortalRedirectHandler`, registered before the catch-all

### Frontend (duoptimum-hub-web)

- [ ] **Vite base** - `VITE_BASE` `/hub/portal/` -> `/hub/` (`.env.hub`); drives asset URLs + router base
- [ ] **Router basename** - `portalBasename()` / `portalAssetBase()` drop the `/portal` suffix (read `window.jhdata.base_url` -> `<base>/hub` not `<base>/hub/portal`)
- [ ] **Home route** - `/home` -> `/dashboard` in `router.tsx` (index redirect, `*` fallback), `nav.ts`, and every `navigate('/home')` / `to="/home"` (label stays "Home")

### Edge cases

- [ ] **Reserved paths still work** - `/hub/login`, `/hub/logout`, `/hub/api/*`, `/hub/static/*`, `/hub/spawn`, `/hub/health` are served by JupyterHub built-ins, never the SPA catch-all
- [ ] **Deep-link / refresh** - hard refresh on `/hub/servers`, `/hub/users`, `/hub/dashboard`, `/hub/servers/:name/starting` serves the shell (no 404, no stock page)
- [ ] **Edge: `/hub/home` typed directly** - shows stock hub home (built-in, unavoidable while extra_handlers run after built-ins); the SPA never links there once the landing is `/dashboard`
- [ ] **Edge: bare `/hub/`** - RootHandler redirects to `default_url` (the portal landing)
- [ ] **Edge: wrapper Traefik** - the live stack routes the public root to `/hub`; dropping `/portal` is internal to the hub image and needs no wrapper change
- [ ] **Mock/dev** - dev-proxy + mock (no shell) fall back to `BASE_URL`; `/dashboard` works there too

### API / routes (after)

- `/hub/assets/(.*)` -> ImmutableStaticFileHandler (hashed bundle)
- `/hub/brand/(.*)` -> StaticFileHandler (public, no auth)
- `/hub/(.*)` -> PortalHandler (`@authenticated` shell; reserved paths already claimed by built-ins)
- `default_url = <base_prefix>/hub/dashboard`

## Duoptimumhub Service + Image Rename

The hub's Docker Compose service is renamed `jupyterhub` -> `duoptimumhub` and the published image `stellars/stellars-jupyterhub-ds` -> `stellars/duoptimumhub`, so the deployment matches the Duoptimum Hub branding and the DockerHub push targets the new repo. The hub's URL prefix (`/jupyterhub`, `JUPYTERHUB_BASE_URL`) and all `JUPYTERHUB_*` env vars are unchanged - only the compose service identity and the image tag move. Verified against the code 2026-06-18.

### Compose service rename

- [x] **Service key** - `compose.yml` hub service is `duoptimumhub` (was `jupyterhub`)
- [x] **depends_on updated** - traefik and watchtower `depends_on` point at `duoptimumhub`
- [x] **Traefik identifiers** - router/service/middleware renamed `jupyterhub-rtr`/`jupyterhub-svc`/`jupyterhub-ratelimit` -> `duoptimumhub-*`, consistently in `compose.yml` and the wrapper override
- [x] **URL path unchanged** - the router rule still matches `Path(/jupyterhub)`; the deploy prefix is a separate concern from the service name and was not touched
- [x] **container_name** - the literal suffix is `-duoptimumhub` (`${COMPOSE_PROJECT_NAME:-…}-duoptimumhub`)
- [x] **Hub bind/connect host** - `c.JupyterHub.hub_ip` and `hub_connect_url` in `config/jupyterhub_config.py` use `duoptimumhub`; the hub binds to, and CHP / spawned labs reach the hub by, the compose service name

### Image rename

- [x] **Image tag** - the hub image is `stellars/duoptimumhub` everywhere it is built, tagged, pulled or referenced: Makefile (`HUB_IMAGE`, build `--tag`, `tag`, push, success banners), `compose.yml`, the functional compose, `start.sh`, `start.bat`
- [x] **README DockerHub badges** - image-size and pulls badges point at `stellars/duoptimumhub`
- [x] **Only the hub image** - the gpuinfo (`stellars/stellars-gpuinfo-nvidia`) and lab (`stellars/stellars-jupyterlab-ds`) images are unchanged

### Collaterals (verified independent)

- [x] **gpuinfo sidecar unaffected** - the hub finds the sidecar by its own DNS name (`gpuinfo-nvidia`) and joins the sidecar network by container id, never by the hub's compose service name
- [x] **Networks/volumes unchanged** - network and volume names derive from `COMPOSE_PROJECT_NAME`, not the service name

### Tests + harness

- [x] **Functional harness renamed** - the service is `duoptimumhub` in all three harness compose files; `conftest.py` `BASE_URL`/`HUB_HOST` default to `duoptimumhub`; the Makefile `--wait`/`restart` targets name `duoptimumhub`
- [ ] **Functional suites pass post-rebuild** - `make test-functional` and `make test-functional-env` are green against the rebuilt `stellars/duoptimumhub:latest` image

### Deployment surfaces

- [x] **Wrapper override + compose** - `../compose.yml` refreshed from the submodule; `../compose_override.yml` service + traefik + branding-env names renamed
- [x] **Copier template** - `copier-stellars-jupyterhub-ds` override `.jinja` service key + traefik + image comment renamed; `tests/test_render.sh` assertions updated

### Edge cases

- [x] **Edge: GitHub repo URLs preserved** - `github.com/.../stellars-jupyterhub-ds` and `copier-stellars-jupyterhub-ds` URLs are the repo, not the image, and are left unchanged
- [ ] **Edge: live recreate required** - a running stack must be recreated (`down`/`up`) to pick up the new service + container name; `make start` uses `--no-recreate` and will not rename a running container in place
- [x] **Edge: historical docs untouched** - `CHANGELOG.md`, `docs/medium/*`, and journals keep the old names (they record past state)

## Edit User Returns to Its Origin

Configuring a user (`UserConfig`, route `/users/:name`) is reachable from three places - the Home "Active servers" widget, the Servers list, and the Users list. Save, Cancel and Remove must return to the page the edit was opened from, and the breadcrumb parent must name that origin. Mechanism reuses the existing nav-origin pattern (the one `ManageVolumes` uses): the opening `<Link>` tags `state.from = {to, label}`; `UserConfig` reads `backTo = state.from?.to ?? '/users'`; `Breadcrumbs` prefers `state.from` over the static route parent. Verified against the code 2026-06-18.

### Return navigation

- [x] **From Home -> Home** - opening Configure-user from the Home servers widget returns to `/dashboard` on Save / Cancel / Remove
- [x] **From Servers -> Servers** - opening it from the Servers list returns to `/servers`
- [x] **From Users -> Users** - opening it from the Users list returns to `/users`
- [x] **Cancel returns to origin** - the footer Cancel navigates to `backTo`, not a hardcoded `/users`
- [x] **Save returns to origin** - a successful save (mock and live paths) navigates to `backTo`
- [x] **Remove returns to origin** - deleting the user (live mode) navigates to `backTo`

### Breadcrumb

- [x] **Parent names the origin** - the breadcrumb second crumb is Home / Servers / Users matching where the edit was opened, linking back there
- [x] **Default parent is Users** - with no origin state the crumb falls back to the route's static parent (Users)

### Edge cases

- [x] **Edge: deep link / refresh** - landing on `/users/:name` directly (no `state.from`) returns to `/users` and shows Users as the parent
- [x] **Edge: Profile route (/profile)** - admin self-edit via `/profile` (no `:name`, no origin) keeps the prior behaviour, returning to `/users`
- [x] **Edge: single source of truth** - the same `from`-state shape (`{to, label}`) drives both the return navigation and the breadcrumb, so they can never disagree

## Platform Event Log (Persistence + Clear)

The portal's audit feed (Overview "Recent events" + the Events page) is backed by a persistent SQLite store, so events survive a hub restart; an admin can clear the whole log from the Events panel. Store: `duoptimum_hub_services/event_log.py` (`/data/event_log.sqlite`); handler: `handlers/events_data.py`; UI: `pages/Events.tsx`.

### Persistence

- [x] **Stored in SQLite, not memory** - events are written to `/data/event_log.sqlite` (the persistent `jupyterhub_data` volume), so they survive a hub restart / recreate
- [x] **Bounded** - the table is pruned to the most recent 1000 rows on each record, so it never grows unbounded
- [x] **Override path** - `STELLARS_EVENT_LOG_DB_PATH` overrides the DB location (tests point it at a temp file)

### Clear action

- [x] **Clear button in the Events panel** - the Events toolbar has a danger-toned "Clear log" button (close icon), disabled when the feed is already empty
- [x] **Confirm before clearing** - clicking it opens a confirm modal ("Clear the event log? This permanently deletes every recorded event. This cannot be undone.") with a danger OK
- [x] **Wipes the store** - confirming calls `DELETE /hub/api/events` -> `EventLogManager.clear()` (admin-only), emptying the table; the feed refetches empty
- [x] **Admin-only** - both GET and DELETE on `/api/events` 403 for non-admins
- [x] **Log keeps working after a clear** - new events record normally into the emptied store
- [ ] **Edge: clear is not itself audited** - clearing leaves the log empty (no "log cleared" marker is recorded); revisit if an audit trail of the clear is wanted

### API

- `GET /hub/api/events` -> `{events: [{id, ts, type, text}]}` (admin, newest first, <=100)
- `DELETE /hub/api/events` -> `{cleared: <n>}` (admin) - empties the log

### Tests

- [x] **Store unit tests** - record/recent/prune/clear covered in `tests/test_event_log.py`
- [x] **Functional SPA test** - the harness drives the Events page end-to-end: an admin action records an event, the feed shows it, Clear log + confirm empties the feed and disables the button

## Force Password Change on Next Login (#232 / #233)

An admin can require a user to change their password before they can use the platform. Enforcement is "no escape" at the spawner: a flagged user cannot start a lab by any route until the password is changed. All backend logic lives in the `duoptimum-hub-services` package.

### Storage (duoptimum_hub_services.user_profiles)

- [x] **must_change_password flag** - a Boolean column on the `user_profiles` table, default False
- [x] **Idempotent migration** - a pre-existing DB without the column gets it via `ALTER TABLE ... ADD COLUMN ... DEFAULT 0` (create_all never ALTERs); checked against the column list first
- [x] **Profile edits preserve the flag** - a name/email `save_profile` never clobbers must_change_password

### Set / read (admin only)

- [x] **Admin-only set endpoint** - `POST /api/users/{user}/force-password-change {value}` sets/clears the flag; 403 for non-admin (a user must not clear their own gate)
- [x] **Flag read via the profile** - `GET /api/users/{user}/profile` returns `must_change_password`; the frontend maps it to `UserProfile.mustChangePassword`

### Enforcement (no escape)

- [x] **Spawn hard-block** - `pre_spawn_hook` raises 403 with a clear message when the flag is set, so a flagged user - or an admin starting them - cannot get a lab by ANY route (the no-escape guarantee)
- [x] **Fail-open on a store error** - if the flag cannot be read (profiles DB momentarily unreadable) the spawn is ALLOWED, never blocked - blocking-on-error would lock the whole platform out
- [x] **Clears on a successful change** - `DuoptimumHubAuthenticator.change_password` clears the flag on NativeAuth's success return, so a self-service change lets the user spawn again
- [ ] **Login auto-redirect (deferred)** - a flagged user is NOT yet auto-redirected to the change-password page on login; the spawn-block + the clear message enforce no-escape, but the funnel is manual

### UI (#232 Configure-user)

- [x] **Toggle** - "Force password change on next login" switch on Configure-user (non-builtin users), initial state from `mustChangePassword`
- [x] **Hidden for admins** - the toggle only shows when the configured user is NOT an admin; flipping Administrator on hides it reactively - gated on `liveAdmin`, mirroring the Authorised switch
- [x] **Help is a tooltip on the control, not an inline note or (?) icon** - "The user cannot start their server until they set a new password" is a standard hover tooltip on the switch itself (native `title` on `<Switch>`)
- [x] **Applied after the password set** - in `save()` the flag is applied AFTER any password set, so an admin setting a temp password + forcing a change leaves the gate ON
- [x] **Reactive admin reveal** - flipping Administrator updates the dependent controls at once via `Form.useWatch`

### Edge cases

- [x] **Admin set-password vs force flow** - an admin password set clears the flag; the Configure-user toggle (applied last) re-sets it, so "temp password + force change" works
- [ ] **Runtime: end-to-end** - on the live hub: admin flags a user -> user cannot spawn (clear 403) -> user changes password -> spawn allowed; pends operator rebuild

### API

- `POST /api/users/{user}/force-password-change` body `{value: bool}` -> `{username, must_change_password}`; 403 non-admin
- `GET /api/users/{user}/profile` -> now includes `must_change_password: bool`

## Functional Test Harness

A standing functional regression harness that boots the built hub image in a fully isolated throwaway compose deployment and drives the running platform end-to-end (UI actions + multi-step scenarios) with a containerized Playwright runner. Purpose: validate future fundamental rebuilds; local-only (GitHub cannot run the DockerSpawner deployment); removes everything it creates on completion.

Legend: `[x]` implemented, `[ ]` planned (the test/scenario backlog). Each item is one functional test unless noted. Items needing the real `stellars-jupyterlab-ds` lab image (not the minimal singleuser one) are tagged `(real-lab)` and are out of scope for the default minimal run.

> 2026-06-18 SPA rebuild: the old `test_hub_ui` / `test_scenarios` drove the stock JupyterHub HTML (`#groups-table-body`, Bootstrap modals), dead against the React portal. The harness now drives the live SPA (visible text / antd `aria-label` / placeholders - no data-testids), authenticates by injecting the API session's hub cookies (a direct `/hub/login` self-redirects), and waits on the `.ant-layout` shell not `networkidle`. `make test-functional-all` (22 tests) green across all three setups on a GPU host.

### Setups (initial conditions, run one by one)

- [x] **Sequential multi-setup runner** - `make test-functional-all` boots each setup, runs its regime, cleans, moves to the next, and reports which passed (non-zero exit if any failed)
- [x] **Setup: signup-bootstrap** - fresh DB, signup off; admin via the bootstrap-signup window; runs the full SPA UI suite + container policy + GPU (when present)
- [x] **Setup: env-password admin** - signup off + `JUPYTERHUB_ADMIN_PASSWORD`, restart-to-provision; one focused login test
- [x] **Setup: signup-open** - signup enabled, admin env-provisioned; a non-admin self-signs-up and the admin authorises via the SPA Users page
- [x] **Regime gating** - a conftest collection hook deselects (never skips) tests outside the run's regime, keyed off `FUNCTEST_AUTH_MODE` + GPU presence
- [x] **Coverage declaration + report** - every functional test declares the acc-crit it covers via `@pytest.mark.acc_crit("<doc-slug>::<label>", ...)`; a collected test with no declaration aborts the run, and the suite prints a `MET`/`UNMET` coverage report per criterion at conclusion

### Harness infrastructure

- [x] **Isolated project** - runs under its own compose project `stellars-functest`, never the operator's
- [x] **Isolated network** - `stellars-functest_network`; spawned labs join only this network
- [x] **Namespaced volumes** - project-prefixed volumes; no shared `jupyterhub_*` names
- [x] **Dedicated admin** - `functestadmin`, distinct from any real `admin`
- [x] **No host port** - containerized runner reaches the hub by service name; operator `:8000` never bound
- [x] **Containerized runner** - Playwright runs in `mcr.microsoft.com/playwright/python`; no host browser deps
- [x] **Minimal spawn image** - `quay.io/jupyterhub/singleuser` pulled for spawn; hub image left intact
- [x] **Health gate** - runner waits on the HTTP health endpoint before tests (not the buggy compose pgrep healthcheck)
- [x] **Complete teardown** - on pass or fail, removes containers, spawned labs, network, all volumes, and pulled test images
- [x] **Idempotent clean target** - `make test-functional-clean` force-removes a leftover harness safely
- [x] **CI split** - pytest unit suites run as a GitHub `unit_tests` job; the harness is never wired into CI
- [ ] **Run isolation** - parallel/repeat runs do not collide (unique project suffix per run)
- [ ] **Diagnostics on failure** - capture hub logs + Playwright trace/screenshot artifacts on failure
- [ ] **Edge: interrupted run** - Ctrl-C / killed run still leaves zero trace (trap-based teardown)
- [ ] **Edge: stale harness present** - a prior leftover deployment is cleaned before a new run starts

### Fixtures

- [x] **base_url / admin_creds** - session fixtures from env
- [x] **admin_page / admin_portal** - admin page authenticated by injecting the `admin_api` session's hub cookies (no flaky form login); `admin_portal` wraps it with SPA navigation (`goto(route)` + `.ant-layout` ready wait)
- [x] **clean_groups** - autouse fixture wiping all groups before/after each test (API), so tests are independent
- [x] **admin_api** - logged-in requests session for API-level setup/teardown
- [x] **signup_user** - factory that self-signs-up an arbitrary user via the NativeAuth form (the signup-open pending user)
- [ ] **seeded_groups** - fixture pre-creating a known set of groups for scenarios
- [ ] **seeded_users** - fixture pre-creating non-admin users with set memberships
- [ ] **api_client** - authenticated requests session for API-level assertions alongside the UI

### Auth & bootstrap

- [x] **Login shell served** - `/hub/login` serves the SPA auth shell (`window.jhdata.authPage = "login"`), which renders the antd sign-in screen
- [x] **Signup bootstrap window** - on a fresh DB (signup off, no env password) the first admin is created by signing up, then authenticates and reaches the hub
- [x] **Admin reaches the portal** - the authenticated admin loads the SPA app shell (`.ant-layout`), not bounced to login
- [x] **Admin env-password login (mode 2)** - signup disabled + JUPYTERHUB_ADMIN_PASSWORD; `make test-functional-env` does the restart-to-provision and runs ONE focused test
- [x] **Signup enabled/disabled** - signup form present iff `JUPYTERHUB_SIGNUP_ENABLED=1`
- [x] **Non-admin needs authorization** - a self-signed user lands in the pending queue (`is_authorized=False`), not authorised
- [x] **Admin authorizes user** - admin authorises a pending user through the SPA Users page; the pending queue empties and the backend reports `is_authorized=true`
- [ ] **Logout** - logout returns to login and clears the session
- [ ] **Wrong password rejected** - invalid login shows an error, no session
- [ ] **Edge: failed-login lockout** - N failed attempts locks the account for the window
- [ ] **Edge: admin password change ignores env** - after UI password change, env password no longer logs in

### Hub pages & navigation

- [x] **SPA page-render smoke** - every major SPA screen mounts and shows its signature control: dashboard ("Active servers"), servers (user filter), users ("Inactive" pill), groups ("Add group"), events ("Clear log"), notifications ("Send broadcast"), settings ("Full reference"), lab setup ("Lab image"), design language
- [x] **Groups page renders** - "Add group" button visible (SPA)
- [x] **Settings / Notifications render** - signature controls visible (SPA)
- [ ] **Activity** - activity is folded into the dashboard / servers meters; there is no standalone `/activity` SPA page (the old 200-check is retired)
- [ ] **Admin home renders** - admin home lists users + server controls
- [ ] **Token page renders** - /hub/token page loads, can request a token
- [ ] **Non-admin denied admin pages** - a non-admin user gets 403 on groups/settings/activity/notifications
- [ ] **Nav links** - admin nav exposes the custom pages and they are reachable

### Branding - hub

- [ ] **Custom logo** - `JUPYTERHUB_BRANDING_LOGO_URI` logo renders on hub login/home
- [ ] **Custom favicon** - `JUPYTERHUB_BRANDING_FAVICON_URI` favicon served on hub pages
- [ ] **file:// logo/favicon** - a `file://` URI is copied to the static dir and served
- [ ] **External URL logo/favicon** - an `http(s)://` URI is passed through
- [ ] **Default branding** - empty branding env yields stock JupyterHub assets
- [ ] **Favicon CHP proxy route (real-lab)** - a lab session's favicon request routes back to the hub's custom favicon

### Branding - lab container (injected env, asserted via docker inspect)

- [ ] **Main icon injected** - `JUPYTERLAB_MAIN_ICON_URI` present in the spawned container Env
- [ ] **Splash icon injected** - `JUPYTERLAB_SPLASH_ICON_URI` present in the container Env
- [ ] **Busy favicon injected** - `JUPYTERHUB_BRANDING_FAVICON_BUSY_URI` resolved and reaches the lab
- [ ] **System name rebrand** - `JUPYTERLAB_SYSTEM_NAME` injected into the container Env
- [ ] **System name capitalize / color** - `JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME` and `JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR` injected
- [ ] **Empty = no rebrand** - empty branding env leaves the lab env unset (no rebrand)
- [ ] **Visual rebrand (real-lab)** - welcome page / MOTD / toolbar header badge reflect the system name
- [ ] **Visual icons (real-lab)** - the lab shows the custom main/splash icons and busy favicon frames

### Groups - management

- [x] **Create group** - "Add group" -> the NewGroup form -> Create -> the row appears on /groups
- [x] **Name opens config** - the group-name link routes to `/groups/:name` (SPA, no modal)
- [x] **Delete group** - the danger delete icon removes the row directly (no confirm modal in the SPA)
- [x] **Reorder priority** - the move-up icon reorders the row above its neighbour (optimistic)
- [ ] **Move down** - move-down reorders below its neighbour
- [ ] **Priority persists** - reordered priority survives a page reload
- [ ] **Description** - group description saves and displays
- [ ] **Edit existing group** - reopening a saved group shows its persisted config
- [ ] **Empty state** - no groups shows the "Add Group" empty message
- [ ] **Edge: duplicate name** - creating a duplicate group name is rejected
- [ ] **Edge: invalid name** - name not matching the pattern is rejected with a message
- [ ] **Edge: cancel modal** - cancelling the add/config modal makes no change

### Groups - membership

- [ ] **Add member** - chip-input adds a user to a group
- [ ] **Remove member** - removing a chip removes membership
- [ ] **Member count** - the row member count reflects membership
- [ ] **Members tooltip** - hovering the count lists members
- [ ] **Edge: unknown user** - adding a non-existent user is handled gracefully
- [ ] **Edge: rename sync** - renaming a user in the admin panel keeps group membership

### Policy config - per type (save + reopen + persist for each)

- [x] **Sudo** - enable section, member-sudo on/off; persists
- [x] **Downloads** - enable section, allow/block; persists
- [x] **Memory** - enable cap, set GB; persists
- [ ] **Memory swap** - swap-disabled toggle persists
- [ ] **CPU** - enable cap, set cores; persists
- [ ] **GPU all** - enable access, all-GPUs; persists
- [ ] **GPU specific** - enable access, specific device ids; persists
- [ ] **Env vars add** - enable section, add a var; persists
- [ ] **Env vars remove** - remove a var row; persists
- [ ] **Docker raw** - enable section, raw-socket access; persists
- [ ] **Docker limited** - limited access + quotas (containers/volumes/networks/storage/cpu/mem); persists
- [ ] **Docker dangerous flags** - allow-dangerous toggle persists with warning
- [ ] **Docker compose project** - per-user compose-project enable + allow-override persist
- [ ] **Docker hub-network** - hub-network-access toggle persists
- [ ] **Docker privileged** - privileged toggle persists with warning
- [ ] **API keys pair** - pair mode, id/secret var names + credentials; persists masked
- [ ] **API keys single** - single mode, key var + credentials; persists masked
- [ ] **Volume mounts** - add a volume->mountpoint; persists
- [ ] **Section fold/unfold** - toggling a section active flag shows/hides its body

### Policy config - validation (save rejected with message)

- [ ] **Reserved env var** - a reserved name (e.g. PATH / JUPYTERHUB_*) is rejected, `#config-error` shown
- [ ] **Reserved api-keys target** - reserved pool target var rejected
- [ ] **GPU incoherent** - access on, not-all, no device ids -> rejected
- [ ] **Docker mutual exclusivity** - raw + limited in one group -> rejected
- [ ] **Docker negative quota** - negative quota -> rejected
- [ ] **Mem/CPU zero-when-enabled** - enabled with zero/blank value -> rejected
- [ ] **Volume protected mountpoint** - mounting over /etc, /home etc. -> rejected
- [ ] **Volume duplicate** - duplicate mountpoint or volume -> rejected
- [ ] **API keys incomplete** - enabled pool missing mode/var/credentials -> rejected

### Policy display

- [x] **Badges from policy_summary** - after an API config change the SPA row renders the server-sourced policy tag(s) (`CappedTags`)
- [x] **No badges when inactive** - a group with no active policy shows the empty marker (no `.ant-tag`)
- [x] **Multiple badges** - a group with three active policies renders >= 3 inline tags (cap 4)
- [ ] **Hover tooltip** - the tag detail tooltip lists the valued policy line (hover; not asserted)
- [ ] **Badge per type** - each policy type shows its expected badge text

### Policy resolution scenarios (multi-group)

- [ ] **Priority-wins (sudo/downloads)** - higher-priority configuring group wins (real-lab spawn assert)
- [ ] **Biggest-wins (mem/cpu)** - largest enabled cap wins across groups
- [ ] **OR-grant (gpu/docker)** - any granting group grants
- [ ] **Section-off ignored** - an inactive section does not configure
- [ ] **Env precedence** - higher-priority group env var wins; pool var vs plain var precedence
- [ ] **Volume union** - mounts union across groups; conflict priority-wins

### Spawn & lab lifecycle

- [x] **Spawn creates the container** - starting a server creates `jupyterlab-functestadmin`, inspected for policy effects (test_container_policy)
- [ ] **Spawn with overlay** - spawn-config overlay makes the minimal image spawn reliably
- [ ] **Stop server** - stop returns to a stopped state
- [ ] **Restart server** - one-click restart preserves the container
- [ ] **Sudo applied (real-lab)** - resolved sudo reaches the lab as JUPYTERLAB_SUDO_ENABLE
- [ ] **Env applied (real-lab)** - group env vars present in the lab environment
- [ ] **Volume mounted (real-lab)** - group volume mounted at the configured path
- [ ] **Edge: spawn failure surfaces** - an un-spawnable image shows a spawn error, not a hang

### Spawned container - end-to-end policy application (docker inspect/exec)

- [x] **Container created** - spawning a member of a configured group creates `jupyterlab-<user>` (running)
- [x] **Env: sudo** - container Env has `JUPYTERLAB_SUDO_ENABLE=<resolved>`
- [x] **Env: group vars** - configured group env vars present in container Env
- [ ] **Env: reserved stripped** - reserved names never injected
- [ ] **Env: GPU flags** - `ENABLE_GPU_SUPPORT` / `NVIDIA_VISIBLE_DEVICES` / `CUDA_VISIBLE_DEVICES` match the gpu policy
- [ ] **Env: api-keys** - pool target vars present; two running containers never hold the same credential
- [x] **Mounts: group volume** - the configured volume -> mountpoint appears in Mounts
- [ ] **Mounts: per-user volumes** - home/workspace/cache mounted
- [ ] **Mounts: docker socket** - raw access mounts `/var/run/docker.sock`; limited mounts the proxy subpath + sets `DOCKER_HOST`
- [x] **Limit: memory** - `HostConfig.Memory == cap` bytes; `MemorySwap` per swap policy
- [ ] **Limit: cpu** - `NanoCpus` / `CpuQuota` == ceil(cores)
- [ ] **Privileged** - `HostConfig.Privileged` true only when granted
- [ ] **Network** - attached to the test network; limited-docker hub-network visibility per flag
- [x] **Labels: compose project** - `com.docker.compose.project` stamped on the lab
- [ ] **Labels: api-keys slot** - durable slot label present per pool
- [ ] **Exec: sudo reality** - `exec` confirms sudo availability matches the policy
- [ ] **Exec: mountpoint reality** - `exec` confirms the group mountpoint exists / is writable
- [ ] **Negative: no group** - a member of no group gets defaults (no extra mounts, default sudo)
- [ ] **Edge: leaving a group unmounts** - re-spawn after removal drops the group volume

### Group policy -> container effect matrix

- [ ] **sudo on** -> `JUPYTERLAB_SUDO_ENABLE=1` in Env
- [x] **sudo off** -> `JUPYTERLAB_SUDO_ENABLE=0`
- [ ] **sudo unconfigured** -> platform default value
- [x] **mem 4G** -> `HostConfig.Memory == 4*1024^3`
- [ ] **mem 4G + no-swap** -> `MemorySwap == Memory`
- [ ] **mem disabled** -> no memory limit
- [ ] **cpu 2** -> `NanoCpus == 2e9` (or CpuQuota/Period)
- [ ] **cpu 2.5** -> ceil to 3 cores
- [ ] **gpu all (gpu host)** -> `device_requests` Count -1, `NVIDIA_VISIBLE_DEVICES=all`
- [ ] **gpu specific [0,2]** -> DeviceIDs [0,2], `NVIDIA_VISIBLE_DEVICES=0,2`, CUDA by uuid
- [ ] **gpu none** -> `NVIDIA_VISIBLE_DEVICES=void`, no device_requests
- [x] **env FOO=bar** -> `FOO=bar` in Env
- [ ] **env reserved (PATH)** -> not injected
- [ ] **docker raw** -> `/var/run/docker.sock` mounted, no DOCKER_HOST
- [ ] **docker limited** -> `DOCKER_HOST` set, proxy subpath mount, no raw socket
- [ ] **docker privileged** -> `HostConfig.Privileged=true`
- [x] **volume vol->/mnt/x** -> Mounts contains the named volume at /mnt/x
- [ ] **api-keys pool** -> target var(s) set, durable slot label present
- [ ] **downloads block** -> per-user CHP block routes registered

#### Combinations + multi-group resolution

- [ ] **All-policies group** -> one spawn reflects sudo+env+mem+cpu+gpu+docker+volumes+api-keys simultaneously
- [ ] **Priority-wins** -> two groups configuring sudo/downloads: the higher-priority value lands in the container
- [ ] **Biggest-wins** -> two groups capping mem/cpu: the larger cap lands in the container
- [ ] **OR-grant** -> two groups, only one grants gpu/docker: the grant lands
- [ ] **Section toggled off** -> turning a section off then re-spawning drops that effect from the container
- [ ] **Membership change** -> adding/removing the user from a group changes the next spawn's container config

### Server lifecycle control

- [ ] **Spawn via UI** - start server from the UI
- [ ] **Spawn via API** - start server via the API
- [ ] **Stop** - stop removes the container
- [ ] **Restart preserves container** - restart keeps the same container (no recreate)
- [ ] **Concurrent users** - two users spawn distinct containers
- [ ] **Edge: re-spawn picks up new policy** - changing the group then re-spawning re-applies config

### Idle culling

- [ ] **Idle culled** - an idle server is stopped after a short test timeout
- [ ] **Active not culled** - an active server survives the interval
- [ ] **Extension delays cull** - a granted extension delays culling
- [ ] **Culled container removed** - the lab container is gone after culling

### Logs

- [ ] **Resolution log** - the hub log shows the per-spawn groups/policy resolution line
- [ ] **Policy apply logs** - api-keys assignment / docker-proxy / downloads-route lines appear per policy
- [ ] **Spawn failure logged** - a failed spawn logs the cause
- [ ] **Lab logs retrievable** - the spawned container logs are fetchable and show startup

### Activity reporting

- [ ] **Active server reported** - a running server appears in activity data within the sample interval
- [ ] **Resource stats** - CPU/memory for the running lab report back to the hub
- [ ] **Stopped drops out** - a stopped server leaves the active set
- [ ] **Manual sample** - a manual sample updates the data immediately

### Limits enforcement (real effect)

- [ ] **Memory OOM** - in-container stress beyond the cap is OOM-limited
- [ ] **CPU throttle** - in-container CPU beyond the cap is throttled
- [ ] **Volume quota warning** - exceeding the volume/container-size threshold raises the activity warning

### GPU auto-detection (GPU host only)

- [x] **Auto-detect enables on GPU host** - `make test-functional` auto-detects a host GPU, sets `JUPYTERHUB_GPU_ENABLED=2`, and the test asserts the hub `[GPU debug]` line reports `detected=1 enabled=1` with GPUs enumerated
- [x] **Deselected on CPU host** - no GPU -> the gpu test is deselected (not collected), no skip noise and no CUDA pull
- [ ] **GPU policy spawn (GPU host)** - a gpu-access group member spawns with `device_requests` and `NVIDIA_VISIBLE_DEVICES` set
- [ ] **Specific-GPU selection (GPU host)** - a device-id subset reaches the container env

### Self-service

- [ ] **Manage volumes list** - the volume reset UI lists home/workspace/cache
- [ ] **Manage volumes reset** - selected volume reset works (server stopped)
- [ ] **Restart server (self)** - user restarts own running server
- [ ] **Session extend** - idle session extend updates the remaining time
- [ ] **Edge: manage volumes blocked while running** - reset refused while the server runs

### Notifications broadcast

- [ ] **Page renders form** - message field, type selector, auto-close toggle
- [ ] **Char limit** - 140-char limit + live counter
- [ ] **Broadcast no servers** - sending with no active servers reports zero deliveries
- [ ] **Broadcast delivery (real-lab)** - active lab with the extension receives the toast; per-user status shown
- [ ] **Edge: extension missing** - server without the extension reports "not installed"

### Settings

- [ ] **Settings list** - settings render from the dictionary
- [ ] **Edit setting** - changing a setting persists
- [ ] **Hidden secrets** - admin-password-style settings absent from the page

### Activity monitor

- [ ] **Activity data** - the activity page shows user rows / data
- [ ] **Resource stats** - CPU/memory/status columns populate
- [ ] **Reset** - reset clears activity samples
- [ ] **Manual sample** - trigger a sample updates the data

### Lab-extension features (real-lab; out of scope for the minimal run)

- [ ] **Download blocked** - a download-blocked user gets 403 on the download surfaces
- [ ] **Download toast** - a blocked attempt pushes a notification toast
- [ ] **Download allowed** - an allowed user downloads normally
- [ ] **Favicon proxy** - custom favicon served through the per-user CHP route
- [ ] **Inline view allowed** - inline image/media still served to a blocked user

### Abuse protection & ops

- [x] **Health endpoint** - /hub/health returns 200 JSON
- [ ] **Rate limit** - exceeding the ingress rate returns 429 (needs Traefik; out of scope minimal)
- [ ] **Concurrent spawn limit** - spawn-storm protection caps simultaneous spawns
- [ ] **Idle culler** - an idle server is culled after the timeout

### Teardown verification

- [x] **No containers left** - after a run, no `stellars-functest` or spawned `jupyterlab-functestadmin` containers remain
- [x] **No network left** - `stellars-functest_network` removed
- [x] **No volumes left** - project + spawned per-user volumes removed
- [x] **Pulled images removed** - singleuser + Playwright images removed (unless KEEP_IMAGES)
- [x] **Hub image intact** - the image under test is not removed
- [ ] **Teardown asserted in-suite** - a final check confirms zero trace (or a separate verify step)

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
- [x] **Functional fidelity** - entries describe routes, actions, endpoints, states; no CSS selectors, class names or DOM structure
- [x] **Single source** - one master doc, one section per screen plus a shared global-layer section
- [x] **Provenance** - catalogue names the source files (templates, handlers, config) it was built from

### Per-screen completeness

Every screen section must carry, where applicable: route, purpose, actions (+ target endpoint), inputs/validation, conditionals (role/state gating), messages, navigation, modals, dynamic behaviour, API. A label is omitted only when genuinely N/A.

- [x] **Route present** - each screen states its URL path(s)
- [x] **Actions enumerated** - every button/link/form submit listed with what it does and the endpoint it hits
- [x] **Inputs + validation** - form fields, limits and validation rules captured (char limits, name regex, reserved/protected rejections)
- [x] **Conditionals** - role gating (admin vs user vs anon) and state gating (server running/stopped/pending, bootstrap window) captured per screen
- [x] **Messages** - error/success/info text and the trigger condition captured
- [x] **Navigation** - outbound links per screen captured
- [x] **Modals** - confirmation/config dialogs and what they guard captured
- [x] **Dynamic behaviour** - JS-driven polling, timers, redirects, auto-close, spinners, live counters captured
- [x] **API** - method, path, payload shape and error codes captured for screens that call endpoints

### Screen inventory (every hub screen accounted for)

- [x] **Auth + landing** - login, native-login, signup, logout, change-password, change-password-admin, authorization-area, oauth, accept-share, error, 404, message, token
- [x] **Spawn + home + self-service** - home, named-servers, manage-volumes, restart, extend-session, spawn, spawn_pending, stop_pending, not_running
- [x] **Groups + policy** - groups page with layout regions, actions, all nine policy types, badges, tooltip, validation, persistence, API
- [x] **Admin platform** - admin, settings, activity, notifications
- [x] **Global layer** - page.html base, navigation map, branding, dark mode, mobile.js, session-timer.js, shared messaging

### Capability depth gates

- [x] **Branding fully mapped** - every branding env var (logo, favicon, favicon-busy, lab main/splash icons, base url), file:// vs URL handling, and the favicon CHP proxy mechanism captured
- [x] **Navigation role matrix** - which nav items each role sees (anonymous/user/admin) captured, not just the link list
- [x] **Policy types complete** - all nine (env, gpu, docker, cpu, mem, sudo, downloads, api-keys, volume-mounts), each with config inputs, badge, tooltip detail, cross-group resolve rule and apply effect
- [x] **Badge/tooltip provenance** - documented as server-computed `policy_summary` consumed verbatim by the client, not recomputed in the browser
- [x] **Self-service flows** - manage-volumes, restart, extend-session each carry their poll loops, timeouts and reload behaviour
- [x] **Spawn lifecycle** - spawn -> spawn_pending (EventSource + lab-ready fallback) -> not_running/stop_pending state machine captured
- [x] **Bootstrap window** - first-admin signup-window behaviour and its gating env vars captured on the signup screen

### Edge cases

- [x] **Edge: empty states** - no-groups, no-volumes-yet, no-active-servers, no-tokens captured as distinct UI states
- [x] **Edge: failure paths** - spawn-failed (Relaunch), broadcast partial-failure, validation 400/409, restart timeout captured
- [x] **Edge: external state drift** - home drift detector reloading on externally-stopped server, spawn-pending fallback poll on mid-spawn hub restart captured
- [x] **Edge: admin-acting-for-user** - admin spawning/managing another user's server and volumes captured
- [x] **Edge: mobile vs desktop divergence** - device-specific controls (mobile start/stop interception, status strip, card views, inline extend panel) captured where behaviour differs
- [x] **Edge: one-time secrets** - token "you won't see it again" card and api-keys masked-on-read noted as non-recoverable display states

### Sign-off

- [x] **No orphan screens** - every template in `html_templates_enhanced/*.html` maps to a catalogue section or is explicitly out of scope
- [x] **No orphan handlers** - custom page/API handlers referenced by a catalogued screen appear in that screen's API list
- [ ] **Rebuild-ready** - a developer can rebuild any single screen from its section without reading the source


## GPU Utilisation Cache Logging

The background GPU-utilisation sampler (`gpu_cache._refresh_sync`) ticks every `JUPYTERHUB_GPU_UTIL_UPDATE_INTERVAL` seconds (default 30). Per-tick "cache updated" lines are noise, so only the first successful sample logs at INFO - carrying the refresh cadence - and every later refresh logs at DEBUG.

- [x] **First sample INFO** - first successful refresh (cache timestamp was `None`) logs once at INFO: device count plus `refreshing every <interval>s`
- [x] **Interval source** - the cadence in the INFO line reads `_get_update_interval()` (`JUPYTERHUB_GPU_UTIL_UPDATE_INTERVAL`, default 30), not a hardcoded number
- [x] **Subsequent samples DEBUG** - every refresh after the first logs `Cache updated: N device(s)` at DEBUG, off by default at INFO log level
- [x] **First detection** - "first" keyed off `_gpu_util_cache['timestamp'] is None` before the write, so it fires exactly once per process lifetime
- [ ] **Edge: empty sample** - sidecar returns nothing -> `Sample empty - keeping previous cache` stays at INFO (left unchanged; flags a degraded sidecar, not routine churn)
- [ ] **Edge: sample after empties** - if the very first non-empty sample arrives after one or more empty ticks, it still logs the INFO init line (timestamp still `None` until a non-empty write)


## gpuinfo-nvidia sidecar (logging + graceful no-hardware)

The GPU-info sidecar logs its lifecycle so an operator can see it start, serve and what hardware it detected. A failure to start the container is an acceptable outcome - it means no NVIDIA hardware - and the hub degrades to GPU-off without stalling or alarming.

### Logging

- [x] **Startup line** - on boot the sidecar logs `[gpuinfo-nvidia] vX starting (vendor=nvidia)` via a FastAPI `lifespan`
- [x] **Detected hardware** - it samples once and logs each GPU (`GPU <i>: <name> (<uuid>, <N> GB)`), or a single `no NVIDIA driver/GPU detected - serving empty inventory` warning
- [x] **Health at startup** - each detected-GPU line also reports the current health snapshot (`- health: N% util, U/T GB mem, NN C, NN W`), skipping any metric the driver did not report (so a partial sample never prints `None`)
- [x] **Hub logs caps + health too** - besides the sidecar's own log, the HUB logs a readable per-card line at boot - `[GPU] GPU <i>: <name> (<N> GB) - <util>% util, <used>/<total> GB, <temp> C, <power> W` - capabilities (name, total mem) + a live health snapshot, omitting any metric the sidecar did not report; the raw `[GPU debug] gpus=[...]` dict line stays for debugging
- [x] **Serving line** - logs `ready - serving /health and /gpus`; uvicorn's own "Uvicorn running on ..." also shows
- [x] **Visible by default** - `GPUINFO_LOG_LEVEL` default changed `warning` -> `info` (warning hid uvicorn's running line); overridable via env
- [x] **No request spam** - `access_log=False`; the hub polls `/health`+`/gpus` every ~30s, so per-request lines would bury the useful logs
- [x] **Untyped-package import** - a `declare module` shim is not needed (the sidecar is Python); fastapi tests gate the image build (bare `TestClient` does not trigger the lifespan, so no nvidia-smi call in tests)

### Graceful no-hardware (container fail = no GPU = OK)

- [x] **Container fails to start = no GPU** - if the nvidia runtime is absent the container cannot launch; that is an expected, acceptable outcome meaning no NVIDIA hardware, not an error to surface
- [x] **Hub self-start returns a bool** - `ensure_gpuinfo_sidecar` returns False when docker/nvidia is unavailable; the hub does not block on it
- [x] **Bounded boot probe** - the hub's GPU probe is time-bounded (~3s), so an unreachable/failed sidecar never stalls hub boot
- [x] **Degrades to GPU-off** - with no reachable sidecar the hub resolves GPU-off (empty inventory, GPU widgets hidden via `window.jhdata.gpu_enabled`)
- [x] **App still serves on a GPU-less host** - if the container DOES run without a driver, `/health` stays 200 and `/gpus` returns `available:false` (the no-driver warning is logged once at startup)
- [x] **Runtime: logs show start/serve/hardware** - on the live hub, `docker logs gpuinfo-nvidia` shows the startup, detected-GPU and serving lines (or the no-driver warning)

### Lifecycle (tied to the hub)

The sidecar is hub-managed (created over the docker socket by `ensure_gpuinfo_sidecar`), not a compose service, so compose `down` leaves it orphaned. The hub now owns its teardown too.

- [x] **SIGTERM reaches the hub (exec)** - `start-platform.sh` now `exec`s jupyterhub so it is PID 1 and receives docker's SIGTERM directly on `docker stop` / compose down/restart; without exec the signal hit the shell (no forwarding), jupyterhub was SIGKILLed after the grace period and atexit never ran - the real reason teardown did not fire
- [x] **Removed on hub shutdown** - the hub registers `atexit(stop_gpuinfo_sidecar)` when it owns the sidecar; with the exec fix a clean hub stop (SIGTERM -> clean exit) now actually runs it and removes the sidecar instead of leaving it parentless
- [x] **Recreated fresh from the hub every boot** - `ensure_gpuinfo_sidecar` REMOVES any pre-existing sidecar then CREATEs a new one from the current image, so the hub always recreates it (current `:latest`, never a stale reuse) even if a hard SIGKILL left one behind; the structural fix for the stale-reuse logging bug above
- [x] **Best-effort** - never raises; a hard SIGKILL of the hub still skips the atexit, but the next boot's recreate-fresh removes+replaces any survivor, so a stale sidecar never persists across a boot
- [ ] **Runtime: sidecar gone after hub stop** - on the live host, stopping the hub removes `gpuinfo-nvidia`; starting the hub recreates it


## Group-Gated File Downloads

Best-effort, hub-side blocking of browser file downloads from spawned labs. Section-gated and priority-wins: a group whose File Downloads section (`downloads_active`) is on explicitly configures member downloads to allow or block (`downloads_allow`); among a user's configuring groups the highest-priority one wins; if no group configures it, the platform default `JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS` applies. For a blocked user, `pre_spawn_hook` overlays per-user CHP routes (favicon-route mechanism) onto the lab's download surfaces, sending them to hub guard handlers that 403 genuine downloads and reverse-proxy inline content. Every block fires a throttled "blocked by policy" toast and an audit log line. This is policy + notification + audit, NOT exfiltration prevention - the lab user is root with open egress, so a terminal/kernel transfer over an encrypted channel is out of reach by design.

### Platform setting

- [x] **Default policy** - `JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS` (`0`/`1`, default `0`) is the fallback applied only when no group configures downloads; dormant (no routes/handlers) when the default is allow AND no group configures it - zero change for existing deployments
- [x] **Settings page** - listed in `settings_dictionary.yml` (Abuse Protection category) so it shows on the admin Settings page
- [x] **Startup log** - hub prints the policy state (BLOCK/ALLOW) once at config load

### Group config (admin)

- [x] **Section** - foldable "File Downloads" section with header switch `config-downloads-active` (default off), following the `*_active` section pattern
- [x] **Value control** - when the section is on, toggle `config-downloads-allow` chooses allow (1) or block (0) for members
- [x] **Persistence** - `downloads_active: False`, `downloads_allow: True` in `default_config()`; section folded off persists data and restores on re-enable; legacy rows default off (no inference - section off = not configured)
- [x] **API accept** - `GroupsConfigHandler.put` accepts boolean body keys `downloads_active` and `downloads_allow`
- [x] **Badge** - groups table shows `Downloads on` or `Downloads off` (reflecting the configured value) when `downloads_active` is on; no badge when the section is off
- [x] **Section-gated** - a group with `downloads_active` false does NOT configure downloads (its `downloads_allow` is ignored); only sections explicitly on are considered
- [x] **Priority-wins** - among configuring groups the highest-priority `downloads_allow` wins (priority-descending walk, first configuring group decides) - not OR, not biggest-wins
- [x] **Resolved value** - `resolve_group_config` returns `downloads_allow` as `True`/`False` when some group configures it, else `None`; the hook applies the platform default when `None`
- [x] **No admin exemption** - admins follow the same resolution as any user (no implicit bypass)

### Enforcement (hub overlay)

- [x] **Vector inventory** - verified against the deployed image: block surfaces are `files/` (download / open-to-save), `nbconvert/` (download / open-to-save), `jupyterlab-export-markdown-extension/export/` (POST, always attachment), `jupyterlab-share-files-extension/public/share/` (GET, unauthenticated public link). Not vectors: export-svg-as-png (client-side), jupyterlab_zip (POST create only), jupyter-archive (absent)
- [x] **Route overlay** - for blocked users `pre_spawn_hook` registers one CHP route per surface to the hub, recorded in `app.proxy.extra_routes` so `check_routes()` does not reap them
- [x] **Survivor re-registration** - `schedule_startup_downloads_callback` re-applies block routes for labs still running after a hub restart
- [x] **Grant change removes routes** - a user resolved as allowed has any stale block routes deleted on next spawn (`_unregister_download_block`); symmetric add/remove
- [x] **Allowed = no overlay** - users resolved to allow get no routes; traffic flows browser -> CHP -> container with zero added hops
- [x] **Group blocks regardless of default** - a configuring group resolving to block overlays routes even when the platform default is allow; a group resolving to allow removes them even when the default is block
- [x] **Pure-download block** - `DownloadBlockHandler` 403s the export-markdown and share-files prefixes unconditionally (no auth, so it also blocks the unauthenticated public share link); GET/POST/HEAD
- [x] **Download-intent block** - `FilesGuardHandler._is_download_request` 403s `files/`/`nbconvert/` when the request is a save / open vector: a truthy `?download` arg, OR `Sec-Fetch-Dest` of `empty` (fetch / `<a download>`), `document` (top-level navigation / open-in-tab), or absent (non-browser / plain-HTTP - fail-closed)
- [x] **Inline pass-through** - `files/`/`nbconvert/` requests whose `Sec-Fetch-Dest` is an inline subresource render (`image`, `video`, `audio`, `font`, `style`, `script`, `object`, `embed`, `iframe`, `frame`, `track`, `manifest`) reverse-proxy to the container, forwarding the `Range` header and relaying status/headers/body (markdown/notebook images, embedded media, in-lab viewers keep working)
- [x] **Defense in depth** - if a proxied inline response unexpectedly carries `Content-Disposition: attachment`, it is converted to a 403 before any body reaches the client
- [x] **Owner isolation** - `FilesGuardHandler` is a plain `tornado.web.RequestHandler` (hub login cookie is scoped to `/hub/` and never reaches `/user/...`, so `@web.authenticated` there loops to login); isolation holds because the inline proxy forwards the request's `/user/{u}/` cookie to that user's own container and the browser only sends that cookie to the user's own prefix
- [x] **Block response** - 403 with an HTML page for top-level navigation (Accept: text/html), JSON `{"error":"downloads_blocked"}` otherwise
- [x] **Audit log** - every block logs username, path, and the trigger (`via=pure-download|download-arg|sec-fetch-dest=<v>|attachment-header`)

### Must not break

- [x] **Contents API untouched** - `/user/{u}/api/contents/*` never intercepted; browse, open, edit, save, rename, upload work for blocked users
- [x] **Kernels and terminals untouched** - `/api/kernels`, `/api/terminals`, websockets unaffected
- [x] **Lab UI untouched** - `/lab`, `/static/`, extension assets, settings/themes unaffected
- [x] **Export format listing untouched** - the `nbconvert` POST (inline render) and format metadata are not blocked; only download-arg GETs are
- [x] **Favicon overlay coexistence** - block routes and the favicon route coexist in `extra_routes` without prefix collision

### Notification

- [x] **Toast on block** - hub pushes a warning toast to the blocked user's lab via the notifications-extension ingest endpoint (temp 5-min token), naming the file
- [x] **Fire and forget** - notification is scheduled on the IO loop and never delays or alters the 403
- [x] **Throttle** - at most one toast per user per 10 s; further blocks in the window are counted and the next toast carries the aggregate ("N downloads blocked")
- [x] **Extension absent / server down** - block is still enforced; notify failure is logged and swallowed

### Lifecycle

- [x] **Group change** - adding/removing a user from a configuring group, or toggling `downloads_active`/`downloads_allow`, takes effect at the user's next server start
- [x] **Feature toggle** - flipping the platform default requires a hub restart; the survivor callback applies the new state to running labs (dormant default off + no configuring group -> `check_routes()` reaps leftover routes since they are no longer in `extra_routes`)

### Edge cases

- [x] **Edge: user in no groups** - no group configures -> platform default applies
- [x] **Edge: configuring groups disagree** - highest-priority configuring group wins regardless of the others
- [x] **Edge: higher-priority section OFF, lower-priority ON** - the lower-priority group (the only one configuring) decides
- [x] **Edge: `?download=0` / falsy** - not treated as a download; passes through (`_is_download_arg`)
- [x] **Edge: burst of blocked clicks** - one throttled toast, not a storm
- [x] **Edge: default allow, no group configures** - no routes, no handlers; downloads work for everyone
- [ ] **Edge: group deleted while member's lab runs** - lab keeps spawn-time behaviour until restart, then re-resolves

### Tests

- [x] **Resolver tests** - `TestDownloadsAllow`: no group configures -> None, section-off -> None, single allow/block, higher-priority wins, higher-off+lower-on decides, only-matched-groups-count
- [x] **Discriminator tests** - `TestIsDownloadArg` / `TestIsDownloadRequest` / `TestFilenameFromPath` cover the block/allow decision and toast naming; `TestIsDownloadRequest` asserts inline dests allowed, empty/document/absent blocked, `?download` wins
- [ ] **Live end-to-end** - post-rebuild probe as `konrad.jelen`: Download button (`<a download>`, no arg) -> 403 + toast + audit, `?download=1` -> 403, open-in-tab -> 403, inline markdown image -> 200 via proxy, export-markdown POST -> 403, granting group -> downloads succeed; contents API / kernels / terminals unaffected

### Documentation

- [x] **README** - Groups section documents the File Downloads switch, the allow/block value, the priority-wins/default-fallback rule, and the platform default env var; states it is browser-download policy with notification, not full DLP

### Out of scope

- Exfiltration via terminal/kernel egress, `git push`, the contents API, or any encrypted channel - structurally unblockable while the lab stays usable (root + sudo + needed egress)
- Upload blocking; per-path or per-filetype allowlists; named servers (one server per user here)

### API

- Blocked vectors (blocked users): `GET|HEAD /user/{u}/files/*` and `/nbconvert/*` when `?download` is truthy OR `Sec-Fetch-Dest` in {`empty`, `document`, absent}, `POST /user/{u}/jupyterlab-export-markdown-extension/export/*`, `GET /user/{u}/jupyterlab-share-files-extension/public/share/*` -> `403` (HTML or `{"error":"downloads_blocked"}`); inline `files/`/`nbconvert/` with a media `Sec-Fetch-Dest` -> proxied 200/206
- `PUT /hub/api/admin/groups/{group}/config` body gains optional booleans `downloads_active`, `downloads_allow`
- Env: `JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS` (`0`/`1`, default `0`) - platform default when no group configures


## Group Policy Import/Export Bundle Shape

The group policy export/import bundle uses the hierarchy group -> policy[] -> members instead of one flat per-group `config` dict. Each policy is a named section carrying its own settings. The hub still stores and validates a single flat config, so this is purely the on-disk bundle shape, folded on export and unfolded on import.

- [x] **Folded export** - export emits `{groups:[{name, description, priority, policies:[{key, label, settings}]}]}`; each policy carries only the flat keys it owns
- [x] **Nine sections in backend order** - env_vars, gpu, docker, cpu, mem, sudo, downloads, api_keys, volume_mounts; key ownership matches the backend POLICY_TYPES
- [x] **Unfolded import** - import merges every section's `settings` back into the flat config the hub PUTs
- [x] **Round-trips** - an exported bundle re-imports through the same flat config the editor PUTs (hub coerces + validates)
- [x] **Legacy bundles still import** - a file with a flat `config` (older export) is still accepted
- [x] **Edge: malformed file** - non-JSON / shapeless file shows "Import failed: …" and writes nothing; same file re-pickable
- [x] **Edge: api_keys nested object** - the `api_keys_pool` nested object travels whole inside the api_keys policy's settings


## Unified Group Policy Model

One policy-type registry is the single source for every group permission (default, set-rule, validate, cross-group resolve), and at spawn a user's groups collapse into one effective policy object the hook reads. The legacy resolver and per-field validator are deleted, gated on a frozen golden snapshot proving the new engine reproduces them (v3.11.6 -> 3.12.0).

### Registry + engine

- [x] **Single source** - `POLICY_TYPES` is the only place each type's default, coerce, validate, and resolve live
- [x] **default_config from registry** - `default_config()` is assembled from each type's `default`, no hand-listed field bag
- [x] **resolve_policies drop-in** - same signature and output key set as the deleted `resolve_group_config`; the three hook call sites switch with no behaviour change
- [x] **Registry-driven save** - `GroupsConfigHandler.put` coercion and validation loop over `POLICY_TYPES`; no per-field if-chain remains
- [x] **ctx carries non-config inputs** - `gpu_available`, reserved env names/prefixes flow via a context object, not globals

### Per-type set-rule + resolve-rule

- [x] **env_vars** - reserved names stripped to `skipped_env_vars`; priority-first-wins on name; inactive section contributes nothing
- [x] **gpu** - OR-grant; all-GPUs wins else device-id union; hardware-gated; grant with neither all nor ids falls back to all
- [x] **docker** - OR-grant access/limited/privileged; max quota across granting groups; raw supersedes limited (clears limited + its flags)
- [x] **mem** - biggest-enabled-GB wins; swap policy follows the winning cap; disabled group does not un-cap
- [x] **cpu** - biggest-enabled-cores wins; disabled group does not un-cap
- [x] **sudo** - section-gated priority-wins; `None` when unconfigured (hook applies platform default)
- [x] **downloads** - section-gated priority-wins; `None` when unconfigured (hook applies platform default)
- [x] **api_keys** - priority-ordered pool list; reserved target names rejected at save
- [x] **volume_mounts** - union keyed by mountpoint; priority-wins on conflict; protected-mountpoint blacklist re-checked at resolve

### Models own apply + lifecycle (the controller layer)

- [x] **Policy is a model class** - each permission is a `Policy` subclass (`EnvVarsPolicy`, `GpuPolicy`, ...) owning default/coerce/validate/resolve/summarize/apply/on_hub_startup; `POLICY_TYPES` is a list of instances
- [x] **apply imposes the resolved value** - each model's `apply(spawner, resolved, actx)` mutates the spawner / registers routes / assigns slots; moved verbatim from the old monolithic `pre_spawn_hook`
- [x] **Thin hook** - `pre_spawn_hook` = resolve -> `apply_policies` loop -> non-policy steps only (compose labels, favicon, lab icons, aggregate log); no per-feature branches
- [x] **Unified startup** - one `schedule_policy_startup(actx)` -> `run_hub_startup` loops each model's `on_hub_startup`; replaces the three per-feature startup callbacks; favicon stays separate (non-policy)
- [x] **ApplyContext** - spawn-time hub config (proxy dirs, compose project, gpu uuid map, sudo/downloads defaults, reconcile interval) threaded to apply/startup via one frozen context built once in `make_pre_spawn_hook`
- [x] **api_keys / docker controllers unchanged** - `PoolManager` and proxy `register_user` logic preserved, now invoked from `ApiKeysPolicy`/`DockerPolicy`; dead `schedule_*` functions removed
- [x] **Apply regression guard** - `tests/test_policy_apply.py` FakeSpawner asserts exact spawner state per model (gpu/docker/mem/cpu/sudo/env/volumes/api-keys/downloads); resolve golden + all prior suites still green (506 tests)
- [x] **api_keys restart persistence** - in-use set is label-derived; a lab surviving a hub restart keeps its slot; `ApiKeysPolicy.on_hub_startup` rebuilds in-use before any new spawn assigns
- [x] **api_keys label at create** - the slot label is stamped on the container via `extra_create_kwargs` at create (the one gap that would reintroduce collisions)
- [x] **Edge: collision after restart** - two labs running, hub restarts, a third spawn must not re-hand-out either surviving slot
- [x] **Edge: exhausted pool** - more containers than credentials sets the target vars empty and logs a warning, never reuses a live slot

### Migration + no-regression

- [x] **Golden frozen** - `tests/golden/policy_resolution.json` captures the old resolver outputs across the scenario matrix
- [x] **Golden green** - new engine output deep-equals the frozen golden for every scenario
- [x] **Old path deleted** - `resolve_group_config` and per-field `GroupConfigValidator` methods removed; no shim, no fallback; importers updated

### Bundle round-trip (import/export foundation)

- [x] **Bundle shape** - a group serializes to `{group_name, description, priority, policies}`
- [x] **Round-trip** - export then import a bundle through the registry coerce path deep-equals the source config

### UI

- [x] **Name opens config** - clicking the group name opens its configuration modal (edit icon dropped)
- [x] **Hover tooltip** - hovering the group name lists the group's active policies, rendered from the server-provided `policy_summary` detail lines (no policy-display logic in the browser)
- [x] **Single-source badges + tooltip** - each `PolicyType.summarize(config)` returns `{badge, detail}`; `summarize_config` feeds `GroupsDataHandler.policy_summary`; the group table badges and tooltip both render it, so neither drifts from the registry

### Edge cases

- [x] **Edge: zero matched groups** - resolve returns all defaults / `None` for section-gated types
- [x] **Edge: section off with stale data** - an inactive section contributes nothing while its stored data persists
- [x] **Edge: legacy row missing active flags** - `infer_active_flags` still applies; legacy groups keep working
- [x] **Edge: conflicting priorities** - higher-priority group wins for priority-type keys; ties keep the higher-priority (earlier) group
- [x] **Edge: reserved env-var name** - rejected at save with the stable `reserved_env_var_names` JSON error

### Gate

- [x] **Tests green** - `uv run pytest` passes including golden, per-type, driver, restart, round-trip
- [x] **Version bumped** - root `pyproject.toml` 3.11.6 -> 3.12.0

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
- [x] **Settings page** - listed in `settings_dictionary.yml` so it appears on the admin Settings page
- [x] **Compose default** - `JUPYTERHUB_LAB_SUDO_ENABLE=1` present in `compose.yml` jupyterhub service environment

### Group config (admin)

- [x] **Section** - foldable "Sudo Access" section in the group modal with a section-active switch `config-sudo-active` (default off), following the `*_active` section pattern
- [x] **Value control** - when the section is on, a toggle `config-sudo-enable` chooses enable (1) or disable (0) for members
- [x] **Persistence** - `default_config()` carries `sudo_active: False` and `sudo_enable: True`; data persists when the section is folded off and restores when re-enabled (same as other `*_active` sections)
- [x] **No inference** - brand-new feature; legacy rows default to `sudo_active: False` (not configured -> platform default applies), no `infer_active_flags` entry
- [x] **API accept** - `GroupsConfigHandler.put` accepts boolean body keys `sudo_active` and `sudo_enable`
- [x] **Badge** - groups table shows `Sudo on` or `Sudo off` when `sudo_active` is set (reflecting the configured value); no badge when the section is off

### Resolution

- [x] **Section-gated** - a group with `sudo_active` false does NOT configure sudo (its `sudo_enable` is ignored); only sections explicitly on are considered
- [x] **Priority-wins** - among groups with `sudo_active` on, the highest-priority group's `sudo_enable` wins (groups resolved in descending priority order; first configuring group decides) - not OR, not biggest-wins
- [x] **Resolved value** - resolver returns `sudo_enable` as `True`/`False` when configured by some group, or `None` when no group configures it
- [x] **Default fallback** - the spawn-time value is the resolved `sudo_enable` when not `None`, else `JUPYTERHUB_LAB_SUDO_ENABLE` (resolver stays pure; the hook applies the default)

### Spawn injection

- [x] **Always set** - `pre_spawn_hook` always sets `spawner.environment['JUPYTERLAB_SUDO_ENABLE']` to `'1'` or `'0'` (never left unset) so the container gets an explicit value every spawn
- [x] **Disable wins when configured** - a higher-priority group setting `sudo_enable=false` yields `JUPYTERLAB_SUDO_ENABLE=0` even if a lower-priority group enables it and even if the platform default is `1`
- [x] **Log line** - the existing pre_spawn resolution log line includes the resolved sudo value (configured vs default) for audit

### Edge cases

- [x] **Edge: user in no groups** - no group configures sudo -> platform default applies
- [x] **Edge: all configuring groups agree** - any number of groups with the same value resolves to that value
- [x] **Edge: configuring groups disagree** - highest-priority configuring group wins regardless of the others
- [x] **Edge: section on, value unset in stored row** - defaults to `sudo_enable: True` from `default_config()`
- [x] **Edge: higher-priority group section OFF, lower-priority ON** - the lower-priority group (the only one configuring) decides
- [x] **Edge: membership change** - takes effect on the member's next server start (consistent with other group settings)

### Tests

- [x] **Resolver tests** - `TestSudoAccess`: no groups -> None; single configuring group -> its value; section-off group -> None; two configuring groups -> higher priority wins; higher-priority-off + lower-priority-on -> lower-priority value

### Documentation

- [x] **README** - Groups section documents the Sudo Access switch, the value toggle, the priority-wins/default-fallback rule, and the master default env var

### Out of scope

- Enforcing sudo inside the container from the env var - the image owns that; the hub only injects `JUPYTERLAB_SUDO_ENABLE`
- Per-user (non-group) sudo overrides
- Runtime sudo change without a server restart

### API

- `PUT /hub/api/admin/groups/{group}/config` body gains optional booleans `sudo_active`, `sudo_enable`
- Env into container: `JUPYTERLAB_SUDO_ENABLE` (`0`/`1`)
- Platform env: `JUPYTERHUB_LAB_SUDO_ENABLE` (`0`/`1`, default `1`)


## Label Capitalisation (Title Case)

Button labels and header labels across the portal use Title Case - every principal word capitalised, minor words lowercase unless first/last. This is a system-wide design-language rule (cross-ref [acc-crit-design-language]); the live reference is the `/design-language` Conventions card. The trigger was the Events "Clear log" button, which should read "Clear Events". Verified against the code 2026-06-18.

### The rule

- [x] **Title Case principal words** - capitalise the first word and every principal word of a label
- [x] **Minor words stay lowercase** - a, an, the, and, or, but, nor, of, to, in, on, at, by, for, from, with, vs, per, as, into stay lowercase UNLESS first or last word
- [x] **Acronyms preserved** - JSON, API, CPU, GPU, TLS, URL, ID, NAS, CIFS, MLflow, TTL kept as-is (never "Api"/"Gpu")
- [x] **Units / tokens / numbers preserved** - "+7h", "24h", "30s", "GB", ".txt", "30%" unchanged

### Scope (Title-Cased)

- [x] **Button labels** - every button's visible text, and Modal action buttons (`okText`/`cancelText`) that are action labels
- [x] **Page / card / section headers** - `PageHeader` titles, `Card` / `CardHeadLink` titles, `oh-section-title`
- [x] **Table column headers** - the `title` of list/table columns
- [x] **Section / mode tabs** - tab and segmented labels that name a section or mode (not a data value)

### Out of scope (left sentence case / unchanged)

- [x] **Form-field input labels** - `Form.Item` labels (First name, Last name, Email, Change password) stay sentence case - they are field prompts, not button/header labels
- [x] **Sentence copy** - descriptions, `sub` lines, notices, alerts, tooltips and confirm-modal prompts ("Stop all running servers?", "Clear the event log?") stay sentence case
- [x] **Filter data-values** - Segmented/Radio option values that are data (statuses All/Active/Idle/Offline/Culled/Unauthorised, time ranges Last 24h / Last 7 days, percentages, durations, language names) stay as-is
- [x] **Dynamic / cell content** - table cell values and interpolated runtime strings unaffected

### Edge cases

- [x] **Same string, two roles** - a literal that appears both as a button AND as a sentence/tooltip is Title-Cased only in the label occurrence, not globally
- [x] **Demo / reference pages** - `/design-system` (dev kitchen-sink) showcase headings were left as-is; `/design-language` carries the canonical Conventions rule + a Title-Case example row

### Verification

- [x] **Frontend gates** - `npx tsc -b`, `npm run lint`, `npm run build:hub` all clean after the sweep


## Live Data Honesty (no mock masquerade)

In live mode the portal must never present fabricated mock data as if it were real. A live `DataSource` method either returns real hub data, returns an honest empty/disabled state, or the surface is hidden - it never silently delegates to `mockSource` for content a user reads as fact. Mock mode (the design pages) keeps full mock data so the UI demos whole.

### Effective grants (per-user resolved policy)

- [x] **Real resolve endpoint** - `getEffectiveGrants(user)` calls `GET /api/users/{user}/effective-grants`, not `mockSource`
- [x] **Backend resolves across the user's groups** - `EffectiveGrantsHandler` loads the user's ORM groups, runs `resolve_policies`, then `effective_grants(matched, resolved)`
- [x] **Source attribution** - each grant cites the highest-priority group that granted it (`from`), resolved by walking the priority-descending matched configs
- [x] **Honest empty** - a user whose groups grant nothing special returns `[]` (runs on platform defaults), not fabricated CPU/memory rows
- [x] **GPU hardware-gated** - the GPU grant appears only when `gpu_available` (resolver gates `gpu_access` on it); `gpu_available` threaded into `stellars_config`
- [x] **Grant value formatting** - memory `N GB` (`(no swap)` annotated), CPU `N cores`, GPU `all devices` or `GPU 0, 1`, sudo `enabled`/`disabled`, docker `socket`/`limited`/`privileged` (privileged annotated onto the same row)
- [x] **Unique icon keys** - the full grant fanout uses distinct `key`s (gpu/memory/cpu/shield/box) so the React row keys never collide; docker+privileged collapse to one `box` row
- [x] **Self-or-admin** - non-admin may read only their own grants (403 otherwise), same rule as the profile handler
- [x] **Failure falls to honest empty** - a fetch error returns `[]`, never the mock grants
- [x] **Edge: unknown user** - handler returns 404 when the ORM user does not exist
- [x] **Edge: biggest-wins attribution** - when two groups set memory/cpu, the row cites the highest-priority group at the winning (max) value
- [ ] **Runtime: konrad sees real grants** - on the live hub the Home / UserConfig grants reflect his actual group policy with correct source, not the mock list

### Activity report download

- [x] **Real report** - the Servers "Report" action downloads a real CSV of the servers currently in scope (one row per server, the same activity / CPU / memory / volume / time-left numbers the table shows), client-side from already-fetched data
- [x] **Edge: empty scope** - the Report button is disabled when no server is in scope (nothing to export)

### Group policy import / export

- [x] **Export uses real configs** - "Export N groups" downloads `{groups:[{name, description, priority, config}]}` built from the live `/admin/groups` configs (raw flat `config` now carried on `GroupRow`), client-side, real success toast
- [x] **Import writes via real endpoints** - the Import file-picker parses the bundle and `importGroups` creates each group (409 already-exists falls through) then PUTs `/admin/groups/{name}/config`; one toast + one `['groups']` invalidation for the batch
- [x] **Round-trips** - an exported bundle re-imports through the same flat-config shape the editor PUTs (hub coerces + validates)
- [x] **Edge: malformed file** - a non-JSON / shapeless file shows "Import failed: ..." and writes nothing; the same file can be re-picked (input value cleared)

### General rule

- [x] **Audit remaining mock delegations** - an adversarial sweep found 11 live-mode mock-masquerades; every `mockSource.*` in `liveSource` is now removed - on a 403/404/500/network error each method returns honest-empty/neutral, never fabricated content

### Adversarial mock sweep (2026-06-17) - all fixed

- [x] **getGroups / getGroupConfig** - catch returned `mockSource` (fabricated ~15 groups / a policy config that would PUT back on save); now `[]` / `undefined`
- [x] **getTokens** - catch fabricated 5 tokens incl. a fake `admin:users`-scoped one; now `[]`
- [x] **getUserVolumes** - catch fabricated home/workspace/cache sizes; now `[]`
- [x] **getEvents** - catch fabricated a named event feed as the real activity log; now `[]`
- [x] **getSessionInfo** - catch fabricated a per-user TTL driving the extend control; now an honest neutral from real idle-culler config
- [x] **getGroupCorpus / getUserCorpus** - catch injected fixture names into pickers; now `[]`
- [x] **getSettingsReference** - was hardwired to mock (no live attempt) despite a real `/settings`; now fetches `/settings` (env name + live value + description), honest-empty on error
- [x] **Servers "View spawn log"** - was `mockAction('Tail live spawn log')`; now opens the real Start-server page (`/servers/{user}/starting`)
- [x] **Verified honest (no change)** - getTotalResources, getHubInfo, getUserProfile, getLabContainer, getSettings, getEffectiveGrants, getSentNotifications already return honest-empty/last-known
- [ ] **AppLayout language toast** - `mockAction('Language: ...')` fires in both modes; client-only (no i18n backend) - lowest priority, left as-is

### API

- `GET /api/users/{user}/effective-grants` -> `{grants: [{key, label, value, from}]}`; 403 not-self-not-admin, 404 unknown user


## Mobile Responsive Portal

Below a mobile breakpoint the Duoptimum Hub portal switches to a JupyterHub-style minimal home: status plus the few controls that make sense on a phone. The lab itself (JupyterLab) is not mobile-friendly, so the portal never navigates into the user server on mobile.

- [x] **Breakpoint** - below a mobile width (target < 768px) the portal renders the mobile layout; the desktop layout is unchanged at/above it
- [x] **Mobile home content** - shows server status (pill + time-left) and exactly these controls: Start (launch), Stop, Extend TTL
- [x] **No lab navigation on mobile** - no Open-lab / Enter-session affordance anywhere on mobile; the portal never links into the user server UI
- [x] **Allowed mobile actions (closed set)** - launch server, stop server, extend session TTL; nothing else for a regular user
- [x] **No Restart on mobile** - restart is a desktop action; mobile exposes only Start/Stop/Extend
- [x] **Admin extras** - admin additionally sees the servers widget below the home card, plus a link to the Servers screen and a link to the Users screen
- [x] **No other admin mobile actions** - beyond the two links and the widget, no admin actions on mobile (no groups / tokens / settings / notifications inline)
- [x] **Servers/Users via link** - the Servers and Users screens are reached as links (navigation), not embedded inline on the mobile home
- [x] **Edge: resize / rotate across breakpoint** - layout swaps without losing query state (shared TanStack cache)
- [ ] **Edge: deep link to a desktop-only route on mobile** - degrade gracefully (redirect to mobile home or show a brief "desktop only" note), never a broken screen
- [x] **Edge: TTL/extend on mobile** - the extend control works on mobile (touch-friendly hours input); the bar follows the same base-relative behaviour as desktop
- [x] **Look good on a phone (runtime)** - visual polish, spacing, touch targets confirmed on an actual narrow viewport

## Navigation patterns (edit pages -> parent + breadcrumbs)

Every form / sub screen reached from a list must offer a way back to its parent and show a breadcrumb that names that parent - never a dead end and never a wrong parent. Two shapes: a screen with ONE parent returns to that fixed canonical route (matching its breadcrumb `parent` route handle); a screen reachable from MORE THAN ONE place records its origin in `state.from = {to, label}` and both the return target and the breadcrumb parent honour it. Mechanism: `react-router` route handles (`{crumb, parent}`) + `Breadcrumbs.tsx` (prefers `state.from` over the static parent) + `FormFooter` (Cancel + Save/Done/Ok). Cross-ref [acc-crit-edit-returns-to-origin] (UserConfig), [acc-crit-design-language] (the system-wide nav rules), [acc-crit-volume-reset]. Verified against the code 2026-06-18.

### Single-parent edit / sub pages

- [x] **Configure group -> Groups** - `/groups/:name` Save / Cancel / Delete return to `/groups`; breadcrumb parent Groups
- [x] **New user -> Users** - `/users/new` Save / Cancel return to `/users`; breadcrumb parent Users
- [x] **New group -> Groups** - `/groups/new` Save / Cancel return to `/groups`; breadcrumb parent Groups
- [x] **Bulk add -> Users / result** - `/users/bulk` Cancel returns to `/users`; submit advances to `/users/bulk/result`; breadcrumb parent Users
- [x] **Bulk result -> Users** - `/users/bulk/result` Done returns to `/users`; breadcrumb parent Users
- [x] **Export groups -> Groups** - `/groups/export` Cancel returns to `/groups`; breadcrumb parent Groups
- [x] **Full reference -> Settings** - `/settings/reference` (read-only) has no footer; the breadcrumb parent Settings is the way back

### Multi-origin pages (honour state.from)

- [x] **Configure user** - `/users/:name` returns to its origin (Home / Servers / Users) via `state.from`, Users as the canonical fallback; breadcrumb parent matches
- [x] **Manage volumes** - `/servers/:name/volumes` returns to its origin (Home or Servers) via `state.from`, Servers as the canonical fallback; breadcrumb parent matches
- [x] **Start server** - `/servers/:name/starting` returns to Home for your own server, Servers for another user's

### Breadcrumb rules

- [x] **Crumb from the route handle** - each page declares `handle.crumb`; the breadcrumb shows "Duoptimum Hub / [parent] / crumb"
- [x] **Origin beats static parent** - when `state.from` is present it overrides the route's static `parent` so the crumb names where the user actually came from
- [x] **Parent crumb is a link** - the parent crumb navigates back to the parent list; the current page crumb is bold, not a link
- [x] **Single source of truth** - the same `state.from` drives BOTH the breadcrumb parent and the footer return target, so they can never disagree

### Edge cases

- [x] **Edge: deep link / refresh** - landing on a sub page directly (no `state.from`) returns to the canonical parent and shows it as the breadcrumb parent
- [x] **Edge: never a dead end** - every list-reachable screen has either a footer Cancel/Done or a parent breadcrumb link back
- [x] **Edge: rename changes the route** - renaming a user on `/users/:name` navigates to `/users/:newName` (the renamed profile), carrying the origin state forward

### Functional tests

- [x] **Origin round-trip** - a Playwright test opens Configure user from the Users list and asserts the breadcrumb parent link is Users and Cancel returns to /users
- [x] **Single-parent round-trip** - tests open New user (-> Users) and New group (-> Groups) and assert the breadcrumb parent link + that Cancel returns to the parent list


## Old portal cleanup

Remove the dead remnants of the pre-React portal now that `duoptimum-hub-web` serves the portal via `PortalHandler` and the React SPA owns the former server-rendered routes. Surgical, not blanket: many `html_templates_enhanced/*.html` are still rendered by stock JupyterHub and MUST stay.

### Removed (confirmed dead)

- [x] **Dead page templates** - `activity.html`, `settings.html`, `groups.html`, `notifications.html` deleted from `html_templates_enhanced/`; referenced only by their own unregistered handlers
- [x] **Dead page handlers** - `ActivityPageHandler`, `SettingsPageHandler`, `NotificationsPageHandler`, `GroupsPageHandler` classes removed; their API data handlers kept
- [x] **Handler count test** - `test_imports` expectation 30 -> 26
- [x] **Orphaned import** - `import os` dropped from `groups.py` (only the removed page handler used it)
- [x] **Static mock prototype** - the `mock/` static HTML prototype tree (368K) deleted; unreferenced by any build/serve path
- [x] **Stale comments** - config `template_vars` comments naming `GroupsPageHandler` updated to the live consumers

### Kept (still live - must not remove)

- [x] **Stock-rendered templates kept** - `error.html`, `404.html`, `logout.html`, `oauth.html`, `spawn*.html`, `stop_pending.html`, `not_running.html`, `my_message.html`, `change-password*.html`, `authorization-area.html`, `accept-share.html`, `page.html` base - rendered by stock JupyterHub / NativeAuth
- [x] **Static assets kept** - `custom.css`, `session-timer.js`, `mobile.js` - referenced by `page.html`
- [x] **API data handlers kept** - the `*DataHandler` classes serving the SPA stay registered

### Held for a rebuild-verified pass (confirmed dead, not removed blind)

- [ ] **Shadowed auth/redirect templates** - enhanced `login.html`, `signup.html`, `native-login.html`, `home.html`, `token.html`, `admin.html` are shadowed by the duoptimum-hub-web wheel / remapped in `auth.py`; deleting them is auth-critical and wants an image rebuild to verify before removal
- [x] **package-lock name** - `duoptimum-hub-web/package-lock.json` already carries the correct name (no longer `mock-antd`)


## Portal UI Polish (2026-06-17 session)

Running checklist for the rapid UI feedback pass: TTL animation, GPU labels + rich tooltip, list tooltips, resource tooltips, upgrade pill, footer, list sub-names. Status is honest - `[x]` = in code + verified (tests/typecheck), `[ ]` = pending; backend-dependent items are flagged. Nothing here is live until the next image rebuild.

### TTL extend

- [x] **Extend refetches the bar** - `extendSession` invalidates `['hero', user]` so the bar refetches; backend persists `cull_at` and `remaining_seconds_for` reads it
- [ ] **Animate the increase** - on extend the bar should animate up to the new remaining, not snap

### GPU labels + tooltip

- [x] **Mini name as bar label** - per-GPU bar labels show the stripped name ("5090") not the index
- [x] **Full name fits before the bar (single line)** - the device-name label column is wide enough for the full short name ("A500 Embedded GPU"), single line, never wrapped/truncated, bar flexes after it
- [x] **Rich multiline GPU tooltip** - hover shows full info, one field per line: full name, UUID, memory total, current utilisation, memory used, temperature, wattage
  - [x] **Sub: extend sidecar** - add `temperature.gpu`, `power.draw` to `_GPU_QUERY` + schema (`gpuinfo-nvidia`, separate image)
  - [x] **Sub: thread fields** - keep uuid/temp/power through `gpu_cache` -> activity gpu entry -> `GpuDevice` -> tooltip
- [x] **Standard (native) tooltip, not a styled popup** - the GPU tooltip is the SAME native browser `title` tooltip the CPU/memory/volume/system cells use, so every resource tooltip reads identically - not a bespoke antd `Tooltip` popup

### List + resource tooltips

- [ ] **Multiline list tooltips** - long tooltips on Servers, Users and Groups lists wrap to a sensible max-width multiline box, not one ridiculously long line
- [x] **Resource widget tooltips** - on the resources tracker widget EVERY progress bar carries the detail tooltip, not just the % value

### Upgrade pill

- [x] **Desktop pill** - gold "Upgrade available" left of the status pill on the Server status card, running servers only
- [x] **Mobile pill** - same pill on the mobile MyServerCard header, running only
- [x] **Recency check** - `docker image ls` newest local image for the repo vs the running container's image created time (`image_upgrade_available`, 6 unit tests); unknown -> no pill

### Dashboard freshness

- [x] **Refresh server status on return** - returning to the dashboard after starting the lab must redraw the server control, servers widget and servers list with current status, not a stale "offline" from the hydrated cache for ~10s

### Misc

- [x] **Footer label** - bottom stack chip reads "Ant Design" not "Ant Design Pro"
- [x] **First/last name in users list** - the users list shows the profile first/last name as a sub-name under the username

### Verification

- [x] **Backend + frontend green** - `make test` 564, docker-proxy 63, portal `tsc --noEmit` clean as of this session
- [ ] **Live** - rebuild + hard refresh; confirm TTL animates up on extend, GPU names fit, tooltips wrap, pill shows


## Profile name display

A user's display name (first + last) edited on the Profile / Configure-user page must show everywhere it appears once saved. The backend store + API are correct (verified live: DB holds the new name, `GET /api/user-profiles` returns it); the bug was a frontend cache that never refetched after the save. `services/ops.ts::saveUserProfile`; display in `pages/Users.tsx` (`fullName` hint) + the profile form.

- [x] **Save invalidates the table** - `saveUserProfile` invalidates `['users']` (the Users table reads `fullName` from `/user-profiles` under that key) in addition to `['user-profile', name]` and `['user', name]`
- [x] **Form refetches** - `['user-profile', name]` invalidation refetches the edit form so its own fields/header reflect the save
- [x] **List refetches on mount** - `Users.tsx` force-invalidates `['users']` on mount (mirroring `Home.tsx`), so returning to the list after a save shows the new name immediately instead of repainting the persisted cache for ~2 min
- [x] **Backend correct** - PUT `/users/{name}/profile` persists first/last/email; bulk `GET /api/user-profiles` returns `{profiles: {username: {first_name,last_name,email}}}`
- [x] **Admin tag spacing** - the Users cell renders the username Link and the "admin" Tag in a flex row with a gap, so they no longer run together as "konrad.jelenadmin"
- [x] **Full name shown as hint** - `fullName` renders as the muted `oh-name-hint` line under the username (Users table + pending list)
- [ ] **Runtime: saved name refreshes the list** - on the live hub, saving a last name updates the Users table `fullName` without a manual reload

### Edge cases

- [x] **Edge: empty profile** - no first/last set -> no `fullName` hint rendered (the `{u.fullName && ...}` guard)
- [x] **Edge: self vs admin save** - both the user's own Profile page and the admin Configure-user page call the same `saveUserProfile`, so both invalidate `['users']`
- [ ] **Edge: rename + profile** - a username rename (`renameUser`) and a profile edit are separate ops; the rename already invalidates `USER_KEYS(name)`; the display name (fullName) is independent of the username


## Profile route (role-aware self-view)

The Profile nav link (`/profile`) opens the current user's own profile. It is role-aware: an admin gets the full Configure-user screen scoped to themselves; a plain user gets the self-service Profile page. `duoptimum-hub-web/src/router.tsx::ProfileRoute`, `pages/UserConfig.tsx`, `pages/Profile.tsx`.

### Routing

- [x] **Admin -> Configure-user (self)** - an admin's `/profile` renders `UserConfig`, which falls back to `useRole().username` when there is no `:name` param, so it is the same screen as `/users/{self}`
- [x] **Non-admin -> self-service Profile** - a plain user's `/profile` renders `Profile.tsx` (own name/email/password only), NOT `UserConfig`
- [x] **Breadcrumb** - the crumb is "Profile" for both roles (PageHeader title/sub are ignored by design, so the breadcrumb is the visible label)

### Admin self-view (UserConfig)

- [x] **Builtin admin controls hidden** - for the platform admin viewing self, Remove-user, Administrator and Authorised are hidden and the built-in-admin notice shows (`isBuiltinAdmin`)
- [x] **Force-password hidden** - the force-password toggle is hidden for an admin target (`!liveAdmin`), so it never shows on an admin's own profile

### Non-admin self-view (Profile.tsx)

- [x] **No admin controls** - only username (read-only), first/last name, email and password; no Administrator/Authorised/Remove/Groups
- [x] **Self password change with challenge** - changing the password requires the current password (`changeOwnPassword` -> `/change-password`), not the admin no-challenge endpoint
- [x] **No admin-only fetch** - the page reads only self-allowed endpoints (`/users/{self}/profile`), never the admin-only `/users` list
- [x] **Cancel/save stay put** - save and cancel return via `navigate(-1)`, not `/users` (which `RequireAdmin` would bounce a non-admin off)

### Edge cases

- [x] **Edge: no dead code** - `Profile.tsx` and `changeOwnPassword` are live again (used by the non-admin branch), not orphaned
- [ ] **Runtime: both roles** - on the live hub, an admin's Profile shows the Configure screen and a plain user's shows the self-service page with a working current-password change


## Rename user (admin action on the profile)

An admin can rename a user from the Configure-user screen via an action attached to the Username input (the design-language input-with-attached-action pattern, like Change password / Generate). The rename is destructive-adjacent: it goes through a confirmation popup, is only possible while the user's server is stopped, and warns that the renamed user's existing volumes do NOT follow the rename (an admin must migrate them separately). On success the screen navigates to the renamed user's profile. Backend is the stock JupyterHub admin rename (`PATCH /users/{name}` with `{name}`) plus the existing sync listener (`events.py::sync_nativeauth_on_rename`). Frontend `ops.renameUser`. Verified against the code 2026-06-18.

### Control + placement

- [ ] **Adjacent to the Username input** - the Rename action sits attached to the Username field as a `Space.Compact` input + button (the same pattern as the Change-password / Generate row), not a separate panel
- [x] **Admin role only** - the Rename control renders / is usable only for an admin; a plain user (self-service Profile page) never sees it
- [x] **Hidden for the built-in admin** - the platform admin account (`JUPYTERHUB_ADMIN`) cannot be renamed (like it cannot be removed/de-authorised)

### Rules

- [x] **Enabled only when the server is stopped** - the Rename button is disabled while the user's server is running/spawning; a tooltip says to stop it first
- [x] **Confirmation popup** - clicking Rename opens a confirmation dialog before any write; cancelling makes no change
- [x] **Volumes-not-migrated warning** - the confirmation states that the user's existing volumes (home / workspace / cache) stay attached to the OLD name and will NOT follow the rename; an admin must migrate them separately
- [x] **Back to the renamed profile** - on a successful rename the screen navigates to `/users/{newName}` (the renamed user's Configure screen)
- [x] **No-op guards** - Rename is disabled when the new name is blank or unchanged from the current name

### Backend (existing, reused)

- [x] **Rename endpoint records the actor** - the write goes through a custom admin endpoint `POST /users/{name}/rename` (not the stock PATCH) so the recorded event can name the acting admin; the rename itself is the orm `user.name = newName` + commit, identical to what stock does
- [x] **NativeAuth UserInfo synced** - the rename event listener updates the NativeAuthenticator `UserInfo.username` so authorisation + password survive the rename
- [x] **Activity + profile synced** - the listener renames the user's ActivityMonitor samples and display profile (first/last/email) to the new name
- [x] **Event recorded** - the rename records a `user` event so it shows in the Events feed
- [x] **Event names the actor (who renamed whom)** - the rename event identifies the acting admin AND both names, e.g. "<admin> renamed <old> to <new>"; the actor is taken from the authenticated request (server-trusted), never the client
- [x] **Volumes are NOT renamed** - the Docker per-user volumes (`jupyterlab-{encoded}_home` etc.) are keyed on the old encoded name and are intentionally left untouched by the rename (hence the UI warning)

### Post-rename + collateral (renamer's responsibility)

- [x] **Logs in with the new name** - after the rename the user authenticates with the NEW username; the credentials carry over because the NativeAuth `UserInfo` row (username + password hash + authorisation) is moved by the listener
- [x] **DB rows keyed on username are synced** - every platform store keyed on the username moves to the new name automatically: JupyterHub's own user row (the hub), NativeAuth `users_info`, ActivityMonitor samples, the display-profile row
- [x] **Renamer owns the remaining collateral** - the acting admin is responsible for everything the rename does NOT move automatically - chiefly the Docker per-user volumes (keyed on the old encoded name) - and the confirm dialog states this explicitly so it is a conscious choice
- [x] **No silent half-rename** - if any sync step fails the failure is logged; the rename never half-applies the auth row silently (UserInfo move is the auth-critical step, asserted in the unit test)

### Edge cases

- [x] **Edge: rename to an existing username** - the endpoint returns 409; the error toast surfaces and the screen stays put (no navigation)
- [x] **Edge: server running** - Rename stays disabled; no write is attempted
- [x] **Edge: mock mode** - the demo shows the success toast and does NOT navigate (the renamed mock user does not exist), matching Remove-user mock behaviour
- [x] **Edge: user creation is not a rename** - the `set` listener fires on the INITIAL name-set (user creation) with SQLAlchemy's `NO_VALUE` sentinel as oldvalue (not None); it must early-return so creation records no spurious rename event and never binds the sentinel into the username lookups

### Tests

- [x] **Unit: rename sync orchestration** - renaming an ORM user fires the listener: NativeAuth UserInfo username updated + authorisation preserved, a rename event recorded, the event names the actor when set, a same-value set records nothing, and user creation (NO_VALUE oldvalue) records no rename event
- [x] **Functional: SPA rename flow** - a Playwright test renames a stopped user from the Configure screen (confirm dialog -> rename), asserts navigation to the new profile and the actor-named rename event in the feed; carries `@pytest.mark.acc_crit("rename-user::...")`

### API

- `POST /hub/api/users/{name}/rename` body `{ "name": "<newName>" }` (admin) -> renames via the orm + records the actor event; returns `{ "name": "<newName>" }`; 400 blank/unchanged, 404 no such user, 409 name clash


## Resource bars (limits + tooltips)

The CPU/Memory/GPU progress bars on the "Server Status" panel (the server card's right half), the Servers table, and the Home "Host Status" widget (renamed from "Total resources usage"; the server card's status+controls half is titled "Server Control"). Each bar must read 0-100% against the right reference (a quota-limited user's bar measures against THEIR ceiling, not the host) and every bar must carry a hover tooltip with the precise breakdown. Backend `docker_utils.get_container_stats`; frontend `liveSource` (`getServerHero`/`getServers`/`getTotalResources`) + `components/meters.tsx` (`ResourceBars`).

### CPU bar reference

- [x] **Quota detected two ways** - `get_container_stats` reads BOTH `HostConfig.NanoCpus` (DockerSpawner `cpu_limit`) and `HostConfig.CpuQuota`/`CpuPeriod` (the cpu-quota-* cgroup groups); either yields `cpu_cores` + `cpu_cores_limited=True`
- [x] **CpuPeriod default** - a quota set without an explicit period uses the kernel cfs default 100000 (so 3200000/100000 = 32)
- [x] **No limit -> host cores** - absent any limit, `cpu_cores` = `online_cpus`, `cpu_cores_limited=False`
- [x] **Bar is usage/assignment** - the CPU bar value = `cpu_percent / cpu_cores` clamped 0-100 (`cpuBarPct`), parallel to the memory bar's usage/limit; docker's `cpu_percent` is cores-used x 100, so a multi-core container previously overflowed past 100%
- [x] **CPU tooltip names the ceiling** - `cpuTip` = "N cores assigned" (limited) or "N cores host (no limit)"

### Memory bar reference

- [x] **Bar is usage/limit** - `memory_percent` = usage / container memory limit; a 256 GiB-limited user reads against 256 GiB, not host RAM
- [x] **memory_limited flag** - the service exposes whether the bar's denominator is an explicit per-user limit or the host fallback, parallel to `cpu_cores_limited`; from `HostConfig.Memory > 0`
- [x] **Memory tooltip names the ceiling honestly** - "N GB used of M GB assigned" when `memory_limited`, else "of M GB host (no limit)"; Servers also annotates "(over warning threshold)" on a `memory_max_usage_mb` breach
- [x] **Usage excludes page cache** - `memory_mb`/`memory_percent` use `mem_usage_excluding_cache(memory_stats)` = cgroup `usage` minus `total_inactive_file` (v1) / `inactive_file` (v2), the exact figure `docker stats` and Docker Desktop show

### Granular assigned-resource service design

- [x] **Pure, tested helpers** - `derive_cpu_assignment(hostcfg, online_cpus)`, `derive_memory_assignment(hostcfg, stats_limit_bytes)` and `mem_usage_excluding_cache(memory_stats)` in `docker_utils` are pure functions, unit-tested independently of Docker (13 cases)
- [x] **Edge: nano-cpus wins over quota; zero mem limit = unlimited** - explicit `NanoCpus` takes precedence over a cfs quota; `HostConfig.Memory == 0` reads as host fallback, not a 0-byte ceiling
- [x] **Exposed on /activity** - per-user `memory_limited` added (default `False`, set from the stats passthrough in `handlers/activity.py`)

### Colour ramp (mem + cpu, both Total and the widget)

- [x] **Calm to 50%** - the CPU/memory fill keeps the default accent up to and including 50% (`meters.barColor` returns undefined)
- [x] **Gradual ramp past 50%** - 50-75% blends accent -> warning, 75-90% blends warning -> danger, and >=90% saturates to full danger via `color-mix` (smooth, design-token based, no hardcoded RGB)
- [x] **Smooth recolour** - the fill transitions width + background ~0.4s so a value change eases rather than jumps
- [x] **CPU/memory only** - the ramp rides the standard fill bar; GPU rows (labelled striped per-GPU bars) and the activity meter keep their own colours
- [x] **Both surfaces** - one helper in `meters.tsx`, used by the "Server status" panel and the "Host status" widget alike

### Tooltips on every bar

- [x] **Bar + value carry the tip** - `ResourceBars` puts `title={r.tip}` on BOTH the `.oh-res-bar` span and the value readout, so hovering the bar itself (not only the %) shows the breakdown
- [x] **Host status tips populated** - the Home "Host status" rows pass `tip` for CPU (`cpuTip`) and Memory (`memTip`); previously they passed none so the bars had no tooltip
- [x] **Host status tips quote % used** - both Host CPU and Memory tooltips lead with a `N% used` line (the bar value) followed by the absolute breakdown, multiline like the per-server widget
- [x] **Host memory denominator is host RAM** - the Host memory bar + tooltip divide by `activity.memory_host_total_mb` (real host RAM), NOT `active[0].memory_total_mb`
- [x] **Mock parity** - the demo (`mockSource`) matches live: `getTotalResources` returns `cpuTip`/`memTip` leading with `N% used`, and the activity meter carries `activityHours`
- [x] **Per-server memory tooltip leads with % used** - the per-server memory tooltip leads with `N% used` (the bar value), matching CPU and the Host tooltips, then the absolute line
- [x] **Total CPU is host-relative** - the aggregate CPU bar = total cores-used / host cores (largest assigned-core count among active servers), not a clamped sum
- [x] **GPU tooltips native** - per-GPU bars carry the standard browser `title` (name/UUID/memory/util/temp/power), not a bespoke antd popup
- [x] **GPU rows always show striped bars** - a GPU row with devices renders one labelled striped bar per device whether or not live utilisation is sampled; absent utilisation the bars render at zero fill (empty striped track), never collapsing to inventory chips
- [x] **Multiline tooltips** - the Servers memory/volume/system tooltips are `\n`-joined (one fact per line) like the GPU tooltip, not a single long " / "-joined string

### Edge cases

- [x] **Edge: just-started container** - empty `precpu_stats` -> get_container_stats try/except returns None -> bars show "-" rather than 500
- [x] **Edge: no active servers (totals)** - `getTotalResources` returns cpu/mem 0 with the real GPU inventory still surfaced
- [ ] **Runtime: konrad CPU bar reads against 32 cores** - on the live hub the CPU bar + tooltip reflect his 32-core quota, not 64 host
- [x] **Edge: GPU absent** - `gpuSupported()` false (live `window.jhdata.gpu_enabled` false) -> GPU rows hidden entirely, not a "-" row

### Tooltip percentages (added 2026-06-17)

The bars are 0-100% but the tooltips must also quote the live usage %, not only the assigned ceiling, on BOTH the server-resources widget and the servers-list per-user cells (identical tooltip text on both surfaces).

- [ ] **CPU tooltip shows % used** - in addition to "N cores assigned" / "N cores host (no limit)", the CPU tooltip quotes the live usage % (the bar value)
- [ ] **Servers-list CPU cell = same tooltip as the widget** - the per-user CPU cell on the Servers list uses the exact same tooltip text as the server-resources CPU bar
- [ ] **Memory tooltip shows % of assigned + % of total** - alongside the assigned info ("X GB used of Y GB assigned/host"), the memory tooltip states the % of the assigned that is used AND the % of the host total it is
- [ ] **Edge: unlimited memory** - when not limited (host fallback), "% of assigned" and "% of total" coincide; show one clearly rather than a redundant duplicate
- [ ] **Reflected in the design language** - the "tooltip carries the live % + the assigned reference" rule appears on /design-language as a visual cue


## Restart/stop progress feedback

During a server restart or stop the progress modal must clearly read as "something is happening": the bar creeps (it no longer sits at a static full bar that looks done) and a rotating funny "loading..." line plays underneath, sourced from a ready package.

- [x] **Creeping bar** - while busy the bar eases toward (never reaching) 90%, so it reads as ongoing work instead of a static 100% that looks complete
- [x] **Active style** - the bar keeps antd's `status="active"` shimmer while busy
- [x] **Rotating flavour line** - a random message rotates every ~1.6s below the bar
- [x] **Ready package** - flavour text comes from the `loading-messages` npm package (MIT, 305 messages), not a hand-rolled list
- [x] **Untyped shim** - a `declare module 'loading-messages'` ambient type lets TS import the untyped package
- [x] **Settle** - on success the bar jumps to 100% (success colour) and the modal auto-closes; the flavour line and timers stop
- [x] **Edge: error** - on failure the bar shows the exception state and the flavour line is hidden; modal stays open with Close


## Roles reference page

A read-only reference page under Advanced documenting the two IMPLICIT platform roles (admin, user) and the access each is granted across every page and action. Roles are not assigned by name - the platform derives them from JupyterHub's `admin` flag (admin) vs a regular authenticated, authorised account (user). Page: `Roles.tsx`, route `/roles`, nav under Administration -> Advanced. Verified against the code 2026-06-18.

### Placement + access

- [x] **Under Advanced** - the page is a leaf in the Administration -> Advanced submenu, beside Settings and Tokens
- [x] **Admin-only** - the route is under RequireAdmin; a plain user never reaches it
- [x] **Read-only reference** - no writes, no footer; pure documentation (like Settings reference)

### Roles are implicit (documented here, not on the page)

The roles are implicit - NOT assigned by name. The platform derives the role from JupyterHub's `admin` flag (admin) versus a regular authenticated, authorised account (user). A guest role is planned for the future but is not added now. This explanation lives in this acc-crit, not as on-page prose.

- [x] **Implicit model captured in acc-crit** - the implicit-role explanation is recorded here (above), not as an inline Notice on the page
- [x] **Role definitions single panel** - the role definitions live in ONE panel ("Role definitions") holding a single table, not per-role prose cards
- [x] **Role table columns** - columns are Role, Description, How assigned, Who; descriptions terse (technical-documentation style); Who is a terse example audience, not names
- [x] **Admin row** - terse: full read/write/create/remove across fleet, users, groups, platform; assigned = holds JupyterHub's `admin` flag (JUPYTERHUB_ADMIN at login, or toggled on Users); who = operators, maintainers
- [x] **User row** - terse: own server + profile only, no fleet/user/group rights; assigned = authenticated, authorised account without the admin flag; who = data scientists, notebook authors, learners
- [x] **Guest not on the page** - guest is documented as a planned future role here only; it is NOT shown on the page and NOT added as a current role

### Access matrix (every page + function, per role)

- [x] **One row per capability** - the matrix lists each page AND each action (server lifecycle, user admin, groups/policy, platform), grouped by area
- [x] **Per-capability description** - every capability row carries a terse description column stating the read/write/list/create/remove rights it entails
- [x] **A column per role** - Admin and User columns, one access cell each
- [x] **Access level per cell, not just yes/no** - each cell shows the level: Full / Self only / View / Denied (the operator's "access level or deny or etc")
- [x] **Colour-coded pills** - access levels render as pills on the shared palette (green full, amber self-only, blue view, red denied), per the design-language state=colour rule
- [x] **Accurate to the code** - the matrix reflects the real gating: RequireAdmin page gating + the handlers' self-or-admin rules (e.g. start/stop = self for user, full for admin; rename/groups/broadcast = admin only)
- [x] **Notes for nuance** - rows whose access needs a caveat (own-only, admin-can-enter-any, rename needs stopped server) carry a muted sub-note
- [x] **Zebra rows** - the matrix tables use the mandatory alternating-row striping

### Verification

- [x] **Frontend gates** - `npx tsc -b`, `npm run lint`, `npm run build:hub` clean with the new page + route + nav


## Server lifecycle UX (inline spinners, no modal, real log)

Server start/restart/stop show progress with an INLINE spinner on the control (no modal popup): the op fires, a background monitor polls the real hub status until the transition lands, then the affected views refresh immediately. A spawning server shows a rotating spinner (not the old ekg/activity glyph), and the spawn log opens the real Start-server page.

### Restart / Stop (no modal, inline spinner)

- [x] **No modal** - the restart/stop progress modal (creeping bar + flavour text) is removed; `ServerLifecycle` is a context provider with no popup UI
- [x] **Inline spinner** - while restarting/stopping, the control shows a spinner in place of its icon (hero buttons via antd `loading`; row actions via `IconAction busy`)
- [x] **Background monitor + immediate refresh** - the op's `run()` toasts + invalidates on POST; `pollUntil` then monitors the real status until the transition lands, then invalidates servers/hero/resources/stats so the views update at once
- [x] **Conflicting controls disabled** - other lifecycle buttons disable while a transition is in flight (the busy map)
- [x] **Failure surfaces as a toast** - a failed POST shows the op's error toast (no stuck modal); busy clears

### Spawning (rotating spinner, real log)

- [x] **Rotating spinner, not ekg** - a spawning server's row shows an antd `Spin`, not the activity/ekg icon
- [x] **Real spawn log** - "View spawn log" navigates to the real Start-server page (`/servers/{user}/starting`, live progress + container-log tail), not a `(mock)` toast
- [x] **Per-row probe/refresh on ready** - the servers list fast-polls (2.5s) while any server is spawning, so a spawning row flips to active within ~2.5s of ready; `statusOf` reads the post-spawn settle window as spawning so the fast poll engages
- [ ] **Runtime: spinner + heal** - on the live hub a spawning row shows the spinner and flips to active within ~2-3s of ready

### Starting / restarting ANOTHER user's server - inline, no nav (#243, supersedes #237)

Starting or restarting another user's server from the Servers widget or list must NOT navigate to the start/progress screen. It behaves exactly like Stop/Restart already do: an inline spinner on the play (or restart) button until the server is up, then an immediate row refresh.

- [ ] **No start-screen navigation** - starting another user's server does not route to `/servers/{user}/starting`
- [ ] **Inline play spinner** - the play button shows the SAME inline spinner pattern as the stop button (`IconAction busy` / hero `loading`) while the server starts
- [ ] **Restart same** - restarting another user's server is also inline-spinner + refresh, no navigation
- [ ] **Background monitor + immediate refresh on ready** - the existing `runOp`/`pollUntil` monitor drives the start too; the row flips to active immediately when the server is up (reuse the start op, add a `start` mode to the lifecycle busy map)
- [ ] **Self-start unchanged** - a user starting their OWN server keeps the start page (this only changes starting someone ELSE's server); confirm the self path still shows progress
- [ ] **Reflected in the design language** - the "admin start = inline spinner, not a nav" cue is on /design-language

## Server Status Immediacy

After a server starts or stops, the hub status (hero + table) must reflect the new state immediately, not ~10s later. The authoritative signal is the spawner state from `/users/{user}` (`ready`/`pending`), not the activity sampler's `server_active`/`recently_active`, which lags by one ~10s sample.

- [x] **Spawner is authoritative for presence** - `statusOf` derives status from `srv.ready` / `srv.pending`, dropping the stale `|| a.server_active` OR that kept a just-stopped server showing active
- [x] **Hero fetches the spawner** - `getServerHero` now fetches `/users/{user}` and derives status from `servers['']`, so it no longer trusts only the lagging activity snapshot
- [x] **Start reflects immediately** - a just-started (ready) server reads active/idle at once
- [x] **Stop reflects immediately** - a just-stopped server reads offline at once, not active-for-10s
- [x] **Spawning shown** - `srv.pending === 'spawn'` reads as spawning
- [x] **Resources still keyed on the sample** - CPU/memory stay keyed on `server_active` (they only exist once stats are sampled), while presence comes from the spawner
- [ ] **Runtime: no 10s lag** - on the live hub the status flips within one refresh of start/stop

## Servers List Layout

The Servers page table column structure, ordering, alignment, widths, and the user-name + time-left columns. Distinct from the Server widget (which intentionally clubs status + last-activity); the LIST keeps them as separate columns. `duoptimum-hub-web/src/pages/Servers.tsx`.

### Columns and order

- [ ] **Status and Last activity are separate columns** - the list does NOT club last-activity into the status label (unlike the widget); Status is its own column, Last activity its own
- [ ] **Column order** - Status, then Last activity, then Activity tracker (left to right)
- [ ] **Status column just wide enough** - the Status column is sized to its content, not over-wide
- [ ] **Last activity column just wide enough** - same: sized to content, not over-wide

### Activity column

- [ ] **Activity meter centered** - the activity tracker is centered within its column, not left-aligned
- [ ] **Activity tooltip: real uncapped %** - the tooltip shows the REAL activity % which MAY exceed 100% (>100% is desirable - the user works more than the 8h/day target); not clamped
- [ ] **Activity tooltip multiline** - the % plus the existing info (avg active hours/day) on separate lines, not one super-long single line

### Row actions

- [x] **No "View spawn log" action** - the spawning-row actions are the spinner + Cancel spawn only; the "View spawn log" icon (which navigated to the Start page) is removed - not needed

### User name column

- [ ] **Name is a link to the user** - the username links to the user config page (same target as the Users page), no artificial click-friction
- [ ] **First + last name shown** - the cell shows the user's first and last name exactly like the Users page (name under / alongside the username), from the same profile source

### Time-left column

- [ ] **Tooltip: hours over standard TTL** - the Time-left tooltip states how many hours over the standard (base) TTL the session currently is (the extension beyond the base timeout)
- [ ] **Edge: not extended** - when the session is at or under the base TTL, the tooltip does not claim a negative over-hours (shows none / "within standard TTL")

### Reflected in the design language

- [ ] **Visual cues on /design-language** - the column-separation, ordering, alignment, and name-as-link conventions are shown on the design-language page as visual cues (not before/after examples)

## Servers Resource Cells

The Servers table enriches every resource cell with a full breakdown and its quota so an admin reads usage-vs-limit at a glance. Data comes from the `/api/activity` payload (per-user `memory_mb`/`memory_total_mb`, `volume_breakdown`, `container_size_rw_mb`/`container_size_rootfs_mb`, `last_activity`) plus the aggregate quotas (`memory_max_usage_mb`, `volume_max_total_size_mb`, `container_max_extra_space_mb`). Absent values render as the muted dash, never a fabricated zero.

- [x] **Mem column label** - the Memory column header reads "Mem"
- [x] **Mem tooltip breakdown** - tooltip shows used vs configured per-user limit vs total host RAM (e.g. "19.2 GB used / 32 GB limit / 64 GB host")
- [x] **Mem over-quota** - cell flags (warn colour) when used exceeds the configured per-user limit; tooltip states it is over
- [ ] **CPU assigned cores** - CPU cell/tooltip also shows how many cores are assigned to the user (per-user limit), not only % of host
- [x] **Volumes tooltip breakdown** - tooltip lists per-volume sizes (home / workspace / cache) and the total; shows the quota when the total is exceeded
- [x] **Volumes over-quota** - cell flags (warn colour) when total exceeds the volume quota; tooltip states the quota
- [x] **System size breakdown** - tooltip shows base image size, writable layer size, and the quota (e.g. "base 3.1 GB + writable 1.4 GB / 10 GB quota")
- [x] **System over-quota** - cell flags (warn colour) when writable layer exceeds the extra-space quota; tooltip states the quota
- [x] **Last activity column** - a "Last activity" column sits immediately after Status, showing time-ago of the last activity, shortened per design language ("2m", "3h", "2d")
- [x] **GPU column gating** - the GPU column is shown only when the platform has GPU (window.jhdata.gpu_enabled), hidden entirely otherwise
- [x] **Edge: server stopped** - resource cells (cpu/mem/system/last-activity) read the muted dash when the server is not running; volumes still show last-known size
- [x] **Edge: data not yet sampled** - before the first stats/volume sample lands, cells show the muted dash (or last-known for volumes), never a 0
- [x] **Edge: no quota configured** - when a quota env is 0/unset, the cell never flags over-quota and the tooltip omits the quota clause
- [x] **Edge: no last activity** - users with no recorded activity show the muted dash in the Last activity column

### Data sources (existing /api/activity per-user fields)

- `memory_mb`, `memory_percent`, `memory_total_mb` - mem used / % host / host total
- `volume_size_mb`, `volume_breakdown` (suffix -> MB) - volumes total + per-mount
- `container_size_rw_mb`, `container_size_rootfs_mb` - writable layer + full rootfs (base = rootfs - rw)
- `last_activity` (ISO) - last activity timestamp
- aggregate quotas: `memory_max_usage_mb`, `volume_max_total_size_mb`, `container_max_extra_space_mb`
- MISSING: per-user assigned CPU cores (needs to be added to the payload for the CPU-cores criterion)

## Dedicated Start-server Page with Live Container-log Feed

Starting your OWN server leaves the lightweight modal behind and navigates to a dedicated page that shows a spawn progress bar plus a rolling 10-15 line tail of the freshly-started container's logs, then redirects into the lab when it is ready. Restart/stop keep the small popup (they settle in seconds). Supersedes the start-page items under "Live QA - round 3" in `duoptimum-hub-web/acc-crit-portal-fixes.md`.

Two data sources: the **progress bar** rides the hub spawn-progress SSE (`GET /hub/api/users/{name}/server/progress`, no backend change); the **log feed** is the actual container stdout/stderr via a new backend tail endpoint (the SSE `message` field is spawn-progress text, not container logs).

### Page + navigation

- [ ] **Start -> dedicated page** - clicking Start on your own server navigates to `/servers/:name/starting` (no modal); restart/stop keep the lightweight popup
- [ ] **Progress bar** - a progress bar bound to the spawn SSE advances with the hub's reported spawn progress (0-100)
- [ ] **Auto-navigate on ready** - on the SSE `ready` event the page redirects into the running server (`userServerUrl`); there is NO Close/Continue button on the success path
- [ ] **Failure path** - on `failed` (or stream drop without ready) the page shows the error + a Back-to-portal action; no auto-redirect
- [ ] **Admin starting another user's server** - lands on the page; on ready returns to the parent screen (Servers), never auto-enters someone else's lab (consistent with the open-someone-else confirm rule)

### Live container-log feed

- [ ] **Rolling tail** - the page shows the last 10-15 lines of the freshly-started container's logs, in a fixed-height monospaced panel that scrolls with new lines (newest at bottom)
- [ ] **Live update** - the feed refreshes while spawning (poll ~1-2s or stream) so the user watches the container come up, not a frozen snapshot
- [ ] **Stops on ready/redirect** - polling/stream stops when the page redirects or unmounts (no leaked timer/EventSource)
- [ ] **Admin-or-self only** - the log endpoint is authorised to the server owner or an admin; a non-owner non-admin gets 403
- [ ] **Bounded** - only a tail (N lines, capped) is returned; never the full log; never secrets echoed by the entrypoint beyond what the container itself prints

### Look and feel (must look polished)

- [ ] **Centered, branded** - a single centered card with the Duoptimum Hub mark and the server name as a clear title ("Starting konrad.jelen's lab"), generous standard panel padding, no raw full-width sprawl
- [x] **Terminal-styled log panel** - the log feed reads like a real terminal: monospaced, dark subdued panel, soft rounded corners, dim line text, fixed height (~10-15 rows) that scrolls, not a plain bulleted list
- [x] **Wide enough, no line-wrap** - the panel is wide enough for real log lines and never breaks a line mid-content; long lines scroll horizontally
- [ ] **Smooth progress** - the progress bar animates smoothly (antd Progress, accent blue), with a short human status line above it ("Pulling image...", "Starting server...") sourced from the latest SSE message
- [ ] **No layout shift / no flicker** - the card and log panel reserve their space from first paint; new log lines append without the page jumping; the redirect on ready is clean, not a flash
- [ ] **On-brand + design-language consistent** - colours, spacing, pills and typography match the rest of the portal (cross-check `/design-language`); dark-mode correct; tasteful, calm, not busy
- [ ] **Graceful states look intentional** - waiting/placeholder, failure and "logs unavailable" states are styled (muted, centered, an icon), never raw error text
- [ ] **Subtle motion** - a light spinner/pulse while spawning conveys liveness without being noisy; stops on ready

### Edge cases

- [ ] **Edge: SSE unsupported / drops** - progress falls back to status polling (`isRunning`); the log feed still tails independently
- [ ] **Edge: navigate away mid-spawn** - spawn continues server-side; returning to the page reflects current state (re-attaches SSE + log tail)
- [ ] **Edge: container not created yet** - before the container exists, the log panel shows a muted "waiting for container..." placeholder, not an error
- [ ] **Edge: logs unavailable** - if docker logs can't be read (permissions, container gone), the panel shows a muted notice and the progress bar still drives readiness
- [ ] **Edge: very chatty container** - the tail is line-capped so a noisy container can't blow up the DOM/memory (keep last N only)
- [ ] **Edge: spawn succeeds before page mounts** - if the server is already ready on mount, skip the wait and redirect immediately
- [ ] **Mock parity** - in mock mode the page animates progress and shows a canned 10-15 line log sample so the demo shows the flow (no hub)

### API

- existing: `GET /hub/api/users/{name}/server/progress` (SSE) - drives the progress bar; `_xsrf` as query param (EventSource can't set headers)
- NEW: `GET /api/users/{name}/server/logs?tail=15` -> `{lines: string[]}` (admin-or-self) - tails the spawned container (`docker logs --tail N jupyterlab-{name}`); 403 non-owner, 404 no container, capped tail
- existing: status poll (`GET /hub/api/users/{name}`) - SSE fallback for readiness

## Startup Hydration

A single startup-hydration step warms every cache and fires the deferred checks ONCE at boot, so a (re)started hub shows a populated portal immediately instead of an empty one until an admin first opens the Activity page. Everything runs on the IOLoop after the hub is serving (best-effort, never blocks boot) and is consolidated behind one entry point. Module: `hydrate.py::schedule_startup_hydration`; wired in `config/jupyterhub_config.py` Section 5. Verified against the code 2026-06-18.

### Consolidation

- [x] **Single entry point** - one `schedule_startup_hydration(...)` call replaces the previously scattered startup work (lazy refresher starts in the `/activity` handler + the separate favicon and policy callbacks)
- [x] **Deferred, never blocks boot** - hydration is registered via `IOLoop.current().add_callback` and runs after the hub is serving; the synchronous boot work (bounded GPU probe, sidecar self-start, branding) stays where it is
- [x] **Best-effort** - each hydration step is wrapped so a failure (docker unreachable, etc.) is logged and skipped, never crashing boot or the IOLoop
- [x] **Shared with the handler (fallback)** - the `/activity` handler calls the same `start_activity_refreshers(...)`, so a direct `/activity` hit still works if hydration was skipped; the refreshers are idempotent

### Cache hydration (populate right away)

- [x] **Activity refreshers started at boot** - volume sizes + container sizes refreshers start at hydration; each `start()` submits an immediate first refresh, so the caches warm without waiting for the first request
- [x] **GPU utilisation gated on hardware** - the GPU-utilisation refresher is started only when the host has GPUs (`gpu_list` enumerated at boot); GPU-less hosts skip it (no pointless sidecar polling)
- [x] **Live stats warmed for survivors** - servers that survived the restart get a live-stats sample triggered at hydration, so the activity map shows CPU/memory immediately
- [x] **Periodic refresh continues** - after the immediate warm, each refresher keeps its normal PeriodicCallback cadence (volume 3600s, container size 300s, GPU util 30s, stats activity-gated 10s)

### Pick up running servers (restart survivors)

- [x] **Survivor caches rehydrated** - the warmed size/volume/stats caches reflect already-running labs at boot, not only after the first `/activity` poll
- [x] **Survivor CHP favicon routes** - per-user favicon routes for already-running servers are re-registered (pre_spawn_hook only fires on new spawns)
- [x] **Survivor policy re-imposed** - each policy model's `on_hub_startup` runs for survivors (docker-proxy re-bind, download-block route re-registration, api-keys reconcile)

### Image-update check (immediate)

- [x] **Image snapshot warmed at boot** - the slow `docker image ls` scan that backs "update available" is built at hydration, so the per-container check is immediate from the first `/activity` request instead of lazily on first access
- [x] **Configured lab image reported** - hydration logs whether the configured lab image is up to date, has a newer local build, or is not present yet

### Edge cases

- [x] **Edge: no survivors** - with nothing running, stats warming is a no-op (no docker calls); refreshers still start and find an empty fleet
- [x] **Edge: docker unreachable** - image snapshot + stats warming degrade to empty/last-known and log a warning; hydration completes
- [x] **Edge: GPU-less host** - GPU-utilisation refresher is not started; no error
- [x] **Edge: runs once** - hydration is a one-time boot callback; the refreshers' idempotent `start()` means a later `/activity` hit does not double-start them

### Tests

- [x] **Unit: shared helper + gating** - `start_activity_refreshers` starts volume + container-size refreshers always and GPU utilisation only when `gpu_list` is non-empty; the hydration entry is importable + callable
- [ ] **Functional: restart with a running lab** - start a lab, restart the hub, then confirm the portal shows the survivor's sizes/stats and the update state without a manual `/activity` visit

## TTL Extend Bar Animation

Extending the idle-session TTL must move the progress bar immediately on click and animate smoothly to the **computed post-extend target %**, with no overshoot, no snap-back and no delayed flash. The bar and the time-left counter animate on click in lockstep, then settle when the refetched value lands - landing on the same % it animated to, so there is no jump.

- [x] **Immediate animate to target** - on Extend the bar starts moving on click (optimistic boost) toward the post-extend target %, not 2-3s later
- [x] **Target = computed post-extend %, not 100%** - the boost target is `pctFor(min(ceiling, timeLeft + addedHours))` through the same two-phase formula (base scale below base, ceiling scale when extended), NOT a hard-coded 100%; so an already-extended session animates to its true partial % and never overshoots to full
- [x] **No snap-back on settle** - because the ceiling is invariant across an extend, the optimistic target equals the refetched %, so when the value lands the bar is already there (no visible jump)
- [x] **Hold until refetch** - the boost (bar held at the target) holds until the refetched `timeLeftMin` actually changes, so the bar never snaps back to the old value mid-flight
- [x] **Minimum fill window** - the boost lasts at least `ANIMATION.ttlExtendMs` so the growth is always visible even if the refetch is fast
- [x] **3s duration** - the fill/glow animation runs over 3s
- [x] **Time counter climbs with the bar** - during the boost the shown minutes count UP from the captured baseline to the post-extend target over the SAME `ttlExtendMs` duration and CSS-`ease` easing as the bar fill, so the number climbs in lockstep with the bar; on settle it lands on the live refetched value
- [x] **Edge: extend rejected** - if `onExtend` rejects, the boost drops immediately (bar returns to the real %)
- [x] **Edge: value never changes** - a safety cap (`ttlExtendMs + 6s`) ends the boost so it can never stick
- [x] **Edge: extend across the base crossover** - extending a session from below base up past base animates to the post-extend ceiling-scaled % (a one-time scale-switch drop is the operator-chosen two-phase model, not the bug); within the banked regime (both endpoints > base) the bar grows monotonically

## TTL Progress Bar Behaviour Matrix

The idle-session TTL bar (`TtlGadget`, `components/meters.tsx`) reads ~100% when time is ample and drains as the session is used, shifting blue -> orange -> red as the cull nears; the used-up remainder is the gray trail. Extend opens a popover to type the hours to add, capped at the configured ceiling. A fresh session reads ~100% and drains; an EXTENDED session (time banked above base) drains against the extension ceiling (base + max_extension) so the user sees it running out, then rescales to full at the standard baseline. Verified against the code 2026-06-17, warn threshold = 60 min (`THRESHOLDS.timeLeftWarnMin`).

### Rules (verified in meters.tsx)

- [x] **Two-phase pct** - below base: `min(100, timeLeft/base)`; extended (timeLeft > base): `timeLeft / ceiling` where `ceiling = timeLeft + maxAddHours*60` (= base + max_extension), so the extended bar drains instead of pinning at 100%
- [x] **Rescale to base at the baseline** - the moment timeLeft falls to base the scale switches to base (full again), then drains normally below; a visible snap-to-full at the baseline crossover (operator-chosen model)
- [x] **Colour bands** - danger (red) at `timeLeftMin <= 20` (warn/3); warning (amber) at `<= 60`; accent (blue) above
- [x] **Readout matches the bar tone** - the remaining-time text and the clock icon take the SAME colour the bar shows at that moment (accent / warning / danger), driven by one shared `barTone` so the readout and the bar can never disagree
- [x] **Readout follows the boost** - during an extend boost the bar is forced accent; the readout is too (same `barTone`), so the whole gadget reads accent while the optimistic fill plays
- [x] **Extend = hours input** - Extend opens a popover with an InputNumber (min 1, max = round(maxAddHours)); apply clamps and calls onExtend
- [x] **At ceiling disables Extend** - `atCeiling = maxAddHours <= 0` -> Extend button disabled
- [x] **Hidden when stopped** - the gadget is only rendered for a running server

### Behaviour matrix (base = 240 min)

Each row is demonstrated live on `/design-language` (TTL behaviour matrix row).

- [x] **Full** - timeLeft 240, maxAdd 12 -> pct 100, blue, Extend enabled (max 12h)
- [x] **Ample** - timeLeft 180, maxAdd 12 -> pct 75, blue, Extend enabled
- [x] **Warn** - timeLeft 45, maxAdd 12 -> pct 19, amber, Extend enabled
- [x] **Low / danger** - timeLeft 12, maxAdd 12 -> pct 5, red, Extend enabled
- [x] **Extended-drains** - timeLeft 300 (> base 240), maxAdd 6 -> ceiling 300+360=660, pct 45 (drains against the ceiling, NOT capped at 100), blue, Extend enabled (max 6h)
- [x] **At ceiling** - timeLeft 180, maxAdd 0 -> pct 75, blue, Extend DISABLED
- [x] **Stopped** - server offline -> gadget not rendered at all

### Extension flow

- [x] **Extend caps at allowance** - typed hours clamped to [1, round(maxAddHours)] before onExtend
- [ ] **Runtime: extend round-trips** - clicking Extend issues the real `POST /users/{name}/extend-session` and the bar/clock refresh to the new remaining time
- [x] **Runtime: visual drain + colour shift** - the matrix renders blue -> amber -> red with the base-relative cap and the at-ceiling disable

### Replenish laws (SSOT: idle_culler.py, mirrored in the bar)

- [x] **Activity floor = base** - an active server retains at least base; activity replenishes remaining up to base, never above (`calc_remaining` activity_floor = base - idle)
- [x] **No replenish above base** - while extended (remaining > base) an active server is NOT topped up; the banked time drains via the deadline until it falls to base
- [x] **Drains to base then replenishes** - once remaining falls below base, an active server is topped back to exactly base ("max becomes base again") and normal replenish resumes
- [x] **Ceiling cap** - no extend sequence banks lifetime past base + max_extension; the deadline never sits more than ceiling ahead of now

### Extended TTL must visibly drain (operator 2026-06-17)

The backend already drains banked extension down to base; the BAR now shows it. Operator-chosen model: scale the extended bar to the extension ceiling so it drains (gray trail growing), then rescale to the standard baseline at the crossover (snaps full again, against the standard baseline not the extended scale).

- [x] **Drains while extended** - when remaining > base the bar shrinks against the ceiling as time passes (the user sees time running out), no longer pinned at 100%
- [x] **Gray leftover** - the drained portion above the current remaining shows as the standard gray trail (antd Progress trailColor)
- [x] **Full again at the standard TTL** - at the standard baseline the bar rescales to base and reads full again (against the standard baseline, not the extended scale); below base it drains normally

### Extend refetches the bar

- [x] **Extend invalidates hero** - `extendSession` invalidates `['hero', user]` (plus session, servers) so the bar refetches and grows after a successful extend
- [x] **Runtime: extend grows the bar** - on a running session, Extend visibly animates the bar to the post-extend remaining; below base it fills toward base, when banked above base it grows against the ceiling (never pinned at a false 100%)

### Staged extend animation

On Extend the gadget plays a three-step animation instead of a single jump (`TtlGadget` boost state + `.oh-ttl-boost` in global.css). The bar animates to the **computed post-extend target %** (against the invariant ceiling), never a blanket 100%.

- [x] **Step 1 - bar moves to target, time held** - on click the bar animates immediately toward `boostPct = pctFor(min(ceiling, timeLeft + addedHours))` (the same two-phase formula) while the time text holds its pre-extend value
- [x] **Step 2 - grow to new limit over a configured duration** - the bar visibly fills to the new ceiling (not a snap) with a brief accent glow, like the old design
- [x] **Duration is package-config** - the fill duration lives in `duoptimum-hub-web/src/services/config.ts` (`ANIMATION.ttlExtendMs`, default 1000), NOT a Docker env (too granular); it drives the JS hold timer and, via the `--oh-ttl-anim` CSS var on the bar, the CSS transition + glow from one place
- [x] **Step 3 - time text updates, no snap** - once the refetched `timeLeftMin` lands the bar settles on the real % (which equals the target it already animated to, ceiling being invariant, so no jump) and the clock text reveals the new remaining time
- [x] **Clock icon before the time** - the clock glyph renders immediately left of the remaining-time text in the gadget
- [x] **Edge: partial extend below base** - extending only part-way (remaining still < base) animates to the base-scaled target % and settles there; no overshoot to 100%
- [x] **Edge: extend while banked (> base)** - both endpoints above base -> the bar grows monotonically against the ceiling (the operator's reported case: 56h -> 63h), no overshoot/snap
- [ ] **Runtime: animation on the live hub** - the three-step sequence is visible end-to-end on a real extend round-trip

### Test harness

- [x] **Python SSOT matrix runs all scenarios** - `test_ttl_matrix.py` + `test_idle_culler.py` cover progress pct, ceiling, available hours, extend (add/cap/maxed), remaining (activity floor, replenish, ceiling, floor), cull
- [ ] **No JS test harness for the bar** - the portal has no vitest setup; the `TtlGadget` pct formula mirrors `calc_progress_pct` verbatim and is covered in Python; a JS unit test would need a new harness

### Home server-controls additions

- [x] **Uptime on the TTL line** - the TtlGadget shows "up Xh" inline (next to the remaining-time clock) for a running server
- [x] **Upgrade-available pill** - a gold "Upgrade available" pill shows left of the status pill on the Server status card when a newer lab image is available locally than the running container's
- [x] **Edge: image id unknown** - local image absent / docker unreachable -> `lab_image_id` None -> no upgrade offered (never a false pill)
- [ ] **Edge: re-tag to older** - if the local tag is moved to an OLDER image the pill still shows (different-id heuristic; watchtower only pulls forward so this is theoretical)

## "Upgrade Available" Pill

The home/server "Upgrade available" pill tells a user that a stop/start would land their lab on a newer image. Detection compares image IDs (not `Created` times): the running container's image is frequently pruned right after a rebuild - the very moment an upgrade exists - so its timestamp is unreadable; the reliable signal is that the configured lab image tag now resolves to a different id than the one the container runs. Backend `docker_utils.newer_lab_image_available` + pure `image_upgrade_available`; surfaced as `/activity` `lab_image_upgrade_available` -> `hero.upgradeAvailable`.

### Detection algorithm

- [x] **Ref from settings** - the compared ref is the configured lab image (`stellars_config['lab_image']` = `JUPYTERHUB_LAB_IMAGE`), passed per-container to `newer_lab_image_available(image_ref, container_image_id)`
- [x] **No tag -> :latest** - a ref with no tag on its final path segment gets an implicit `:latest` (docker's own default); a `@sha256` digest is stripped (`_normalize_ref`)
- [x] **Tag supplied -> use it** - a ref that already carries a tag (`repo:3.8.5`, `repo:latest`) is compared on that exact tag, not coerced
- [x] **Compare resolved-tag id vs running id** - `tag_to_id[ref]` (the id the tag currently points to) is compared to the running container's `container.attrs['Image']`; differ -> candidate upgrade
- [x] **Guard: tag must be the repo's newest** - the candidate only fires when the resolved tag id equals the repo's newest-by-`Created` image id, so a deliberate re-tag of the lab tag to an OLDER image never offers a false upgrade
- [x] **ID comparison, not Created** - the running image's `Created` is NOT read (it is gone from the store after a rebuild+prune); only ids are compared, with `Created` used solely to pick the repo's newest image

### Created parsing (why the old code never fired)

- [x] **ISO-8601 string parse** - docker-py returns image `Created` as an ISO-8601 string with nanosecond precision + trailing `Z` (`2026-06-17T11:20:48.755861714Z`), not an epoch int; `_parse_created` normalises `Z`->`+00:00`, trims ns->us, and `datetime.fromisoformat`s it
- [x] **Epoch fallback** - an int/float `Created` (older docker clients) is accepted as-is
- [x] **Unparseable -> None** - a malformed/empty `Created` yields None and the image is skipped for the newest-by-repo calc (never crashes the snapshot)

### Snapshot + caching

- [x] **One snapshot, dict lookups** - `docker image ls -a` is snapshotted to `(tag_to_id, newest_id_by_repo)` and cached `_IMAGE_TTL` = 300s so the polled `/activity` endpoint does a dict lookup, not a socket call per user
- [x] **Dangling/untagged skipped** - tags whose repo is `<none>` are not indexed

### Display

- [x] **Running server only** - the pill shows only for an active server (the upgrade check runs on the container stats path, default `lab_image_upgrade_available: False`)
- [x] **Label is "Update available"** - the user-facing pill label reads "Update available" (capital U); internal identifiers (`upgradeAvailable`, `lab_image_upgrade_available`) keep "upgrade"
- [ ] **Pill desktop + mobile** - `hero.upgradeAvailable` renders a gold "Update available" pill on the "Server Control" card (desktop) and the mobile MyServerCard
- [x] **Tooltip says stop/start, not restart** - the pill tooltip reads "A newer lab image is available locally - stop your server and start a new one to update"; a Docker restart reuses the existing container/image so it would NOT update
- [ ] **Runtime: pill clears after upgrade** - after stop/start onto the new image the running id == tag id -> pill disappears on the next `/activity` refresh

### Edge cases

- [x] **Edge: running image pruned/gone** - the running id is not inspectable/listed (rebuilt+pruned); pill still fires because the comparison never looks the running image up - it only needs the tag's current id and the running id (already held from the stats inspect)
- [x] **Edge: running the current tag** - running id == tag id -> no pill
- [x] **Edge: re-tag to older** - the lab tag points at an image that is NOT the repo's newest -> guard rejects -> no false pill
- [x] **Edge: docker unreachable** - snapshot is empty -> `tag_to_id.get(ref)` None -> no pill (conservative)
- [x] **Edge: container image id unknown** - stats returned no `image_id` -> no pill
- [ ] **Edge: pinned non-latest tag with a newer sibling tag** - operator pins `:3.8.5` while a newer `:latest`/`:3.9.0` exists; the pinned tag is not the repo's newest so no pill - acceptable, since a restart spawns the pinned tag, not the sibling

### API / functions

- `newer_lab_image_available(image_ref, container_image_id) -> bool` - resolves the ref, snapshots images, delegates to the pure helper
- `image_upgrade_available(latest_tag_id, container_image_id, newest_repo_id) -> bool` - pure: `latest_tag_id and container_image_id and latest_tag_id != container_image_id and latest_tag_id == newest_repo_id`
- `_image_snapshot_get() -> (tag_to_id, newest_id_by_repo)` - cached ~5min
- `_normalize_ref(image_ref) -> "repo:tag"` - implicit `:latest`, strips `@digest`
- `_parse_created(created) -> epoch float | None` - ISO-8601 string or epoch int

## Version Sync Across Subpackages

`make increment_version` bumps the patch version of the root project and every in-repo package baked into the hub image in lockstep, by setting the new version absolutely (not matching the old string) so a drifted subpackage is pulled back into sync rather than skipped.

- [x] **Root + three subpackages** - sets the version on `pyproject.toml`, `duoptimum-hub-web/pyproject.toml`, `duoptimum-hub-services/pyproject.toml`, `duoptimum-docker-proxy/pyproject.toml`, and `duoptimum-hub-web/package.json`
- [x] **Image packages only** - the three subpackages are exactly the wheels the hub image installs (Dockerfile lines 174-176); `duoptimum hub`, `jupyter hub services`, and `the other one` = docker-proxy
- [x] **gpuinfo-nvidia excluded** - the GPU-info sidecar is a separate image with its own version; intentionally not synced
- [x] **Absolute set fixes drift** - uses `s/^version = "[^"]*"$/.../` so hub-services (was 3.8.0) and any drifted package jump to the new root version, not just packages already in sync
- [x] **Single version line** - each pyproject has exactly one `[project] version` line and package.json one `"version"`, so the absolute sed touches only the intended line
- [x] **package-lock.json tracks the bump** - `increment_version` also rewrites the lockfile's own version (root `.version` + `packages[""].version`) so it never drifts from package.json; the image build runs `npm ci` (`Dockerfile.jupyterhub:61`) which aborts with EUSAGE on a package.json/lock version mismatch
- [x] **Edge: transitive deps named like the project version** - the lockfile holds many `"version"` lines; the bump targets only the first two (root + `packages[""]`, always the first two in lockfileVersion 3) so a transitive dep that happens to share the project version is not corrupted
- [x] **Edge: no helper script** - manifest set is an inline Make variable + a bash `for` loop in the recipe, no external script

## Volume Reset Confirmation

After an admin/user resets selected volumes, the panel reports what was done and offers a clean way back. The list paints volume names instantly with sizes filling in (see [acc-crit-resource-bars] for the names/sizes split). `duoptimum-hub-web/src/components/VolumeReset.tsx`, `pages/ManageVolumes.tsx`.

### After reset (same screen, no separate view)

- [x] **Stays on the volumes screen** - resetting does NOT switch to a separate confirmation view; the same table + buttons remain and the removed rows are marked in place
- [x] **"removed" in red, not a pill** - each removed volume reads "removed" in dangerous (red) text in its Size cell, never an antd Tag/pill
- [x] **Removed rows non-selectable** - a removed volume's checkbox is disabled so it cannot be re-selected; Reset re-disables when nothing is selected
- [x] **Irreversibility warning** - the top notice is a WARNING (not the info/activity "EKG" glyph) stating that removing volumes is irreversible - the selected volumes and all their contents are permanently deleted

### Close behaviour

- [x] **Cancel + Done footer** - the dedicated Manage-volumes page uses the standard config footer (Reset destructive on the left; Cancel + a primary Done on the right), matching Configure-user / Configure-group; both Cancel and Done leave the screen
- [x] **Returns to the true origin** - Cancel / Done return to where the screen was opened from per the nav-origin state - Home if opened from Home, Servers if opened from the Servers list - not a hardcoded /servers
- [x] **Edge: reached from the user-config Volumes tab vs the dedicated Manage-volumes page** - Close returns to whichever parent opened it (the tab keeps its own footer; the page returns to its origin), not a dead-end empty panel

### Audit

- [x] **Event logged on reset** - a successful reset records a `volume` event on the event log (`record_event`), surfaced in Recent events and on the Events page with the disk icon and a `warn` tone; hub log keeps its `[Manage Volumes]` lines too
- [x] **Event names actor and owner** - text names the actor; when an admin resets another user's volumes it names both ("<b>admin</b> reset <b>alice</b> volumes: home, workspace"), all HTML-escaped
- [x] **No UI notify** - the event log + hub log are the record; no extra toast/notification is sent on reset
- [ ] **Edge: all requested volumes already gone** - when nothing is actually removed (all not-found) no event is recorded

### Already in place (keep)

- [x] **Names instant, sizes fill in** - the table paints volume names at once and sizes show "updating..." then fill (split fast names / slow sizes)
- [x] **Reset gated on stopped server** - reset is disabled while the server runs (backend also rejects)
