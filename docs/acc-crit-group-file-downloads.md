# Acceptance Criteria - Group-Gated File Downloads

Best-effort, hub-side blocking of browser file downloads from spawned labs. Section-gated and priority-wins: a group whose File Downloads section (`downloads_active`) is on explicitly configures member downloads to allow or block (`downloads_allow`); among a user's configuring groups the highest-priority one wins; if no group configures it, the platform default `JUPYTERHUB_BLOCK_FILE_DOWNLOADS` applies. For a blocked user, `pre_spawn_hook` overlays per-user CHP routes (favicon-route mechanism) onto the lab's download surfaces, sending them to hub guard handlers that 403 genuine downloads and reverse-proxy inline content. Every block fires a throttled "blocked by policy" toast and an audit log line. This is policy + notification + audit, NOT exfiltration prevention - the lab user is root with open egress, so a terminal/kernel transfer over an encrypted channel is out of reach by design.

## Platform setting

- [x] **Default policy** - `JUPYTERHUB_BLOCK_FILE_DOWNLOADS` (`0`/`1`, default `0`) is the fallback applied only when no group configures downloads; dormant (no routes/handlers) when the default is allow AND no group configures it - zero change for existing deployments
  - log: 2026-06-12 implemented (v3.11.5) - read in `config/jupyterhub_config.py`, threaded into `make_pre_spawn_hook` and `schedule_startup_downloads_callback`
  - log: 2026-06-12 reworked to default-fallback (section-gated/priority-wins) - a configuring group overrides it and can block even when default is allow
- [x] **Settings page** - listed in `settings_dictionary.yml` (Abuse Protection category) so it shows on the admin Settings page
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Startup log** - hub prints the policy state (BLOCK/ALLOW) once at config load
  - log: 2026-06-12 implemented (v3.11.5)

## Group config (admin)

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

## Enforcement (hub overlay)

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

- [x] **Group change** - adding/removing a user from a configuring group, or toggling `downloads_active`/`downloads_allow`, takes effect at the user's next server start
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Feature toggle** - flipping the platform default requires a hub restart; the survivor callback applies the new state to running labs (dormant default off + no configuring group -> `check_routes()` reaps leftover routes since they are no longer in `extra_routes`)
  - log: 2026-06-12 implemented (v3.11.5)

## Edge cases

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

## Tests

- [x] **Resolver tests** - `TestDownloadsAllow`: no group configures -> None, section-off -> None, single allow/block, higher-priority wins, higher-off+lower-on decides, only-matched-groups-count
  - log: 2026-06-12 reworked to tri-state priority-wins - `tests/test_group_resolver.py`
- [x] **Discriminator tests** - `TestIsDownloadArg` / `TestIsDownloadRequest` / `TestFilenameFromPath` cover the block/allow decision and toast naming; `TestIsDownloadRequest` asserts inline dests allowed, empty/document/absent blocked, `?download` wins
  - log: 2026-06-12 implemented (v3.11.5) - `tests/test_downloads_guard.py`
  - log: 2026-06-12 added `TestIsDownloadRequest` for the `Sec-Fetch-Dest` discriminator (build-gated by the Dockerfile pytest step)
- [ ] **Live end-to-end** - post-rebuild probe as `konrad.jelen`: Download button (`<a download>`, no arg) -> 403 + toast + audit, `?download=1` -> 403, open-in-tab -> 403, inline markdown image -> 200 via proxy, export-markdown POST -> 403, granting group -> downloads succeed; contents API / kernels / terminals unaffected
  - log: 2026-06-12 pending operator-initiated hub rebuild (Playwright already confirmed the per-vector `Sec-Fetch-Dest` values the discriminator keys off)

## Documentation

- [x] **README** - Groups section documents the File Downloads switch, the allow/block value, the priority-wins/default-fallback rule, and the platform default env var; states it is browser-download policy with notification, not full DLP
  - log: 2026-06-12 implemented (v3.11.5)

## Out of scope

- Exfiltration via terminal/kernel egress, `git push`, the contents API, or any encrypted channel - structurally unblockable while the lab stays usable (root + sudo + needed egress)
- Upload blocking; per-path or per-filetype allowlists; named servers (one server per user here)

## API

- Blocked vectors (blocked users): `GET|HEAD /user/{u}/files/*` and `/nbconvert/*` when `?download` is truthy OR `Sec-Fetch-Dest` ∈ {`empty`, `document`, absent}, `POST /user/{u}/jupyterlab-export-markdown-extension/export/*`, `GET /user/{u}/jupyterlab-share-files-extension/public/share/*` -> `403` (HTML or `{"error":"downloads_blocked"}`); inline `files/`/`nbconvert/` with a media `Sec-Fetch-Dest` -> proxied 200/206
- `PUT /hub/api/admin/groups/{group}/config` body gains optional booleans `downloads_active`, `downloads_allow`
- Env: `JUPYTERHUB_BLOCK_FILE_DOWNLOADS` (`0`/`1`, default `0`) - platform default when no group configures
