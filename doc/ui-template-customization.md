# UI Template Customization

JupyterHub's web interface can be customized by extending base templates. This platform customizes the user control panel to add self-service features like server restart and volume management directly accessible from the home page.

**Key Implementation Details:**
- Custom templates placed in `services/jupyterhub/templates/`
- Templates extend JupyterHub's base templates using Jinja2 `{% extends "page.html" %}`
- Docker image copies templates to `/srv/jupyterhub/templates/` at build time
- JupyterHub automatically discovers custom templates in this directory
- Changes require Docker rebuild and container restart to take effect

## Template Structure

JupyterHub uses Jinja2 templating engine with a hierarchical template system. The base template `page.html` defines the overall page structure including navigation, headers, and content blocks. Custom templates extend this base and override specific blocks to add new functionality.

The `home.html` template is the user control panel where users manage their JupyterLab server. This platform extends it to add custom buttons for server restart and volume management operations. The template must preserve existing JupyterHub functionality while adding new features.

**Template Blocks Available:**
- `{% block main %}` - Main content area for page-specific content
- `{% block script %}` - JavaScript section for client-side functionality
- `{% block nav_bar_left_items %}` - Left side navigation menu items
- `{% block nav_bar_right_items %}` - Right side navigation menu items

## JavaScript Integration

Custom templates often need JavaScript for interactive features. JupyterHub loads jQuery and other libraries via RequireJS module system. All custom JavaScript must be wrapped in RequireJS `require()` calls to ensure proper dependency loading.

**RequireJS Pattern:**
```javascript
<script>
require(["jquery"], function($) {
  "use strict";
  // Your code here with jQuery as $
});
</script>
```

This pattern ensures jQuery is loaded before the custom code executes. Without this wrapper, custom JavaScript may fail with "$ is not defined" errors. The platform's custom handlers use this pattern for all interactive features including volume management modals and server restart buttons.

## Bootstrap 5 Compatibility

JupyterHub 5.4.2 uses Bootstrap 5 for UI components. Custom templates must use Bootstrap 5 syntax, not Bootstrap 4. Modal triggers use `data-bs-toggle` and `data-bs-target` attributes instead of older `data-toggle` and `data-target` attributes.

**Bootstrap 5 Modal Example:**
```html
<button type="button" class="btn btn-primary"
        data-bs-toggle="modal"
        data-bs-target="#myModal">
  Open Modal
</button>
```

The close button in modals uses `btn-close` class instead of custom HTML with `&times;` entity. These differences are critical - Bootstrap 4 syntax silently fails in Bootstrap 5 without error messages.

## Font Awesome Icons

The platform uses Font Awesome icons to enhance button visibility and user experience. Icons are added using `<i>` tags with appropriate classes.

**Icon Examples:**
- Server restart: `<i class="fa fa-rotate" aria-hidden="true"></i>`
- Volume management: `<i class="fa fa-database" aria-hidden="true"></i>`
- Server stop: `<i class="fa fa-stop" aria-hidden="true"></i>`
- Server start: `<i class="fa fa-play" aria-hidden="true"></i>`

Icons should include `aria-hidden="true"` attribute to prevent screen readers from announcing them redundantly when button text is already present.

## Custom API Handlers

Templates interact with custom API handlers registered in `jupyterhub_config.py`. These handlers extend JupyterHub's REST API with new endpoints for platform-specific features.

The platform registers handlers using `c.JupyterHub.extra_handlers` configuration:
```python
c.JupyterHub.extra_handlers = [
    (r'/api/users/([^/]+)/manage-volumes', ManageVolumesHandler),
    (r'/api/users/([^/]+)/restart-server', RestartServerHandler),
    (r'/api/notifications/broadcast', BroadcastNotificationHandler),
    (r'/notifications', NotificationsPageHandler),
]
```

Each handler URL pattern uses regex to extract route parameters like username. Handlers must be imported from `custom_handlers.py` module at the top of the config file.

## CSRF Protection

All POST requests from custom templates must include XSRF token for security. JupyterHub provides this token automatically in templates via `{{ xsrf_form_html() }}` or through cookies accessible from JavaScript.

**AJAX Request with XSRF:**
```javascript
$.ajax({
  url: '/hub/api/users/konrad/restart-server',
  method: 'POST',
  headers: {
    'X-XSRFToken': getCookie('_xsrf')
  },
  success: function(data) { /* handle success */ }
});
```

Missing XSRF tokens result in 403 Forbidden errors. The platform's custom handlers automatically validate XSRF tokens on all POST, PUT, and DELETE requests.

## Build Process

Custom templates are copied into the Docker image during build. The Dockerfile includes:
```dockerfile
COPY --chmod=644 services/jupyterhub/templates/*.html /srv/jupyterhub/templates/
```

Changes to templates require rebuilding the Docker image and recreating the JupyterHub container. The build process should use `--no-cache` flag to ensure template changes are not cached from previous builds.

**Rebuild Command:**
```bash
docker compose -f compose.yml build --no-cache jupyterhub
docker stop stellars-jupyterhub-ds-jupyterhub
docker rm stellars-jupyterhub-ds-jupyterhub
docker compose up -d jupyterhub
```

Simple container restart with `docker restart` does not reload changed templates - the container must be recreated from the updated image.

## Testing Custom Templates

After deploying custom templates, verify they render correctly by accessing the relevant pages in a browser. Check browser console for JavaScript errors and network tab for failed API requests.

**Common Issues:**
- 404 errors indicate template file not found in `/srv/jupyterhub/templates/`
- JavaScript errors about undefined $ mean RequireJS wrapper is missing
- Bootstrap modals not opening indicate Bootstrap 4 syntax instead of Bootstrap 5
- 403 errors on POST requests indicate missing XSRF token
- Buttons without icons mean Font Awesome not loaded or wrong class names

Template customization enables powerful extensions to JupyterHub without forking the core codebase. The platform demonstrates this with server restart, volume management, and notification broadcast features all built through template extensions.
