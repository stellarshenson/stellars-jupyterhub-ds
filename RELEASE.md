# Release v3.2.11

## Major Features

**Configuration-Agnostic Volume Management**
- Volume list dynamically generated from `DOCKER_SPAWNER_VOLUMES` configuration
- Optional `VOLUME_DESCRIPTIONS` dict for user-friendly volume descriptions
- UI automatically adapts if volumes renamed, added, or removed in config
- Template uses Jinja2 loop with conditional description display
- Handler validates against `USER_VOLUME_SUFFIXES` from config

**Admin Notification Broadcast**
- Broadcast notifications to all active JupyterLab servers via `/hub/notifications`
- Six notification types: default, info, success, warning, error, in-progress
- 140-character message limit with live counter
- Concurrent delivery using `asyncio.gather()` with 5-second timeout per server
- Temporary API tokens (5-minute expiry) for authentication
- Requires `jupyterlab_notifications_extension` on spawned servers

**Privileged User Access Control**
- Group-based docker.sock access via `docker-privileged` built-in group
- Pre-spawn hook conditionally mounts `/var/run/docker.sock` based on group membership
- Built-in group protection (auto-recreates if deleted)
- Managed through JupyterHub admin panel at `/hub/admin`

## Technical Improvements

**Configuration**
- `jupyterhub_config.py` protected from import errors with `if c is not None:` guards
- `DOCKER_SPAWNER_VOLUMES` defined as module-level constant (importable by handlers)
- `get_user_volume_suffixes()` extracts volume suffixes from config
- `USER_VOLUME_SUFFIXES` calculated and exposed to templates

**Handlers**
- `ManageVolumesHandler` validates against configured volumes (not hardcoded)
- `BroadcastNotificationHandler` sends to `/jupyterlab-notifications-extension/ingest`
- `NotificationsPageHandler` renders broadcast form
- One-line logging per server: username, message preview, type, outcome

**Templates**
- Dynamic volume checkbox generation from `user_volume_suffixes`
- Conditional description display from `volume_descriptions`
- Bootstrap 5 modal syntax throughout
- RequireJS wrapped JavaScript with CSRF protection

## Documentation

**Modus Primaris Style**
- README reorganized: features first, screenshots, then architecture
- Simplified notification description (verbose → concise)
- Simplified architecture diagram labels
- Features as bullet points at top

**New Documentation**
- `doc/notifications.md` (35 lines) - notification system implementation
- `doc/ui-template-customization.md` (58 lines) - template extension patterns
- `doc/docker-socket-permissions.md` (66 lines) - socket access control

**Screenshots**
- `screenshot-home.png` - user control panel with restart and volume management
- `screenshot-send-notification.png` - admin notification broadcast interface
- `screenshot-volumes.png` - volume management modal
- `screenshot-volumes-modal.png` - volume selection checkboxes

## Version History

- **v3.2.11**: Configuration-agnostic volume management, optional descriptions
- **v3.2.0**: Admin notification broadcast system
- **v3.1.2**: Privileged user docker.sock access control
- **v3.0.23**: Production readiness, CI/CD, architecture cleanup
- **v3.0.14**: User self-service capabilities (restart, volume management)

## Upgrade Notes

No breaking changes. Configuration backward compatible.

**Optional**: Add `VOLUME_DESCRIPTIONS` dict to `jupyterhub_config.py` for user-friendly volume descriptions in UI:
```python
VOLUME_DESCRIPTIONS = {
    'home': 'User home directory files, configurations',
    'workspace': 'Project files, notebooks, code',
    'cache': 'Temporary files, pip cache, conda cache'
}
```

**Optional**: Install `jupyterlab_notifications_extension` on spawned servers to enable admin notification broadcast.

Existing deployments adopt new features upon container rebuild and restart.

---

**From**: v3.0.14_cuda-12.9.1_jh-5.4.2
**To**: v3.2.11_cuda-12.9.1_jh-5.4.2
**Date**: 2025-11-09
