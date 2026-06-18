# Acceptance Criteria - Rename user (admin action on the profile)

An admin can rename a user from the Configure-user screen via an action attached to the Username input (the design-language input-with-attached-action pattern, like Change password / Generate). The rename is destructive-adjacent: it goes through a confirmation popup, is only possible while the user's server is stopped, and warns that the renamed user's existing volumes do NOT follow the rename (an admin must migrate them separately). On success the screen navigates to the renamed user's profile. Backend is the stock JupyterHub admin rename (`PATCH /users/{name}` with `{name}`) plus the existing sync listener (`events.py::sync_nativeauth_on_rename`). Frontend `ops.renameUser`. Verified against the code 2026-06-18.

## Control + placement

- [ ] **Adjacent to the Username input** - the Rename action sits attached to the Username field as a `Space.Compact` input + button (the same pattern as the Change-password / Generate row), not a separate panel
  - log: 2026-06-18 to implement (UserConfig Username Form.Item)
- [x] **Admin role only** - the Rename control renders / is usable only for an admin; a plain user (self-service Profile page) never sees it
  - log: 2026-06-18 UserConfig is admin-only (`/users/:name` under RequireAdmin); gated on role
- [x] **Hidden for the built-in admin** - the platform admin account (`JUPYTERHUB_ADMIN`) cannot be renamed (like it cannot be removed/de-authorised)
  - log: 2026-06-18 gated on `isBuiltinAdmin`

## Rules

- [x] **Enabled only when the server is stopped** - the Rename button is disabled while the user's server is running/spawning; a tooltip says to stop it first
  - log: 2026-06-18 gated on the server status (`useServerHero(name).status === 'offline'`)
- [x] **Confirmation popup** - clicking Rename opens a confirmation dialog before any write; cancelling makes no change
  - log: 2026-06-18 Modal.confirm with a danger OK
- [x] **Volumes-not-migrated warning** - the confirmation states that the user's existing volumes (home / workspace / cache) stay attached to the OLD name and will NOT follow the rename; an admin must migrate them separately
  - log: 2026-06-18 the operator's explicit warning text
- [x] **Back to the renamed profile** - on a successful rename the screen navigates to `/users/{newName}` (the renamed user's Configure screen)
  - log: 2026-06-18 navigate to the new name; origin state carried forward
- [x] **No-op guards** - Rename is disabled when the new name is blank or unchanged from the current name
  - log: 2026-06-18 disabled unless `newName.trim()` and `!= current`

## Backend (existing, reused)

- [x] **Rename endpoint records the actor** - the write goes through a custom admin endpoint `POST /users/{name}/rename` (not the stock PATCH) so the recorded event can name the acting admin; the rename itself is the orm `user.name = newName` + commit, identical to what stock does
  - log: 2026-06-18 `UserRenameHandler` added + route registered; `ops.renameUser` repointed from stock PATCH to the custom endpoint
- [x] **NativeAuth UserInfo synced** - the rename event listener updates the NativeAuthenticator `UserInfo.username` so authorisation + password survive the rename
  - log: 2026-06-18 `events.py::sync_nativeauth_on_rename` (verified); covered by the new unit test
- [x] **Activity + profile synced** - the listener renames the user's ActivityMonitor samples and display profile (first/last/email) to the new name
  - log: 2026-06-18 `rename_activity_user` + `UserProfileManager.rename_user` (both already unit-tested; orchestration covered)
- [x] **Event recorded** - the rename records a `user` event so it shows in the Events feed
  - log: 2026-06-18 `record_event` in the listener (base text "<old> renamed to <new>")
- [x] **Event names the actor (who renamed whom)** - the rename event identifies the acting admin AND both names, e.g. "<admin> renamed <old> to <new>"; the actor is taken from the authenticated request (server-trusted), never the client
  - log: 2026-06-18 operator: "event about user rename (and who did rename who)"; implemented via a `rename_actor` contextvar set by `UserRenameHandler` and read by the listener (falls back to "<old> renamed to <new>" with no actor); covered by `test_rename_event_names_the_actor`
- [x] **Volumes are NOT renamed** - the Docker per-user volumes (`jupyterlab-{encoded}_home` etc.) are keyed on the old encoded name and are intentionally left untouched by the rename (hence the UI warning)
  - log: 2026-06-18 no volume rename in the listener - the documented platform behaviour the warning surfaces

## Post-rename + collateral (renamer's responsibility)

- [x] **Logs in with the new name** - after the rename the user authenticates with the NEW username; the credentials carry over because the NativeAuth `UserInfo` row (username + password hash + authorisation) is moved by the listener
  - log: 2026-06-18 operator: "when user is renamed, they will log in using this new name"; UserInfo username synced -> old name no longer logs in, new name does
- [x] **DB rows keyed on username are synced** - every platform store keyed on the username moves to the new name automatically: JupyterHub's own user row (the hub), NativeAuth `users_info`, ActivityMonitor samples, the display-profile row
  - log: 2026-06-18 operator "(db changes too)"; the rename listener fans out to all three platform DBs; the hub renames its own row
- [x] **Renamer owns the remaining collateral** - the acting admin is responsible for everything the rename does NOT move automatically - chiefly the Docker per-user volumes (keyed on the old encoded name) - and the confirm dialog states this explicitly so it is a conscious choice
  - log: 2026-06-18 operator: "the renamer must take care of all collateral"; volumes are the known non-migrated item (cross-ref the volumes warning above)
- [x] **No silent half-rename** - if any sync step fails the failure is logged; the rename never half-applies the auth row silently (UserInfo move is the auth-critical step, asserted in the unit test)
  - log: 2026-06-18 listener wraps each sync; UserInfo move covered by test_rename_sync

## Edge cases

- [x] **Edge: rename to an existing username** - the endpoint returns 409; the error toast surfaces and the screen stays put (no navigation)
  - log: 2026-06-18 `UserRenameHandler` 409 on `find_user(new_name)`; `ops.run` error toast; navigate only on success
- [x] **Edge: server running** - Rename stays disabled; no write is attempted
  - log: 2026-06-18 server-stopped gate (`serverStopped` from `useServerHero`)
- [x] **Edge: mock mode** - the demo shows the success toast and does NOT navigate (the renamed mock user does not exist), matching Remove-user mock behaviour
  - log: 2026-06-18 `if (!isMock()) navigate(...)`
- [x] **Edge: user creation is not a rename** - the `set` listener fires on the INITIAL name-set (user creation) with SQLAlchemy's `NO_VALUE` sentinel as oldvalue (not None); it must early-return so creation records no spurious rename event and never binds the sentinel into the username lookups
  - log: 2026-06-18 functional run exposed live log spam + a bogus creation event (`type 'LoaderCallableStatus' is not supported`); guard changed to `if not isinstance(oldvalue, str) or oldvalue == value`; covered by `test_create_user_records_no_rename_event`

## Tests

- [x] **Unit: rename sync orchestration** - renaming an ORM user fires the listener: NativeAuth UserInfo username updated + authorisation preserved, a rename event recorded, the event names the actor when set, a same-value set records nothing, and user creation (NO_VALUE oldvalue) records no rename event
  - log: 2026-06-18 `tests/test_rename_sync.py` (4 tests, in-memory JH + NativeAuth orm); `make test`-runnable
- [x] **Functional: SPA rename flow** - a Playwright test renames a stopped user from the Configure screen (confirm dialog -> rename), asserts navigation to the new profile and the actor-named rename event in the feed; carries `@pytest.mark.acc_crit("rename-user::...")`
  - log: 2026-06-18 `tests/functional/test_rename_user.py` added; collects + declares acc_crit (runs against a live stack in the harness)

## API

- `POST /hub/api/users/{name}/rename` body `{ "name": "<newName>" }` (admin) -> renames via the orm + records the actor event; returns `{ "name": "<newName>" }`; 400 blank/unchanged, 404 no such user, 409 name clash
