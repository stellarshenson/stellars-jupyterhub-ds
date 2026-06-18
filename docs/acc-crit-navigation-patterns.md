# Acceptance Criteria - Navigation patterns (edit pages -> parent + breadcrumbs)

Every form / sub screen reached from a list must offer a way back to its parent and show a breadcrumb that names that parent - never a dead end and never a wrong parent. Two shapes: a screen with ONE parent returns to that fixed canonical route (matching its breadcrumb `parent` route handle); a screen reachable from MORE THAN ONE place records its origin in `state.from = {to, label}` and both the return target and the breadcrumb parent honour it. Mechanism: `react-router` route handles (`{crumb, parent}`) + `Breadcrumbs.tsx` (prefers `state.from` over the static parent) + `FormFooter` (Cancel + Save/Done/Ok). Cross-ref [acc-crit-edit-returns-to-origin] (UserConfig), [acc-crit-design-language] (the system-wide nav rules), [acc-crit-volume-reset]. Verified against the code 2026-06-18.

## Single-parent edit / sub pages

- [x] **Configure group -> Groups** - `/groups/:name` Save / Cancel / Delete return to `/groups`; breadcrumb parent Groups
  - log: 2026-06-18 verified (GroupConfig `navigate('/groups')` x3 + `FormFooter onCancel`; router `groupsParent`)
- [x] **New user -> Users** - `/users/new` Save / Cancel return to `/users`; breadcrumb parent Users
  - log: 2026-06-18 verified (NewUser FormFooter + `navigate('/users')`)
- [x] **New group -> Groups** - `/groups/new` Save / Cancel return to `/groups`; breadcrumb parent Groups
  - log: 2026-06-18 verified (NewGroup FormFooter + `navigate('/groups')`)
- [x] **Bulk add -> Users / result** - `/users/bulk` Cancel returns to `/users`; submit advances to `/users/bulk/result`; breadcrumb parent Users
  - log: 2026-06-18 verified (BulkUsers)
- [x] **Bulk result -> Users** - `/users/bulk/result` Done returns to `/users`; breadcrumb parent Users
  - log: 2026-06-18 verified (BulkResult `navigate('/users')`)
- [x] **Export groups -> Groups** - `/groups/export` Cancel returns to `/groups`; breadcrumb parent Groups
  - log: 2026-06-18 verified (GroupsExport)
- [x] **Full reference -> Settings** - `/settings/reference` (read-only) has no footer; the breadcrumb parent Settings is the way back
  - log: 2026-06-18 verified (router parent Settings -> /settings; read-only page, no footer by design)

## Multi-origin pages (honour state.from)

- [x] **Configure user** - `/users/:name` returns to its origin (Home / Servers / Users) via `state.from`, Users as the canonical fallback; breadcrumb parent matches
  - log: 2026-06-18 implemented this session; full matrix in [acc-crit-edit-returns-to-origin]
- [x] **Manage volumes** - `/servers/:name/volumes` returns to its origin (Home or Servers) via `state.from`, Servers as the canonical fallback; breadcrumb parent matches
  - log: 2026-06-17 implemented (ManageVolumes `backTo = state.from?.to ?? '/servers'`); cross-ref [acc-crit-volume-reset]
- [x] **Start server** - `/servers/:name/starting` returns to Home for your own server, Servers for another user's
  - log: 2026-06-18 verified (Starting `navigate(isOwn ? '/dashboard' : '/servers')`); cross-ref [acc-crit-start-server-page]

## Breadcrumb rules

- [x] **Crumb from the route handle** - each page declares `handle.crumb`; the breadcrumb shows "Optimum Hub / [parent] / crumb"
  - log: 2026-06-18 verified (Breadcrumbs reads the deepest matched handle)
- [x] **Origin beats static parent** - when `state.from` is present it overrides the route's static `parent` so the crumb names where the user actually came from
  - log: 2026-06-17 implemented (Breadcrumbs `origin ?? handle.parent`)
- [x] **Parent crumb is a link** - the parent crumb navigates back to the parent list; the current page crumb is bold, not a link
  - log: 2026-06-18 verified (Breadcrumbs builds `<Link to={parent.to}>` + bold current)
- [x] **Single source of truth** - the same `state.from` drives BOTH the breadcrumb parent and the footer return target, so they can never disagree
  - log: 2026-06-18 verified (UserConfig + ManageVolumes read the one `state.from`)

## Edge cases

- [x] **Edge: deep link / refresh** - landing on a sub page directly (no `state.from`) returns to the canonical parent and shows it as the breadcrumb parent
  - log: 2026-06-18 fallback routes (`?? '/users'`, `?? '/servers'`) + static route parent
- [x] **Edge: never a dead end** - every list-reachable screen has either a footer Cancel/Done or a parent breadcrumb link back
  - log: 2026-06-18 audited the edit/sub pages (see lists above)
- [x] **Edge: rename changes the route** - renaming a user on `/users/:name` navigates to `/users/:newName` (the renamed profile), carrying the origin state forward
  - log: 2026-06-18 implemented with the rename action (`navigate('/users/'+newName, { state })`) - cross-ref [acc-crit-rename-user]

## Functional tests

- [x] **Origin round-trip** - a Playwright test opens Configure user from the Users list and asserts the breadcrumb parent link is Users and Cancel returns to /users
  - log: 2026-06-18 `tests/functional/test_navigation.py::test_configure_user_returns_to_users` (acc_crit `navigation-patterns::Origin round-trip`); Servers/Home origins covered by code + the design-language nav rules
- [x] **Single-parent round-trip** - tests open New user (-> Users) and New group (-> Groups) and assert the breadcrumb parent link + that Cancel returns to the parent list
  - log: 2026-06-18 `test_navigation.py::test_new_user_returns_to_users` + `test_new_group_returns_to_groups`
