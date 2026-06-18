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
  - log: 2026-06-18 operator removed the on-page intro text ("remove that text") and asked for it as acc-crit ("all that -> acc crit"); the page conveys the derivation only through the definition cards
- [x] **Admin definition (page)** - card states it holds JupyterHub's `admin` flag (JUPYTERHUB_ADMIN at login, or toggled on Users) and manages the whole fleet
  - log: 2026-06-18 Admin definition card (no "implicit"/"by name" prose)
- [x] **User definition (page)** - card states any authenticated authorised account without the admin flag; operates only their own server + profile
  - log: 2026-06-18 User definition card
- [x] **Guest not on the page** - guest is documented as a planned future role here only; it is NOT shown on the page and NOT added as a current role
  - log: 2026-06-18 operator: "in the future we will have guest also" / "but don't add guest"; on-page guest note removed with the intro text

## Access matrix (every page + function, per role)

- [x] **One row per capability** - the matrix lists each page AND each action (server lifecycle, user admin, groups/policy, platform), grouped by area
  - log: 2026-06-18 operator: "list each function each page"; `CAPS` grouped by area (Pages / Server / Users / Groups / Platform)
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
