# Acceptance Criteria - Profile route (role-aware self-view)

The Profile nav link (`/profile`) opens the current user's own profile. It is role-aware: an admin gets the full Configure-user screen scoped to themselves; a plain user gets the self-service Profile page. `duoptimum-hub-web/src/router.tsx::ProfileRoute`, `pages/UserConfig.tsx`, `pages/Profile.tsx`.

## Routing

- [x] **Admin -> Configure-user (self)** - an admin's `/profile` renders `UserConfig`, which falls back to `useRole().username` when there is no `:name` param, so it is the same screen as `/users/{self}`
  - log: 2026-06-17 `ProfileRoute` + `name = paramName || username`
- [x] **Non-admin -> self-service Profile** - a plain user's `/profile` renders `Profile.tsx` (own name/email/password only), NOT `UserConfig`
  - log: 2026-06-17 `ProfileRoute` role switch; fixes the sweep HIGH where a non-admin saw admin-only controls + a 403 on the admin-only `/users` fetch
- [x] **Breadcrumb** - the crumb is "Profile" for both roles (PageHeader title/sub are ignored by design, so the breadcrumb is the visible label)
  - log: 2026-06-17 `router.tsx` crumb

## Admin self-view (UserConfig)

- [x] **Builtin admin controls hidden** - for the platform admin viewing self, Remove-user, Administrator and Authorised are hidden and the built-in-admin notice shows (`isBuiltinAdmin`)
  - log: 2026-06-17 pre-existing UserConfig guards apply to self
- [x] **Force-password hidden** - the force-password toggle is hidden for an admin target (`!liveAdmin`), so it never shows on an admin's own profile
  - log: 2026-06-17 cross-ref [acc-crit-force-password-change]

## Non-admin self-view (Profile.tsx)

- [x] **No admin controls** - only username (read-only), first/last name, email and password; no Administrator/Authorised/Remove/Groups
  - log: 2026-06-17 `Profile.tsx` unchanged self-service page
- [x] **Self password change with challenge** - changing the password requires the current password (`changeOwnPassword` -> `/change-password`), not the admin no-challenge endpoint
  - log: 2026-06-17 the sweep flagged that routing self through UserConfig's admin `setUserPassword` would 403 + skip the current-password challenge
- [x] **No admin-only fetch** - the page reads only self-allowed endpoints (`/users/{self}/profile`), never the admin-only `/users` list
  - log: 2026-06-17 avoids the 403 a non-admin hit in the broken interim
- [x] **Cancel/save stay put** - save and cancel return via `navigate(-1)`, not `/users` (which `RequireAdmin` would bounce a non-admin off)
  - log: 2026-06-17 `Profile.tsx` navigation

## Edge cases

- [x] **Edge: no dead code** - `Profile.tsx` and `changeOwnPassword` are live again (used by the non-admin branch), not orphaned
  - log: 2026-06-17 the interim `/profile`->`UserConfig`-always change had orphaned both
- [ ] **Runtime: both roles** - on the live hub, an admin's Profile shows the Configure screen and a plain user's shows the self-service page with a working current-password change
  - log: 2026-06-17 code + tsc/eslint/build green; on-screen confirm pends operator rebuild
