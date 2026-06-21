# Portal UI Catalogue - JupyterHub Hub

Complete functional inventory of every hub-side screen, action, capability, modal, message, navigation path and dynamic behaviour. Purpose: a single source of truth for a future complete portal rebuild. Scope is the hub portal only (no JupyterLab UI). Fidelity is functional - routes, actions, endpoints, states, conditionals - not CSS, DOM structure or class names.

> [!NOTE]
> Historical document. The rebuild this catalogue specified is complete: the React portal SPA now owns every user/admin journey and `html_templates_enhanced/` (all templates + `custom.css` + `session-timer.js` + `mobile.js`) has been eliminated (#419). The few pages JupyterHub still renders fall back to plain stock JupyterHub/NativeAuth. The screen-by-screen inventory below describes the now-removed layer and is retained as the rebuild record.

Current source of truth: the React SPA `services/jupyterhub/duoptimum-hub-web/src/`; hub-side handlers `services/jupyterhub/duoptimum-hub-services/duoptimum_hub_services/handlers/*.py`, `services/jupyterhub/conf/bin/custom_handlers.py`, `config/jupyterhub_config.py`. The legacy `html_templates_enhanced/*.html` layer catalogued below has been removed.

## Global layer

Shared across every page via the `page.html` base template; each screen below inherits all of it.

### Base template (page.html)

- **Inheritance** - every screen does `{% extends "page.html" %}`; provides nav bar, script/style loads, announcement bar, global error modal, blocks children fill (header, stylesheet, scripts)
- **Reusable modal macro** - `modal(title, btn_label, btn_class)` defines the standard confirm-dialog shell children reuse
- **Favicon injection** - `favicon_uri` template var (empty -> stock; `file://` -> copied to static; `http(s)://` -> passthrough)
- **Logo injection** - logo served via `/logo` route; nav brand links to `logo_url or base_url`
- **Version badges** - `stellars_version`, `server_version` exposed to all templates
- **Announcement bar** - `announcement` (hub-wide) or page-specific override rendered as a safe-HTML warning band when set

### Navigation map

Top nav, gated by auth and role; mobile collapses to a reduced inline set.

- **Anonymous** - login link only (plus theme toggle)
- **Any logged-in user** - Home (`/hub/home`), Token (`/hub/token`), Change Password (`/hub/change-password`), Logout
- **Admin-only** - Admin (`/hub/admin`), Authorize Users (`/hub/authorize`), Activity (`/hub/activity`), Notifications (`/hub/notifications`), Settings (`/hub/settings`), Groups (`/hub/groups`)
- **Services** - dropdown listing each configured service `href` (when services present)
- **Visibility source** - admin items gated by `'admin-ui' in parsed_scopes` (server-side role)
- **Active state** - each routed page marks its own matching nav item; base template sets none
- **Theme toggle** - dark/light switch in nav (desktop + mobile variants)

### Branding system

- **Env vars** - `JUPYTERHUB_BRANDING_STAGE`, `JUPYTERHUB_BRANDING_LOGO_URI`, `JUPYTERHUB_BRANDING_FAVICON_URI`, `JUPYTERHUB_BRANDING_FAVICON_BUSY_URI`, `JUPYTERHUB_BRANDING_LAB_MAIN_ICON_URI`, `JUPYTERHUB_BRANDING_LAB_SPLASH_ICON_URI`, `JUPYTERHUB_BASE_URL`
- **Resolution** - startup branding setup processes each URI: `file://` copied into the static dir, `http(s)://` passed through, empty falls back to stock JupyterHub assets
- **Lab icons** - main/splash icon URIs passed into spawner env (`JUPYTERLAB_LAB_MAIN_ICON_URI`, `JUPYTERLAB_LAB_SPLASH_ICON_URI`) for the lab to consume
- **Favicon CHP proxy** - when favicon URI set, hub registers per-user CHP routes so lab sessions also serve the custom favicon; registered at startup for surviving servers and in `pre_spawn_hook` for new spawns; busy-state favicon proxied separately when `FAVICON_BUSY_URI` set

### Global client behaviour

- **Dark mode** - theme persisted in `localStorage` (`jupyterhub-bs-theme`); falls back to OS `prefers-color-scheme`; toggled via nav buttons; applied via `data-bs-theme` on the document
- **Shared state** - `window.jhdata` exposes `base_url`, `prefix`, `user`, `admin_access`, `options_form`, `xsrf_token` (the XSRF token used on all API calls)
- **Global error modal** - a single AJAX error dialog populated by API failure handlers
- **No global toast system** - feedback is modals + inline alerts only

### Mobile layer (mobile.js)

- **Device detection** - user-agent regex plus viewport/touch heuristic sets `data-device=mobile|desktop`; CSS shows/hides per device (functional toggle, not restyle)
- **Mobile home controls** - intercepts Start (`POST /api/users/{user}/server`) and Stop (`DELETE /api/users/{user}/server`), reloads on completion
- **Server status strip** - online/connection-lost/offline dot + label, uptime counter from spawner start time updated each minute
- **Health polling** - polls `/api/users/{user}` every 15s, reacts to browser online/offline events
- **Mobile activity monitor** - admin-only inline card list on home, polls `/api/activity` every 10s, sorted active -> idle -> offline
- **Mobile activity page** - full card rendering of `/activity` for small screens

### Session timer (session-timer.js)

- **Init** - `SessionTimer.init({username, baseUrl, getCookie})` called from home when idle culler enabled and server active
- **Polling** - fetches `/api/users/{user}/session-info` on init and every 5 min; local countdown ticks each minute
- **Display** - progress bar with green->yellow->red interpolation; hides itself when culler disabled or server inactive
- **Extend (desktop)** - modal with an hours field bounded by available extension hours -> `POST /api/users/{user}/extend-session`
- **Extend (mobile)** - inline slider panel, same endpoint
- **Feedback** - inline success/warning alert, auto-dismiss (1.5s success / 2.5s truncated), refetches info after extend

## Auth and landing screens

### Login (`/hub/login`)

- **Purpose** - native username + password sign-in
- **Actions** - form POST to the authenticator login URL; on success redirect to `next` or default URL
- **Inputs** - `username`, `password`, optional `otp` (when authenticator requests it), `_xsrf`
- **Conditionals** - OAuth login button replaces the form when `login_service` set; terms checkbox required when a terms URL is configured; insecure (HTTP) warning revealed by JS when context not secure
- **Messages** - `login_error` on failed auth; HTTP-insecure warning
- **Navigation** - signup link (when signup enabled) -> `/hub/signup`
- **Dynamic** - submit disables button + shows spinner; JS detects insecure context

### Native login (NativeAuthenticator variant)

- **Purpose** - native sign-in with password-visibility toggle and optional 2FA
- **Actions** - form POST to `login_url?next=...`; eye button toggles password visibility
- **Inputs** - `username` (autofocus), `password` (toggleable), optional `2fa`, `_xsrf`
- **Conditionals** - 2FA field when two-factor enabled; signup link when `enable_signup`; HTTP warning via JS
- **Messages** - `login_error`; HTTPS warning on HTTP

### Signup (`/hub/signup`)

- **Purpose** - self-registration, gated by `JUPYTERHUB_SIGNUP_ENABLED` or the bootstrap window
- **Actions** - form POST to signup handler; eye toggle on both password fields; terms checkbox disables submit until checked; optional reCAPTCHA
- **Inputs** - `username` (required, autofocus), optional `email`, `signup_password` + confirmation, optional `2fa` checkbox, optional `tos_check`, `_xsrf`
- **Conditionals** - email field when `ask_email`; 2FA setup when enabled; terms checkbox when configured; result banner; generated 2FA backup code shown on success; HTTP warning
- **Messages** - success/error result banner; 2FA backup code on success
- **Navigation** - login link -> `/hub/login`
- **Bootstrap window** - on a fresh DB with signup disabled and no env admin password, a one-shot window opens that accepts only the `JUPYTERHUB_ADMIN` username so the first admin can self-register; closes permanently once the admin row exists
- **Dynamic** - eye toggles both password fields together; terms checkbox enables submit; reCAPTCHA script when configured

### Change password - self (`/hub/user/{username}/change-password`)

- **Purpose** - authenticated user changes own password
- **Actions** - form POST to change-password handler; eye toggle on all three fields
- **Inputs** - `old_password`, `new_password`, `new_password_confirmation`, `_xsrf`
- **Messages** - success/error result banner
- **Dynamic** - eye toggles all three fields together

### Change password - admin override (`/hub/change-password/{username}`)

- **Purpose** - admin resets a user's password without the old password
- **Actions** - form POST to change-password handler with admin override; eye toggle
- **Inputs** - `new_password`, `new_password_confirmation`, `_xsrf`
- **Conditionals** - admin-only; result banner after submit
- **Messages** - reset success/error

### Authorization area (`/hub/authorize`)

- **Purpose** - admin approves/rejects pending signups and toggles authorization
- **Actions** - per-row links: Authorize/Unauthorize (`/authorize/{user}`), Change Password (`/change-password/{user}`), Discard (`/discard/{user}`, only for not-yet-active users)
- **Inputs** - none (link-driven)
- **Conditionals** - admin-only; authorized rows highlighted; Discard hidden when the username already exists as a hub user; email column when signup collects email; button label flips Authorize/Unauthorize by state
- **Dynamic** - none (server-rendered table)

### OAuth authorization (`/hub/oauth_authorize`)

- **Purpose** - user consents to an OAuth client (notebook server or external app)
- **Actions** - form POST submits the pre-selected scopes + `_xsrf`
- **Inputs** - `_xsrf`, hidden `scopes`, disabled display-only scope checkboxes
- **Conditionals** - scopes listed read-only (cannot deselect)
- **Navigation** - success redirects to the client `redirect_uri`

### Accept share (`/hub/accept-share?code=...`)

- **Purpose** - user accepts an invitation to access another user's shared server
- **Actions** - form POST submits the invite `code` + `_xsrf`
- **Inputs** - `_xsrf`, hidden `code`
- **Conditionals** - danger alert when the target server is not running; scopes shown read-only
- **Navigation** - on accept, redirect to the shared server URL

### Error (`/hub/error` / any error)

- **Purpose** - generic HTTP error display
- **Conditionals** - `message_html` (safe) preferred over plain `message`; optional `extra_error_html`; status code + status message in heading
- **Dynamic** - JS strips the `redirects` query param on load (breaks redirect loops)

### 404

- **Purpose** - not-found page (extends error.html)
- **Messages** - "Jupyter has lots of moons, but this is not one..."

### Message (`/hub/message`)

- **Purpose** - ad-hoc message display with a constant login link
- **Inputs** - none; shows `message` context var
- **Navigation** - login link

### Token (`/hub/token`)

- **Purpose** - manage API tokens and view authorized OAuth applications
- **Actions** - request new token (form, JS-driven); revoke token (per-row buttons); expiry dropdown
- **Inputs** - `token-note`, `token-expiration-seconds` (select), `token-scopes` (space-separated), `_xsrf`
- **Conditionals** - tokens section only when tokens exist; OAuth-clients section only when present; per-row note/scopes/last-activity/created/expiry shown
- **Messages** - one-time "your new API token" card with copy-now warning ("you won't be able to see it again")
- **Dynamic** - JS module handles request + revoke; scope lists expand/collapse

## Spawn, home and self-service

### Home (`/hub/home`)

- **Purpose** - primary dashboard for server lifecycle and session monitoring
- **Actions** - Start My Server (-> `/hub/spawn`); Stop My Server; Restart Server (modal); Manage Volumes (modal, server stopped); Extend Session (modal/panel, culler enabled + server active)
- **Conditionals** - Start/Stop toggle on `spawner.active`; Restart hidden when inactive; Manage Volumes hidden when active; session timer only when culler enabled + active; named-servers table desktop-only; mobile status strip per server state
- **Messages** - mobile "Server Online + uptime" / "Server Offline"; session countdown + loading spinner; restart "Lab is starting up..."; stop "Stopping server..."
- **Modals** - Manage Volumes; Restart Server; Extend Session (desktop) / inline panel (mobile)
- **Dynamic** - stop poll (1.5s, max 5min, auto-reload); restart poll on `/lab-ready` (1.5s, max 5min); drift detector polls `/api/users/{user}` every 30s and reloads if the server stopped externally (pauses when tab hidden); auto-reload on extend/volume-reset success
- **API** - `GET /api/users/{user}`; `POST .../restart-server`; `GET|DELETE .../manage-volumes`; `GET .../lab-ready`; `GET|POST .../session-info` + `.../extend-session`

### Named servers (table on home)

- **Purpose** - create/start/stop/delete additional named servers (desktop)
- **Actions** - Add (inline row, name input); Start (-> `/hub/spawn/{user}/{name}`); Stop; Delete (all built-in JupyterHub)
- **Inputs** - server name (alphanumeric + hyphens)
- **Conditionals** - Start hidden when active; Stop hidden when inactive; Delete hidden when active; add row always present
- **Messages** - per-server last-activity timestamp or "Never"

### Manage Volumes (modal on home)

- **Purpose** - delete selected user volumes while the server is stopped
- **Actions** - Reset Selected (`DELETE .../manage-volumes` with chosen suffixes)
- **Inputs** - one checkbox per existing volume (loaded on open)
- **Conditionals** - Reset disabled until a selection exists; "no volumes yet" when the list is empty; selection count badge
- **Messages** - "this action cannot be undone"; "N volume(s) selected"; confirm prompt
- **Dynamic** - on open `GET .../manage-volumes` renders checkboxes; on submit DELETE then close + alert + reload; on error close + alert + re-enable
- **API** - `GET .../manage-volumes` -> `{volumes:[{suffix,name,description}]}`; `DELETE .../manage-volumes` body `{volumes:[suffix]}` -> `{message,reset_volumes,failed_volumes}`

### Restart Server (modal on home)

- **Purpose** - confirm and run an in-place Docker container restart (no recreate)
- **Actions** - Restart (`POST .../restart-server`) then probe lab readiness
- **Conditionals** - available only when server active
- **Messages** - explains graceful restart preserves volumes/config; warns unsaved notebook work is lost, files on disk safe
- **Dynamic** - on click disable + "Restarting container..."; on success poll `/lab-ready` (1.5s, max 5min) then restore Start; timeout alert after 5min
- **API** - `POST .../restart-server` -> `{message}`; `GET .../lab-ready` -> `{ready,reason}`

### Extend Session (modal desktop / panel mobile)

- **Purpose** - add hours to the idle-culler deadline
- **Actions** - Extend (`POST .../extend-session` with hours)
- **Inputs** - hours number field (min 1, bounded by available) / range slider (mobile)
- **Conditionals** - only when culler enabled + server active
- **Messages** - "available: N hour(s)"; success/error feedback
- **Dynamic** - on open `GET .../session-info` populates available hours; auto-close on success; home timer refreshes
- **API** - `GET .../session-info` -> `{culler_enabled,server_active,timeout_seconds,max_extension_hours,last_activity,time_remaining_seconds,extensions_available_hours}`; `POST .../extend-session` body `{hours}` -> `{success,message,truncated,session_info}`

### Spawn options (`/hub/spawn` or `/hub/spawn/{user}/{name}`)

- **Purpose** - server configuration form before launch
- **Actions** - Start submits the spawner options form (multipart), runs `pre_spawn_hook` + container start
- **Inputs** - rendered spawner options form (group-driven fields)
- **Conditionals** - "spawning server for {user}" when an admin spawns for another; error shown as plain text or safe HTML
- **Dynamic** - submit shows spinner + disables the button

### Spawn pending (`/hub/spawn/{user}/{name}` during spawn)

- **Purpose** - live progress bar + event log during container startup
- **Actions** - Refresh (manual reload)
- **Conditionals** - progress bar driven by streamed `progress`; event log auto-opens on failure; bar turns danger on fail
- **Messages** - "your server is starting up... redirected automatically"; per-event message (plain or safe HTML); screen-reader progress text
- **Navigation** - auto-redirect to the lab when a `ready` event arrives
- **Dynamic** - EventSource stream from `progress_url` yields `{progress,message,html_message,ready,failed}`; fallback `/lab-ready` poll every 2s catches a hub restart mid-spawn; reloads once stream closes or lab ready

### Stop pending (`/hub/stop/{user}/{name}`)

- **Purpose** - holding page while the server shuts down
- **Actions** - Refresh (manual reload)
- **Messages** - "your server is stopping..."; spinner
- **Dynamic** - auto-reload every 5s

### Not running (`/hub/user/{username}[/{name}]`)

- **Purpose** - offer to launch a non-running server, optionally auto-spawning
- **Actions** - Launch / Relaunch (-> `/hub/spawn/...`)
- **Conditionals** - heading + button flip on `failed`; auto-redirect after `implicit_spawn_seconds` when set; failure detail shown as plain or safe HTML
- **Dynamic** - timed redirect to the spawn URL when implicit spawn configured

## Groups and policy page (`/hub/groups`)

The primary rebuild target. Central admin panel managing user groups, their priority order, and per-group policy rules; every active policy is summarised server-side into badges + tooltip detail consumed verbatim by the page.

### Layout regions (functional)

- **Toolbar** - group count badge; Add Group + Refresh buttons (revealed after load or error)
- **Groups table** - one row per group: drag handle, priority number, clickable group name, description, policy badges, member count (hover lists members), actions (move up, move down, delete)
- **Empty state** - "no groups" alert when none exist
- **Add Group modal** - name + optional description -> Create
- **Configure Group modal** - scrollable panel: description plus the policy sections, each with an enable toggle that disables its controls when off

### Actions

- **Add Group** - opens modal, `POST /api/admin/groups/create {name,description}`, reload on success
- **Open config** - clicking the group name does `GET /api/admin/groups/{name}/config`, populates and shows the modal (the old edit/cog affordance was dropped)
- **Move up / down** - swap in the order array, `POST /api/admin/groups/reorder`, re-render (buttons disabled at first/last)
- **Drag reorder** - drag-drop a row, persist via reorder endpoint
- **Delete** - confirm dialog then `DELETE /api/admin/groups/{name}/delete`, reload (page reloads after delete so the row never lingers)
- **Save config** - `PUT /api/admin/groups/{name}/config` with the full payload, close + reload
- **Cancel** - dismiss either modal without saving
- **Refresh** - re-fetch and re-render

### Policy types

All nine; each contributes a badge + tooltip detail when active and resolves across groups by its own rule.

- **env_vars** - set of `{name,value,description}`; badge "N Var(s)", detail "Environment Variables: N var(s)"; reserved names rejected on coerce/validate; resolve = priority-first-wins per name, reserved skipped, source group tracked
- **gpu** - `gpu_access`, `gpu_all`, `gpu_device_ids`; badge "GPU", detail "GPU: all" or "GPU: 0,1,2"; validate requires device ids when access on but all off; resolve = OR access + union ids (all wins); apply sets `NVIDIA_VISIBLE_DEVICES`/`CUDA_VISIBLE_DEVICES` + device requests
- **docker** - normal raw-socket vs limited (mutually exclusive in one group) with limited quotas (max containers/volumes/networks/storage-gb, cpu-cap, mem-cap) + flags (dangerous flags, user compose project + override, hub network access) + orthogonal privileged; badge "Docker", detail "Docker: raw socket" / "limited" / "limited + privileged"; resolve = OR grants (wider wins), max quotas, raw supersedes limited; apply mounts the socket or registers with the in-process proxy; re-registers surviving users on hub startup
- **cpu** - `cpu_limit_enabled`, `cpu_limit_cores`; badge "CPU", detail "CPU: N cores"; resolve = max enabled wins; apply sets spawner cpu limit (ceil, min 1)
- **mem** - `mem_limit_enabled`, `mem_limit_gb`, `mem_swap_disabled`; badge "Mem", detail "Memory: Ng" (+ "(no swap)"); resolve = max enabled wins, swap flag carried; apply sets mem limit (+ memswap)
- **sudo** - section-gated `sudo_active` + `sudo_enable`; badge "Sudo on/off", detail "Sudo: on/off"; resolve = highest-priority active group wins else None (platform default); apply sets `JUPYTERLAB_SUDO_ENABLE`
- **downloads** - section-gated `downloads_active` + `downloads_allow`; badge "Downloads on/off", detail "Downloads: on/blocked"; resolve = highest-priority active group wins else None; apply registers/unregisters per-user CHP download-block routes; re-registers surviving users on hub startup
- **api_keys** - pool `{enabled,mode(single|pair),env_var_key|env_var_id+secret,credentials[{slot,...}]}`; badge "Keys", detail "API Keys pool: N credential(s)"; coerce preserves stored secrets by slot (masked on read); resolve = list of pools keyed by group; apply assigns one slot per pool per user from the pool manager, sets env vars + durable labels (no secrets in labels), collision-free across hub restarts
- **volume_mounts** - section-gated list of `{volume,mountpoint}`; badge "Volumes", detail "Volume Mounts: N mount(s)"; protected mountpoints rejected on coerce; resolve = union by mountpoint (higher priority wins); apply mounts into the spawner and tracks so leaving a group unmounts on next spawn

### Badges and tooltip

- **Badges** - rendered from the server `policy_summary` array (`{key,badge,detail}` per active type), produced by `summarize_config` looping the registry order; the client never recomputes them
- **Tooltip** - native title on the group name: group name, priority position, the active policy details (one per badge) or "No policies configured", plus a "Click to configure" footer; built client-side from `policy_summary[].detail`

### Inputs and validation

- **Field types** - text (names, values, paths), number (gb/cores/quotas), checkbox toggles, select (api-keys mode), textareas
- **Reserved env vars** - rejected with a structured 400 (`reserved_env_var_names` + rejected list), surfaced inline in the modal
- **Protected mountpoints** - system paths rejected client hint + server coerce
- **Group name** - must start with a letter, `[a-zA-Z0-9_-]*`, max 255; enforced client + server; duplicate -> 409
- **Error surfacing** - 400 shows an inline banner in the modal with the parsed message and scrolls into view

### Persistence

- **Create** - inserts the group + a config row (priority 0, description)
- **Read config** - returns `{group_name,description,priority,config,policy_summary}`
- **Save** - validates + coerces the body, merges onto stored config, re-validates, writes JSON
- **List** - all config rows sorted by priority desc, matched to groups, plus shared-volume metadata
- **Reorder** - bulk priority update reflected on next render
- **Delete** - removes group + config

### Conditionals

- **Admin-only** - every handler 403s for non-admins
- **Empty state** - table/toolbar hidden when zero groups
- **GPU section** - disabled when no GPUs detected; advisory note when GPU isolation not enforced (WSL2)
- **Docker limited** - quota panel enabled only when the limited toggle is on
- **API keys mode** - switches single-var vs pair-var inputs and credential columns
- **Section folds** - a disabled section is hidden and omitted from the PUT, but its stored data persists
- **Shared volume quick-add** - shown only when the shared volume exists and is not already mounted

### Messages

- **Create** - success closes + reloads; failure marks the name field invalid with text
- **Save** - success closes + reloads; failure shows the config-error banner
- **Delete** - confirm "Delete group '{name}'? This will remove all users from this group."
- **Validation** - client checks (gpu devices, docker normal+limited conflict, empty volume fields, api-keys completeness) plus server 400 codes per policy type

### API

- `GET /api/admin/groups` -> `{groups:[{name,description,priority,member_count,members,config,policy_summary:[{key,badge,detail}]}],shared_volume:{name,exists}}`
- `POST /api/admin/groups/create` body `{name,description}` -> `{success,name}`; 403 / 400 bad name / 409 exists
- `DELETE /api/admin/groups/{name}/delete` -> `{success}`; 403 / 404
- `GET /api/admin/groups/{name}/config` -> `{group_name,description,priority,config,policy_summary}`; 403
- `PUT /api/admin/groups/{name}/config` body = full policy payload -> updated config; 403 / 400 coerce (reserved names, protected paths) + validate (per-type coherence)
- `POST /api/admin/groups/reorder` body `{groups:[{name,priority}]}` -> `{success}`; 403 / 400

## Admin platform pages

### Admin (`/hub/admin`)

- **Purpose** - user + group management (React SPA enhanced with custom hooks), bulk user creation, credential generation, volume reset
- **Actions** - add/edit/delete users; start/stop/delete servers; reset volumes; manage group membership via autocomplete chips; copy/download generated credentials
- **Inputs** - username field; password-generation toggle; group chips with autocomplete; volume checkboxes; modal confirmations
- **Data shown** - user table (name, admin badge, authorization, server state, last activity, groups); per-row server controls; credentials modal (username/password); group-change summary
- **Conditionals** - admin-only; volume management only when the server is stopped; credentials modal after bulk creation; custom chip editor replaces the stock React group tile UI
- **Messages** - group-update success (added/removed counts); API error messages; spinners during create/delete/rename
- **Navigation** - links to Settings, Activity, Notifications, Groups
- **Modals** - user credentials (copy/download); group membership changes; loading; volume management with deletion warning
- **Dynamic** - intercepts fetch for user CRUD (POST/DELETE/PATCH `/api/users[/{user}]`), shows spinner, debounced credential fetch post-create, observer injects volume buttons as the React table re-renders
- **API** - `POST /api/users` (batch create -> user objects); `DELETE /api/users/{user}`; `PATCH /api/users/{user}` (rename); `POST /api/admin/credentials` (cached passwords); `GET|DELETE /api/users/{user}/manage-volumes`

### Settings (`/hub/settings`)

- **Purpose** - read-only display of platform environment configuration
- **Actions** - none (display-only)
- **Data shown** - rows grouped by category (JupyterHub core, Docker, GPU, Services, Idle Culler, Abuse Protection, Activity Monitor, User Environment, Branding); each row = env var name, current value (truncated > 50 chars), description from the settings dictionary
- **Conditionals** - admin-only; rows driven by `settings_dictionary.yml`; `JUPYTERHUB_ADMIN_PASSWORD` deliberately absent so it is never displayed
- **Dynamic** - none (server-side render of the dictionary merged with the environment)
- **API** - none; handler reads the settings dictionary + environment

### Activity (`/hub/activity`)

- **Purpose** - real-time per-user resource usage and engagement scoring tied to the activity-based idle culler
- **Actions** - Refresh; Reset (clear samples); Report (download HTML snapshot); column sort; desktop table vs mobile cards
- **Inputs** - sortable headers (cycle none/desc/asc); refresh/reset/report buttons
- **Data shown** - per user: username, authorization, server status dot (active/idle/offline), CPU %, memory (GB + %), volume sizes (hover breakdown), container writable layer (+GB), time-to-cull, last activity, activity score bar (sampling-aware)
- **Conditionals** - admin-only; Docker stats only for active servers; quota-threshold warnings when volume/memory/container exceed limits; "no active servers" when empty
- **Messages** - loading spinner; inline quota warnings; report header with timestamp + active/idle/offline counts
- **Dynamic** - polls `/api/activity` every 10s; manual refresh debounced; client-side column sort; live bars; responsive card view on mobile; thresholds read from the response so config changes take effect mid-session
- **API** - `GET /api/activity` (users + thresholds + timestamp + sampling status); `POST /api/activity/reset`; `POST /api/activity/sample`

### Notifications (`/hub/notifications`)

- **Purpose** - broadcast admin notifications to all active JupyterLab servers
- **Actions** - compose; pick type; toggle auto-close; choose recipients (all or per-user); Send; show/hide delivery details; Select All / Deselect All
- **Inputs** - message textarea (140-char max, live counter); type select (default/info/success/warning/error/in-progress); auto-close checkbox; send-to-all toggle; recipient checkboxes
- **Data shown** - form with inline validation; active-servers list (fetched on load); post-send results alert (success/partial/failure) + per-user details table (username, status badge, error or "-")
- **Conditionals** - admin-only; recipient UI hidden when send-to-all checked; Send button text reflects target count; details table collapsible; form clears after send
- **Messages** - live char count; validation (empty, over-limit, no recipients); post-send summary "delivered X/Y, failed Y"; per-user error rows
- **Dynamic** - fetch active servers on load; counter on input; button text on selection change; spinner during POST; form disabled while sending; results render per-user status
- **API** - `GET /api/notifications/active-servers` -> `{servers:[{username,...}]}`; `POST /api/notifications/broadcast` body `{message,variant,autoClose,recipients?}` -> `{total,successful,failed,details:[{username,status,error?}]}`

## Rebuild insights

Cross-cutting observations from the sweep - what to keep, what to replace, and where the leverage is. The backend and the policy model are rebuild-ready; the work is almost entirely the frontend.

### Three rendering paradigms stitched together

- Server-rendered Jinja (most pages), a stock React SPA (only `/hub/admin`), and vanilla JS modules (`session-timer.js`, `mobile.js`, per-page scripts) - three state models in one portal
- The worst seam is the admin page: the custom layer does not own it, so it intercepts React's own `fetch()` calls and injects DOM via a MutationObserver to add volume buttons and group chips - fighting a framework it does not control
- The single most fragile surface; a rebuild should own that page outright and delete the interception

### The policy registry is the one subsystem built right

- Server computes `policy_summary` (badge + detail per active policy); the client renders it verbatim and computes nothing - display logic single-sourced to the model, a new policy type is one class
- Every other screen does the opposite; the contrast is the lesson - push display semantics server-side (or into one shared schema) and let the client be pure layout
- Also the security control plane (docker socket, privileged, sudo, GPU) - the highest-stakes screen, not just another admin form

### State management is full-page reload

- Delete a group, reset a volume, extend a session - the flow reloads the page; there is no client state model
- The lagging-table re-render bug found during the functional harness was a direct symptom (server deleted, DOM did not, reload masked it)
- A rebuild with one store + optimistic updates deletes a class of bug, not one bug

### Polling sprawl - six independent loops, almost no push

- home stop-poll 1.5s, restart-poll 1.5s, drift-detector 30s, session-timer 5min, mobile health 15s, activity 10s, spawn fallback 2s - each hand-rolled with its own timeout
- Only spawn progress uses a real stream (EventSource), and even that needs a polling fallback for a hub restart mid-spawn
- Unify on one push channel (SSE/WS) with pollers as fallback, not as the primary mechanism

### Mobile is a fork, not a responsive layout

- `mobile.js` reimplements start/stop, the status strip and the activity monitor rather than the same components adapting to viewport
- Two code paths for identical features guarantees drift - collapse to one responsive implementation

### Two pockets of framework-born accidental complexity

- First-admin bootstrap: two mutually-exclusive modes (signup-window vs env-password) plus an ordering trap - the `users_info` table is created after the config runs, so env-password cannot seed on a single fresh boot; exists only because of NativeAuthenticator's lifecycle, a different auth model erases it
- Lab-session favicon: per-user CHP route registration, longest-prefix matching, re-registration to survive `check_routes()` cleanup, and a Tornado handler injected outside the `/hub/` prefix - clever but fighting CHP; revisit whether the rebuild's proxy topology makes it unnecessary

### What is healthy - keep it

- The custom API surface (`custom_handlers.py` + the services handlers) is well-shaped - REST-ish, consistent owner-or-admin 403 gating, clean payloads, XSRF threaded uniformly through `window.jhdata`; the backend is not the problem, the frontend is, so keep these endpoints and replace only the UI
- Feedback is modal/inline-alert only (no toast system) - consistent but thin; only notifications-broadcast has a real delivery-status table, nothing comparable exists for the operator's own actions

### One gap worth flagging

- The Settings page is read-only - it displays platform env config but every change still means editing compose + restarting; the obvious candidate to make live-editable if the rebuild wants operator self-service, and the deliberate hiding of `JUPYTERHUB_ADMIN_PASSWORD` shows the display-gating is already thought through

## Rebuild concept

The target architecture for a modern, responsive, unified portal. One TypeScript SPA owns the entire authenticated surface, served as a static bundle by the hub, consuming the JSON APIs that already exist. The backend does not change. Executed as a strangler, screen by screen, not a big-bang rewrite.

### Security model - hub as the trust boundary

The governing constraint, ahead of every other choice. Hub and lab are two different systems: the hub is the control plane - gateway, proxy, authenticator, authorizer, spawner - and the lab is an isolated workload reached only through it. The rebuild replaces presentation only, so it cannot move the trust boundary, which already lives in the backend, as long as the SPA stays a client and never a bypass.

- **Single trust boundary** - the hub is the only exposed surface and the only thing that authenticates (NativeAuthenticator), authorizes (scopes/roles) and reaches labs; the lab runs on an internal network, trusts the hub-issued OAuth token and nothing the browser sends directly
- **SPA is just another client** - it gets no privilege the hub does not already grant and enforce; bundle served by a hub handler, all data through `/hub/api/...`, guarded by the hub session cookie + XSRF; the SPA stores no tokens of its own, the hub session is the credential; no side service, no direct lab access, no bypass
- **Every mutation re-authorized server-side** - the existing owner-or-admin 403 gating on every endpoint is preserved verbatim, never relaxed for SPA convenience
- **Capability-driven UI is rendering, not authorization** - the server telling the client which actions/fields/rules are available is a render convenience only; the server still enforces on the mutation regardless of what the client was told (render from capabilities, guard on the endpoint - a client that lies still hits a 403)
- **One authorization model** - JupyterHub scopes/roles (`parsed_scopes`, `admin-ui`, role scopes) are the single source of truth for both nav rendering and server checks; no parallel auth model beside the hub's
- **Lab access stays mediated** - the SPA links to `/user/{username}` but never holds lab credentials; the OAuth handshake guards entry, the proxy guards transport; the branding/favicon CHP-route mechanism is proof the hub already controls what reaches the lab, and that pattern stays
- **Groups/policy is a guard surface** - it grants real privilege (docker socket, privileged, sudo, GPU), so hard admin-gate it, and the resolved policies are applied server-side in `pre_spawn_hook`, never trusted from the client

### Feasibility - what "replace the frontend" actually covers

JupyterHub separates its management API from its presentation, so the portal is just a client of a documented REST API. `html_templates_enhanced/` already overrides every hub page - the SPA finishes that move properly. The supported extension surface (`template_paths`, `extra_handlers`, custom route handlers, admin-page override) lets the rebuild own 100% of what a logged-in user or admin sees. Three layers, only two of them ours:

- **Portal pages (fully replaceable)** - home, self-service, groups, admin, settings, activity, notifications, token; the whole rebuild
- **Protocol-bound pages (replaceable UI, mandatory flow)** - OAuth consent + spawn/stop interstitials; reimplement the page but keep consuming the underlying machinery (spawn-progress SSE, the hub<->single-user OAuth handshake that issues the server token); consent can be auto-skipped for trusted internal clients, the handshake cannot be deleted - it is authorization, not UI
- **JupyterLab (not ours)** - everything inside `/user/{username}` is a separate Lumino app, explicitly out of scope; the branding/favicon/icon hooks are the seam, and the rebuild stops at that line
- **Pre-session pages** - login/signup mount before the SPA shell exists; keep them server-rendered (lowest risk, they belong to the authenticator) or ship a small separate pre-auth bundle

The goal is replacing the portal frontend, not JupyterHub. The trap is scope drift across the lab seam or into the protocol-bound handshake - that turns a clean rebuild into forking the hub.

### Boundary - rebuild vs keep

- **Keep server-rendered** - login, native-login, signup, oauth, accept-share, change-password, error/404; security-sensitive, pre-session, owned by NativeAuthenticator, low churn
- **Keep unchanged** - the backend; `custom_handlers.py` + the services handlers are healthy (REST-ish, owner-or-admin 403 gating, clean payloads, uniform XSRF), the rebuild consumes them as-is
- **Rebuild as the SPA** - everything behind login, where all three rendering paradigms, the React interception and the reload-driven state live

### Stack

- **React + TypeScript** - JupyterHub already ships React, team familiarity, ecosystem; the decisive factor is the data layer below (Svelte is the credible lighter alternative if bundle size outweighs ecosystem)
- **TanStack Query** - the server-state layer; the single most important choice, the direct cure for reload-driven state and polling sprawl
- **Vite** bundle served by one hub custom handler under `base_url`, deep-links resolved client-side; single deployment, shares the hub session cookie and proxy, no CORS, no separate service
- **Component library + design tokens** - formalize the existing Stellars Sublime CSS custom properties into tokens; dark mode rides the same token system (keep the `data-bs-theme` approach, centralized)

### Three pillars

- **Server-state cache replaces page reloads** - every screen reads from query hooks; every mutation invalidates the relevant queries and the UI re-renders from fresh server truth, no `location.reload()`; the lagging-DOM class of bug becomes structurally impossible (one source of truth, the cache reconciled with the server); optimistic updates where they help
- **One push channel replaces six pollers** - a single SSE/WS connection multiplexes spawn progress, server state-changes, activity samples and notification delivery, feeding the query cache; per-query `refetchInterval` stays as a declarative fallback - push when present, poll when not, no hand-rolled loops
- **Capability-driven UI generalizes the policy registry** - server owns semantics (summaries, badges, available actions per state, field schemas, validation rules), client owns layout; the `policy_summary` pattern made the rule everywhere, not the exception

### Modern, responsive, unified

- **Unified** - one TypeScript app, one paradigm; collapses the Jinja/React/vanilla split and, when the admin page is ported, deletes the React-interception seam
- **Responsive** - one component tree adapting to viewport; deletes the `mobile.js` fork and its parallel start/stop/status/activity implementations
- **Modern** - SPA + server-state cache + push channel + capability-driven rendering + a real toast/feedback store for the operator's own actions (today only notifications-broadcast has a delivery-status surface)

### Migration - strangler, screen by screen

1. Stand up the SPA shell at one new authenticated route; keep all Jinja pages live behind it
2. Port **groups first** - cleanest API, highest value, the security control plane; validates the capability-driven pattern end to end
3. Then home/self-service, activity, notifications, settings
4. **Admin last and hardest** - porting it is what lets you delete the React-interception seam (own the page instead of injecting into JupyterHub's)
5. Flip nav links as each screen lands; retire each Jinja template only when its replacement ships; auth pages never move

### Risk

- The portal swap is low-risk - stable backend, screen-by-screen strangle
- The only real bite is **scope drift across the lab seam** and **underestimating the protocol-bound pages**; treating the OAuth/spawn handshake or JupyterLab as "frontend to replace" is where a clean rebuild becomes a hub fork - draw the line at the lab seam and the API

## Coverage map

Screens catalogued: login, native-login, signup, logout, change-password, change-password-admin, authorization-area, oauth, accept-share, error, 404, my_message, token, home (+ named servers, manage-volumes, restart, extend-session), spawn, spawn_pending, stop_pending, not_running, groups (+ all nine policy types), admin, settings, activity, notifications. Global layer: page.html base, navigation map, branding, dark mode, mobile.js, session-timer.js, shared messaging.

Out of scope (documented elsewhere or by design): JupyterLab in-session UI, CSS/DOM/class-level detail, the lab-extension surfaces (download-block toast, notification ingest) that live in the spawned image not the hub.
