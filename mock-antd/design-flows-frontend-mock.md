# Optimum Hub - flows, navigation and screen registry

Use-case flows drive the design. Each screen maps to a hub REST endpoint that already exists (the backend does not change; this is presentation only), and carries a stable reference ID so later work can point at it precisely. This document describes the React / Ant Design Pro build (`mock-antd`); routes and component names are the canonical surface.

## Goal

**Philosophy** - reduce the cognitive and navigation burden on users and admins, surface actionable information, and let the most frequent and necessary actions be done simply. Scale target: dozens up to a few hundred users (not thousands) and dozens of policies - so the list machinery is about comfort at hundreds, not survival at thousands (no virtualization).

Three success criteria, every decision is judged against them:

- **Flows clean and converged** - one way to do each task, no contradictions, no duplicate surfaces
- **Admin friction minimal** - fewest clicks, page loads and context losses for the common admin tasks
- **Navigation integrity maximal** - every screen reachable, every action has a clear back-path, placement consistent, role-gating correct

## Navigation laws

The paradigm applied platform-wide, so navigation is learnable once and predictable everywhere.

- **List -> Add -> create screen** - a list's primary action routes to a dedicated create screen, never an inline add-row
- **Row -> detail screen** - clicking a list row routes to a dedicated detail screen; never inline-expand, never a panel at the bottom of the list (editing user 73 of 100 cannot mean scrolling past 72 rows)
- **Detail = tabs that earn their keep** - a tab exists only if it carries an action or a fact nothing else shows
- **Bulk = input screen -> result screen** - a bulk action collects once, then lands on a downloadable result
- **Breadcrumb = depth** - `Users / New user`, `Users / Configure user`; the parent crumb is the way back, abandoning the action
- **Destructive = inline confirm** - delete / reset use a confirm in place, not a screen of their own
- **Widget -> its page** - every dashboard widget is a mini-view that drills into its full page via its card-head link
- **Search before scroll** - any list past a screenful leads with a filter field

## Navigation scheme

Role-gated `ProLayout`. The sider holds only what is visited often; everything else is reached by an action from where it belongs (Add, row-click, palette).

```
SIDER (admin)                         SIDER (user)
    Home           /home                 Home      /home   (no group header)
    Profile        /profile              Profile   /profile
  ADMINISTRATION
    Servers        /servers
    Users          /users
    Groups         /groups
    Lab Container  /lab-container
    Events         /events
    Notifications  /notifications
    Advanced  v                          (collapsible)
      Settings     /settings
      Tokens       /tokens

CONTENT-TOP  breadcrumb (Optimum Hub / [parent /] page)
SIDER FOOT   identity · sign out
HEADER       language · theme controls (actionsRender)
FOOTER       Optimum Hub + JupyterHub versions + stack chips
COLLAPSE     thin handle on the sider's right edge at mid-height
COMMAND-K    role-scoped palette (go-to nav + actions)
MOCK-ONLY    Home carries a dashed Admin / User / design switch - a reviewer helper
```

The split is live-system vs configuration: Home and Servers are the running fleet you watch and act on; Administration is the platform's configuration - who exists (Users), what they may do (Groups, the security control plane: docker socket, privileged, sudo, GPU) and how it is set (Settings, Tokens). `Advanced` keeps the occasional power-user surfaces off the primary rail; both are also reachable by `Cmd-K`.

## Screen registry

| Ref | Screen | Route / component | Reached from | Backing endpoint(s) |
|-----|--------|-------------------|--------------|---------------------|
| OVR-001 | Admin Home (dashboard + own server hero) | `/home` `Home` | sider | aggregates of the below |
| OVR-100 | User Home (launchpad) | `/home` `Home` (role=user) | sider | `GET /api/users/{user}` |
| SRV-001 | Servers list (monitor + lifecycle) | `/servers` `Servers` | sider | `GET /api/activity`, `/api/users` |
| USR-001 | Users list (+ pending panel) | `/users` `Users` | sider | `GET /api/users`, authorize links |
| USR-002 | New user (single) | `/users/new` `NewUser` | USR-001 Add | `POST /api/users`, `/api/admin/credentials` |
| USR-003 | Bulk add users (input) | `/users/bulk` `BulkUsers` | USR-001 Bulk add | `POST /api/users` |
| USR-004 | Bulk result (credentials + download) | `/users/bulk/result` `BulkResult` | USR-003 confirm | `POST /api/admin/credentials` |
| USR-005 | Configure user (tabbed) | `/users/:name` `UserConfig` | USR-001 row / name | `PATCH /api/users/{user}`, manage-volumes, authorize, change-password |
| GRP-001 | Groups list (priority, import / export) | `/groups` `Groups` | sider | `GET /api/admin/groups` |
| GRP-002 | New group | `/groups/new` `NewGroup` | GRP-001 Add | `POST /api/admin/groups/create` |
| GRP-003 | Configure group (tabbed) | `/groups/:name` `GroupConfig` | GRP-001 row | `GET\|PUT /api/admin/groups/{name}/config`, group-users add/remove |
| GRP-004 | Export groups | `/groups/export` `GroupsExport` | GRP-001 Export | per-group `.../config` |
| LAB-001 | Lab Container | `/lab-container` `LabContainer` | sider | `JUPYTERHUB_LAB_IMAGE`, `DOCKER_SPAWNER_VOLUMES` |
| EVT-001 | Events (audit timeline) | `/events` `Events` | sider, Home feed, palette | net-new - no event source exists yet |
| BRD-001 | Notifications (send + sent history) | `/notifications` `Notifications` | sider, palette | `POST /api/notifications/broadcast` |
| SET-001 | Settings (running config, signup toggle) | `/settings` `Settings` | Advanced | settings dictionary |
| SET-002 | Settings reference (every env var) | `/settings/reference` `SettingsReference` | SET-001 | settings dictionary |
| TOK-001 | Tokens (personal API tokens + OAuth) | `/tokens` `Tokens` | Advanced, user-menu | `GET\|POST /hub/api/users/{u}/tokens` |
| SELF-003 | Profile (self-service) | `/profile` `Profile` | sider (both roles) | `PATCH /api/users/{self}`, change-password |
| DSL-001 | Design language / system palette | `/design-language` `/design-system` | URL only | none (gallery) |
| AUTH-* | login / signup | `/login` `/signup` | pre-session | NativeAuthenticator |

## Flows

### Users

**Flow 1 - new user (single)** - USR-001 Add -> USR-002 (username; password auto-generated or typed; groups via `GroupPicker`; authorize-now switch) -> `POST /api/users` (+ credentials) -> back on USR-001 with the new row.

**Flow 2 - bulk add** - USR-001 Bulk add -> USR-003 (paste usernames; configure once: groups, authorize-now, require-password-change) -> `POST /api/users` batch -> USR-004 result table (username / generated password / groups) with download. No per-user password entry.

**Flow 3 - configure one user of many** - USR-001 filter by name, click the name (an accent link) -> USR-005 full tabbed screen: **Profile** (username fixed, email, change-password, Administrator + Authorised switches), **Groups** (`GroupPicker` add + browse, with the resolved effective policies), **Volumes** (reset selected, server stopped only). One Save (`FormFooter`). The Authorised toggle is also inline on the list row. The built-in admin (`JUPYTERHUB_ADMIN`) is locked - its role / authorisation / removal are owned by system config, not the screen.

**Flow 4 - authorize pending signups** - USR-001 leads with a **Pending authorisation** panel (orange-bordered, shown only when something waits): a table of user link / groups / signed-up / Authorize + Discard, calling `/authorize/{user}` / `/discard/{user}`. Approved users drop into the main list; the panel vanishes when empty. The main list's Authorised switch is the deliberate de-authorisation lever (off != pending).

### Groups

**Flow 5 - create a group and set policy** - GRP-001 Add -> GRP-002 (name + description) -> back, click the name -> GRP-003 Policy tab = `GroupPolicyTab`, nine fold-on-toggle sections (env vars, GPU all-or-per-device, memory + swap, CPU, Docker standard | limited + privileged, volume mounts, API-keys pool, downloads, sudo) -> `PUT /api/admin/groups/{name}/config`. An off section collapses and is omitted from the payload. Policy downloads / uploads as validated JSON.

**Flow 6 - reorder priority** - GRP-001 is a `DragSortTable`; drag a row -> `POST /api/admin/groups/reorder`; higher priority wins on conflict.

**Flow 7 - delete a group** - GRP-001 row -> inline confirm ("removes all users from this group") -> `DELETE /api/admin/groups/{name}/delete`.

### Servers

**Flow 8 - triage and reclaim** - SRV-001 carries the live monitor's columns (Status, Activity, CPU, Memory, GPU, Volumes, System, Time-left) plus lifecycle actions, sortable, with quota-breach colour cells and Reset-samples / Report / Refresh in the toolbar. Status (instantaneous lifecycle) and Activity (24h engagement meter, % in tooltip) are distinct columns. Per-row by state: Offline -> Start (admin stays on the list); Active -> Enter (confirm) / Restart / Stop; Spawning -> view log / Cancel. Scope pills keep Offline out of the default view; the pager offers 25 / 50 / 100.

### Self-service

**Flow 9 - user runs their lab** - OVR-100 launchpad: one `ServerHero` for their server (Open / Restart / Stop, TTL gadget with Extend), read-only effective access and groups, resources. Change password and tokens via Profile / user-menu. No fleet pages.

### Platform

**Flow 10 - broadcast** - BRD-001: message (140-char), type, auto-close, recipients -> Send -> results table -> `POST /api/notifications/broadcast`.

**Flow 11 - review config** - SET-001: rows by category, mostly a read-only reference; signup renders as a live override Switch (default from `JUPYTERHUB_SIGNUP_ENABLED`); `JUPYTERHUB_ADMIN_PASSWORD` stays hidden.

## Interaction language

The control layer is one named system, shown live on `/design-language`.

- **Colour = state** - green ok (active / authorised / success), amber warn (idle / inactive), red danger (error / unauthorised), cyan accent for neutral emphasis and aggregates; colour alone signals a threshold breach
- **State as pills** - `StatusPill` (coloured dot + soft background) for every lifecycle / type; scope-filter pills double as counts, dim to .6 inactive, lit with an accent ring when active, default scope never "everything"
- **Buttons** - antd `Button` by context: page primary / default / danger for form and page-head, `size="small"` for list-row actions, `IconAction` (icon-only) for dense row actions. The filled square is an actual server stop / cancel; remove / delete is the `×` close glyph
- **Config screens** - heavy entities (user, group) and Lab Container open full tabbed screens with one `FormFooter` (destructive left, Cancel / Save right); Create reuses Configure with elements toggled
- **Zebra everywhere** - one global rule alternates table rows and survives filter / sort; bespoke tables match the `ProTable` cell padding
- **Short relative time everywhere** - `timeAgoShort`, exact date in the tooltip
- **Tooltips, notices, navigate-out** - help lives in `title` tooltips; a `Notice` (coloured-left-edge bar) confirms under the action that produced it; a widget's whole card-head is a chevron link to its page
- **Identity** - a username shows its full name stacked below in muted text; names and group chips are accent links into their Configure screen, with `CappedTags` (+N) capping long chip lists

## Backend reality - corrections and net-new

Most flows map to real endpoints; these are the deltas.

Corrections:

- **Authorize is a toggle, not a PATCH** - pending Authorize / Discard and the Authorised switch call `/authorize/{user}` / `/discard/{user}` (NativeAuthenticator); re-clicking toggles
- **Passwords are auto-generated today** - single + bulk create auto-generate (xkcd) and cache for retrieval via `POST /api/admin/credentials`

Net-new (the design assumes it; build or drop per item):

- **Manual password at create** (USR-002) - creation is auto-gen only today
- **Authorize-later at create** (USR-002/003) - every created user is auto-authorized today
- **Require password change on first login** (USR-003) - no `UserInfo` field; needs schema + login-hook change
- **Per-user effective-policy read** (OVR-100, USR-005) - `policy_summary` is per group; no per-user resolved-policy read endpoint exists
- **Events / audit source** (EVT-001) - no event store; minimal source = SQLAlchemy listeners on tracked mutations + broadcast-sent, to a small append log
- **Bulk partial-failure reporting** (USR-004) - the result must show per-user success / failure
- **GPU utilisation data** (Resources / GPU meter) - CPU / Mem are in `GET /api/activity`; per-server GPU use is not sampled (GPU is group-granted), so the GPU meter shows allocation or needs a stats source

Keep (real capabilities the flows must not drop): typeahead group chips, copy / download credentials, rename via `PATCH`, policy badges + "click to configure" from `policy_summary`, member-count drill-in, shared-volume include / exclude, drag-reorder.

## Relationship to the static mock

`../mock/` is the original static HTML/CSS/JS prototype that established this design language and screen set. `mock-antd` is the higher-fidelity React realisation and the canonical artefact going forward; where the two differ, this build wins. The static tree remains only as a historical reference.
