# Acceptance Criteria - Roles reference page

A read-only reference page under Advanced documenting the two IMPLICIT platform roles (admin, user) and the access each is granted across every page and action. Roles are not assigned by name - the platform derives them from JupyterHub's `admin` flag (admin) vs a regular authenticated, authorised account (user). Page: `Roles.tsx`, route `/roles`, nav under Administration -> Advanced. Verified against the code 2026-06-18.

## Placement + access

- [x] **Under Advanced** - the page is a leaf in the Administration -> Advanced submenu, beside Settings and Tokens
  - log: 2026-06-18 added to `nav.ts` NAV_ADMIN Advanced children (`/roles`, shield icon)
- [x] **Admin-only** - the route is under RequireAdmin; a plain user never reaches it
  - log: 2026-06-18 `/roles` inside the RequireAdmin block in `router.tsx`
- [x] **Read-only reference** - no writes, no footer; pure documentation (like Settings reference)
  - log: 2026-06-18 static curated data, no mutations

## Roles are implicit (documented here, not on the page)

The roles are implicit - NOT assigned by name. The platform derives the role from JupyterHub's `admin` flag (admin) versus a regular authenticated, authorised account (user). A guest role is planned for the future but is not added now. This explanation lives in this acc-crit, not as on-page prose.

- [x] **Implicit model captured in acc-crit** - the implicit-role explanation is recorded here (above), not as an inline Notice on the page
  - log: 2026-06-18 operator removed the on-page intro text ("remove that text") and asked for it as acc-crit ("all that -> acc crit"); the page conveys the derivation only through the definitions table
- [x] **Role definitions single panel** - the role definitions live in ONE panel ("Role definitions") holding a single table, not per-role prose cards
  - log: 2026-06-18 operator: "it was supposed to be panel with table with rows" / "make it as table in the panel (single panel)"; replaced the two `Card` prose blocks with one `Card` + `Table<RoleDef>`
- [x] **Role table columns** - columns are Role, Description, How assigned, Who; descriptions terse (technical-documentation style); Who is a terse example audience, not names
  - log: 2026-06-18 operator: "role name; description; how assigned; who (examples - not names, just terse description)"; `roleColumns`
- [x] **Admin row** - terse: full read/write/create/remove across fleet, users, groups, platform; assigned = holds JupyterHub's `admin` flag (JUPYTERHUB_ADMIN at login, or toggled on Users); who = operators, maintainers
  - log: 2026-06-18 `ROLES[0]`
- [x] **User row** - terse: own server + profile only, no fleet/user/group rights; assigned = authenticated, authorised account without the admin flag; who = data scientists, notebook authors, learners
  - log: 2026-06-18 `ROLES[1]`
- [x] **Guest not on the page** - guest is documented as a planned future role here only; it is NOT shown on the page and NOT added as a current role
  - log: 2026-06-18 operator: "in the future we will have guest also" / "but don't add guest"; not in the definitions table

## Access matrix (every page + function, per role)

- [x] **One row per capability** - the matrix lists each page AND each action (server lifecycle, user admin, groups/policy, platform), grouped by area
  - log: 2026-06-18 operator: "list each function each page"; `CAPS` grouped by area (Pages / Server / Users / Groups / Platform)
- [x] **Per-capability description** - every capability row carries a terse description column stating the read/write/list/create/remove rights it entails, not only the few rows that needed a caveat
  - log: 2026-06-18 operator: "provide short explanation (description colum) - terse style" / "also focus on read, write, list, remove, create rights"; added the required `desc` field to every `Cap` and a Description column
- [x] **A column per role** - Admin and User columns, one access cell each
  - log: 2026-06-18 two role columns
- [x] **Access level per cell, not just yes/no** - each cell shows the level: Full / Self only / View / Denied (the operator's "access level or deny or etc")
  - log: 2026-06-18 `Level` = full|self|view|none, rendered as coloured pills
- [x] **Colour-coded pills** - access levels render as pills on the shared palette (green full, amber self-only, blue view, red denied), per the design-language state=colour rule
  - log: 2026-06-18 `AccessPill` (color-mix tints of success/warning/accent/danger)
- [x] **Accurate to the code** - the matrix reflects the real gating: RequireAdmin page gating + the handlers' self-or-admin rules (e.g. start/stop = self for user, full for admin; rename/groups/broadcast = admin only)
  - log: 2026-06-18 sourced from `router.tsx` RequireAdmin + ops/handlers; cross-ref [acc-crit-rename-user], [acc-crit-navigation-patterns]
- [x] **Notes for nuance** - rows whose access needs a caveat (own-only, admin-can-enter-any, rename needs stopped server) carry a muted sub-note
  - log: 2026-06-18 `note` sub-line under the capability
- [x] **Zebra rows** - the matrix tables use the mandatory alternating-row striping
  - log: 2026-06-18 `rowClassName` oh-row-alt (design-language)

## Verification

- [x] **Frontend gates** - `npx tsc -b`, `npm run lint`, `npm run build:hub` clean with the new page + route + nav
  - log: 2026-06-18 all green
