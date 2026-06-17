# Acceptance Criteria - old portal cleanup

Remove the dead remnants of the pre-React portal now that `optimum-hub-web` serves the portal via `PortalHandler` and the React SPA owns the former server-rendered routes. Surgical, not blanket: many `html_templates_enhanced/*.html` are still rendered by stock JupyterHub and MUST stay.

## Removed (confirmed dead)

- [x] **Dead page templates** - `activity.html`, `settings.html`, `groups.html`, `notifications.html` deleted from `html_templates_enhanced/`; referenced only by their own unregistered handlers
  - log: 2026-06-17 `git rm`; verified no other `render_template` refs
- [x] **Dead page handlers** - `ActivityPageHandler`, `SettingsPageHandler`, `NotificationsPageHandler`, `GroupsPageHandler` classes removed; their API data handlers kept
  - log: 2026-06-17 removed from the 4 handler modules + `handlers/__init__.py` imports/`__all__`
- [x] **Handler count test** - `test_imports` expectation 30 -> 26
  - log: 2026-06-17 updated + suite green (592 passed)
- [x] **Orphaned import** - `import os` dropped from `groups.py` (only the removed page handler used it)
  - log: 2026-06-17
- [x] **Static mock prototype** - the `mock/` static HTML prototype tree (368K) deleted; unreferenced by any build/serve path
  - log: 2026-06-17 `git rm -r mock/`; grep confirmed no Dockerfile/compose/config/script refs
- [x] **Stale comments** - config `template_vars` comments naming `GroupsPageHandler` updated to the live consumers
  - log: 2026-06-17 `config/jupyterhub_config.py`

## Kept (still live - must not remove)

- [x] **Stock-rendered templates kept** - `error.html`, `404.html`, `logout.html`, `oauth.html`, `spawn*.html`, `stop_pending.html`, `not_running.html`, `my_message.html`, `change-password*.html`, `authorization-area.html`, `accept-share.html`, `page.html` base - rendered by stock JupyterHub / NativeAuth
  - log: 2026-06-17 left in place
- [x] **Static assets kept** - `custom.css`, `session-timer.js`, `mobile.js` - referenced by `page.html`
  - log: 2026-06-17
- [x] **API data handlers kept** - the `*DataHandler` classes serving the SPA stay registered
  - log: 2026-06-17

## Held for a rebuild-verified pass (confirmed dead, not removed blind)

- [ ] **Shadowed auth/redirect templates** - enhanced `login.html`, `signup.html`, `native-login.html`, `home.html`, `token.html`, `admin.html` are shadowed by the optimum-hub-web wheel / remapped in `auth.py`; deleting them is auth-critical and wants an image rebuild to verify before removal
  - log: 2026-06-17 left in place pending a rebuild-verified sweep; flagged to the operator
- [x] **package-lock name** - `optimum-hub-web/package-lock.json` already carries the correct name (no longer `mock-antd`)
  - log: 2026-06-17 verified after `make install`
