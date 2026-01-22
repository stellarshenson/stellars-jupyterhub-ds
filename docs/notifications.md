# Notification Broadcast System

Admin-only broadcast system sending notifications to all active JupyterLab servers simultaneously. Accessible at `/hub/notifications`.

**Key Implementation Facts**:
- Concurrent delivery using `asyncio.gather()` with 5-second timeout per server
- Temporary API tokens generated per broadcast (5-minute expiry via `user.new_api_token()`)
- Dynamic endpoint URL construction: `http://jupyterlab-{username}:8888{base_url}jupyterlab-notifications-extension/ingest`
- 140-character message limit with live counter
- Six notification types: default, info, success, warning, error, in-progress
- Payload includes actions array with Dismiss button
- One-line logging per server: username, message preview, type, outcome (SUCCESS/FAILED/ERROR)

**Handler Implementation** (`services/jupyterhub/conf/bin/custom_handlers.py`):
- `NotificationsPageHandler` - Renders broadcast form at `/hub/notifications`
- `BroadcastNotificationHandler` - API endpoint for sending notifications at `/hub/api/notifications/broadcast`
- Both restricted to admin users via `@admin_only` decorator

**Template** (`services/jupyterhub/templates/notifications.html`):
- Bootstrap 5 form with message textarea, type selector, auto-close toggle
- RequireJS wrapped JavaScript for CSRF protection
- Results display with expandable per-user status table

**Dependencies**:
- Requires `jupyterlab_notifications_extension` installed on spawned JupyterLab servers
- Extension provides ingest endpoint at `/jupyterlab-notifications-extension/ingest`
- Extension repository: https://github.com/stellarshenson/jupyterlab_notifications_extension

**Error Handling**:
- Connection timeout -> "Server not responding"
- HTTP 404 -> "Notification extension not installed"
- HTTP 401/403 -> "Authentication failed"
- HTTP 500 -> "Server error processing notification"
- Failures don't block other deliveries (fault-tolerant)
