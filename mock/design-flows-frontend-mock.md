# Optimum Hub - flows, navigation and screen registry

Use-case flows drive the redesign. Each flow is walked step by step against the real capability inventory in `portal-ui-catalogue.md`, so every screen and action maps to an endpoint that already exists. Screens carry stable reference IDs (USR-002 etc.) so later work can point at them precisely. Slop is whatever a flow does not need - it gets named and cut at the flow that exposes it.

This is the navigation scheme first. The mock is rebuilt against these refs afterwards, not before.

## Goal

Three success criteria, every decision is judged against them:

- **Flows clean and converged** - one way to do each task, no contradictions, no duplicate surfaces
- **Admin friction minimal** - fewest clicks, page loads and context losses for the common admin tasks
- **Navigation integrity maximal** - every screen reachable, every action has a clear back-path, placement is consistent, role-gating is correct

Status (this revision): all three locked, no open decisions remain - the Tokens, Activity and per-tab resolutions are recorded under Critic pass. A later **Refinement round - scale and coherence** (see that section) supersedes the edit-as-drawer decision: Configure user and Configure group are now full tabbed screens, and the lists are built to hold up at large user/group counts.

## How to read this

- **Screen ref** - `DOM-NNN`, e.g. `USR-002`; a sub-area is `USR-005/groups`
- **Flow** - numbered steps an actor takes; each step names the screen it lands on and the endpoint it calls
- **Slop cut** - what the flow proves unnecessary, removed at that point
- **Endpoints** are quoted from the catalogue; the backend does not change, the rebuild is presentation only

## Navigation laws

The paradigm, extracted from the two seed scenarios and applied platform-wide. Every screen obeys these so navigation is learnable once and predictable everywhere.

- **List -> Add -> create screen** - a list's primary action navigates to a dedicated create screen, never an inline add-row
- **Row -> detail screen** - clicking a list row navigates to a dedicated detail screen; never inline-expand, never a panel at the bottom of the list (editing user 73 of 100 cannot mean scrolling past 72 rows)
- **Detail = tabs that earn their keep** - a tab exists only if it carries an action or a fact nothing else shows; no tab for tokens we do not issue
- **Bulk = input screen -> result screen** - a bulk action collects once, then lands on a confirmation/result screen that can be downloaded
- **Breadcrumb = depth** - `Users / New user`, `Users / alice / Groups`; the crumb is the way back, lists are never a dead end forward
- **Destructive = inline confirm** - delete/reset use a confirm dialog in place, not a screen of their own
- **Widget -> its page** - every dashboard widget is a mini-view that drills into its dedicated full page
- **Search before scroll** - any list past a screenful leads with a filter field; you find a row, you do not hunt it

## Navigation scheme

Role-gated. The sidebar holds only what is visited often; everything else is reached by an action from where it belongs (Add, row-click, topbar, palette). Off-rail screens are not lost - they are one obvious click from their context and reachable by `Cmd-K`.

```
SIDEBAR (admin)                        SIDEBAR (user)
    Overview     OVR-001                  Overview   OVR-100   (no header - one item)
  ADMINISTRATION
    Servers        SRV-001
    Users          USR-001
    Groups         GRP-001
    Lab Container  LAB-001  (lab-container.html - image + volume set)
    Events         EVT-001
    Notifications  BRD-001  (notifications.html - send + sent history)
    Advanced  v                      (expandable)
      Settings     SET-001
      Tokens       TOK-001

TOPBAR      breadcrumb · Cmd-K   (no action icons)
SIDEBAR-FOOT identity · theme toggle · sign out
OFF-RAIL    create + configure screens (full), reached from their list row
USER-MENU   change password · sign out   (plain user also: API tokens)
MOCK-ONLY   the Overview carries a dashed Admin/User view switch - a reviewer
            navigation helper, explicitly not part of the design
```

`Advanced` is a collapsible item inside Administration holding the occasional power-user surfaces - **Settings** (read-only reference) and **Tokens** (personal credentials) - so the primary rail stays lean (Overview, Servers, Users, Groups). Both are also reachable by `Cmd-K`, the fast path for admins who automate. Plain users have no Administration section; they reach their own tokens from the user-menu.

The split is live-system vs configuration, not frequency: **Operate** is the running fleet you watch and act on right now (Overview, Servers - including stopping another user's container); **Administration** is the platform's configuration - who exists (Users), what they may do (Groups, the security control plane: docker socket, privileged, sudo, GPU) and how it is set (Settings, Tokens). This boundary predicts location: a server action is Operate, an identity or policy change is Administration.

## Screen registry

| Ref | Screen | Reached from | Backing endpoint(s) |
|-----|--------|--------------|---------------------|
| OVR-001 | Admin Overview (dashboard) | sidebar | aggregates of the below |
| OVR-100 | User Overview (launchpad) | sidebar (user) | `GET /api/users/{user}` |
| SRV-001 | Servers list | sidebar | `GET /api/activity`, `/api/users` |
| SRV-002 | Server detail (logs, resources) | SRV-001 row | spawn `progress_url`, `GET /api/users/{user}` |
| USR-001 | Users list (+ pending section) | sidebar | `GET /api/users`, authorize links |
| USR-002 | New user (single) | USR-001 Add | `POST /api/users`, `POST /api/admin/credentials` |
| USR-003 | Bulk add users (input) | USR-001 Bulk add | `POST /api/users` |
| USR-004 | Bulk result (credentials + download) | USR-003 confirm | `POST /api/admin/credentials` |
| USR-005 | Configure user (full screen `user-config.html`) - Profile (username, names, email, admin toggle, password) / Groups (typeahead add + browse-list) / Volumes; bottom action footer (Remove/Cancel/Save) | USR-001 row | `PATCH /api/users/{user}`, manage-volumes, authorize, change-password |
| GRP-001 | Groups list (priority-ordered) | sidebar | `GET /api/admin/groups` |
| GRP-002 | New group (name + description) | GRP-001 Add | `POST /api/admin/groups/create` |
| GRP-003 | Configure group (full screen, tabbed) - General / Policy (nine sections) / Members; bottom action footer (Delete/Cancel/Save) | GRP-001 row | `GET|PUT /api/admin/groups/{name}/config`, group-users add/remove |
| LAB-001 | Lab Container (full screen `lab-container.html`) - spawned image + volume set (core home/workspace/cache locked, add custom) | sidebar | `JUPYTERHUB_LAB_IMAGE`, `DOCKER_SPAWNER_VOLUMES`, `VOLUME_DESCRIPTIONS` |
| EVT-001 | Events (audit timeline) | Administration nav, OVR-001 feed, palette | net-new - no event source exists yet |
| SET-001 | Settings (read-only reference) | Advanced menu | settings dictionary |
| BRD-001 | Notifications (full screen) - send (left) + sent history (right) | Notifications nav item, palette | `POST /api/notifications/broadcast` |
| SELF-001 | Manage volumes (user) | OVR-100 | `GET|DELETE .../manage-volumes` |
| SELF-002 | Extend session | OVR-100 | `GET|POST .../session-info`,`.../extend-session` |
| AUTH-* | login / signup / oauth / change-pw / error | pre-session | NativeAuthenticator (kept server-rendered) |
| SPN-* | spawn options / pending / stop / not-running | protocol-bound | spawner + SSE (kept, reskinned) |

## Flows

### Domain: Users

The flows that taught the paradigm. Users is frequent and list-heavy, so the create/detail/bulk split matters most here.

**Flow 1 - Configure a new user (single)**

1. Admin on **USR-001** (Users list), clicks **Add user**
2. Lands on **USR-002** (New user) - a dedicated screen, not an inline row
3. Configures: username; password (auto-generated xkcd-style by default, or typed by hand via a toggle); groups (chip field with list + autocomplete, RustFS-style); authorize now (switch)
4. Clicks **Add** -> `POST /api/users` (+ `POST /api/admin/credentials` if password generated)
5. Returns to **USR-001**; the new user is a row in the list
6. = done

- Slop cut: no stock inline add-row, no scroll, no modal cramped against the table; one screen owns user creation
- Note: USR-002 and USR-005/profile share the same field components - create and edit are the same form in two modes

**Flow 2 - Bulk add users**

1. Admin on **USR-001**, clicks **Bulk add**
2. Lands on **USR-003** (Bulk add) - paste a list of usernames (one per line)
3. Configures once for the batch: groups (chip field, same control as single); authorize now or leave for later (switch); require password change on first login (switch)
4. No password fields - every password is auto-generated (operator cannot set 100 passwords by hand)
5. Clicks **Create** -> `POST /api/users` (batch)
6. Lands on **USR-004** (Bulk result) - a table of username / generated password / assigned groups, with **Download .txt** (the current credentials-file behaviour)
7. Admin confirms done

- Slop cut: no per-user password entry; no per-user screens; the batch is configured once and the secrets surface exactly once, downloadable

**Flow 3 - Edit one user out of 100**

1. Admin on **USR-001**, filters by name (search before scroll), clicks the row
2. **USR-005** opens as a right-side **drawer** over the list - the list, filter and scroll stay put (a cheap edit must not cost a page change). Tabs:
   - **Profile** - username (fixed), email (optional), avatar; read-only facts: signed up, last active; **Change password** (admin override, no old password); **Authorized** switch
   - **Groups** - current groups as removable chips + add-from-list autocomplete (membership is the only lever; it grants policy), and a read-only **Effective access** panel below: the policy resolved across her groups (GPU, sudo, docker, mem...), each grant citing the group that won - so an admin can answer "what can alice actually do" without opening every group
   - **Volumes** - table of the user's volumes; select which to reset; reset enabled only when the server is stopped
3. One **Save** for the whole user (not per-tab) -> `/authorize` or `/discard` (authorize), change-password handler, group membership, `DELETE .../manage-volumes`. The Authorized toggle is also available inline on the list row (a cheap toggle needs no drawer)
4. Close the drawer -> back on the list, exactly where it was

- Slop cut: the v2 bottom-of-list "Configure user" preview is gone (unreachable at scale); the **Keys** tab is gone (API keys are a group pool injected as env, not a user credential); Identity -> **Profile**, Storage -> **Volumes**
- Note on "Access": the v2 tokens-style Access tab stays removed, but the *effective-policy readout* it should have been now lives inside the Groups tab (the critic flagged its absence as a security blind spot - membership without its resolved result is half the picture)

**Flow 4 - Authorize pending signups**

1. Admin on **USR-001**; a **Pending authorisation** section sits at the top, shown only when something waits
2. Per pending row: **Authorize** or **Discard** -> `/authorize/{user}`, `/discard/{user}`
3. Approved users drop into the main list below; the section vanishes when empty

- Slop cut: pending is a transient top section, not a column state mixed into the main list; the main list's **Authorized** switch is the admin's deliberate de-authorisation lever (off != pending - off means an admin turned them off, and that distinction is theirs to see)

### Domain: Groups

The highest-stakes surface. Same create/detail laws as Users; the detail is heavier (nine policy types) so it is a full screen, never a modal cramped by nine sections.

**Flow 5 - Create a group and set its policy**

1. Admin on **GRP-001** (Groups list), clicks **Add group**
2. Lands on **GRP-002** (New group) - name (`[a-zA-Z0-9_-]`, starts with a letter) + optional description -> `POST /api/admin/groups/create`
3. Returns to **GRP-001**; clicks the group name
4. Lands on **GRP-003** (Group config) - the nine policy sections, each an enable toggle that reveals its controls; priority shown
   - sections: `env_vars`, `gpu`, `docker`, `cpu`, `mem`, `sudo`, `downloads`, `api_keys`, `volume_mounts` (GRP-003/<section>)
5. Saves -> `PUT /api/admin/groups/{name}/config`; returns to the list with refreshed badges

- Slop cut: the v2 bottom-of-page "Configure group" preview is deleted - same scale problem as users; group config is a dedicated screen; a section that is off collapses and is omitted from the payload

**Flow 6 - Reorder priority** - GRP-001 drag handle or move up/down -> `POST /api/admin/groups/reorder`; higher priority wins on conflict (the resolve order)

**Flow 7 - Delete a group** - GRP-001 row -> Delete -> inline confirm "removes all users from this group" -> `DELETE /api/admin/groups/{name}/delete`; no screen for a confirm

### Domain: Servers

The daily operate surface. One list carrying the live monitor's columns and the lifecycle actions on every row, with a light detail for the rare deep look.

**Flow 8 - Triage and reclaim a server**

1. Admin on **SRV-001**; scans Status (Active / Idle Xm / Spawning / Stopped / Failed) alongside the resource columns - Activity (24h engagement meter + %), CPU, Memory, GPU, Volumes, System (writable layer), Time-left - to find idle or wasteful holders of resources
2. Per-row actions by state: Stopped -> **Start** (spawns for the user; admin stays on the list - starting is not entering); Running -> **Enter** (confirm popup "Enter <user>'s running server? You will be acting in their session" before navigating) / Restart / Stop; Spawning -> view live log / Cancel; Failed -> view error / Relaunch
3. SRV-001 also sorts by any column, badges quota overflow (volume / memory / container-extra-space) and carries Reset-samples + Report in its toolbar - the old Activity page is fully absorbed, nothing lost
4. For the deep look the row expands to current status + the live spawn log (during spawn); **SRV-002** stays light because no per-server history or persistent log exists
5. Stop -> `DELETE /api/users/{user}/server`; start -> `POST /api/users/{user}/server`; restart -> `POST .../restart-server`; enter -> admin spawn/open for that user

- Slop cut: image column gone (uniform, no decision); uptime gone (Time-left is the actionable countdown); Auth column dropped here (authorisation is a Users-page concern); Activity-as-a-page gone (its columns and deep tools moved onto Servers, not a second surface)
- Admin safety: start any server freely, but entering another user's session is always a deliberate, confirmed second click

### Domain: Self-service (user)

**Flow 9 - User runs their lab**

1. User on **OVR-100** (launchpad); one hero card is their server
2. Stopped -> **Start** -> **SPN-001** options (if any) -> **SPN-002** pending (SSE progress) -> lab opens
3. Running -> Open / Restart / Stop; Idle -> Time-left shown; **Extend session** -> **SELF-002** (culler enabled + active); **Manage volumes** -> **SELF-001** (server stopped only)
4. Read-only "what your groups grant" (effective access) + groups; change password and API tokens via the user-menu

- Slop cut: no fleet pages, no Administration section for a user; the launchpad is the whole portal for them

### Domain: Broadcast and platform

**Flow 10 - Broadcast a notification** - topbar megaphone -> **BRD-001**: message (140-char counter), type, auto-close, recipients (all or per-user) -> Send -> results table (delivered X/Y, per-user status) -> `POST /api/notifications/broadcast`

**Flow 11 - Review platform config** - sidebar -> **SET-001**: rows by category, a static read-only reference of the running configuration (what is set, not an editor). Decision locked: no in-place editing now; in-place change is a future option, not built yet. `JUPYTERHUB_ADMIN_PASSWORD` stays hidden by design

**Flow 12 - First-admin bootstrap** - **AUTH-002** signup window, kept server-rendered (pre-session, owned by the authenticator); the SPA does not mount before login

## Slop reduction ledger

Every cut traces to a flow that did not need the thing.

- **Bottom-of-list edit previews** (user + group) -> dedicated detail screens (Flows 3, 5) - the scale-killer
- **Access tab, Keys tab** on the user (Flow 3) - showed nothing actionable; we issue no per-user tokens, API keys are a group pool
- **Per-user password entry in bulk** (Flow 2) - auto-generate + force-change switch instead
- **Image column, uptime** on servers (Flow 8) - no decision rides on them
- **Activity as a separate page** (Flow 8) - it is columns on Servers
- **Policies as a separate page** (Flow 5) - it is the group config
- **Confirm-as-a-screen** (Flow 7) - inline dialog for delete/reset
- **Personal API tokens as primary nav** - real but niche; demoted to the user-menu (`/hub/token`)
- **Named servers (multiple per user)** - real capability, kept but secondary; most users have one, so it does not earn a primary surface (revisit if multi-server becomes common)
- **Mobile as a fork** - one responsive component tree, not a parallel `mobile.js` set of screens

## Decisions and naming (locked)

- **Events, not Logs** - the "recent events" widget drills into **EVT-001 Events**, an audit timeline of actions (user created, group policy changed, server culled, broadcast sent); "Logs" (raw hub/container process output) is a separate technical concern, out of scope now, a future Advanced item if ever needed
- **Broadcast vs Notifications - two concepts, two controls** - **Broadcast** (BRD-001) is outgoing: admin -> all or selected active labs, from the topbar megaphone (the current hub mislabels this page "Notifications"); the **bell** is incoming - the admin's own notification inbox; naming the outgoing one with the verb "Broadcast" ends the ambiguity; BRD-001 is a focused composer, not embedded in Servers or Activity, and reads the active-server list only to target per-user recipients
- **Resources wide widget, Groups card dropped** - on OVR-001 the Groups count card is removed (a group count is not a monitoring signal; Groups stays in the sidebar) and the GPU card becomes a wide **Resources** widget spanning two columns: three bars (CPU, Memory, GPU) for platform/host utilisation; the top row reads Servers | Users | Resources (x2). On OVR-100 the user hero shows the same three bars for their own server
- **Status and Activity are distinct columns (reversal)** - an earlier revision merged them into one column on the theory that a running server "simply reads Active or Idle". Reviewing the live hub's Activity Monitor (which the operator endorsed) reversed that: the two answer different questions. **Status** is the instantaneous lifecycle that drives the action set (Active / Idle Xm / Spawning / Stopped / Failed); **Activity** is the 24h engagement trend (5-segment meter + %, red low / amber mid / green high, from `activity_score`) that drives capacity and cleanup decisions. The meter is the Activity column, not an inline badge on the Status pill. Every column and its manifestation was thought out against the live page rather than copied
- **User cells show identity, not membership** - the Servers list shows the username and role (admin is a role, fine to show), never a group name under it; a user can be in dozens of groups, so a single group sub-line is arbitrary and misleading - membership belongs to Users/Groups, not the server list
- **Admin starts a server without entering it** - SRV-001 play is state-aware: Stopped -> Start (admin stays on the list); Running -> Enter, gated by a confirm popup; starting is never entering, entering another user's lab is always a deliberate confirmed act
- **The Activity Monitor is absorbed into Servers, columns and all** - SRV-001 carries the live monitor's columns (Status, Activity, CPU, Memory, GPU, Volumes, System, Time-left), sortable headers, quota-warning cells (memory / total volumes / container writable layer turn danger with a triangle and the threshold in the tooltip) and Reset-samples / Report / Refresh in the toolbar, and adds the lifecycle actions the monitor lacked (start / stop / restart / enter / manage-volumes). The standalone Activity page retires with nothing lost. Resource cells show `--` when the server is stopped, except Volumes which persists; per-mount, memory-total and writable-vs-base breakdowns live in each cell's tooltip
- **SRV-002 stays light** - no per-server history and the spawn log is live-only, so the deep view is current status + live spawn log; likely an inline expandable row, not a full screen

## Refinement round - scale and coherence

Driven by the operator after reviewing the rebuilt mock: make it logical and make it hold up when users number in the hundreds-to-thousands and groups in the dozens-to-hundreds. The mock stays static (no real API); interaction-critical behaviour is wired for real over the sample rows / in-script corpora, and pagination is represented visually.

**Design principles (govern every choice here):** purpose first - a control earns its place by the decision it drives; the visual metaphor (bar / meter / pill) carries the glance while precise values live in the tooltip; colour alone signals a threshold breach (no warning icon); the mock shows the target design - no implementation-tracking badges ("net-new") on screen, backend gaps tracked in this doc only.

**Three reusable patterns** (in `assets/app.js` / `assets/app.css`, applied across pages):
- **Scaled list** (`data-list`) - servers, users, groups, events, tokens each lead with a wired search, scope-filter pills (the default scope is never "everything" - Servers default to Active, Stopped behind its pill), sortable headers, a no-results state, and a visual pager. Rows carry `data-text` / `data-scope` / `data-sort-<key>`
- **Typeahead combobox** (`data-combo="groups|users"`) - replaces every `<select>` / fake-autocomplete membership picker (a port of the live hub's admin chip editor): type to filter the corpus, Enter/Tab/click to add, x to remove. Used in Configure user (groups), new-user, bulk-users, Configure group (members)
- **Relationship at scale** - Configure group gains a **Members** tab (typeahead add + a searchable, paged member list with per-row remove); display chip lists cap at a few with a `+N` that expands (`data-chips`); the Users list shows a group **count** that drills in, and group member counts drill in - neither enumerates names in a tooltip

**Configure user / group are full screens (supersedes the P5 edit-as-drawer decision):** both entities carry too much config for a side panel, and a list row should never open a cramped panel for a heavy entity. `user-config.html` (USR-005): Profile (avatar, first/last name, email, change-password, role, authorised) / Groups / Volumes. `group-config.html` (GRP-003): General (name, description, priority) / Policy (the nine sections) / Members. One Save per screen. The user-edit drawer is removed (and later BRD-001 too - see the Navigation follow-up; no feature uses a drawer now).

**Per-element refinements:** Activity is a meter only, the % in its tooltip (not inline); quota breaches (memory / volumes / writable layer) are colour-only; the Users list drops the email sub-line (email lives on the Profile tab); new-user has one password field pre-filled with a generated value that the admin types over (no "set manually" mode); the Overview active-servers mini-table un-clubs Status and Activity into separate columns to match Servers; the Users list drops the Role column - role is binary (user/admin), so a near-constant column is wasted and admins are flagged by an inline accent tag beside the name; membership chips and the member-remove control use a clean x (close) glyph instead of the stop square, so add (typeahead) and remove (x) read as one visual language; the back-link chevron is dropped from the config/create screens - an unsized inline SVG rendered it oversized, and a forward > on a Back link was wrong regardless.

**Navigation follow-up - Events and Notifications promoted into Administration:** both were off-rail (Events via the Overview widget + palette, Broadcast via a topbar megaphone). They now sit in the Administration nav - **Events** as a page (`events.html`), **Notifications** as a full screen (`notifications.html`) split into send (left, the broadcast composer) and past notifications (right, the sent history). This reverses the P6 "Broadcast is a drawer" decision: the right-side overlay with a large icon was the wrong home for it, so it becomes a screen and the drawer subsystem (host, composer, `data-open-drawer`/`data-nav-action` wiring) is removed entirely - no feature uses a drawer any more. The topbar drops both action icons (theme toggle and the megaphone), keeping only the breadcrumb and Cmd-K; the **theme toggle relocates to the sidebar foot** beside sign-out so theme switching survives. The Groups priority list also gains drag-by-row-number reordering (the # column is the drag handle) plus up/down arrows, retiring the standalone drag ellipsis; and the policy / effective-access grant rows get distinct per-row icons (GPU, Memory, CPU, Docker, Volumes, Downloads, Environment no longer share the cpu/shield/server glyphs). Finally, **Servers moves into Administration** as well: with Overview the only thing left to "operate", the Operate group dissolves - Overview stands alone at the top of the rail (headerless) and a single role-gated Administration section holds Servers, Users, Groups, Events, Notifications and Advanced. This supersedes the earlier Operate-vs-Administration (live-system vs configuration) split.

**Consistency pass - one interaction language (no ambiguities):** after a rapid iteration round an adversarial critic sweep drove a codification of the interaction language, now applied across every screen. **Remove/delete is always the `×` close glyph** (the filled square is reserved for an actual server stop/cancel-spawn) - the groups Delete buttons were the last holdout. **Colour equals state on one palette** - `.tag.ok` (green: active/created/success), `.tag.warn` (amber: idle/pending), `.tag.danger` (red: error/failed), `.tag.accent` (cyan: neutral emphasis) - so colour alone carries the signal on pills, tags and meters alike (previously error rendered amber and success grey). **Buttons**: dense list rows are icon-only with tooltips, `btn-primary` is reserved for a screen's submit/CTA, a single consequential row action may be labelled (Change password stays a secondary `btn-sm`). **Back**: the footer Cancel is the back/discard path on every full screen, back-links are bare text, and the page-head ghost-Back on the create screens was dropped. **Config screens are symmetric**: user-config, group-config and the new LAB-001 all use one bottom action footer (destructive left, Cancel/Save right). Navigation orphans were closed (the Overview Broadcast shortcut now opens Notifications; the Servers nav badge was dropped; Manage-volumes shows only on stopped server rows where it works). The Users dashboard widget became action-oriented (pending / never-logged-in / inactive 30d+) with matching scope pills on the Users list, and the avatars/initials were dropped everywhere. New **LAB-001 Lab Container** defines the spawned image and volume set, the source the user Volumes tab reads its names/mounts/descriptions from. Removed dead code (`.act`, `.avatar`, drawer host) and the user-config Effective-access section. Out of scope: mobile navigation (the rail hides under 860px with no replacement - desktop admin design for now).

## Design language - control vocabulary

The control layer was unified into one named system (live reference: `design-system.html`, a mock-only palette).

- **Action buttons** - one class per button, two axes: context sets size, variant sets colour, never stacked. Contexts `page` (form / page-head, the Save baseline), `list` (dense table-row, more compact), `input` (inline with a field), `list-icon` (icon-only square). Variants `primary` (filled accent), `secondary` (bordered neutral), `dangerous` (red), `disabled` (muted, inert). The old `btn`/`btn-sm`/`btn-primary`/`btn-danger`/`btn-ghost`/`icon-btn` vocabulary is retired. Change-password on the Users list is `list-primary` (no icon) at the operator's call; Stop / Cancel-spawn / Remove / Delete are `list-icon-dangerous`
- **Labels** - pills, tags and chips share one slightly-rounded-rectangle shape (was a stadium pill). Passive by default; an active label carries a remove `×` that reveals on hover - defined in the language, ready to use, no page rolls it out yet. Status-pill dots stay circular
- **Help in tooltips, notes for designers** - field help lives in the control's `title` tooltip, not inline; visible explanatory commentary uses a dashed `Note:` box (`.note`). Screens stay minimal
- **Compact + zebra** - controls use compact padding; list rows get a JS-applied alternating tint that survives filter and sort (CSS `nth-child` would miscount hidden rows)
- **Create reuses Configure** - `new-user.html` is the `user-config.html` tabbed screen (Profile / Groups) with mode cues toggled: no rename acknowledgement, no Created/Last-active, no Remove user; Admin off, Authorise on, an initial password and require-change-at-first-login. One design, elements switched on/off to stay robust
- **Icons** - Settings/Configure uses a clean gear; Tokens / API-keys / Change-password a classic key matching the original hub
- **Lab Container** - lists only custom mounts (the three standard volumes are platform-managed, called out in a Note); custom names are fully qualified (`jupyterhub_shared`); the view is full width; disabled inputs render explicitly inert (dashed, muted)

## Backend reality - corrections and net-new

From the five code sweeps. The backend is healthy and most flows map to real endpoints; these are the deltas.

Corrections (the flow named the wrong mechanism):

- **Authorize is a toggle, not a PATCH** - USR-001 pending Authorize/Discard and the USR-005 Authorized switch call `/authorize/{user}` and `/discard/{user}` (NativeAuthenticator), not `PATCH /api/users/{user}`; re-clicking toggles
- **Passwords are auto-generated today** - single + bulk create both auto-generate (xkcd) and cache for retrieval via `POST /api/admin/credentials`; the result-screen copy/download is real

Net-new backend work (the design assumes it; it does not exist yet - build or drop, per item):

- **Manual password at create** (USR-002) - the seed flow wants an optional hand-typed password; creation is auto-gen only today
- **Authorize-later at create** (USR-002/003) - every created user is auto-authorized today; deferring needs the creation path to skip the flag
- **Require password change on first login** (USR-003) - no `UserInfo` field exists; needs schema + login-hook change
- **Per-user effective-policy read** (OVR-100 "what your groups grant") - `policy_summary` is computed per group for admins; no per-user resolved-policy read endpoint exists for a user to see their own grants
- **Events/audit source** (EVT-001) - no event store exists; minimal source = SQLAlchemy listeners on the mutations already tracked (user/group/server) + broadcast-sent, written to a small append log
- **Bulk partial-failure reporting** (USR-004) - the result must show per-user success/failure; do not assume atomic all-or-nothing
- **GPU utilisation data** (Resources bars) - CPU/Mem are in `GET /api/activity`; per-server GPU utilisation is not (GPU is group-granted, not sampled); the GPU bar needs a stats source or shows allocation, not live use

Keep (real capabilities the flows must not drop): autocomplete group chips, copy/download credentials, rename via `PATCH` (a USR-005 action), policy badges + "click to configure" tooltip from `policy_summary`, member-count hover list, shared-volume quick-add, drag-reorder plus move up/down for keyboard users.

## Critic pass - independent review

An independent xhigh review attacked the scheme adversarially (separate model, no shared context, prompted to find flaws, not validate). Disposition:

- **Bell removed (P1)** - the topbar carried a broadcast megaphone AND a notifications bell, but the backend has only outbound broadcast; there is no inbox endpoint. Two notification metaphors where one exists -> the bell is deleted until an incoming-notification source is real
- **Effective-access readout added (P2)** - folding Policies into per-group config left policy visible one group at a time only; an admin could not see what a user can actually do (resolved across groups). Fixed without a new tab: the USR-005 Groups tab now carries a read-only Effective-access panel (resolved grants, winning group cited), the same per-user resolve the user sees on OVR-100; closes a security blind spot during incident response
- **Edit = drawer, create = full screen (P5)** - full-page routing for every edit destroyed list context for cheap changes; resolution: heavy create stays a full screen (USR-002/003, GRP-002/003), editing an existing user is a right-side drawer over the list, one Save not per-tab, cheap toggles inline on the row
- **Plain-user sidebar header dropped (P6)** - a section header over a single Overview link is noise
- **Operate/Administration rationale fixed (P6)** - reframed from frequency x stakes (did not predict location) to live-system vs configuration (does)
- **Broadcast is a drawer (P6)** - a routed page reachable by one glyph had no breadcrumb home; an overlay drawer closes back to context and removes the orphan; Events keeps a stable breadcrumb home (Overview)

Resolved calls (no open decisions remain):

- **Tokens + Advanced (P4) - resolved (a)** - Advanced now holds **Settings + Tokens** (both occasional), so the primary rail is lean (Overview, Servers, Users, Groups) and Advanced is no longer a one-item menu; Tokens stays under Advanced per the operator's instruction, with `Cmd-K` as the admin fast-path (one keystroke, not two disclosure clicks). Reversible if the operator prefers Tokens in the user-menu for everyone
- **Activity merge (P3) - reversed (un-merge)** - the brief one-column merge was undone after the operator reviewed the live Activity Monitor and asked for its full column set restored. SRV-001 now carries Status and Activity as distinct columns plus the live monitor's resource columns, and adds the lifecycle actions the monitor lacked. This lands where the critic originally argued (un-merge); the decision is the operator's, grounded in the live page
- **Per-tab save (P5) - resolved** - USR-005 commits once for the whole user, not per tab (Flow 3)

## Build backlog (mock, next)

What the mock becomes once the scheme is agreed, by ref. Net new screens are the create/detail/bulk ones the laws demand.

- New screens (full): **USR-002** new user, **USR-003** bulk input, **USR-004** bulk result, **GRP-002** new group, **GRP-003** group config
- New full screens: **USR-005** Configure user (`user-config.html`: Profile / Groups + effective access / Volumes); **GRP-003** gains General + Members tabs. **BRD-001** Notifications is a full screen (send + sent history); all drawers removed - see Refinement round
- New: **EVT-001** Events timeline (needs the net-new event source), **SRV-002** light row-expand (current status + live spawn log)
- Changed: **USR-001** (Add + Bulk lead to full screens; row opens the Configure-user screen; authorize inline; pending-on-top kept), **GRP-001** (Add + row navigate; drop bottom preview), **SRV-001** (all users' server state; full monitor columns - Status, Activity, CPU, Memory, GPU, Volumes, System, Time-left - plus lifecycle actions, sort, quota-warning cells, Reset/Report/Refresh toolbar, light row-expand), **OVR-001** (Groups card -> wide Resources widget; events widget -> EVT-001)
- Removed from v2: the inline "Configure user"/"Configure group" preview panels; the Keys user tab; the topbar notifications bell (no backend)
- Unchanged: the role-aware shell, the token system, the visual language
