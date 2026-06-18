# Duoptimum Hub - web

The Duoptimum Hub JupyterHub portal: a React / Ant Design Pro SPA plus a thin JupyterHub integration layer, packaged together as the installable `duoptimum-hub-web` wheel. The hub serves the SPA at `/hub/portal` (a hub-rendered shell that injects a valid XSRF token), so it replaces the stock home/admin portal with real reads and real writes against the hub REST API. A `mock` data mode (the default `npm run build`) still runs standalone on fixtures for design work.

The flow-driven design that this build realises is `design-flows-frontend-mock.md` (navigation laws, screen registry by route, flows, the interaction language, backend reality).

## Philosophy

Reduce the cognitive and navigation burden on users and admins, surface actionable information, and let the most frequent and necessary actions be done simply. The portal manages **dozens up to a few hundred users (not thousands) and dozens of policies** - so search, filter, sort and pagination are about comfort at hundreds, not survival at thousands (no virtualization).

In practice: navigate to nouns, not views - one entity, one place. Home sits on top; everything an admin manages - the live servers and the configuration - lives under one role-gated Administration section. Every dashboard widget is a mini-view that drills into its page (the whole card header is a link). Show only what drives a decision, and let the visual metaphor carry the glance while exact values live in the tooltip.

## Stack

- **Vite + React 18 + TypeScript** - lean build, fast HMR
- **antd 5 + @ant-design/pro-components** - `ProLayout`, `ProTable`, `ProForm`, `ProCard`, `DragSortTable`; standard components first, custom only where antd has no JupyterHub equivalent
- **TanStack Query** - read hooks with loading / empty / error
- **react-router-dom 6** - routing + breadcrumb handles (`handle.crumb` / `handle.parent`)

## Data modes

A single `DataSource` interface has two implementations, selected by `VITE_DATA_MODE`:

- **mock** (default) - deterministic fixtures (`services/mockSource.ts`) shaped into view models; runs with no hub. The visible cast (alice, konrad, milan, nina) plus deterministic filler at realistic hundreds
- **live** - readonly GETs to the hub through the Vite dev proxy: `/users`, `/groups`, `/activity`, `/admin/groups`, `/users/{u}/session-info`, `/info`; auth rides the hub session cookie, no API token. Set `VITE_DATA_MODE=live` and `VITE_HUB_ORIGIN`. Hub-absent views fall back to the mock
- **Reads only** - the hub client (`services/hub/client.ts`) exposes no POST/PUT/DELETE; every action routes through `mockAction` and never mutates, so a real write cannot leak even in live mode

## Run

```bash
make install     # npm install
make dev         # dev server on :5180
make build       # typecheck + production build
make typecheck   # tsc -b --noEmit
make lint        # eslint
```

Copy `.env.example` to `.env.local` to switch modes. Open `http://localhost:5180`.

## Theme

- One token source (`src/theme/tokens.ts`) feeds both the antd `ConfigProvider` theme and the injected CSS variables the bespoke components read - so the antd surface and the hand-built meters / pills / bars never drift
- Three modes (light / dark / system) persisted in `localStorage`; dark uses antd `darkAlgorithm`, light `defaultAlgorithm`
- Palette transcribed from the Sublime greys + Stellars cyan set; the accent blue is tuned for legible name links and pill text in both themes

## Roles

Role-aware via `RoleContext` (admin default). One build serves both; the dashed **Admin / User / design** switch on Home is a reviewer helper, not part of the product:

- **Admin** - the fleet Home dashboard, a personal Profile, and a single Administration section (Servers, Users, Groups, Lab Container, Events, Notifications, Advanced -> Settings, Tokens). The admin runs a lab too, so Home also carries the personal server hero
- **User** - Home (one launchpad: their server open / restart / stop + idle-TTL gadget, their groups read-only, their resources) and a personal Profile. No Administration, no fleet pages
- **Profile** (both roles) - self-service: edit own name, email and password (type or generate) only; username read-only, admin-only controls (authorisation, admin flag, require-change) absent; no Groups or Volumes tabs

## Shell

`AppLayout` on `ProLayout` (`layout/`):

- **Sider** - the brand logo well, a role-gated `Menu` (Home, Profile, then the Administration group with the collapsible Advanced submenu), and a foot carrying identity + sign-out. **Collapsible**: a thin rectangular handle straddles the sider's right edge at mid-height; collapsed swaps the wide logo for the square `jl-logo` mark and the menu becomes an icon rail
- **Header / content** - the breadcrumb sits at the top of the content (`oh-topbar`, flush with the sider logo divider); the standard antd controls (language, theme) render via `actionsRender`; a read-only banner states the mocked contract
- **Footer** - Duoptimum Hub + JupyterHub versions as tags on one line with the JupyterHub / JupyterLab / Ant Design Pro stack chips
- **Command palette** - `Cmd/Ctrl+K`, role-scoped (go-to nav + actions)

## Bespoke components (`src/components/`)

The JupyterHub metaphors antd lacks, themed by the shared tokens: `StatusPill`, `ActivityMeter`, `Spark`, `ResourceBars`, `TtlGadget`, `GpuMeter` (per-device bars), `ServerHero`, `MetricCard`, `ScopeFilterPills`, `Notice`, `CappedTags` (+N), `Combo` (typeahead membership), `GroupPicker` (browse-and-add), `GroupPolicyTab` (the nine-section policy form), `IconAction`, `CardHeadLink`, `FormFooter`, `PageHeader`, `Icon`. The `/design-language` route shows the full system live in both themes (unlisted - URL only).

## Interaction language

One language across every screen, so the portal reads as one system. Verified live on `/design-language`.

- **Colour = state** - one palette: green ok (active / authorised), amber warn (idle / inactive), red danger (error / unauthorised), cyan accent for neutral emphasis and aggregates (the `All` filter). Pills, tags, meters and scope filters share it, and colour alone carries a threshold breach
- **State as pills** - lifecycle and type render as `StatusPill` (coloured dot + soft background); server / notification / event states never render as bare text
- **Scope-filter pills** - colour by state and double as counts; the default scope is never "everything"; inactive pills dim to .6, the active one is lit with an accent ring
- **Zebra rows on every table** - a global rule (`nth-child`) so alternating tint survives filter and sort; bespoke tables (the pending panel) match the `ProTable` cell padding
- **Short relative time everywhere** - `timeAgoShort` (2m / 5h / 3d / 4mo), the exact date in the cell tooltip
- **Tooltips everywhere** - the metaphor in the glance, the precise value + context on hover
- **Notices** - a coloured-left-edge status bar (success / info / warning / error), shown directly under the action that produced it
- **Remove / delete = `×`** - the close glyph is the single remove affordance; the filled square is reserved for an actual server stop / cancel-spawn
- **Config screens** - heavy entities (user, group) and Lab Container open full tabbed screens with one `FormFooter` (destructive left, Cancel / Save right). Create and Configure share one design with elements toggled
- **Identity in lists** - a username shows its full name stacked below in muted text; names and group chips are accent links into their Configure screen
- **Standard panel padding** - cards share one padding; whole card-heads are chevron links to their full page (no "View all" text)

## Routes / screens (`src/pages/`)

```
/home            Home - admin fleet dashboard (server hero, Servers/Users metrics, resources,
                 pending callout, active-servers preview, quick actions, recent events) or the
                 user launchpad
/profile         Profile - self-service (both roles)
/servers         Servers - fleet monitor + lifecycle actions; scope pills, sortable columns,
                 quota-breach colour cells, 25/50/100 pager
/users           Users - pending-authorisation panel (orange-bordered table) on top, then the
                 scaled list with state scope pills, inline authorise toggle, capped group chips
/users/new       New user (single) - one password field (type or generate) + GroupPicker
/users/bulk      Bulk add users (input) -> /users/bulk/result (credentials + download)
/users/:name     Configure user - tabbed (Profile / Groups / Volumes), built-in admin locked
/groups          Groups - priority-ordered DragSortTable, policy tags, JSON import / export
/groups/new      New group
/groups/export   Export groups - check / uncheck, download one JSON bundle
/groups/:name    Configure group - tabbed (General / Policy / Members); Policy = GroupPolicyTab
/lab-container   Lab Container - spawned image + volume set (platform volumes include / exclude)
/events          Events - audit timeline; 24h / 7d / 30d range drives the type-pill counts
/notifications   Notifications - send (composer, 140-char) + sent history
/settings        Settings - running configuration; signup is a live override Switch
/settings/reference  every platform env var, value + description
/tokens          personal API tokens + OAuth apps
/design-language /design-system  unlisted palette galleries
/login /signup   standalone auth screens (outside the app shell)
```

## Layout

```
src/
  theme/        tokens, antdTheme, cssVars, ThemeProvider
  layout/       AppLayout (ProLayout), SiderMenu, Breadcrumbs, CommandPalette, MockSwitch,
                ReadonlyBanner, MessageBinder
  app/          RoleContext, nav model
  components/   bespoke design-system set + Icon
  services/     types, config, dataMode, datasource, mockSource, actions, hub/ (client + liveSource)
  hooks/        TanStack Query read hooks
  pages/        one file per screen
  styles/       global.css (design-language enforcement: zebra, pills, meters, handle)
```

## Tests

`tests/smoke.spec.ts` asserts the shell renders with no console errors; `tests/shots.spec.ts` captures full-page screenshots per page in both themes (Playwright). Run `npx playwright test` against a running dev server.

## Status

Design build for review - faithful to `design-flows-frontend-mock.md`: every screen and action is present, both themes verified. Not wired to a live hub by default; mocked actions throughout. The rebuild concept and the hub-as-trust-boundary security model live in `../docs/portal-ui-catalogue.md`.
