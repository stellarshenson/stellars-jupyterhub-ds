# Mobile Interface Implementation Plan

**Version**: 3.9.0
**Date**: 2026-03-24
**Status**: Planning - not yet implemented

## Context

The Stellars JupyterHub DS platform currently has zero mobile responsiveness - no CSS media queries, fixed-width table layouts, and desktop-optimized templates. Mobile users need a simplified interface to monitor their JupyterLab instances (start/stop/restart, idle session tracking) and admins need a mobile-friendly activity monitor. The mobile interface does NOT provide access to JupyterLab itself - only server management and monitoring.

## Requirements

### Functional Requirements

- [ ] **FR-1**: Detect mobile vs desktop device on every page load
- [ ] **FR-2**: Mobile login screen - simplified, touch-friendly, same authentication flow
- [ ] **FR-3**: Mobile home screen for regular users:
  - Start/Stop/Restart server buttons (large, touch-friendly)
  - Idle session timeout progress bar with extension prompt
  - No access to JupyterLab server (no "My Server" link that opens the notebook)
  - No named servers table
  - No manage volumes (too destructive for mobile)
- [ ] **FR-4**: Mobile home screen for admin users:
  - Everything from FR-3 (their own server controls)
  - Simplified activity monitor showing all users
- [ ] **FR-5**: Only two screens available on mobile: Home and Activity (admin only)
- [ ] **FR-6**: No other screens accessible from mobile navigation (no Token, Change Password, Settings, Notifications, Authorize Users, Admin panel)
- [ ] **FR-7**: Desktop experience remains completely unchanged

### Non-Functional Requirements

- [ ] **NFR-1**: Device detection must work reliably across iOS Safari, Android Chrome, and other mobile browsers
- [ ] **NFR-2**: Touch targets minimum 44x44px (Apple HIG) / 48x48dp (Material Design)
- [ ] **NFR-3**: No new Python dependencies - pure CSS/JS/Jinja2 solution
- [ ] **NFR-4**: No new API endpoints required - reuse existing handlers
- [ ] **NFR-5**: Dark mode must work on mobile
- [ ] **NFR-6**: Page must be usable in portrait orientation

## Architecture Decision: Server-Side vs Client-Side Detection

**Chosen approach: Server-side detection via User-Agent + client-side CSS media queries**

Server-side detection in `page.html` base template sets a `data-device="mobile"` attribute on `<body>`. CSS media queries handle layout. Jinja2 conditionals hide sections server-side where possible.

**Rationale**: Server-side detection allows hiding entire HTML blocks (named servers table, navbar items) from the DOM rather than just CSS-hiding them. This is cleaner and prevents accidental mobile access to desktop-only features. CSS media queries handle the responsive layout.

**Detection method** (in `page.html` `<script>` block, runs before render):

```javascript
// Set on <body> for CSS targeting
const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
  || (window.innerWidth <= 768);
document.body.setAttribute('data-device', isMobile ? 'mobile' : 'desktop');
```

Additionally, pass a `is_mobile` template variable from a base handler mixin that checks `User-Agent` header, enabling Jinja2 `{% if not is_mobile %}` blocks for server-side DOM exclusion.

## Implementation Plan

### Phase 1: Device Detection Infrastructure

**Files to modify**:
- `config/jupyterhub_config.py`
- `services/jupyterhub/html_templates_enhanced/page.html`
- `services/jupyterhub/html_templates_enhanced/static/custom.css`

#### 1.1 Server-side detection (jupyterhub_config.py)

Add a `MobileDetectionMixin` or a template processor that injects `is_mobile` into template namespace. The simplest approach is a custom `template_vars` callable or a Jinja2 environment extension.

**Preferred approach**: Add a custom `BaseHandler` mixin that all existing handlers inherit from, which adds `is_mobile` to template namespace. However, since JupyterHub's built-in handlers (HomeHandler, LoginHandler) cannot be easily subclassed, the better approach is:

**Use `c.JupyterHub.template_vars` with a callable**: Not supported - template_vars is a static dict.

**Use Jinja2 extension**: Add a Jinja2 extension that provides `is_mobile` global function.

**Simplest working approach**: Use JavaScript-only detection. Set `data-device` attribute on `<body>` element early in page load. Use CSS `[data-device="mobile"]` selectors for all mobile styling. Use JavaScript to hide/show DOM elements after load.

This avoids modifying any Python handler code. All detection and adaptation happens in the browser.

#### 1.2 Client-side detection (page.html)

Add detection script in `<head>` section of `page.html` (before body renders):

```html
<script>
(function() {
  var ua = navigator.userAgent;
  var isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(ua)
    || (window.innerWidth <= 768 && 'ontouchstart' in window);
  document.documentElement.setAttribute('data-device', isMobile ? 'mobile' : 'desktop');
})();
</script>
```

Set on `<html>` element (not `<body>`) so CSS rules apply before body renders, preventing flash of desktop content.

#### 1.3 CSS foundation (custom.css)

Add mobile-specific CSS at the end of `custom.css` using attribute selector:

```css
/* ============================================================
   MOBILE INTERFACE
   ============================================================ */
[data-device="mobile"] .mobile-hidden { display: none !important; }
[data-device="desktop"] .desktop-hidden { display: none !important; }
```

### Phase 2: Mobile Navigation

**Files to modify**:
- `services/jupyterhub/html_templates_enhanced/page.html`

#### 2.1 Simplified navbar for mobile

The existing navbar in `page.html` (lines 118-229) contains all navigation items. On mobile, wrap non-essential items with a CSS class that hides them:

**Desktop navbar items** (lines 143-191):
- Home - KEEP on mobile
- Token - HIDE on mobile
- Admin - HIDE on mobile
- Authorize Users - HIDE on mobile
- Activity - KEEP on mobile (admin only)
- Notifications - HIDE on mobile
- Settings - HIDE on mobile
- Change Password - HIDE on mobile
- Services dropdown - HIDE on mobile

**Implementation**: Add `mobile-hidden` class to nav items that should not appear on mobile. The Activity link stays visible for admins.

```html
<li class="nav-item">
  <a class="nav-link" href="{{ base_url }}home">Home</a>
</li>
<li class="nav-item mobile-hidden">
  <a class="nav-link" href="{{ base_url }}token">Token</a>
</li>
{% if 'admin-ui' in parsed_scopes %}
  <li class="nav-item mobile-hidden">
    <a class="nav-link" href="{{ base_url }}admin">Admin</a>
  </li>
  <li class="nav-item mobile-hidden">
    <a class="nav-link" href="{{ base_url }}authorize">Authorize Users</a>
  </li>
  <li class="nav-item">
    <a class="nav-link" href="{{ base_url }}activity">Activity</a>
  </li>
  <li class="nav-item mobile-hidden">
    <a class="nav-link" href="{{ base_url }}notifications">Notifications</a>
  </li>
  <li class="nav-item mobile-hidden">
    <a class="nav-link" href="{{ base_url }}settings">Settings</a>
  </li>
{% endif %}
<li class="nav-item mobile-hidden">
  <a class="nav-link" href="{{ base_url }}change-password">Change Password</a>
</li>
```

### Phase 3: Mobile Login Screen

**Files to modify**:
- `services/jupyterhub/html_templates_enhanced/login.html`
- `services/jupyterhub/html_templates_enhanced/signup.html`
- `services/jupyterhub/html_templates_enhanced/static/custom.css`

#### 3.1 Login form mobile styling

The login form (`login.html` line 24-58) uses `.auth-form-body` class. Add mobile CSS:

```css
[data-device="mobile"] .auth-form-body {
  max-width: 100%;
  padding: 1rem;
}

[data-device="mobile"] .auth-form-body input {
  font-size: 1rem;
  padding: 0.75rem;
  height: auto;
}

[data-device="mobile"] .auth-form-body .btn {
  font-size: 1rem;
  padding: 0.75rem 1.5rem;
  width: 100%;
  min-height: 48px;
}

[data-device="mobile"] .auth-form-header h1 {
  font-size: 1.5rem;
}
```

No structural changes to login.html - CSS-only adaptation.

### Phase 4: Mobile Home Screen

**Files to modify**:
- `services/jupyterhub/html_templates_enhanced/home.html`
- `services/jupyterhub/html_templates_enhanced/static/custom.css`

This is the most complex phase. The home screen must show:
1. Server control buttons (Start/Stop/Restart) - large, touch-friendly
2. Idle session progress bar with extension
3. Admin activity monitor (if admin)

#### 4.1 Hide desktop-only sections

Add `mobile-hidden` class to these sections in `home.html`:

- **Named Servers table** (lines 96-162): Wrap with `<div class="mobile-hidden">` - entire `{% if allow_named_servers %}` block
- **Manage Volumes button** (lines 36-43): Add `mobile-hidden` class to the button
- **Manage Volumes modal** (lines 165-208): Add `mobile-hidden` class
- **"My Server" link** (lines 16-23): The Start button currently links to `{{ url }}` which opens JupyterLab. On mobile, this link must be suppressed. Add JavaScript to intercept and only start the server without navigating.

#### 4.2 Mobile server controls

Replace the button row layout for mobile. Current buttons (lines 10-44) are inline `btn-lg` elements.

Mobile CSS:

```css
[data-device="mobile"] .container > .row > .text-center {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0 1rem;
}

[data-device="mobile"] .container > .row > .text-center .btn-lg {
  width: 100%;
  min-height: 56px;
  font-size: 1.1rem;
}
```

#### 4.3 Suppress JupyterLab navigation on mobile

The "My Server" / "Start My Server" button (line 16-23) is an `<a>` tag with `href="{{ url }}"`. On mobile, clicking this should start the server but NOT navigate to JupyterLab.

Add JavaScript in the `{% block script %}` section:

```javascript
if (document.documentElement.getAttribute('data-device') === 'mobile') {
  var startBtn = document.getElementById('start');
  if (startBtn && startBtn.tagName === 'A') {
    // If server is already running, prevent navigation
    {% if default_server.active %}
    startBtn.removeAttribute('href');
    startBtn.style.cursor = 'default';
    startBtn.style.opacity = '0.5';
    startBtn.textContent = 'Server Running';
    startBtn.classList.remove('btn-primary');
    startBtn.classList.add('btn-success');
    {% else %}
    // Start server via API instead of navigation
    startBtn.addEventListener('click', function(e) {
      e.preventDefault();
      var btn = this;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Starting...';
      $.ajax({
        url: '{{ base_url }}api/users/{{ user.name }}/server',
        type: 'POST',
        headers: { 'X-XSRFToken': getCookie('_xsrf') },
        success: function() { location.reload(); },
        error: function(xhr) {
          btn.disabled = false;
          btn.innerHTML = '<i class="fa fa-play"></i> Start My Server';
          alert('Failed to start server: ' + xhr.statusText);
        }
      });
    });
    {% endif %}
  }
}
```

#### 4.4 Mobile session timer bar

The session timer (lines 48-76) is a compact progress bar with time display and Extend button, managed by `static/session-timer.js`. The layout uses `col-md-4 offset-md-4` centering. On mobile, make it full-width:

```css
[data-device="mobile"] #session-timer-row .col-md-4 {
  width: 100%;
  margin-left: 0;
  padding: 0 0.5rem;
}

[data-device="mobile"] #session-timer-row .offset-md-4 {
  margin-left: 0;
}
```

The progress bar and Extend button should work well on mobile with this width adjustment. The `session-timer.js` file handles all timer logic and does not need modification.

#### 4.5 Inline activity monitor for admin (mobile only)

For admin users on mobile, embed a simplified activity monitor directly on the home page below the session timer. This avoids navigating to a separate page.

Add a new section in `home.html` after the session timer block (line 93):

```html
{# Mobile admin activity monitor - inline on home page #}
{% if 'admin-ui' in parsed_scopes %}
<div class="desktop-hidden mt-4" id="mobile-activity-section">
  <div class="card">
    <div class="card-body">
      <h6 class="card-title mb-3">
        <i class="fa fa-users" aria-hidden="true"></i>
        User Activity
        <span class="badge bg-dark ms-2" id="mobile-active-count"></span>
      </h6>
      <div id="mobile-activity-loading" class="text-center py-2">
        <span class="spinner-border spinner-border-sm"></span>
        Loading...
      </div>
      <div id="mobile-activity-list" class="d-none">
        <!-- Populated by JavaScript - card-based layout, not table -->
      </div>
    </div>
  </div>
</div>
{% endif %}
```

#### 4.6 Mobile activity monitor JavaScript

Add JavaScript that fetches from the existing `GET {{ base_url }}api/activity` endpoint and renders a card-based layout instead of a table:

```javascript
if (document.documentElement.getAttribute('data-device') === 'mobile'
    && document.getElementById('mobile-activity-section')) {

  function fetchMobileActivity() {
    $.get('{{ base_url }}api/activity', function(data) {
      var container = $('#mobile-activity-list');
      container.empty().removeClass('d-none');
      $('#mobile-activity-loading').addClass('d-none');

      var activeCount = 0, idleCount = 0, offlineCount = 0;

      data.users.forEach(function(user) {
        if (user.server_active && user.recently_active) activeCount++;
        else if (user.server_active) idleCount++;
        else offlineCount++;

        // Status dot color
        var statusColor = user.server_active
          ? (user.recently_active ? '#28a745' : '#ffc107')
          : '#dc3545';

        var timeLeft = user.time_remaining_seconds
          ? formatTimeRemaining(user.time_remaining_seconds)
          : '-';

        container.append(
          '<div class="mobile-user-card d-flex align-items-center py-2 border-bottom">' +
            '<span class="me-2" style="color:' + statusColor + ';font-size:1.2em;">&#9679;</span>' +
            '<span class="flex-grow-1">' + escapeHtml(user.username) + '</span>' +
            '<span class="text-muted small">' + timeLeft + '</span>' +
          '</div>'
        );
      });

      $('#mobile-active-count').text(
        data.users.length + ' users (' + activeCount + ' active)'
      );
    });
  }

  fetchMobileActivity();
  setInterval(fetchMobileActivity, 10000); // refresh every 10s
}
```

### Phase 5: Mobile Activity Page (Admin)

**Files to modify**:
- `services/jupyterhub/html_templates_enhanced/activity.html`
- `services/jupyterhub/html_templates_enhanced/static/custom.css`

The full activity page (`activity.html`) is also accessible on mobile for admins via the navbar Activity link. It needs a card-based layout replacing the table.

#### 5.1 Dual-layout activity template

Add a mobile-specific container alongside the existing table:

```html
<!-- Desktop table (existing, unchanged) -->
<div class="mobile-hidden" id="activity-table-container">
  <!-- existing table markup unchanged -->
</div>

<!-- Mobile card list -->
<div class="desktop-hidden" id="mobile-activity-container" style="display: none;">
  <div id="mobile-activity-cards">
    <!-- Populated by JavaScript -->
  </div>
</div>
```

#### 5.2 Mobile activity card design

Each user rendered as a card:

```html
<div class="card mb-2 mobile-user-activity-card">
  <div class="card-body py-2 px-3">
    <div class="d-flex align-items-center justify-content-between">
      <div class="d-flex align-items-center">
        <span class="status-dot me-2">&#9679;</span>
        <strong>username</strong>
      </div>
      <span class="badge">active</span>
    </div>
    <div class="d-flex justify-content-between mt-1 small text-muted">
      <span>CPU: 12.3%</span>
      <span>Mem: 1.2 GB</span>
      <span>Time: 5h 30m</span>
    </div>
    <!-- Activity bar (same 5-segment visualization, scaled wider) -->
    <div class="mt-1">...</div>
  </div>
</div>
```

#### 5.3 Mobile activity CSS

```css
[data-device="mobile"] .mobile-user-activity-card {
  border-radius: 6px;
}

[data-device="mobile"] .mobile-user-activity-card .card-body {
  padding: 0.5rem 0.75rem;
}
```

#### 5.4 JavaScript modification in activity.html

Modify the existing `fetchActivityData()` function to detect device and render either table rows OR mobile cards based on `data-device` attribute. The data fetching logic is identical - only the DOM rendering differs.

### Phase 6: Mobile CSS Stylesheet

**File to modify**:
- `services/jupyterhub/html_templates_enhanced/static/custom.css`

All mobile CSS rules collected at the end of `custom.css` in a clearly marked section:

```css
/* ============================================================
   MOBILE INTERFACE - v3.8.0
   All rules scoped to [data-device="mobile"] attribute
   ============================================================ */

/* --- Utility classes --- */
[data-device="mobile"] .mobile-hidden { display: none !important; }
[data-device="desktop"] .desktop-hidden { display: none !important; }

/* --- Global mobile adjustments --- */
[data-device="mobile"] body { font-size: 1rem; }
[data-device="mobile"] .container { padding: 0.5rem; }
[data-device="mobile"] h1 { font-size: 1.5rem; }
[data-device="mobile"] h2 { font-size: 1.25rem; }

/* --- Navbar --- */
[data-device="mobile"] .navbar { padding: 0.25rem 0.5rem; }
[data-device="mobile"] .jpy-logo { height: 1.75rem; }

/* --- Login --- */
[data-device="mobile"] .auth-form-body { max-width: 100%; padding: 1rem; }
[data-device="mobile"] .auth-form-body input { font-size: 1rem; padding: 0.75rem; }
[data-device="mobile"] .auth-form-body .btn { width: 100%; min-height: 48px; font-size: 1rem; }

/* --- Home: Server controls --- */
[data-device="mobile"] .container > .row > .text-center {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0 0.5rem;
}
[data-device="mobile"] .container > .row > .text-center .btn-lg {
  width: 100%;
  min-height: 56px;
  font-size: 1.1rem;
}

/* --- Home: Session timer bar --- */
[data-device="mobile"] #session-timer-row .col-md-4 { width: 100%; }
[data-device="mobile"] #session-timer-row .offset-md-4 { margin-left: 0; }

/* --- Activity: Mobile cards --- */
[data-device="mobile"] .mobile-user-card { min-height: 44px; }

/* --- Footer --- */
[data-device="mobile"] .version_footer { font-size: 0.75rem; text-align: center; }
```

## Codebase Structure (as of v3.8.2)

The codebase was recently refactored. Handlers are now in the `stellars_hub` package:

```
services/jupyterhub/stellars_hub/stellars_hub/
  handlers/           # All custom API handlers
    activity.py       # ActivityPageHandler, ActivityDataHandler, ActivityResetHandler, ActivitySampleHandler
    credentials.py    # GetUserCredentialsHandler
    favicon.py        # FaviconRedirectHandler
    notifications.py  # NotificationsPageHandler, ActiveServersHandler, BroadcastNotificationHandler
    server.py         # RestartServerHandler
    session.py        # SessionInfoHandler, ExtendSessionHandler
    settings.py       # SettingsPageHandler
    volumes.py        # ManageVolumesHandler
  activity/           # Activity monitoring subsystem
  auth.py             # StellarsNativeAuthenticator
  branding.py         # Logo/favicon handling
  hooks.py            # pre_spawn_hook, post_spawn_hook
  ...
```

Templates and static files:
```
services/jupyterhub/html_templates_enhanced/
  page.html           # Base template (navbar, head, footer)
  home.html           # User home page (buttons, session timer, modals)
  activity.html       # Admin activity monitor
  login.html          # Login form
  signup.html         # Registration form
  admin.html          # Admin dashboard
  notifications.html  # Broadcast notifications
  settings.html       # Platform settings
  static/
    custom.css        # All custom styling (1629+ lines, NO media queries)
    session-timer.js  # Session timer logic (extracted from home.html)
```

## Files Modified Summary

| File | Changes |
|------|---------|
| `services/jupyterhub/html_templates_enhanced/page.html` | Add device detection script in `<head>`, add `mobile-hidden` class to navbar items |
| `services/jupyterhub/html_templates_enhanced/home.html` | Add `mobile-hidden` to named servers/manage volumes, add mobile start button JS, add inline admin activity monitor |
| `services/jupyterhub/html_templates_enhanced/activity.html` | Add mobile card container, modify JS to render cards on mobile |
| `services/jupyterhub/html_templates_enhanced/login.html` | No structural changes (CSS-only) |
| `services/jupyterhub/html_templates_enhanced/signup.html` | No structural changes (CSS-only) |
| `services/jupyterhub/html_templates_enhanced/static/custom.css` | Add mobile CSS section (~80-100 lines) |
| `config/jupyterhub_config.py` | No changes needed |
| `services/jupyterhub/stellars_hub/` | No changes needed (handlers unchanged) |
| `project.env` | Already bumped to 3.9.0 |

## Implementation Order for Agent

Execute phases in this exact order. Each phase should be validated before proceeding.

### Step 1: Device detection (page.html)

1. Open `services/jupyterhub/html_templates_enhanced/page.html`
2. Add the detection script IMMEDIATELY after `<meta name="viewport">` tag (line 40) and BEFORE any stylesheet loading:
   ```html
   <script>
   (function(){
     var ua=navigator.userAgent;
     var m=/Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(ua)
       ||(window.innerWidth<=768&&'ontouchstart' in window);
     document.documentElement.setAttribute('data-device',m?'mobile':'desktop');
   })();
   </script>
   ```
3. Add `mobile-hidden` class to navbar items per Phase 2.1 specification above
4. Do NOT change any other navbar behavior or structure

### Step 2: CSS foundation (custom.css)

1. Open `services/jupyterhub/html_templates_enhanced/static/custom.css`
2. Append the entire mobile CSS section from Phase 6 at the END of the file
3. Do NOT modify any existing CSS rules

### Step 3: Mobile home screen (home.html)

1. Open `services/jupyterhub/html_templates_enhanced/home.html`
2. Add `mobile-hidden` class to the Manage Volumes button (line 36-43)
3. Wrap the named servers block (lines 96-162) with `<div class="mobile-hidden">`
4. Add `mobile-hidden` class to manage volumes modal (line 165-208)
5. Add inline mobile activity monitor HTML after line 93 (after session timer closing `{% endif %}`) per Phase 4.5
6. Add mobile JavaScript in the `{% block script %}` section:
   - Start button interception (Phase 4.3)
   - Mobile activity monitor fetch/render (Phase 4.6)
7. Preserve ALL existing desktop JavaScript unchanged

### Step 4: Mobile activity page (activity.html)

1. Open `services/jupyterhub/html_templates_enhanced/activity.html`
2. Add `mobile-hidden` class to the existing `activity-table-container` div
3. Add mobile card container HTML per Phase 5.1
4. Modify the existing `fetchActivityData()` function to detect device and render to the appropriate container (table for desktop, cards for mobile)
5. Keep the existing Reset/Refresh buttons visible on mobile
6. Ensure auto-refresh interval works for both layouts

### Step 5: Login/Signup (CSS only)

No template changes needed. The CSS from Step 2 handles login/signup mobile styling.

## Validation Checklist

### Build and Deploy

- [ ] Build the image: `make build BUILD_OPTS='--no-version-increment --no-cache'`
- [ ] Start the platform: `./start.sh`
- [ ] Verify hub starts without errors: `docker logs jupyterhub 2>&1 | tail -20`

### Desktop Validation (must be unchanged)

- [ ] Open `https://localhost/jupyterhub` in desktop browser
- [ ] Verify login page looks identical to current
- [ ] Login as regular user - verify home page is unchanged
- [ ] Verify all navbar items visible (Home, Token, Change Password, etc.)
- [ ] Verify named servers table visible
- [ ] Verify manage volumes button visible when server stopped
- [ ] Verify session timer works
- [ ] Login as admin - verify Activity, Notifications, Settings, Admin all accessible
- [ ] Verify activity page table renders normally
- [ ] Verify dark mode toggle works

### Mobile Validation

Test using browser DevTools mobile emulation (Chrome: F12 -> Toggle Device Toolbar -> select iPhone or Android device) OR real mobile device.

#### Login (mobile)

- [ ] Login page renders full-width
- [ ] Input fields are large enough to tap (min 44px height)
- [ ] Submit button spans full width
- [ ] Login succeeds and redirects to home

#### Home - Regular User (mobile)

- [ ] Only Home link in navbar (no Token, Change Password, etc.)
- [ ] Logout button visible
- [ ] Dark mode toggle visible
- [ ] Start/Stop/Restart buttons are full-width, stacked vertically
- [ ] Manage Volumes button is NOT visible
- [ ] Named servers table is NOT visible
- [ ] Clicking "Start My Server" starts the server WITHOUT navigating to JupyterLab
- [ ] After server starts, page refreshes and shows "Server Running" status
- [ ] Stop button works and refreshes page
- [ ] Restart button works with confirmation modal
- [ ] Session timer card visible and functional
- [ ] Session extension input and button work
- [ ] No inline activity monitor shown (not admin)
- [ ] Version footer visible at bottom

#### Home - Admin User (mobile)

- [ ] Home and Activity links visible in navbar
- [ ] All regular user controls work (start/stop/restart/session timer)
- [ ] Inline activity monitor card visible below session timer
- [ ] Activity monitor shows user list with status dots (green/amber/red)
- [ ] Activity monitor shows time remaining per user
- [ ] Activity monitor auto-refreshes every 10 seconds
- [ ] User count badge shows correct numbers

#### Activity Page - Admin (mobile)

- [ ] Accessible via Activity navbar link
- [ ] Card-based layout (NOT table)
- [ ] Each user card shows: status dot, username, CPU, memory, time remaining
- [ ] Activity bar visualization renders
- [ ] Refresh button works
- [ ] Reset button works with confirmation
- [ ] Auto-refresh works (10s interval)
- [ ] Loading spinner shows during data fetch

#### Dark Mode (mobile)

- [ ] Toggle dark mode on mobile
- [ ] All mobile elements render correctly in dark mode
- [ ] Status dot colors remain visible
- [ ] Cards and backgrounds adapt

#### Edge Cases

- [ ] Rotate device to landscape - layout remains usable
- [ ] Resize desktop browser below 768px - should trigger mobile view
- [ ] Resize back above 768px - should return to desktop view (may require refresh)
- [ ] User with no server running sees only Start button and Manage Volumes (hidden on mobile)
- [ ] Admin with no active servers sees empty activity monitor with appropriate message

## Key Patterns to Reuse

The implementing agent should reuse these existing patterns found in the codebase:

### JavaScript Patterns (from home.html)

- **CSRF token**: `getCookie('_xsrf')` function (home.html line 261-265)
- **AJAX calls**: jQuery `$.ajax()` with `X-XSRFToken` header (home.html line 300+)
- **RequireJS wrapper**: `require(["jquery", "home"], function($) { ... })` (home.html line 251)
- **Bootstrap modals**: `bootstrap.Modal.getInstance()` pattern (home.html)
- **MutationObserver**: For detecting JupyterHub's own DOM changes (home.html)

### API Endpoints (existing, no new ones needed)

- `POST {{ base_url }}api/users/{username}/server` - Start server
- `DELETE {{ base_url }}api/users/{username}/server` - Stop server
- `POST {{ base_url }}api/users/{username}/restart-server` - Restart
- `GET {{ base_url }}api/users/{username}/session-info` - Session timer data
- `POST {{ base_url }}api/users/{username}/extend-session` - Extend session
- `GET {{ base_url }}api/activity` - Activity monitor data (admin only)

### CSS Patterns (from custom.css)

- **Color palette**: Use `--stellars-*` CSS variables defined in `:root`
- **Compact spacing**: Follow existing `--compact-spacing-*` variables
- **Dark mode**: Use `[data-bs-theme="dark"]` for dark mode overrides
- **Status colors**: Green `#28a745`, Yellow `#ffc107`, Red `#dc3545` (explicit hex, not Bootstrap classes)

### Template Patterns

- **Base template**: All pages extend `page.html`
- **Blocks**: `{% block main %}`, `{% block script %}`, `{% block footer %}`
- **Admin check**: `{% if 'admin-ui' in parsed_scopes %}`
- **Server state**: `{% if default_server.active %}`
- **Template vars**: `{{ base_url }}`, `{{ user.name }}`, `{{ stellars_version }}`

## What NOT to Do

- Do NOT create new Python handlers or API endpoints
- Do NOT modify `jupyterhub_config.py` or `custom_handlers.py`
- Do NOT change the Dockerfile
- Do NOT add new JavaScript libraries or dependencies
- Do NOT modify existing desktop CSS rules - only ADD new mobile rules
- Do NOT restructure existing HTML - only add classes and new mobile-only sections
- Do NOT change the authentication flow
- Do NOT add server-side User-Agent detection (keep it pure client-side JS)
- Do NOT use CSS `@media` queries alone - use `[data-device]` attribute for reliable detection
- Do NOT increment version in project.env (already set to 3.9.0)
