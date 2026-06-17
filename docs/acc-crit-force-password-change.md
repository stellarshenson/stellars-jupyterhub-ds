# Acceptance Criteria - force password change on next login (#232 / #233)

An admin can require a user to change their password before they can use the platform. Enforcement is "no escape" at the spawner: a flagged user cannot start a lab by any route until the password is changed. All backend logic lives in the `optimum-hub-services` package.

## Storage (optimum_hub_services.user_profiles)

- [x] **must_change_password flag** - a Boolean column on the `user_profiles` table, default False
  - log: 2026-06-17 added; `get_must_change_password` / `set_must_change_password`
- [x] **Idempotent migration** - a pre-existing DB without the column gets it via `ALTER TABLE ... ADD COLUMN ... DEFAULT 0` (create_all never ALTERs); checked against the column list first
  - log: 2026-06-17 `_migrate_must_change_password`; covered by `test_migration_adds_column_to_legacy_db`
- [x] **Profile edits preserve the flag** - a name/email `save_profile` never clobbers must_change_password
  - log: 2026-06-17 `test_save_profile_preserves_must_change`

## Set / read (admin only)

- [x] **Admin-only set endpoint** - `POST /api/users/{user}/force-password-change {value}` sets/clears the flag; 403 for non-admin (a user must not clear their own gate)
  - log: 2026-06-17 `UserForcePasswordChangeHandler`, registered in config; handler count 26 -> 27
- [x] **Flag read via the profile** - `GET /api/users/{user}/profile` returns `must_change_password`; the frontend maps it to `UserProfile.mustChangePassword`
  - log: 2026-06-17 `_row_to_dict` + `liveSource.getUserProfile`

## Enforcement (no escape)

- [x] **Spawn hard-block** - `pre_spawn_hook` raises 403 with a clear message when the flag is set, so a flagged user - or an admin starting them - cannot get a lab by ANY route (the no-escape guarantee)
  - log: 2026-06-17 `hooks.py`; the message tells the user to change their password then start
- [x] **Fail-open on a store error** - if the flag cannot be read (profiles DB momentarily unreadable) the spawn is ALLOWED, never blocked - blocking-on-error would lock the whole platform out
  - log: 2026-06-17 try/except around the check; 605 backend tests pass (favicon/hook tests green)
- [x] **Clears on a successful change** - `OptimumHubAuthenticator.change_password` clears the flag on NativeAuth's success return, so a self-service change lets the user spawn again
  - log: 2026-06-17 success-gated override
- [ ] **Login auto-redirect (deferred)** - a flagged user is NOT yet auto-redirected to the change-password page on login; the spawn-block + the clear message enforce no-escape, but the funnel is manual. Intercepting the live login redirect was deliberately deferred (too risky to ship without a runtime auth round-trip test)
  - log: 2026-06-17 deferred - documented; revisit with an operator runtime test

## UI (#232 Configure-user)

- [x] **Toggle** - "Force password change on next login" switch on Configure-user (non-builtin users), initial state from `mustChangePassword`
  - log: 2026-06-17 `UserConfig.tsx`
- [x] **Applied after the password set** - in `save()` the flag is applied AFTER any password set, so an admin setting a temp password + forcing a change leaves the gate ON (the password set clears it, the toggle re-sets it)
  - log: 2026-06-17 order enforced in `save()`; `setForcePasswordChange` ops, admin-only
- [x] **Reactive admin reveal** - flipping Administrator updates the dependent controls at once via `Form.useWatch` (admins are auto-authorised -> the Authorised switch yields to a note)
  - log: 2026-06-17 #232 reactive part

## Edge cases

- [x] **Admin set-password vs force flow** - an admin password set clears the flag; the Configure-user toggle (applied last) re-sets it, so "temp password + force change" works
  - log: 2026-06-17 ordering in `save()`
- [ ] **Runtime: end-to-end** - on the live hub: admin flags a user -> user cannot spawn (clear 403) -> user changes password -> spawn allowed; pends operator rebuild
  - log: 2026-06-17 backend + frontend + 605 tests + build green; on-screen confirm pends rebuild

## API

- `POST /api/users/{user}/force-password-change` body `{value: bool}` -> `{username, must_change_password}`; 403 non-admin
- `GET /api/users/{user}/profile` -> now includes `must_change_password: bool`
