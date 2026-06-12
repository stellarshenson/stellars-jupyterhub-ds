# Acceptance Criteria - Group-Gated File Downloads

Best-effort, hub-side blocking of browser file downloads from spawned labs. A platform master switch (`JUPYTERHUB_BLOCK_FILE_DOWNLOADS`) turns it on; a per-group `downloads_active` flag grants members an exemption (any granting group wins). For a blocked user, `pre_spawn_hook` overlays per-user CHP routes (favicon-route mechanism) onto the lab's download surfaces, sending them to hub guard handlers that 403 genuine downloads and reverse-proxy inline content. Every block fires a throttled "blocked by policy" toast and an audit log line. This is policy + notification + audit, NOT exfiltration prevention - the lab user is root with open egress, so a terminal/kernel transfer over an encrypted channel is out of reach by design.

## Platform setting

- [x] **Master switch** - `JUPYTERHUB_BLOCK_FILE_DOWNLOADS` (`0`/`1`, default `0`); `0` = dormant, no routes/handlers registered, zero change for existing deployments
  - log: 2026-06-12 implemented (v3.11.5) - read in `config/jupyterhub_config.py`, threaded into `make_pre_spawn_hook` and `schedule_startup_downloads_callback`
- [x] **Settings page** - listed in `settings_dictionary.yml` (Abuse Protection category) so it shows on the admin Settings page
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Startup log** - hub prints the policy state (BLOCK/ALLOW) once at config load
  - log: 2026-06-12 implemented (v3.11.5)

## Group config (admin)

- [x] **Section** - foldable "File Downloads" section in the group modal with header switch `config-downloads-active` (default off), following the `*_active` section pattern
  - log: 2026-06-12 implemented (v3.11.5) - `groups.html`
- [x] **Persistence** - `downloads_active` in `default_config()` (False); legacy rows default off (no inference - it is a grant, not a section gate, so absent = not granted)
  - log: 2026-06-12 implemented (v3.11.5) - `groups_config.py`
- [x] **API accept** - `GroupsConfigHandler.put` accepts the boolean `downloads_active` body key
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Badge** - groups table shows a `Downloads` badge when `downloads_active` is on
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Resolver grant** - `resolve_group_config` returns `downloads_allowed` True iff ANY of the user's groups has `downloads_active` (OR across groups); no groups / all off -> blocked
  - log: 2026-06-12 implemented (v3.11.5) - `group_resolver.py`, covered by `TestDownloadsAllowed`
- [x] **No admin exemption** - admins are blocked like any user unless in a granting group (no implicit bypass)
  - log: 2026-06-12 implemented (v3.11.5) - confirmed with operator

## Enforcement (hub overlay)

- [x] **Vector inventory** - verified against the deployed image: block surfaces are `files/` (download-param), `nbconvert/` (download-param), `jupyterlab-export-markdown-extension/export/` (POST, always attachment), `jupyterlab-share-files-extension/public/share/` (GET, unauthenticated public link). Not vectors: export-svg-as-png (client-side), jupyterlab_zip (POST create only), jupyter-archive (absent)
  - log: 2026-06-12 implemented (v3.11.5) - probed inside the running container source
- [x] **Route overlay** - for blocked users `pre_spawn_hook` registers one CHP route per surface to the hub, recorded in `app.proxy.extra_routes` so `check_routes()` does not reap them
  - log: 2026-06-12 implemented (v3.11.5) - `hooks.py` `_register_download_block`
- [x] **Survivor re-registration** - `schedule_startup_downloads_callback` re-applies block routes for labs still running after a hub restart
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Grant change removes routes** - a user resolved as allowed has any stale block routes deleted on next spawn (`_unregister_download_block`); symmetric add/remove
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Exempt = no overlay** - granted users get no routes; traffic flows browser -> CHP -> container with zero added hops
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Pure-download block** - `DownloadBlockHandler` 403s the export-markdown and share-files prefixes unconditionally (no auth, so it also blocks the unauthenticated public share link); GET/POST/HEAD
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Download-intent block** - `FilesGuardHandler` 403s `files/`/`nbconvert/` when the `download` query arg is truthy (the only trigger for `Content-Disposition: attachment` on these paths, verified in jupyter_server source)
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Inline pass-through** - non-download `files/`/`nbconvert/` requests reverse-proxy to the container, forwarding the `Range` header and relaying the container's status/headers/body (markdown images, file/PDF viewers keep working)
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Defense in depth** - if a proxied inline response unexpectedly carries `Content-Disposition: attachment`, it is converted to a 403 before any body reaches the client
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Owner isolation** - `FilesGuardHandler` is `@web.authenticated` and requires owner-or-admin, so proxying user content through the hub never crosses users
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Block response** - 403 with an HTML page for top-level navigation (Accept: text/html), JSON `{"error":"downloads_blocked"}` otherwise
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Audit log** - every block logs username, path, and the trigger (`via=pure-download|download-arg|attachment-header`)
  - log: 2026-06-12 implemented (v3.11.5)

## Must not break

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

## Notification

- [x] **Toast on block** - hub pushes a warning toast to the blocked user's lab via the notifications-extension ingest endpoint (temp 5-min token), naming the file
  - log: 2026-06-12 implemented (v3.11.5) - `notify_blocked` reuses the broadcast pattern
- [x] **Fire and forget** - notification is scheduled on the IO loop and never delays or alters the 403
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Throttle** - at most one toast per user per 10 s; further blocks in the window are counted and the next toast carries the aggregate ("N downloads blocked")
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Extension absent / server down** - block is still enforced; notify failure is logged and swallowed
  - log: 2026-06-12 implemented (v3.11.5)

## Lifecycle

- [x] **Group change** - adding/removing a user from a granting group, or toggling `downloads_active`, takes effect at the user's next server start
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Feature toggle** - flipping the master switch requires a hub restart; the survivor callback applies the new state to running labs (master off -> `check_routes()` reaps leftover routes since they are no longer in `extra_routes`)
  - log: 2026-06-12 implemented (v3.11.5)

## Edge cases

- [x] **Edge: user in no groups** - blocked when the master switch is on
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: multiple groups, one granting** - allowed; any granting group wins
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: `?download=0` / falsy** - not treated as a download; passes through (`_is_download_arg`)
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: burst of blocked clicks** - one throttled toast, not a storm
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: master switch off** - no routes, no handlers; downloads work for everyone regardless of group config
  - log: 2026-06-12 implemented (v3.11.5)
- [ ] **Edge: group deleted while member's lab runs** - lab keeps spawn-time behaviour until restart, then resolves as blocked
  - log: 2026-06-12 criterion holds by construction (routes set at spawn / survivor callback); not separately tested

## Tests

- [x] **Resolver tests** - `TestDownloadsAllowed`: no groups -> blocked, explicit false -> blocked, one granting -> allowed, OR across groups, only-matched-groups-count
  - log: 2026-06-12 implemented (v3.11.5) - `tests/test_group_resolver.py`
- [x] **Discriminator tests** - `TestIsDownloadArg` / `TestFilenameFromPath` cover the block/allow decision and toast naming
  - log: 2026-06-12 implemented (v3.11.5) - `tests/test_downloads_guard.py`
- [ ] **Live end-to-end** - post-restart probe as `konrad.jelen`: download-arg -> 403 + toast + audit, inline -> 200 via proxy, export-markdown POST -> 403, granting group -> downloads succeed; contents API / kernels / terminals unaffected
  - log: 2026-06-12 pending operator-initiated hub rebuild/restart

## Documentation

- [x] **README** - Groups section documents the File Downloads switch and the master env var; states it is browser-download policy with notification, not full DLP
  - log: 2026-06-12 implemented (v3.11.5)

## Out of scope

- Exfiltration via terminal/kernel egress, `git push`, the contents API, or any encrypted channel - structurally unblockable while the lab stays usable (root + sudo + needed egress)
- Upload blocking; per-path or per-filetype allowlists; named servers (one server per user here)

## API

- Blocked vectors (blocked users, master on): `GET|HEAD /user/{u}/files/*?download=<truthy>`, `GET|HEAD /user/{u}/nbconvert/*?download=<truthy>`, `POST /user/{u}/jupyterlab-export-markdown-extension/export/*`, `GET /user/{u}/jupyterlab-share-files-extension/public/share/*` -> `403` (HTML or `{"error":"downloads_blocked"}`); inline `files/`/`nbconvert/` -> proxied 200/206
- `PUT /hub/api/admin/groups/{group}/config` body gains optional boolean `downloads_active`
- Env: `JUPYTERHUB_BLOCK_FILE_DOWNLOADS` (`0`/`1`, default `0`)
