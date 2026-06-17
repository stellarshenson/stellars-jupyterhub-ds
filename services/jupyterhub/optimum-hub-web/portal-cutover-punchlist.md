# Optimum Hub - portal cutover punch-list

Issues found in the pre-cutover sweep of the hub-served portal (`/hub/portal`). Three read-only critic passes (backend + hub wiring, frontend actions, build/packaging), cross-checked against the live JupyterHub 5.4.6 route table and NativeAuthenticator. Each item is `done` when fixed and re-verified.

Status: all blockers/highs/mediums/lows resolved on 2026-06-16 (frontend `tsc -b` + `eslint src/` clean; backend `py_compile` clean). The image rebuild (`make rebuild`) and cutover restart remain operator-gated. Severity: BLOCKER = wrong/broken at cutover; HIGH = breaks a real admin/user action or ships silently broken; MEDIUM = correctness/robustness; LOW = polish.

Scope note: the live deployment runs with `base_url=/` (via `compose_override.yml`); H1 made the portal base-agnostic so it also works under `/jupyterhub`. The cutover restart itself is a one-time disruption (the running hub still has `cleanup_servers=True`) - operational, not a code fix.

## Blockers

- [x] **B1 - Hardcoded mock usernames in live API calls** - `Home.tsx` pinned the admin hero to `'konrad'` and the user view to `'alice'`, so every signed-in user saw another identity's server. Fixed: both `AdminHome` and `UserHome` now read `const { username } = useRole()` and pass it to `useServerHero`/`useUser`/`useEffectiveGrants`. Swept all of `src/` - the only other `'alice'`/`'konrad'` literals are mock fixtures (`mockSource.ts`) and `Profile.tsx`'s mock branch (`live ? {username} : ...`)
  - log: 2026-06-16 fixed (Home.tsx:145,227); verified no other live leak
- [x] **B2 - Live datasource is admin-only (by design, now guarded)** - confirmed with the user: `getUsers`/`getServers`/`getStats` ARE admin-only data. The real gap was the absence of a route guard, so a non-admin typing `/hub/portal/users` mounted an admin page and hit an uncaught 403. Fixed by the admin route guard (see Admin gating below); those hooks only mount under admin routes, which non-admins can no longer reach
  - log: 2026-06-16 reclassified (not a bug) + closed via RequireAdmin guard

## Admin gating (explicit requirement)

- [x] **Admin role guard in the SPA** - new `RequireAdmin` wraps every admin route (`servers`, `users/*`, `groups/*`, `lab-container`, `events`, `notifications`, `settings/*`, `tokens`) in `router.tsx`; a non-admin is bounced to `/home` before any admin query mounts. `home`/`profile`/`design-*` stay open. Role resolves from the real session (`RoleContext.ready`) before children render, so no flash. Defense-in-depth only - the API is the real boundary
  - log: 2026-06-16 added (src/app/RequireAdmin.tsx, router.tsx)
- [x] **Server-side API enforcement verified** - audited every custom handler: `groups.py` (data/create/delete/config/reorder all check `current_user.admin`), `notifications.py` (page/active-servers/broadcast), `activity.py` (admin), `server.py`/`volumes.py` (`admin or self`), new `native_users.py` (admin). Stock hub endpoints enforce scopes. The API cannot be hit by an unauthorized user regardless of client
  - log: 2026-06-16 verified, no gaps

## High

- [x] **H1 - Portal is now base-agnostic** - was: baked `VITE_BASE=/hub/portal/` only worked under `base_url=/`. Confirmed no code-splitting and no module-imported assets, so only the router basename + API base + brand-logo URLs baked the prefix. Fixed: `client.ts` derives `HUB_ROOT`/`API_BASE` and exports `portalBasename()`/`portalAssetBase()` at runtime from `window.jhdata.base_url` (the hub prefix, per `BaseHandler.template_namespace` base.py:1462); `router.tsx` + the four brand-logo refs use them. Dev/mock falls back to the build-time base. One build now serves `/` and `/jupyterhub`
  - log: 2026-06-16 fixed (client.ts, router.tsx, AppLayout/Login/Signup); VITE_BASE now runtime-irrelevant
- [x] **H2 - Pending users surface in live mode** - added `GET /hub/api/native-users` (`native_users.py`, admin-only) listing every NativeAuth signup with `is_authorized`/`is_hub_user`. `liveSource.getUsers` merges it: hub users take `is_authorized` as authoritative, and unauthorized signups with no hub User row are appended as `pending:true`. PendingSection / PendingCallout now populate
  - log: 2026-06-16 fixed (native_users.py, config wiring, liveSource.ts)
- [x] **H3 - Idempotent authorize/de-authorize** - replaced the `/authorize/{name}` GET-toggle with `POST /hub/api/native-users/{name}/authorization` `{authorized}` (sets the target state directly, no-op if already there). `ops.setUserAuthorization(name, authorized)` replaces `authorizeUser` at all five call sites (Users switch + Authorize button, UserConfig, NewUser, BulkUsers), each passing the explicit boolean. A stale checkbox can no longer flip the wrong way
  - log: 2026-06-16 fixed (native_users.py, ops.ts, Users/UserConfig/NewUser/BulkUsers)
- [x] **H4 - Group priority direction made consistent** - server resolves higher-priority-wins (engine.py:15/20, sort `reverse=True`). `Groups.tsx` sorted ascending and the tooltip said "lower wins", contradicting the reorder math (top row = highest number). Fixed: list sorts descending and the tooltip says "higher number wins"; reorder math already matched
  - log: 2026-06-16 fixed (Groups.tsx)
- [x] **H5 - Build can no longer ship a manifest-less wheel green** - pinned `hatchling>=1.27,<2` (the `artifacts` glob that captures `.vite/manifest.json` is gitignore-semantics, so cap the major) and hardened the Docker smoke test to assert `_entry_assets()` returns a non-empty entry JS in the installed wheel - a missing manifest now fails the build instead of rendering a blank portal
  - log: 2026-06-16 fixed (pyproject.toml, Dockerfile smoke test)

## Medium

- [x] **M1 - NewUser create flow hardened** - the toggle-off after create is now a deterministic `setUserAuthorization(name, false)` (H3), removing the flip ambiguity. The create+password ordering still relies on the `create_user` override seeding `users_info` synchronously (events.py:68 inserts `is_authorized=1`), which is the documented behaviour; left as-is
  - log: 2026-06-16 partially fixed via H3; ordering left per existing override
- [x] **M2 - Manifest failure no longer silent or permanently cached** - `_entry_assets()` logs a warning on missing/invalid manifest or absent entry chunk and does NOT cache the failure, so a transient read error at first hit is recoverable without a hub restart; only a successful parse is cached
  - log: 2026-06-16 fixed (handlers.py)
- [x] **M3 - Assets no longer block the hub event loop** - `/hub/portal/assets/*` is served by `ImmutableStaticFileHandler` (subclass of Tornado `StaticFileHandler`: async sendfile, ETag/Range/304, immutable cache header), matched before the SPA catch-all. The multi-MB bundle is no longer read blocking via `open().read()` on every hit
  - log: 2026-06-16 fixed (handlers.py, __init__.py)
- [x] **M4 - Stale PLATFORM constants (mock-only)** - clarified: `jupyterhubVersion`/`baseUrl` are read only by `mockSource.ts`; live mode uses the real `/hub/api/info` fetch + settings handler, so they never mislead in live. Bumped the mock version to `5.4.6` and documented the mock-only scope
  - log: 2026-06-16 fixed/clarified (config.ts)
- [x] **M5 - encodeURIComponent on user paths** - `getSessionInfo`, `getUserVolumes`, and the tokens path now encode the username, matching the rest of the codebase
  - log: 2026-06-16 fixed (liveSource.ts)
- [x] **M6 - Dead enhanced admin.html dropped** - the 1100-line enhanced `admin.html` (only template referencing the removed `admin-react.js`) is permanently shadowed by the wheel's redirect stub; the Dockerfile now `rm`s it from `/srv/jupyterhub/templates/` so no image template references the removed bundle
  - log: 2026-06-16 fixed (Dockerfile)
- [x] **M7 - admin-react.js removal fails loudly** - the Dockerfile now asserts the stock bundle exists before removing it (`if [ ! -f ... ]; then exit 1`), so an upstream path move fails the build instead of silently shipping the stock admin app
  - log: 2026-06-16 fixed (Dockerfile)

## Low

- [x] **L1 - XSRF-on-GET comment corrected** - `client.ts` header now states GET/HEAD/OPTIONS are XSRF-exempt (`_xsrf_safe_methods`) and the header on GETs is inert-but-harmless, kept for uniformity
  - log: 2026-06-16 fixed (client.ts)
- [x] **L2 - Version single source** - `package.json` aligned to `0.1.0`; `__version__` now reads `importlib.metadata.version("optimum-hub-web")` (the wheel/pyproject version) with a fallback
  - log: 2026-06-16 fixed (package.json, __init__.py)
- [x] **L3 - engines field** - added `"engines": {"node": ">=20"}`
  - log: 2026-06-16 fixed (package.json)
- [x] **L4 - rebuild cache scope** - documented: `make rebuild BUILD_OPTS=--no-cache` forces the webbuilder/wheel stages for release builds (content-hash cache covers normal edits)
  - log: 2026-06-16 noted (existing knob)
- [x] **L5 - Stale artifacts cleared** - removed local `dist/`, `dist-wheel/`, `build/`, generated `optimum_hub_web/static/`; `make clean` already covers these. Docker regenerates them in the webbuilder stage
  - log: 2026-06-16 cleared
- [x] **L6 - admin_access is not an authz boundary** - confirmed: `RequireAdmin` gates on `role` (reconciled from the real `/hub/api/user` admin flag, not `admin_access` alone), and all data is server-enforced. `admin_access` is only a UI seed/hint
  - log: 2026-06-16 verified

## Operational (not code)

- [ ] **OP1 - Cutover restart stops running labs once** - `config/jupyterhub_config.py:699` sets `cleanup_servers=False`, but the currently-running hub started with `True`, so the cutover restart tears down active containers one time (volumes persist). Schedule when Natalia is off; notify users
  - log: 2026-06-16 noted (jupyterhub_config.py:699)
- [x] **OP2 - eslint no longer scans the generated bundle** - added `optimum_hub_web/static`, `dist-wheel`, `test-results`, `playwright-report` to the eslint flat-config ignores; `npm run lint` is now clean (exit 0) and stays clean after `make assets`
  - log: 2026-06-16 fixed (eslint.config.js)
