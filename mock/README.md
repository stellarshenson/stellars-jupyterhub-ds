# Optimum Hub - frontend mock

A static HTML/CSS/JS prototype of a redesigned JupyterHub portal. Design exploration only - **not wired to the hub, no build step, nothing calls a real API**. Open `home.html` (admin) or `home-user.html` (plain user).

The design that drives this mock is `design-flows-frontend-mock.md` (flows, navigation laws, screen registry, decisions). This tree is built against those screen refs.

## The idea

Navigate to nouns, not views. One entity, one place. The Overview dashboard sits on top; everything you manage - the live servers and the configuration - lives under one role-gated Administration section. Every dashboard widget is a mini-view that drills into its page. Show only what drives a decision, and let the visual metaphor carry the glance while exact values live in the tooltip.

## Navigation

```
SIDEBAR (admin)                 SIDEBAR (user)
    Overview      home.html       Overview            (no header - one item)
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

TOPBAR        breadcrumb · Cmd-K (no action icons)
SIDEBAR-FOOT  identity · theme toggle · sign out
OFF-RAIL      create + configure screens, reached from their list row
MOCK-ONLY     Overview shows a dashed Admin / User / design switch - a helper
              for reviewers (design opens the design-system palette), not part
              of the design
```

Navigation laws: list `Add` opens a full create screen; a list row opens a full detail/configure screen; detail tabs only if each earns its keep; bulk = input screen then result screen; delete/reset are inline confirms; every widget links to its page; long lists lead with a search field.

## Roles

Role-aware via `<body data-role>`:

- **Admin** (`home.html`) - the fleet Overview dashboard plus a single Administration section (Servers, Users, Groups, Events, Notifications, Settings, Tokens)
- **User** (`home-user.html`) - one launchpad: their server (open/restart/stop), what their groups grant (read-only), their storage. No Administration, no fleet pages

## Key decisions in the mock

- **Servers fuses the live Activity Monitor with lifecycle actions** - the rich monitor columns (Status, Activity, CPU, Memory, GPU, Volumes, System, Time-left) plus start/stop/restart/enter/manage-volumes the monitor lacked. Status and Activity are kept as distinct columns - Status is the instantaneous lifecycle that drives the actions, Activity is the 24h engagement meter (the exact % in its tooltip). Quota breaches (memory / volumes / writable layer) are colour-only; Reset-samples / Report / Refresh sit in the toolbar. The standalone Activity page retires
- **Resources widget** - CPU / Memory / GPU as three bars (a wide widget on the admin Overview, the hero block on the user launchpad); the lone GPU tile and the Groups count card are gone
- **Admin starts a server without entering it** - Start spawns it for the user and the admin stays on the list; entering a running server is a second, confirmed action
- **User cells show identity, not membership** - username only; role is binary (user/admin), so there is no Role column - admins carry an inline *admin* tag beside the name. A user can be in dozens of groups, so the Users list caps the group chips at a few with a `+N` that reveals the rest; the username links to the full Configure-user screen
- **Configure user / group = full screens** - both carry too much config for a side panel, so each opens a dedicated tabbed screen from its list row (`user-config.html`: Profile / Groups / Volumes; `group-config.html`: General / Policy / Members). One Save per screen
- **Events and Notifications live in Administration** - Events (the audit timeline behind the Overview feed) is a nav page, not Logs; **Notifications** is a full screen split into send (left, the broadcast composer) and past notifications (right, the sent history) - outgoing only, distinct from any inbox (the bell was removed, no backend). The topbar keeps only the breadcrumb and Cmd-K; the theme toggle moved to the sidebar foot

## Built for scale (many users, many groups)

The mock holds up at hundreds-to-thousands of users and dozens-to-hundreds of groups. Three reusable patterns, wired for real over the sample rows (the pager is the only illustrative part):

- **Scaled list** - every list (servers, users, groups, events, tokens) leads with a wired search, scope-filter pills (default never "everything"), sortable headers, a no-results state and a pager. Try typing in a filter, clicking a scope pill, or a column header
- **Typeahead combobox** - every membership picker (add to group, add a member) is a type-to-filter chip input, not a `<select>` - it scales to hundreds of options. A port of the live hub's admin chip editor
- **Relationship at scale** - `group-config.html` gains a Members tab (typeahead add + a searchable, paged member list) so a 500-member group is manageable; long chip lists cap at a few with a `+N` that expands; counts drill in instead of tooltips enumerating every name

Design principles applied throughout: purpose first; the visual metaphor (bar / meter / pill) carries the glance while precise values live in the tooltip; colour alone signals a threshold breach; the mock shows the target design (no implementation-tracking badges - backend gaps are tracked in the design doc).

## Consistency rules (interaction language)

One language across every screen, so the portal reads as one system with no ambiguity. The live reference is `design-system.html` (mock-only palette).

- **Action buttons** - one class per button: context (size) x variant (colour), never stacked. Contexts: `page` (form / page-head, the Save baseline), `list` (dense table-row action, more compact), `input` (inline with a field - matches the field height and almost blends into it; content can be text, icon+text or icon-only), `list-icon` (icon-only square). Variants: `primary` (filled accent CTA), `secondary` (bordered neutral), `dangerous` (red), `disabled` (muted, inert); the `input` context uses `warning` (amber) in place of `dangerous`. E.g. Save = `page-primary`, Change password = `list-secondary`, Generate = `input-secondary`, Set lab image = `input-primary`, Stop = `list-icon-dangerous`
- **Sortable monitors with tooltips** - the Servers and Users tables sort on every meaningful column (Servers: user / status / activity / cpu / memory / volumes / system / time-left; Users: user / authorised / created / last-seen / activity); every column header and cell carries a `title` tooltip (the metaphor in the glance, the precise value + context on hover)
- **Labels** - pills, tags and chips are one slightly-rounded-rectangle shape. Passive by default (no action); active carries a remove `×` that reveals on hover. Status-pill dots stay circular
- **Colour = state** - green `ok` (active / created / success), amber `warn` (idle / pending), red `danger` (error / failed), cyan `accent` for neutral emphasis; pills, tags and meters share the one palette, and colour alone carries the signal
- **Remove / delete = `×`** - the close glyph is the single remove/delete affordance (chip, member, group, user, volume); the filled square is reserved for an actual server *stop* / cancel-spawn
- **Help in tooltips** - field help and hints live in the control's `title` tooltip, never inline; visible designer/explanatory commentary uses a dashed `Note:` box (`.note`). Screens stay minimal
- **Back** - the footer Cancel is the back/discard path on every full screen; back-links are bare text (no glyph); the topbar breadcrumb shows location
- **Config screens** - heavy entities (user, group) and Lab Container open full tabbed screens with one bottom action footer: destructive on the left, Cancel/Save on the right. Create and Configure share one underlying design - Create just switches elements off (no rename acknowledgement, no Created/Last-active, no Remove) and others on (initial password, require-change-at-first-login)
- **Compact + zebra** - controls use compact padding; list rows carry a subtle alternating tint, applied by JS so it survives filtering and sorting

## Try it

- Toggle theme with the sun/moon button (persists in `localStorage`)
- `Cmd/Ctrl+K` for the command palette (role-scoped); `Advanced` in the sidebar expands to Settings + Tokens
- Type in any list's filter, click a scope pill, sort a column; add a group via the typeahead in Configure user; open Configure group -> Members
- Click a username to open Configure-user; open Lab Container to see the locked core volumes + custom mounts; the Notifications nav item opens Broadcast
- Flip the dashed **Admin / User** switch on the Overview to see both roles; the **design** link opens the control palette (`design-system.html`) - all mock-only helpers
- Buttons fire mock toasts; nothing calls a real API

## Layout

```
mock/
  index.html         redirect to home
  home.html          admin Overview (fleet dashboard)
  home-user.html     plain-user Overview (launchpad)
  servers.html       every lab - monitor columns (status/activity/cpu/mem/gpu/volumes/system/time-left) + lifecycle actions + scope/search/sort
  users.html         pending-on-top + scaled authorised list (action scope pills, group chips, change-password)
  user-config.html   Configure user - full tabbed screen (Profile / Groups / Volumes), bottom action footer
  new-user.html      single create (full screen) - one password field + typeahead groups
  bulk-users.html    bulk create input (full screen) - typeahead groups
  bulk-result.html   bulk credentials + download
  groups.html        priority groups -> policy - scaled list, drag-by-number reorder, fill-with-counter policies
  new-group.html     create group (full screen)
  group-config.html  Configure group - full tabbed screen (General / Policy / Members), bottom action footer
  lab-container.html Lab Container - the spawned image + custom volume set (standard volumes platform-managed)
  design-system.html mock-only control palette - the design language shown live (buttons, labels, inputs)
  events.html        audit timeline - scaled list (type scope pills, search, pager)
  notifications.html broadcast - send (left) + past notifications (right), full screen
  settings.html      read-only configuration reference
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
