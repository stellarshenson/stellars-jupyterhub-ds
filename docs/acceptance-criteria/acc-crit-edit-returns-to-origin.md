# Acceptance Criteria - Edit user returns to its origin

Configuring a user (`UserConfig`, route `/users/:name`) is reachable from three places - the Home "Active servers" widget, the Servers list, and the Users list. Save, Cancel and Remove must return to the page the edit was opened from, and the breadcrumb parent must name that origin. Mechanism reuses the existing nav-origin pattern (the one `ManageVolumes` uses): the opening `<Link>` tags `state.from = {to, label}`; `UserConfig` reads `backTo = state.from?.to ?? '/users'`; `Breadcrumbs` prefers `state.from` over the static route parent. Verified against the code 2026-06-18.

## Return navigation

- [x] **From Home -> Home** - opening Configure-user from the Home servers widget returns to `/dashboard` on Save / Cancel / Remove
  - log: 2026-06-18 implemented - Home username `<Link>` tags `state.from = HOME_ORIGIN`
- [x] **From Servers -> Servers** - opening it from the Servers list returns to `/servers`
  - log: 2026-06-18 implemented - Servers username `<Link>` tags `state.from = SERVERS_ORIGIN`
- [x] **From Users -> Users** - opening it from the Users list returns to `/users`
  - log: 2026-06-18 implemented - Users is the canonical fallback (`?? '/users'`); the link carries no state, mirroring how `ManageVolumes` treats `/servers`
- [x] **Cancel returns to origin** - the footer Cancel navigates to `backTo`, not a hardcoded `/users`
  - log: 2026-06-18 was `navigate('/users')`, now `navigate(backTo)`
- [x] **Save returns to origin** - a successful save (mock and live paths) navigates to `backTo`
  - log: 2026-06-18 both branches changed to `navigate(backTo)`
- [x] **Remove returns to origin** - deleting the user (live mode) navigates to `backTo`
  - log: 2026-06-18 `navigate(backTo)`; mock mode unchanged (stays, list updates in place)

## Breadcrumb

- [x] **Parent names the origin** - the breadcrumb second crumb is Home / Servers / Users matching where the edit was opened, linking back there
  - log: 2026-06-18 `Breadcrumbs` already prefers `state.from` over `handle.parent`; the origin links now feed it
- [x] **Default parent is Users** - with no origin state the crumb falls back to the route's static parent (Users)
  - log: 2026-06-18 unchanged - `usersParent` on the `/users/:name` route handle

## Edge cases

- [x] **Edge: deep link / refresh** - landing on `/users/:name` directly (no `state.from`) returns to `/users` and shows Users as the parent
  - log: 2026-06-18 fallback `?? '/users'`; breadcrumb falls back to `handle.parent`
- [x] **Edge: Profile route (/profile)** - admin self-edit via `/profile` (no `:name`, no origin) keeps the prior behaviour, returning to `/users`
  - log: 2026-06-18 same fallback; out of scope to change, behaviour preserved
- [x] **Edge: single source of truth** - the same `from`-state shape (`{to, label}`) drives both the return navigation and the breadcrumb, so they can never disagree
  - log: 2026-06-18 one `state.from` read in `UserConfig` (return) and `Breadcrumbs` (parent)
