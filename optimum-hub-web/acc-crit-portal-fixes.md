# Acceptance Criteria - Optimum Hub portal de-mock + fixes

Master fix-list for the autonomous sweep that makes the hub-served portal fully wired and free of mocks. Detail/evidence per action lives in `portal-action-audit.md`; this file tracks each fix to done. `[x]` = implemented + tsc/eslint (or py_compile/tests) clean; `[ ]` = pending. Final runtime verification needs an image rebuild (operator).

## Round 2 - operator punch-list (2026-06-16)

Reroute the reset-volumes action to a dedicated page, make every server widget state-aware, make group priority a true contiguous rank with up/down + set-position controls, and surface real per-GPU utilisation sampled from a CUDA subcontainer.

### BLOCKER: stale nginx mock portal shadows the live portal

Root cause of "everything is mock": a leftover standalone container `optimum-hub-portal` (`nginx:alpine`, compose project `deploy`, file `mock-antd/deploy/compose.portal.yml`) is still running and serving the **old mock build**. Its Traefik router (`portal-rtr`, priority 1000) claims `Host(jupyterhub.lab.stellars-tech.eu) && PathPrefix(/portal)`. Visiting `/portal` therefore hits the retired mock SPA, not the hub-served live portal at `/hub/portal`. Proof: the nginx bundle contains the mock banner string "every action is simulated" (mock build) with the old wording "data is pulled live from the hub"; the hub-baked bundle tree-shakes that string out (live build, `isMock()` statically false).

- [ ] **Retire the nginx /portal container** - `docker compose -f mock-antd/deploy/compose.portal.yml down` (removes the mock container + its `/portal` Traefik route); the live portal stays at `/hub/portal` (hub `default_url`)
  - log: 2026-06-16 diagnosed; teardown is a deployment action - operator-gated
- [ ] **Delete the obsolete deploy assets** - remove `mock-antd/deploy/compose.portal.yml` + `nginx.conf` once teardown confirmed (plan's "Retire" step)
  - log: 2026-06-16 criterion added
- [ ] **Single portal URL** - after teardown, `/portal` 404s (or redirects); the only portal is the hub-served live one
  - log: 2026-06-16 criterion added

### Server lifecycle popups (start / restart / stop)

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

### TTL gadget - drain bar + working Extend

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

### Dedicated reset-volumes page

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

### Server widgets - state-aware actions (Home ServerHero + Servers table)

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

### Save user / group -> confirm + return to list

- [x] **Save user returns** - saving in Configure-user shows a success confirmation (per-write toasts) and navigates to the Users list
  - log: 2026-06-16 fixed (UserConfig.save -> navigate('/users'))
- [x] **Save group returns** - saving in Configure-group shows a success confirmation and navigates to the Groups list
  - log: 2026-06-16 fixed (GroupConfig.save -> navigate('/groups'))
- [x] **Edge: save error** - on failure stay on the form with the error, do not navigate
  - log: 2026-06-16 fixed (navigate only after the try-body completes)

### Groups list - contiguous priority rank

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

### Real per-GPU utilisation

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

### Native login + signup served as the antd portal

Today the hub renders the stock NativeAuth `login.html` / `signup.html`; the portal's own `Login.tsx` / `Signup.tsx` are unused. Turn the stock pages off and serve the antd screens, wired to NativeAuth's real POST endpoints. Larger change - touches the public (unauthenticated) serving path, so it needs its own handler (the portal handler is `@authenticated`).

- [x] **antd login screen** - `/hub/login` renders the antd Login, served by a new `OptimumHubAuthenticator`. (First attempt overrode `login.html`, but NativeAuth's `LoginHandler._render` renders `native-login.html` and the enhanced stock copy won the template path - so the override never took.) The authenticator swaps the login handler to render uniquely-named `optimum_login.html` (`window.jhdata.authPage='login'`); `main.tsx` renders `AuthApp` instead of the router app. Verified live: `<title>Sign in - Optimum Hub</title>`, antd form renders, zero console errors
  - log: 2026-06-16 fixed + verified live (auth.py OptimumHubAuthenticator/OptimumLoginHandler, optimum_login.html, AuthApp.tsx, main.tsx); rebuilt + restarted + Playwright against the live URL green
- [x] **antd signup screen** - `OptimumSignUpHandler` renders uniquely-named `optimum_signup.html` (`authPage='signup'`); `BootstrapAdminSignUpHandler` rebased onto it so the bootstrap-admin flow is antd too. Live `/hub/signup` currently 404s because `JUPYTERHUB_SIGNUP_ENABLED=0` (signup disabled, handler 404s before render) - correct; renders antd when signup is enabled
  - log: 2026-06-16 fixed (auth.py OptimumSignUpHandler, optimum_signup.html, config bootstrap rebase); wiring confirmed in the running hub
- [x] **Real login POST** - the antd form does a native browser POST of `username`/`password`/`_xsrf` to `{base}hub/login?next=…` (NativeAuth login logic unchanged - lockout-safe), redirecting on success
  - log: 2026-06-16 fixed (AuthApp postForm)
- [x] **Real signup POST** - native POST of `username`/`signup_password`/`signup_password_confirmation`/`email`/`_xsrf` to `{base}hub/signup` (exact NativeAuth field names); the re-rendered `result_message`+`alert` surface as an antd notice
  - log: 2026-06-16 fixed (AuthApp + signup.html passes result_message/alert into jhdata)
- [x] **Public serving** - login/signup load the bundle + logo unauthenticated: brand assets get a public route (`/portal/brand/*`), assets are already public, the templates are served by NativeAuth's own (public) handlers
  - log: 2026-06-16 fixed (__init__ BRAND_ROUTE; entry chunk via template_vars optimum_entry_js/css)
- [x] **Errors** - failed login shows `login_error`; signup shows the NativeAuth `result_message`; both rendered as an antd Alert/Notice in the form
  - log: 2026-06-16 fixed (AuthApp reads authError/authMessage/authAlert)
- [x] **Lockout safety** - each template includes a `<noscript>` stock fallback form posting to the same endpoint, so a bundle/JS failure can never block login
  - log: 2026-06-16 fixed (login.html/signup.html noscript)
- [ ] **Edge: bootstrap admin window** - first-admin signup through the antd screen - verify by enabling signup (NativeAuth logic unchanged via OptimumSignUpHandler, so expected to work)
- [ ] **Edge: logout** - logout returns to the antd login - verify in a browser session
- [x] **Runtime verify (login)** - deployed; live Playwright confirms the antd sign-in renders with no console errors
  - log: 2026-06-16 verified live after rebuild + restart

### Functional E2E harness - needs porting to the portal

- [ ] **Port `tests/functional/` to the antd portal** - the harness (`test_hub_ui.py`, `test_scenarios.py`, etc.) drives the OLD stock admin UI (`/hub/groups` with `#add-group-modal`, `.btn-config`, `.btn-move-up`, `input[name='username']`) which the portal REPLACED. Running it as-is yields wholesale false negatives. Rewrite the specs against the antd portal (`/hub/portal/*` routes, antd selectors / `get_by_role`, the new `optimum_login` sign-in) before it can gate cutover
  - log: 2026-06-16 criterion added - harness obsolete vs portal; not run (would mislead)

### Groups members tooltip

- [x] **Members tooltip** - hovering the Groups list Members count shows the member names
  - log: 2026-06-16 fixed (Groups.tsx Tooltip; GroupRow.memberNames from backend `members`)
- [x] **Cap at 10** - more than 10 members shows the first 10 then "+N more"
  - log: 2026-06-16 fixed (slice(0,10) + "+N more")
- [x] **Wrap nicely** - the tooltip wraps (normal white-space, break-word, maxWidth 320) rather than one long line
  - log: 2026-06-16 fixed (Groups.tsx tooltip styles)
- [x] **Edge: no members** - tooltip reads "No members"
  - log: 2026-06-16 fixed

### Round 2 - small polish

- [x] **Users default filter = All** - the Users list scope defaults to "All", not "Authorized"
  - log: 2026-06-16 fixed (Users.tsx)
- [x] **Effective-policy / catalogue chips blue** - group-policy tags render in accent blue, not gray (confirmed already accent in `CappedTags`; the gray seen was the stale mock /portal)
  - log: 2026-06-16 verified (CappedTags accent=true default)
- [x] **Users list refresh after delete** - deleting a user invalidates `['users']` so the list drops the row (confirmed `deleteUser` -> `USER_KEYS` already includes `['users']`; the stale row seen was the mock /portal's static fixture)
  - log: 2026-06-16 verified (ops.ts deleteUser invalidation)

### Performance + persistent cache

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

### Round 2 API

- `GET /servers/:name/volumes` - frontend route only; reuses existing `GET /users/{name}/manage-volumes` + `DELETE .../manage-volumes`
- `POST /admin/groups/reorder` - existing; now called after create / delete / move / set-position with a full contiguous `[{name, priority}]`
- `GET /activity` `gpus[]` - add `utilization:int` (+ `memory_used_mb:int`) per device, sampled + cached

## Done (frontend, validated)

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

## Frontend - wire to existing backend (no hub change)

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

## Frontend - decide: wire or remove (currently mock, no real backend)

- [x] **Require-password-change switch** - removed; it was an unbound, unwireable control (NativeAuth has no forced-change flag) that misled admins into thinking it did something
  - log: 2026-06-16 removed (UserConfig.tsx)
- [ ] **Spawn-log tail / activity-report** - remove buttons or build endpoints (Servers)
- [ ] **Lab Container image pull / add-remove mount** - remove or build endpoints
- [ ] **Groups import JSON** - wire (parse + create) or remove
- [ ] **Language switch** - apply real i18n or remove the control

## Backend additions needed

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

## API (new/changed endpoints)

- GPU inventory: delivered inside the existing `GET /activity` payload as `gpus:[{index,name,memory_mb}]` (admin) - no separate endpoint; reuses the startup-cached `gpu_list`
- `GET|PUT /api/users/{name}/profile` -> `{username,first_name,last_name,email}` (admin or self) - DONE
- Lab Container: delivered inside the existing `GET /activity` payload as `lab_image` + `lab_volumes:[{suffix,mount,description}]` (admin) - no separate endpoint
- `GET /api/settings` -> `{settings:[{category,name,value,description}]}` (admin, read-only) - DONE; no write API (running env not runtime-writable)
- existing, to consume: `GET /api/notifications/active-servers`; `PUT /api/admin/groups/{name}/config` (full body)

## Notes

- The backend group-policy model (`groups_config.py` + `policy/registry.py`) already supports full read+write for all nine sections; the gap is purely the React data layer
- A live GPU inventory already exists (`gpu.py::enumerate_gpus` -> `stellars_config['gpu_list']`); it is just never exposed to the portal
