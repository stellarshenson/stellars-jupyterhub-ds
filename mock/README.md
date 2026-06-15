# Optimum Hub - frontend mock

A static HTML/CSS/JS prototype of a redesigned JupyterHub portal. Design exploration only - **not wired to the hub, no build step, nothing calls a real API**. Open `home.html` (admin) or `home-user.html` (plain user).

The design that drives this mock is `design-flows-frontend-mock.md` (flows, navigation laws, screen registry, decisions). This tree is built against those screen refs.

## Philosophy

Reduce the cognitive and navigation burden on users and admins, surface actionable information, and let the most frequent and necessary actions be done simply. The portal is built to manage **dozens up to a few hundred users (not thousands) and dozens of policies** - so search, filter, sort and pagination are about comfort at hundreds, not survival at thousands.

In practice: navigate to nouns, not views - one entity, one place. The Home dashboard sits on top; everything you manage - the live servers and the configuration - lives under one role-gated Administration section. Every dashboard widget is a mini-view that drills into its page (the whole widget header is a link). Show only what drives a decision, and let the visual metaphor carry the glance while exact values live in the tooltip.

## Navigation

```
SIDEBAR (admin)                 SIDEBAR (user)
    Home           home.html      Home                (no header)
    Profile        profile.html   Profile             profile-user.html
  ADMINISTRATION
    Servers        servers.html
    Users          users.html
    Groups         groups.html
    Lab Container  lab-container.html
    Events         events.html
    Notifications  notifications.html
    Advanced v
      Settings     settings.html
      Tokens       tokens.html

TOPBAR        breadcrumb (Optimum Hub / [section /] page) · theme changer (light/dark/system)
SIDEBAR-FOOT  identity · sign out
OFF-RAIL      create + configure screens, reached from a list row; the breadcrumb
              parent (e.g. Users) is a link that returns to the list
VERSION       Optimum Hub 1.0.0 fixed bottom-right on every page
MOCK-ONLY     Home shows a dashed Admin / User / design switch - a reviewer helper
              (design opens the design-system palette), not part of the design
```

Navigation laws: list `Add` opens a full create screen; a list row opens a full detail/configure screen; a sub-page carries a breadcrumb whose parent crumb returns to the list (abandoning the action); detail tabs only if each earns its keep; bulk = input screen then result screen; delete/reset are inline confirms; every widget header is a chevron link to its page; long lists lead with a search field.

## Roles

Role-aware via `<body data-role>`:

- **Admin** (`home.html`) - the fleet Home dashboard, a personal Profile, plus a single Administration section (Servers, Users, Groups, Lab Container, Events, Notifications, Settings, Tokens). The admin runs a lab too, so Home also carries the personal server hero
- **User** (`home-user.html`) - Home (one launchpad: their server open/restart/stop + idle-TTL gadget, their groups read-only, their resources) and a personal Profile. No Administration, no fleet pages
- **Profile** (`profile.html` / `profile-user.html`) - both roles get a self-service Profile: edit own name, email and password only; username is read-only and the admin-only controls (authorisation, admin flag, require-change) are absent. No groups or volumes tabs - a user cannot change those

## Key decisions in the mock

- **Servers fuses the live Activity Monitor with lifecycle actions** - the rich monitor columns (Status, Activity, CPU, Memory, GPU, Volumes, System, Time-left) plus start/stop/restart/enter/manage-volumes the monitor lacked. Status and Activity are kept as distinct columns - Status is the instantaneous lifecycle that drives the actions, Activity is the 24h engagement meter (the exact % in its tooltip). Quota breaches (memory / volumes / writable layer) are colour-only; Reset-samples / Report / Refresh sit in the toolbar. The standalone Activity page retires
- **Resources widget** - CPU / Memory / GPU as three bars (a wide widget on the admin Overview, the hero block on the user launchpad); the lone GPU tile and the Groups count card are gone
- **Admin starts a server without entering it** - Start spawns it for the user and the admin stays on the list; entering a running server is a second, confirmed action
- **User cells show identity, not membership** - username only; role is binary (user/admin), so there is no Role column - admins carry an inline *admin* tag beside the name. A user can be in dozens of groups, so the Users list caps the group chips at a few with a `+N` that reveals the rest; the username links to the full Configure-user screen
- **Configure user / group = full screens** - both carry too much config for a side panel, so each opens a dedicated tabbed screen from its list row (`user-config.html`: Profile / Groups / Volumes; `group-config.html`: General / Policy / Members). One Save per screen
- **Events and Notifications live in Administration** - Events (the audit timeline behind the Overview feed) is a nav page, not Logs; **Notifications** is a full screen split into send (left, the broadcast composer) and past notifications (right, the sent history) - outgoing only, distinct from any inbox (the bell was removed, no backend). The topbar keeps only the breadcrumb and Cmd-K; the theme toggle moved to the sidebar foot

## Built for the right scale (hundreds, not thousands)

The target is dozens up to a few hundred users and dozens of policies/groups - so the list machinery is about staying comfortable at hundreds, not surviving thousands (no virtualization). Three reusable patterns, wired for real over the sample rows (the pager is the only illustrative part):

- **Scaled list** - every list (servers, users, groups, events, tokens) leads with a wired search, state-coloured scope-filter pills (default never "everything"), sortable headers, a no-results state and a pager. Try typing in a filter, clicking a scope pill, or a column header
- **Typeahead combobox** - every membership picker (add to group, add a member) is a type-to-filter chip input, not a `<select>`. A port of the live hub's admin chip editor
- **Relationship at scale** - `group-config.html` has a Members tab (typeahead add + a searchable, paged member list); long chip lists cap at a few with a `+N` that expands; counts drill in instead of tooltips enumerating every name
- **Policy as data** - a group's policy downloads/uploads as JSON on Configure group (upload is validated, then applied and the screen refreshes); the Groups list imports a JSON of many groups and exports a chosen subset via a check/uncheck export screen (`groups-export.html`)

Design principles applied throughout: purpose first; the visual metaphor (bar / meter / pill) carries the glance while precise values live in the tooltip; colour alone signals a threshold breach; the mock shows the target design (no implementation-tracking badges - backend gaps are tracked in the design doc).

## Consistency rules (interaction language)

One language across every screen, so the portal reads as one system with no ambiguity. The live reference is `design-system.html` (mock-only palette).

- **Action buttons** - one class per button: context (size) x variant (colour), never stacked. Contexts: `page` (form / page-head, the Save baseline), `list` (dense table-row action, more compact), `input` (inline with a field - matches the field height and almost blends into it; content can be text, icon+text or icon-only), `list-icon` (icon-only square). Variants: `primary` (filled accent CTA), `secondary` (bordered neutral), `dangerous` (red), `disabled` (muted, inert); the `input` context uses `warning` (amber) in place of `dangerous`. E.g. Save = `page-primary`, Change password = `list-secondary`, Generate = `input-secondary`, Set lab image = `input-primary`, Stop = `list-icon-dangerous`
- **Sortable monitors with tooltips** - the Servers and Users tables sort on every meaningful column (Servers: user / status / activity / cpu / memory / volumes / system / time-left; Users: user / authorised / created / last-seen / activity); every column header and cell carries a `title` tooltip (the metaphor in the glance, the precise value + context on hover)
- **Labels** - pills, tags and chips are one slightly-rounded-rectangle shape. Passive by default (no action); active carries a remove `×` that reveals on hover. Status-pill dots stay circular
- **Colour = state** - green `ok` (active / authorised / success), amber `warn` (idle / inactive / pending), red `danger` (error / blocked / unauthorised), cyan `accent` for neutral emphasis and aggregates (the `All` filter); pills, tags, meters and scope filters share the one palette, and colour alone carries the signal
- **Remove / delete = `×`** - the close glyph is the single remove/delete affordance (chip, member, group, user, volume); the filled square is reserved for an actual server *stop* / cancel-spawn
- **Help in tooltips** - field help and hints live in the control's `title` tooltip, never inline; visible designer/explanatory commentary uses a dashed `Note:` box (`.note`). Screens stay minimal
- **Back** - the footer Cancel is the back/discard path on every full screen; back-links are bare text (no glyph); the topbar breadcrumb shows location
- **Config screens** - heavy entities (user, group) and Lab Container open full tabbed screens with one bottom action footer: destructive on the left, Cancel/Save on the right. Create and Configure share one underlying design - Create just switches elements off (no rename acknowledgement, no Created/Last-active, no Remove) and others on (initial password, require-change-at-first-login)
- **Compact + zebra** - controls use compact padding; list rows carry a subtle alternating tint, applied by JS so it survives filtering and sorting
- **List filters** - scope-filter pills colour by state and double as counts (servers Active green / Idle amber / Offline grey; users Authorised green / Inactive amber / Unauthorised red); the aggregate `All` pill is the accent blue; dim by default, the active filter lit with an accent ring. Enumeration columns (Status, Authorised) note "filter with the pills above" in the header tooltip
- **Notices** - the in-UI confirmation/status line: a subtle bar with a coloured left edge and a sized glyph (success / warning / info / error), mirroring the live hub. Shown directly under the action that produced it - under Set lab image, and as the post-save confirmation when you press Save (Save validates and persists; there is no separate "set password" button)
- **Navigate out** - a dashboard widget's whole card-head is a link to its full page: title plus a chevron, no "View all" text, reusing the metric cards' chevron
- **Adaptive config width** - a tabbed config card resizes to its active tab (narrow Profile form, wider Groups / Members table) so the footer Save / Cancel stay beside the content
- **Identity in lists** - a username shows its full name stacked below in muted text; with no full name the username sits centred on one line

## Try it

- Toggle theme with the sun/moon button (persists in `localStorage`)
- `Cmd/Ctrl+K` for the command palette (role-scoped); `Advanced` in the sidebar expands to Settings + Tokens
- Type in any list's filter, click a scope pill, sort a column; add a group via the typeahead in Configure user; open Configure group -> Members
- Click a username to open Configure-user; open Configure group -> Policy to download / upload a validated policy; Groups -> Export to check/uncheck groups; Settings -> Full reference for every env var
- Open **Profile** (either role) to edit your own details; click a section widget's header (chevron) to jump to its full page; sub-pages return via the breadcrumb parent
- Flip the dashed **Admin / User** switch on Home to see both roles; the **design** link opens the control palette (`design-system.html`) - all mock-only helpers
- Buttons fire mock toasts; nothing calls a real API

## Layout

```
mock/
  index.html         redirect to home
  home.html          admin Home (fleet dashboard + the admin's own server hero)
  home-user.html     plain-user Home (launchpad: server controls + idle-TTL gadget + resources)
  profile.html       self-service Profile (admin) - own name/email/password, no other tabs
  profile-user.html  self-service Profile (user) - same screen, data-role="user"
  servers.html       every lab - monitor columns + lifecycle actions; Active/Idle/Offline/All scope filters
  users.html         pending-on-top + scaled authorised list (state filters: Authorised/Inactive/Unauthorised/All; full name under username)
  user-config.html   Configure user - tabbed screen (Profile / Groups / Volumes), adaptive width, bottom action footer
  new-user.html      single create (full screen) - one password field + typeahead groups
  bulk-users.html    bulk create input (full screen) - typeahead groups
  bulk-result.html   bulk credentials + download
  groups.html        priority groups -> policy - scaled list, drag-by-number reorder, type-only policy pills, import / export
  groups-export.html pick groups (check / uncheck) and export as one JSON bundle
  new-group.html     create group (full screen)
  group-config.html  Configure group - tabbed (General / Policy: download+upload validated / Members), adaptive width
  lab-container.html Lab Container - the spawned image + custom volume set (standard volumes platform-managed)
  design-system.html mock-only control palette - the design language shown live (buttons, labels, filters, notices, inputs)
  events.html        audit timeline - scaled list (type scope pills, search, pager)
  notifications.html broadcast - send (left) + past notifications history filling the height (right)
  settings.html      read-only configuration summary + a Full reference link
  settings-reference.html  every platform env var with value + description, all 11 categories
  tokens.html        personal API tokens + OAuth apps
  design-flows-frontend-mock.md   the design that drives this tree (flows, nav laws, screen registry)
  assets/
    tokens.css       the two themes as CSS custom properties
    app.css          shell + components
    app.js           role-aware shell render + theme + Cmd-K + tabs + scale behaviours + mock role-switch
    brand/           logo + favicon (from ../branding)
```

## Status

Mock for design review. The rebuild concept and the hub-as-trust-boundary security model live in `../docs/portal-ui-catalogue.md`; the flow-driven navigation design (with net-new backend work flagged) is in `design-flows-frontend-mock.md`.
