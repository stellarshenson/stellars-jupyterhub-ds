# Acceptance Criteria - profile name display

A user's display name (first + last) edited on the Profile / Configure-user page must show everywhere it appears once saved. The backend store + API are correct (verified live: DB holds the new name, `GET /api/user-profiles` returns it); the bug was a frontend cache that never refetched after the save. `services/ops.ts::saveUserProfile`; display in `pages/Users.tsx` (`fullName` hint) + the profile form.

- [x] **Save invalidates the table** - `saveUserProfile` invalidates `['users']` (the Users table reads `fullName` from `/user-profiles` under that key) in addition to `['user-profile', name]` and `['user', name]`
  - log: 2026-06-17 FIXED - was `[['user-profile', name], ['user', name]]` only, so a saved last-name change never refreshed the list; the persisted query cache also kept it stale across reloads
- [x] **Form refetches** - `['user-profile', name]` invalidation refetches the edit form so its own fields/header reflect the save
  - log: 2026-06-17 verified (key already present)
- [x] **List refetches on mount** - `Users.tsx` force-invalidates `['users']` on mount (mirroring `Home.tsx`), so returning to the list after a save shows the new name immediately instead of repainting the persisted cache (trusted-as-fresh under the 30s staleTime) for ~2 min
  - log: 2026-06-17 FIXED - root cause of the residual ~2-min staleness: unlike Home, Users had no mount-time refetch, so the hydrated cache held the old name until the query was next re-observed while stale
- [x] **Backend correct** - PUT `/users/{name}/profile` persists first/last/email; bulk `GET /api/user-profiles` returns `{profiles: {username: {first_name,last_name,email}}}`
  - log: 2026-06-17 verified live (user_profiles.sqlite has 'Konrad','Jelenski'; API 200)
- [x] **Admin tag spacing** - the Users cell renders the username Link and the "admin" Tag in a flex row with a gap, so they no longer run together as "konrad.jelenadmin"
  - log: 2026-06-17 FIXED - inner `<div>` was bare (Tag has no left margin); now `display:flex; gap:6`
- [x] **Full name shown as hint** - `fullName` renders as the muted `oh-name-hint` line under the username (Users table + pending list)
  - log: 2026-06-17 present
- [ ] **Runtime: saved name refreshes the list** - on the live hub, saving a last name updates the Users table `fullName` without a manual reload
  - log: 2026-06-17 invalidation fixed; on-screen confirm pends operator rebuild

## Edge cases

- [x] **Edge: empty profile** - no first/last set -> no `fullName` hint rendered (the `{u.fullName && ...}` guard)
  - log: 2026-06-17 verified
- [x] **Edge: self vs admin save** - both the user's own Profile page and the admin Configure-user page call the same `saveUserProfile`, so both invalidate `['users']`
  - log: 2026-06-17 verified (Profile.tsx + UserConfig.tsx)
- [ ] **Edge: rename + profile** - a username rename (`renameUser`) and a profile edit are separate ops; the rename already invalidates `USER_KEYS(name)`; the display name (fullName) is independent of the username
  - log: 2026-06-17 noted; no cross-dependency
