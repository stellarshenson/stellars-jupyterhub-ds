# Custom Branding

Custom logo and favicon for the JupyterHub platform, controlled via environment variables. Both support local files (`file://` prefix) and external URLs (`http(s)://`). Empty value uses stock JupyterHub assets.

## Environment Variables

| Variable | Purpose | Values |
|----------|---------|--------|
| `JUPYTERHUB_LOGO_URI` | Hub login and navigation logo | `file:///path/to/logo.svg` or `https://example.com/logo.svg` |
| `JUPYTERHUB_FAVICON_URI` | Browser tab favicon for hub and JupyterLab | `file:///path/to/favicon.ico` or `https://example.com/favicon.ico` |
| `JUPYTERHUB_LAB_MAIN_ICON_URI` | JupyterLab main logo (toolbar) | `file:///path/to/icon.svg` or `https://example.com/icon.svg` |
| `JUPYTERHUB_LAB_SPLASH_ICON_URI` | JupyterLab splash screen icon | `file:///path/to/splash.svg` or `https://example.com/splash.svg` |

**`file://` handling**: The file is copied to JupyterHub's static directory at startup. The source file must be accessible inside the container (mount via compose volumes). Logo and favicon are served via `static_url()`. Lab icons are resolved to hub static URLs and passed to spawned containers as `JUPYTERLAB_MAIN_ICON_URI` and `JUPYTERLAB_SPLASH_ICON_URI` environment variables.

**URL handling**: External URLs are passed directly to templates (logo, favicon) or to spawned container env vars (lab icons).

## Favicon in JupyterLab Sessions

Hub pages serve the custom favicon directly. JupyterLab sessions present a challenge because favicon requests (`/user/{username}/static/favicons/favicon.ico`) are routed by Configurable HTTP Proxy (CHP) to the user container, bypassing the hub entirely. The user container serves JupyterLab's default favicon.

### Solution - CHP Proxy Route Injection

The platform uses CHP's trie-based longest-prefix-match routing to intercept favicon requests before they reach user containers.

**How it works**:

1. `pre_spawn_hook` registers a per-user CHP route (`/user/{username}/static/favicons/`) pointing back to the hub
2. CHP's longest-prefix-match selects this over the generic `/user/{username}/` route
3. A `FaviconRedirectHandler` (injected into the Tornado app's wildcard router) responds with a 302 redirect to the hub's static favicon

**Request flow**:

```
Browser: GET /user/alice/static/favicons/favicon.ico
  -> CHP: longest-prefix matches /user/alice/static/favicons/ -> hub (host:port)
  -> Hub: FaviconRedirectHandler -> 302 /hub/static/favicon.ico
  -> Browser follows redirect, hub serves custom favicon
```

### Technical Details - Two Pitfalls

Two non-obvious issues required specific solutions during implementation:

**CHP target must be host:port only (no path)**. `app.hub.url` returns `http://jupyterhub:8080/hub/` which includes a `/hub/` path. When a CHP target has a path component, CHP rewrites the forwarded request path - stripping the matched route prefix and prepending the target path. This causes the hub to receive a mangled path that no handler matches. The fix uses `urlparse` to extract just `scheme://netloc` from `app.hub.url`, matching how JupyterHub registers its own hub route (`/ -> http://jupyterhub:8080`).

**Tornado handler must be inserted into the existing wildcard router**. `app.tornado_application.add_handlers(".*", ...)` creates a new host group that Tornado checks after all existing host groups. Since JupyterHub's default handlers include catch-all patterns, the new group is never reached. The fix uses `app.tornado_application.wildcard_router.rules.insert(0, rule)` to prepend the handler rule into the existing host group, ensuring it's checked before any catch-all.

### Why not `extra_handlers`?

JupyterHub auto-prefixes all `extra_handlers` routes with `/hub/`. CHP forwards the original path without `/hub/`, so the handler would never match. Instead, `FaviconRedirectHandler` extends `tornado.web.RequestHandler` (not `BaseHandler`) and is injected directly into the Tornado app's wildcard router.

### Route Lifecycle

- **New spawns**: `pre_spawn_hook` registers per-user CHP route before each spawn (idempotent)
- **Surviving servers**: A one-shot `IOLoop.current().add_callback()` startup callback iterates all active servers and registers their CHP routes immediately after the event loop starts - this covers servers that were already running when JupyterHub restarted
- Tornado handler is injected once (guarded by `app._favicon_handler_injected` flag) by whichever path executes first
- Stale routes when servers stop are harmless (hub is always running to handle them)
- No cleanup needed

### Conditionality

The entire mechanism only activates when `JUPYTERHUB_FAVICON_URI` is non-empty. When empty, JupyterLab sessions display their own default favicon.

## JupyterLab Icons

`JUPYTERHUB_LAB_MAIN_ICON_URI` and `JUPYTERHUB_LAB_SPLASH_ICON_URI` customize the JupyterLab main toolbar logo and splash screen icon. Unlike logo and favicon (which are served by the hub directly), lab icons are passed as environment variables to spawned JupyterLab containers so that extensions can reference them.

**Resolution logic** (`config/jupyterhub_config.py`):

- `file://` - copies to hub static dir as `lab-main-icon{ext}` or `lab-splash-icon{ext}`, resolves to `{base_url}hub/static/lab-main-icon{ext}`
- `http(s)://` - passed through as-is
- Empty - env var not injected into containers

**Container env vars** (only set when URI is non-empty):

| Hub env var | Container env var | Static path after `file://` copy |
|-------------|-------------------|----------------------------------|
| `JUPYTERHUB_LAB_MAIN_ICON_URI` | `JUPYTERLAB_MAIN_ICON_URI` | `{base_url}hub/static/lab-main-icon{ext}` |
| `JUPYTERHUB_LAB_SPLASH_ICON_URI` | `JUPYTERLAB_SPLASH_ICON_URI` | `{base_url}hub/static/lab-splash-icon{ext}` |

Extensions running in JupyterLab can read `JUPYTERLAB_MAIN_ICON_URI` and `JUPYTERLAB_SPLASH_ICON_URI` from the container environment to fetch the icon URLs.

## Implementation Files

| File | Role |
|------|------|
| `config/jupyterhub_config.py` | File copy at startup, CHP route + Tornado handler injection in `pre_spawn_hook`, lab icon env var injection into `DockerSpawner.environment` |
| `services/jupyterhub/conf/bin/custom_handlers.py` | `FaviconRedirectHandler` class (extends `tornado.web.RequestHandler`) |
| `services/jupyterhub/templates/page.html` | Conditional favicon rendering in `<head>` |

## Deployment Example

```yaml
# compose_override.yml
services:
  jupyterhub:
    volumes:
      - ./branding/favicon.ico:/srv/jupyterhub/favicon.ico:ro
      - ./branding/logo.svg:/srv/jupyterhub/logo.svg:ro
      - ./branding/lab-icon.svg:/srv/jupyterhub/lab-icon.svg:ro
      - ./branding/splash-icon.svg:/srv/jupyterhub/splash-icon.svg:ro
    environment:
      - JUPYTERHUB_LOGO_URI=file:///srv/jupyterhub/logo.svg
      - JUPYTERHUB_FAVICON_URI=file:///srv/jupyterhub/favicon.ico
      - JUPYTERHUB_LAB_MAIN_ICON_URI=file:///srv/jupyterhub/lab-icon.svg
      - JUPYTERHUB_LAB_SPLASH_ICON_URI=file:///srv/jupyterhub/splash-icon.svg
```
