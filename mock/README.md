# Optimum Hub - frontend mock

A static HTML/CSS/JS prototype of a redesigned JupyterHub portal. Design exploration only - **not wired to the hub, no build step, nothing calls a real API**. Open `home.html` (admin) or `home-user.html` (plain user).

The design that drives this mock is `../docs/design-flows-frontend-mock.md` (flows, navigation laws, screen registry, decisions). This tree is built against those screen refs.

## The idea

Navigate to nouns, not views. One entity, one place. Split the chrome into what you *operate* (the live system) and what you *administer* (the configuration), gated by role. Every dashboard widget is a mini-view that drills into its page. Show only what drives a decision - and never split one thing into two (status and activity are one column, not two).

## Navigation

```
SIDEBAR (admin)                 SIDEBAR (user)
  OPERATE                         Overview            (no header - one item)
    Overview   home.html
    Servers    servers.html
  ADMINISTRATION
    Users      users.html
    Groups     groups.html
    Advanced v
      Settings settings.html
      Tokens   tokens.html

TOPBAR     breadcrumb · Cmd-K · theme · broadcast (admin) · user-menu
OFF-RAIL   Events (Overview widget + Cmd-K) · Broadcast (topbar drawer)
           create screens + edit drawers, reached from their list
```

Navigation laws: list `Add` opens a full create screen; a list row opens a detail (drawer for edits, full screen for heavy create); detail tabs only if each earns its keep; bulk = input screen then result screen; delete/reset are inline confirms; every widget links to its page; long lists lead with a search field.

## Roles

Role-aware via `<body data-role>`:

- **Admin** (`home.html`) - fleet Overview, Servers, and the Administration section
- **User** (`home-user.html`) - one launchpad: their server (open/restart/stop), what their groups grant (read-only), their storage. No Administration, no fleet pages

## Key decisions in the mock

- **Servers fuses the live Activity Monitor with lifecycle actions** - the rich monitor columns (Status, Activity, CPU, Memory, GPU, Volumes, System, Time-left) plus start/stop/restart/enter/manage-volumes the monitor lacked. Status and Activity are kept as distinct columns - Status is the instantaneous lifecycle that drives the actions, Activity is the 24h engagement meter (the exact % in its tooltip). Quota breaches (memory / volumes / writable layer) are colour-only; Reset-samples / Report / Refresh sit in the toolbar. The standalone Activity page retires
- **Resources widget** - CPU / Memory / GPU as three bars (a wide widget on the admin Overview, the hero block on the user launchpad); the lone GPU tile and the Groups count card are gone
- **Admin starts a server without entering it** - Start spawns it for the user and the admin stays on the list; entering a running server is a second, confirmed action
- **User cells show identity, not membership** - username and role only; a user can be in dozens of groups, so no group sub-line (the Users list shows a group *count* that drills in)
- **Configure user / group = full screens** - both carry too much config for a side panel, so each opens a dedicated tabbed screen from its list row (`user-config.html`: Profile / Groups / Volumes; `group-config.html`: General / Policy / Members). One Save per screen
- **Events, not Logs** - the audit timeline behind the Overview feed; **Broadcast** (outgoing) is a topbar drawer, distinct from any inbox (the bell was removed - no backend for it)

## Built for scale (many users, many groups)

The mock holds up at hundreds-to-thousands of users and dozens-to-hundreds of groups. Three reusable patterns, wired for real over the sample rows (the pager is the only illustrative part):

- **Scaled list** - every list (servers, users, groups, events, tokens) leads with a wired search, scope-filter pills (default never "everything"), sortable headers, a no-results state and a pager. Try typing in a filter, clicking a scope pill, or a column header
- **Typeahead combobox** - every membership picker (add to group, add a member) is a type-to-filter chip input, not a `<select>` - it scales to hundreds of options. A port of the live hub's admin chip editor
- **Relationship at scale** - `group-config.html` gains a Members tab (typeahead add + a searchable, paged member list) so a 500-member group is manageable; long chip lists cap at a few with a `+N` that expands; counts drill in instead of tooltips enumerating every name

Design principles applied throughout: purpose first; the visual metaphor (bar / meter / pill) carries the glance while precise values live in the tooltip; colour alone signals a threshold breach; the mock shows the target design (no implementation-tracking badges - backend gaps are tracked in the design doc).

## Try it

- Toggle theme with the sun/moon button (persists in `localStorage`)
- `Cmd/Ctrl+K` for the command palette (role-scoped); `Advanced` in the sidebar expands to Settings + Tokens
- Type in any list's filter, click a scope pill, sort a column; add a group via the typeahead in Configure user; open Configure group -> Members
- Click a user's Configure to open its full screen; the topbar megaphone opens Broadcast
- Buttons fire mock toasts; nothing calls a real API

## Layout

```
mock/
  index.html         redirect to home
  home.html          admin Overview (fleet dashboard)
  home-user.html     plain-user Overview (launchpad)
  servers.html       every lab - monitor columns (status/activity/cpu/mem/gpu/volumes/system/time-left) + lifecycle actions + scope/search/sort
  users.html         pending-on-top + scaled authorised list (groups as a count drill-in)
  user-config.html   Configure user - full tabbed screen (Profile / Groups / Volumes)
  new-user.html      single create (full screen) - one password field + typeahead groups
  bulk-users.html    bulk create input (full screen) - typeahead groups
  bulk-result.html   bulk credentials + download
  groups.html        priority groups -> policy - scaled list, member-count drill-in, capped policy chips
  new-group.html     create group (full screen)
  group-config.html  Configure group - full tabbed screen (General / Policy / Members)
  events.html        audit timeline - scaled list (type scope pills, search, pager)
  settings.html      read-only configuration reference
  tokens.html        personal API tokens + OAuth apps
  assets/
    tokens.css       the two themes as CSS custom properties
    app.css          shell + components
    app.js           role-aware shell render + theme + Cmd-K + drawer + tabs
    brand/           logo + favicon (from ../branding)
```

## Status

Mock for design review. The rebuild concept and the hub-as-trust-boundary security model live in `../docs/portal-ui-catalogue.md`; the flow-driven navigation design (with net-new backend work flagged) is in `../docs/design-flows-frontend-mock.md`.
