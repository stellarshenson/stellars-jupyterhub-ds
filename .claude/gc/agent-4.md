# Agent 4 - Handlers/templates/static GC report

## Summary
KEPT=34, DELETED=0, PRUNED=1, INCONCLUSIVE=0

All handler classes are registered in `config/jupyterhub_config.py::c.JupyterHub.extra_handlers` (lines 662-683) except `FaviconRedirectHandler` which is injected via `hooks.py` (lines 219-230 and 289-298). All 21 templates are either project-specific (with confirmed `render_template` calls) or JupyterHub/NativeAuthenticator override built-ins. All 3 static assets are referenced in `Dockerfile.jupyterhub` (copied at build) and in `html_templates_enhanced/page.html` (loaded via `static_url`). One small re-export prune in `handlers/session.py` removed unused `calc_*` back-compat aliases (no current importer references `stellars_hub.handlers.session.calc_*`; tests import directly from `stellars_hub.idle_culler` and `stellars_hub` top-level).

## Per-file

### handlers/__init__.py
- STATUS: KEEP
- Reachable via: aggregator imported by `config/jupyterhub_config.py:46-55`. All 19 names listed in `__all__` are actually used in `extra_handlers`/hooks.

### handlers/activity.py
- STATUS: KEEP
- Reachable via: `ActivityPageHandler/ActivityDataHandler/ActivityResetHandler/ActivitySampleHandler` registered at `extra_handlers` lines 670-672, 680.

### handlers/credentials.py
- STATUS: KEEP
- Reachable via: `GetUserCredentialsHandler` at `extra_handlers` line 669.

### handlers/favicon.py
- STATUS: KEEP
- Reachable via: `FaviconRedirectHandler` injected by `stellars_hub/hooks.py:219,229,289,297` and exercised by `tests/test_favicon.py`.

### handlers/groups.py
- STATUS: KEEP
- Reachable via: 6 handler classes registered at `extra_handlers` lines 673-677, 681.

### handlers/health.py
- STATUS: KEEP
- Reachable via: `HealthCheckHandler` at `extra_handlers` line 682. Rate-limit constants and `_start_time` are used inside `get()`.

### handlers/notifications.py
- STATUS: KEEP
- Reachable via: `NotificationsPageHandler`, `ActiveServersHandler`, `BroadcastNotificationHandler` at lines 667-668, 678.

### handlers/server.py
- STATUS: KEEP
- Reachable via: `RestartServerHandler` at line 664.

### handlers/session.py
- STATUS: PRUNE
- Reachable via: `SessionInfoHandler`, `ExtendSessionHandler` at lines 665-666.
- Action: removed legacy back-compat re-exports of `calc_available_hours`, `calc_ceiling`, `calc_effective_timeout`, `calc_new_extensions`, `calc_time_remaining` from `__all__` and updated the module docstring. The imports remain (used inside the handler methods). No external callers reference these via `handlers.session`; `tests/test_idle_culler.py` imports directly from `stellars_hub.idle_culler`.

### handlers/settings.py
- STATUS: KEEP
- Reachable via: `SettingsPageHandler` at line 679.

### handlers/volumes.py
- STATUS: KEEP
- Reachable via: `ManageVolumesHandler` at line 663. The shared `_check_auth_and_get_volumes` helper is called by both `get()` and `delete()`.

### Templates (21 files)

| Template | Status | Reachable via |
|---|---|---|
| 404.html | KEEP | JupyterHub built-in override (status 404 page); `pages.py:753` renders `f'{status_code}.html'` |
| accept-share.html | KEEP | JupyterHub built-in override (share-acceptance UI) |
| activity.html | KEEP | `handlers/activity.py:33` `render_template("activity.html", ...)` |
| admin.html | KEEP | JupyterHub built-in override (admin panel) |
| authorization-area.html | KEEP | NativeAuthenticator override; rendered by `stellars_hub/auth.py:18` |
| change-password.html | KEEP | NativeAuthenticator built-in override |
| change-password-admin.html | KEEP | NativeAuthenticator built-in override |
| error.html | KEEP | JupyterHub built-in override (error page); base for `404.html` |
| groups.html | KEEP | `handlers/groups.py:41` `render_template("groups.html", ...)` |
| home.html | KEEP | JupyterHub built-in override (user home) |
| login.html | KEEP | JupyterHub built-in override |
| logout.html | KEEP | JupyterHub built-in override (`login.py:78`) |
| my_message.html | KEEP | JupyterHub built-in override |
| native-login.html | KEEP | NativeAuthenticator built-in override |
| not_running.html | KEEP | JupyterHub built-in override |
| notifications.html | KEEP | `handlers/notifications.py:24` `render_template("notifications.html", ...)` |
| oauth.html | KEEP | JupyterHub built-in override (`apihandlers/auth.py:371`) |
| page.html | KEEP | JupyterHub built-in override (base layout extended by all other templates) |
| settings.html | KEEP | `handlers/settings.py:24` `render_template("settings.html", ...)` |
| signup.html | KEEP | NativeAuthenticator built-in override |
| spawn.html | KEEP | JupyterHub built-in override |
| spawn_pending.html | KEEP | JupyterHub built-in override |
| stop_pending.html | KEEP | JupyterHub built-in override |
| token.html | KEEP | JupyterHub built-in override |

### static/custom.css
- STATUS: KEEP
- Reachable via: `Dockerfile.jupyterhub:112` copies it into the image; `page.html:47` loads `static_url('css/custom.css')`. Contains `#session-timer-*` rules driving home.html UI.

### static/mobile.js
- STATUS: KEEP
- Reachable via: `Dockerfile.jupyterhub:114`; `page.html:41` `<script src="{{static_url('js/mobile.js')}}">`. Sets `data-device` attribute consumed by `custom.css` mobile breakpoints.

### static/session-timer.js
- STATUS: KEEP
- Reachable via: `Dockerfile.jupyterhub:113`; `page.html:70` `<script src="{{static_url('js/session-timer.js')}}">`. Drives `#session-timer-row` in `home.html`.

## Cross-boundary flags

None. All registrations and references involve files in Agent 1 (`config/jupyterhub_config.py`, `hooks.py`) and Agent 5 (`Dockerfile.jupyterhub`) - flagged here only as registration evidence, not modified.

## Tests final state
171 passing (baseline preserved).
