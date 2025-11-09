# Admin Notification Broadcast System

The platform provides a notification broadcast system allowing administrators to send messages to all active JupyterLab servers simultaneously. This feature is useful for maintenance announcements, system updates, or urgent communications to all users.

**Access Requirements:**
- Admin-only feature accessible at `/hub/notifications`
- Target JupyterLab servers must have `jupyterlab_notifications_extension` installed
- Servers must be running (active spawners only)

## User Interface

The notification panel presents a simple form for composing and broadcasting messages to all active users.

**Form Fields:**
- Message textarea with 140-character limit and live counter (Twitter-style brevity)
- Notification type dropdown: default, info, success, warning, error, in-progress
- Auto-close checkbox: when unchecked, notifications persist until dismissed manually
- Send button: broadcasts to all active servers concurrently

The interface displays broadcast results immediately after sending, showing success and failure counts with expandable per-user details table listing username, delivery status, and error messages for failed deliveries.

## Notification Types and Visual Styling

The extension supports six notification types with distinct visual appearances to convey message urgency and context.

**Available Types:**
- **default** - Neutral gray styling for general announcements
- **info** - Blue styling for informational messages (system updates, tips)
- **success** - Green styling for positive confirmations (maintenance complete)
- **warning** - Yellow/amber styling for important notices (scheduled downtime)
- **error** - Red styling for critical alerts (service disruptions)
- **in-progress** - Animated styling for ongoing operations (deployment in progress)

Users see notifications as toast popups in their JupyterLab interface with the appropriate color scheme. Each notification includes a "Dismiss" button for manual closure regardless of auto-close setting.

## Technical Implementation

The broadcast system uses asynchronous concurrent delivery to all active servers. When an admin submits a notification, the backend queries all running JupyterLab spawners from the JupyterHub database and sends HTTP POST requests to each server's notification endpoint.

**Delivery Process:**
1. Admin submits notification form at `/hub/notifications`
2. Backend validates message length and notification type
3. System queries database for all active user spawners
4. For each active server, generates temporary API token (5-minute expiry)
5. Constructs endpoint URL using spawner's `server.base_url` property
6. Sends concurrent POST requests to all servers using `asyncio.gather()`
7. Each request has 5-second timeout for connection and response
8. Aggregates results and returns success/failure counts to admin

The concurrent delivery ensures broadcast completes quickly even with many active users. A 100-user broadcast completes in approximately 5 seconds rather than 500 seconds with sequential delivery.

## API Endpoint Integration

Notifications are delivered to the JupyterLab extension's ingest endpoint at `/jupyterlab-notifications-extension/ingest`. The platform constructs the full URL dynamically based on each user's server configuration.

**Endpoint URL Construction:**
```python
container_url = f"http://jupyterlab-{username}:8888"
base_url = spawner.server.base_url  # e.g., /jupyterhub/user/konrad/
endpoint = f"{container_url}{base_url}jupyterlab-notifications-extension/ingest"
```

This approach handles different JupyterHub configurations automatically. The base URL varies depending on Traefik routing, reverse proxy setup, and JupyterHub URL prefix settings. Using the spawner's `server.base_url` property ensures correct routing in all configurations.

**Payload Format:**
```json
{
  "message": "Maintenance scheduled for 10 PM tonight",
  "type": "warning",
  "autoClose": false,
  "actions": [
    {
      "label": "Dismiss",
      "caption": "Close this notification",
      "displayType": "default"
    }
  ]
}
```

The payload includes the message text, notification type, auto-close behavior, and action buttons array. The "Dismiss" button is included in all notifications for manual closure.

## Authentication and Security

Each notification request requires authentication via temporary API token. The platform generates a new token for each broadcast event with 5-minute expiry time.

**Token Generation:**
```python
token = user.new_api_token(note="notification-broadcast", expires_in=300)
```

This approach provides several security benefits:
- Tokens expire quickly limiting exposure window if intercepted
- Each broadcast gets unique tokens preventing replay attacks
- Tokens are never logged or persisted beyond the broadcast operation
- Failed deliveries don't leave valid tokens in logs or error messages

The HTTP request includes the token in the Authorization header:
```
Authorization: Bearer <token>
```

JupyterLab server validates the token against the user's stored tokens before processing the notification. Invalid or expired tokens result in 401 Unauthorized errors logged as authentication failures.

## Error Handling and Logging

The broadcast system implements comprehensive error handling for various failure scenarios. Each server delivery can succeed or fail independently without affecting other deliveries.

**Common Failure Scenarios:**
- **Connection timeout** - Server not responding, likely stopped or network issue
- **404 Not Found** - Notification extension not installed on JupyterLab server
- **401/403 Authentication** - Token validation failed, usually configuration issue
- **500 Server error** - Extension error processing notification

Each delivery result is logged with a concise one-line entry showing username, message preview (first 50 characters), notification type, and outcome:

```
[I] [Notification] alice: 'Maintenance scheduled for 10 PM tonight' (warning) - SUCCESS
[W] [Notification] bob: 'System update in progress' (info) - FAILED: HTTP 404: Not Found
[E] [Notification] charlie: 'Critical security patch' (error) - ERROR: Server not responding
```

These logs appear in JupyterHub container logs accessible via `docker logs stellars-jupyterhub-ds-jupyterhub`. The log format enables quick scanning for delivery issues and troubleshooting failed broadcasts.

## Extension Dependency

The notification system requires `jupyterlab_notifications_extension` installed on all spawned JupyterLab servers. The platform does not install this extension - it must be included in the `stellars/stellars-jupyterlab-ds` Docker image or installed via user environment.

**Extension Repository:** https://github.com/stellarshenson/jupyterlab_notifications_extension

The extension provides a server endpoint for ingesting notifications and a frontend component for displaying them in JupyterLab. Notifications appear as toast popups in the top-right corner with persistence in a notification center panel.

**Verifying Extension Installation:**

Check if the extension is installed and enabled on a running JupyterLab server:
```bash
docker exec jupyterlab-konrad bash -c \
  "conda run -n base jupyter server extension list | grep notification"
```

Expected output:
```
jupyterlab_notifications_extension enabled
- Validating jupyterlab_notifications_extension...
  jupyterlab_notifications_extension 1.0.14 OK
```

Missing or disabled extensions result in 404 errors when attempting notification delivery. The broadcast results table indicates which users received notifications successfully and which failed due to missing extensions.

## Usage Recommendations

**Message Length:**

The 140-character limit encourages concise, actionable messages. Longer messages get truncated or may not display properly in the JupyterLab interface. Focus on essential information and include links for details if needed.

**Good:** "Planned maintenance tonight 10 PM - 2 AM. Save work and stop servers. Details: example.com/maint"
**Bad:** "We will be performing scheduled maintenance activities on the infrastructure tonight starting at approximately 10 PM and continuing until around 2 AM the next morning during which time you should make sure to save all your work and stop your servers to avoid any potential data loss or interruption to your research activities..."

**Notification Type Selection:**

Choose notification types based on message urgency and required user action:
- **info** for routine announcements (new features, documentation updates)
- **warning** for actions users should take (save work before maintenance)
- **error** for critical issues requiring immediate attention (security patches)
- **success** for confirmations (maintenance complete, system restored)

**Auto-Close Behavior:**

Leave auto-close unchecked for important messages requiring acknowledgment. Users must manually dismiss the notification, ensuring they see the message. Enable auto-close for low-priority informational messages that don't require explicit acknowledgment.

**Timing Considerations:**

Send notifications when most users are actively working for maximum visibility. Notifications sent outside working hours may be dismissed automatically or missed entirely by users who don't check notification history.

## Troubleshooting

**Notification panel shows "No active servers found":**

No users currently have running JupyterLab servers. Users must have active sessions for broadcast delivery. Check admin panel user list and verify which users have running servers before broadcasting.

**All deliveries fail with "Server not responding":**

JupyterLab containers may not be reachable from JupyterHub container. Verify network connectivity:
```bash
docker exec stellars-jupyterhub-ds-jupyterhub ping -c 3 jupyterlab-konrad
```

Also check JupyterHub network configuration and ensure spawned containers join `jupyterhub_network`.

**Deliveries fail with "Notification extension not installed":**

The JupyterLab image lacks `jupyterlab_notifications_extension`. Update the `stellars/stellars-jupyterhub-ds` image to include the extension or install it in user environments. Rebuild and restart affected JupyterLab servers.

**Some users receive notifications, others don't:**

Check per-user delivery details in the expandable results table. Different failure reasons indicate different issues:
- 404 errors suggest extension not installed on specific user's image version
- Timeout errors suggest specific user's container networking issue
- 401 errors suggest token generation or validation problem for specific user

Individual failures don't prevent successful delivery to other users. The broadcast system is fault-tolerant by design.

**Notifications appear but wrong styling:**

Verify notification type selection in the form. The extension maps types to colors - using "info" when intending "error" results in blue notification instead of red. Check logs for the notification type actually sent.

## Performance Characteristics

The broadcast system is designed for efficient delivery to large numbers of concurrent users.

**Scalability Metrics:**
- 10 active users: ~5 second broadcast time (parallel delivery)
- 50 active users: ~5 second broadcast time (parallel delivery with concurrency)
- 100 active users: ~5-6 second broadcast time (timeout limits total duration)
- 500 active users: ~5-6 second broadcast time (asyncio.gather handles concurrency)

Delivery time is primarily determined by the timeout setting (5 seconds) rather than user count due to concurrent request handling. Even with hundreds of users, total broadcast duration remains under 10 seconds.

**Resource Utilization:**

Each concurrent delivery creates a TCP connection and HTTP request. A 100-user broadcast creates 100 simultaneous connections from JupyterHub container. This is well within typical system limits but may trigger rate limiting or connection limits on restricted networks.

The platform generates temporary API tokens for all users simultaneously. Token generation is lightweight but does query the database. Very large user counts (1000+) may benefit from batch token generation to reduce database load.

## Future Enhancements

Potential improvements for the notification broadcast system:

**Selective Targeting:**
- Broadcast to specific groups instead of all users
- User selection interface for targeted notifications
- Group-based notification permissions

**Scheduled Notifications:**
- Queue notifications for future delivery
- Recurring notifications for regular maintenance windows
- Time-zone aware scheduling for distributed teams

**Notification History:**
- Database persistence of broadcast history
- Admin view of previously sent notifications
- User notification inbox for viewing past messages

**Rich Content:**
- Markdown formatting support in messages
- Embedded links and action buttons
- File attachments or image previews

These enhancements would require modifications to both the broadcast system and the JupyterLab extension. The current implementation provides a solid foundation for basic admin-to-user communication needs.
