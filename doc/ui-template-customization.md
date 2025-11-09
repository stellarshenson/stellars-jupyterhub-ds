# UI Template Customization

JupyterHub templates extended using Jinja2 to add custom UI features (server restart, volume management, notifications). Templates placed in `services/jupyterhub/templates/` and copied to `/srv/jupyterhub/templates/` during Docker build.

**Key Technical Facts**:
- Templates extend base using `{% extends "page.html" %}`
- Override blocks: `{% block main %}`, `{% block script %}`
- Changes require Docker rebuild with `--no-cache` flag
- JupyterHub 5.4.2 uses Bootstrap 5 (not Bootstrap 4)

**JavaScript Integration**:
All custom JavaScript wrapped in RequireJS to ensure library loading:
```javascript
require(["jquery"], function($) {
  "use strict";
  // Custom code here
});
```

**Bootstrap 5 Modal Syntax**:
```html
<button data-bs-toggle="modal" data-bs-target="#myModal">
  <i class="fa fa-rotate" aria-hidden="true"></i> Restart
</button>
```

**CSRF Protection**:
All POST requests include XSRF token via `X-XSRFToken` header:
```javascript
headers: { 'X-XSRFToken': getCookie('_xsrf') }
```

**Custom Handlers** (registered in `jupyterhub_config.py`):
```python
c.JupyterHub.extra_handlers = [
    (r'/api/users/([^/]+)/manage-volumes', ManageVolumesHandler),
    (r'/api/users/([^/]+)/restart-server', RestartServerHandler),
    (r'/api/notifications/broadcast', BroadcastNotificationHandler),
    (r'/notifications', NotificationsPageHandler),
]
```

**Font Awesome Icons**:
- Restart: `fa fa-rotate`
- Volumes: `fa fa-database`
- Stop: `fa fa-stop`
- Start: `fa fa-play`

**Build Process**:
```bash
docker compose build --no-cache jupyterhub
docker stop stellars-jupyterhub-ds-jupyterhub && docker rm stellars-jupyterhub-ds-jupyterhub
docker compose up -d jupyterhub
```
