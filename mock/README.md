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

- **One Status column** - lifecycle and engagement are one axis: Active / Idle Xm / Spawning / Stopped / Failed, with a 5-segment engagement meter inline on running rows. No separate Activity column or page (its Reset/Report tools live in the Servers toolbar)
- **Resources widget** - CPU / Memory / GPU as three bars (a wide widget on the admin Overview, the hero block on the user launchpad); the lone GPU tile and the Groups count card are gone
- **Admin starts a server without entering it** - Start spawns it for the user and the admin stays on the list; entering a running server is a second, confirmed action
- **User cells show identity, not membership** - username and role only; a user can be in dozens of groups, so no group sub-line
- **Edit = drawer, create = full screen** - editing a user opens a drawer over the list (one Save, tabs Profile / Groups + effective access / Volumes); creating is a dedicated screen
- **Events, not Logs** - the audit timeline behind the Overview feed; **Broadcast** (outgoing) is a topbar drawer, distinct from any inbox (the bell was removed - no backend for it)

## Try it

- Toggle theme with the sun/moon button (persists in `localStorage`)
- `Cmd/Ctrl+K` for the command palette (role-scoped); `Advanced` in the sidebar expands to Settings + Tokens
- Click a user's Configure to open the edit drawer; the topbar megaphone opens Broadcast
- Buttons fire mock toasts; nothing calls a real API

## Layout

```
mock/
  index.html         redirect to home
  home.html          admin Overview (fleet dashboard)
  home-user.html     plain-user Overview (launchpad)
  servers.html       every lab - one Status column, resources, time-left
  users.html         pending-on-top + authorised list + USR-005 edit drawer
  new-user.html      single create (full screen)
  bulk-users.html    bulk create input (full screen)
  bulk-result.html   bulk credentials + download
  groups.html        priority groups -> policy
  new-group.html     create group (full screen)
  group-config.html  the nine policy sections (full screen)
  events.html        audit timeline
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
