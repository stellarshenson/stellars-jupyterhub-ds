# Feature Plan: User Control Panel Enhancements

## Overview

Enhance JupyterHub user control panel with two self-service features:
1. **Reset Home Volume**: Allow users to reset their home directory volume when server is stopped
2. **Restart Server**: Provide one-click server restart functionality

Both features include confirmation dialogs and proper permission enforcement.

## Feature Scope

### Feature 1: Reset Home Volume

**Access Control**:
- Users can reset their own home volume
- Admins can reset any user's home volume

**Volume Scope**:
- Only `jupyterlab-{username}_home` volume
- Does NOT affect workspace (`jupyterlab-{username}_workspace`) or cache (`jupyterlab-{username}_cache`) volumes

**UI Location**:
- User control panel (accessible to both user and admin)
- Button visible only when server is stopped

### Feature 2: Restart Server

**Access Control**:
- Users can restart their own server
- Admins can restart any user's server

**Functionality**:
- Uses Docker's native container restart (preserves container, does NOT recreate)
- Performs graceful restart with configurable timeout
- Maintains all volumes, network connections, and container configuration
- Equivalent to "Restart" button in Docker Desktop

**UI Location**:
- User control panel (accessible to both user and admin)
- Button visible only when server is running

**Technical Approach**:
- Direct Docker API call: `container.restart(timeout=10)`
- Does NOT use JupyterHub's `stop()` and `spawn()` methods (which would recreate container)
- Container ID remains the same after restart

## Technical Requirements

### Prerequisites
- User's JupyterLab server must be stopped (for reset volume)
- Volume `jupyterlab-{username}_home` must exist (for reset volume)
- **Docker socket accessible at `/var/run/docker.sock`** (already configured in `compose.yml` line 54 with read-write access)
- Docker Python SDK available (already installed in `Dockerfile.jupyterhub`)

### Existing Infrastructure Leveraged
Both features utilize infrastructure already in place:
- **Docker Socket**: Mounted at `/var/run/docker.sock:rw` for DockerSpawner, we reuse this for volume management and container restart
- **Docker Python SDK**: Already installed via `pip install docker` in the JupyterHub image
- **Container Naming Pattern**: Follows existing convention `jupyterlab-{username}` from `jupyterhub_config.py` line 112
- **Volume Naming Pattern**: Follows existing convention `jupyterlab-{username}_home` from `jupyterhub_config.py` line 116

### Permission Model
- **User access**: Can only reset their own home volume
- **Admin access**: Can reset any user's home volume
- Implemented via custom decorator: `@admin_or_self`

## Implementation Steps

### 1. Create Custom API Handler

**File**: `services/jupyterhub/conf/bin/volume_handler.py` (or inline in `config/jupyterhub_config.py`)

**Purpose**: Handle volume reset requests via REST API

**Endpoint**: `DELETE /hub/api/users/{username}/reset-home-volume`

**Logic**:
```python
from jupyterhub.handlers import BaseHandler
from jupyterhub.utils import admin_or_self
import docker

class ResetHomeVolumeHandler(BaseHandler):
    @admin_or_self
    async def delete(self, username):
        # 1. Verify user exists
        user = self.find_user(username)
        if not user:
            return self.send_error(404, "User not found")

        # 2. Check server is stopped
        spawner = user.spawner
        if spawner.active:
            return self.send_error(400, "Server must be stopped before resetting volume")

        # 3. Connect to Docker
        docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')

        # 4. Verify volume exists
        volume_name = f'jupyterlab-{username}_home'
        try:
            volume = docker_client.volumes.get(volume_name)
        except docker.errors.NotFound:
            return self.send_error(404, f"Volume {volume_name} not found")

        # 5. Remove volume
        try:
            volume.remove()
            self.set_status(200)
            self.finish({"message": f"Volume {volume_name} successfully reset"})
        except docker.errors.APIError as e:
            return self.send_error(500, f"Failed to remove volume: {str(e)}")
```

**Error Handling**:
- 404: User not found or volume doesn't exist
- 400: Server still running
- 500: Docker API error (volume in use, permission denied)

### 2. Register API Handler

**File**: `config/jupyterhub_config.py`

Add handler registration:
```python
from volume_handler import ResetHomeVolumeHandler

c.JupyterHub.extra_handlers = [
    (r'/api/users/([^/]+)/reset-home-volume', ResetHomeVolumeHandler),
]
```

### 3. Extend User Control Panel Template

**File**: `services/jupyterhub/templates/home.html` (override default template)

**Template Structure**:
- Extend JupyterHub's base `home.html` template
- Add "Reset Home Volume" button in server controls section
- Button states:
  - Enabled: Server stopped AND volume exists
  - Disabled: Server running OR volume doesn't exist
  - Tooltip explaining current state

**Button HTML**:
```html
{% if not user.server %}
<button id="reset-home-volume-btn"
        class="btn btn-danger btn-sm"
        data-username="{{ user.name }}"
        data-toggle="modal"
        data-target="#reset-volume-modal">
    <i class="fa fa-trash"></i> Reset Home Volume
</button>
{% endif %}
```

### 4. Create Confirmation Modal

**File**: `services/jupyterhub/templates/home.html` (inline modal)

**Modal Content**:
```html
<div class="modal fade" id="reset-volume-modal" tabindex="-1" role="dialog">
  <div class="modal-dialog" role="document">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Reset Home Volume</h5>
        <button type="button" class="close" data-dismiss="modal">&times;</button>
      </div>
      <div class="modal-body">
        <div class="alert alert-danger">
          <strong>Warning:</strong> This action cannot be undone!
        </div>
        <p>This will permanently delete all files in your home directory:</p>
        <code id="volume-name-display">jupyterlab-{username}_home</code>
        <p class="mt-3">Your workspace and cache volumes will NOT be affected.</p>
        <p><strong>Are you sure you want to continue?</strong></p>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-danger" id="confirm-reset-btn">
          Yes, Reset Home Volume
        </button>
      </div>
    </div>
  </div>
</div>
```

### 5. Implement Client-Side JavaScript

**File**: `services/jupyterhub/templates/home.html` (inline script)

**Functionality**:
- Check server status and volume existence on page load
- Enable/disable reset button based on state
- Handle modal confirmation
- Make API call to reset endpoint
- Display success/error notifications

**JavaScript Logic**:
```javascript
<script>
$(document).ready(function() {
    const username = "{{ user.name }}";

    // Update volume name in modal
    $('#volume-name-display').text(`jupyterlab-${username}_home`);

    // Confirm reset handler
    $('#confirm-reset-btn').on('click', function() {
        const apiUrl = `/hub/api/users/${username}/reset-home-volume`;

        $.ajax({
            url: apiUrl,
            type: 'DELETE',
            headers: {
                'Authorization': 'token ' + window.jhdata.api_token
            },
            success: function(response) {
                $('#reset-volume-modal').modal('hide');
                alert('Home volume successfully reset. Your home directory will be recreated on next server start.');
                location.reload();
            },
            error: function(xhr) {
                $('#reset-volume-modal').modal('hide');
                const errorMsg = xhr.responseJSON?.message || 'Failed to reset volume';
                alert(`Error: ${errorMsg}`);
            }
        });
    });
});
</script>
```

### 6. Update Docker Configuration

**No changes required**:
- Docker Python SDK already installed in `Dockerfile.jupyterhub`
- Docker socket already mounted in `compose.yml` (line 54)
- Existing Docker client code in `jupyterhub_config.py` can be referenced

---

## Feature 2: Restart Server Implementation

### 1. Create Restart Server API Handler

**File**: `config/jupyterhub_config.py` (inline with volume handler)

**Purpose**: Handle server restart requests via REST API

**Endpoint**: `POST /hub/api/users/{username}/restart-server`

**Logic**:
```python
from jupyterhub.handlers import BaseHandler
from jupyterhub.utils import admin_or_self
import docker

class RestartServerHandler(BaseHandler):
    @admin_or_self
    async def post(self, username):
        # 1. Verify user exists
        user = self.find_user(username)
        if not user:
            return self.send_error(404, "User not found")

        # 2. Check server is running
        spawner = user.spawner
        if not spawner.active:
            return self.send_error(400, "Server is not running")

        # 3. Get container name from spawner
        container_name = f'jupyterlab-{username}'

        # 4. Connect to Docker and restart container
        docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')

        try:
            # Get the container
            container = docker_client.containers.get(container_name)

            # Restart the container (graceful restart with 10s timeout)
            container.restart(timeout=10)

            self.set_status(200)
            self.finish({"message": f"Container {container_name} successfully restarted"})
        except docker.errors.NotFound:
            return self.send_error(404, f"Container {container_name} not found")
        except docker.errors.APIError as e:
            return self.send_error(500, f"Failed to restart container: {str(e)}")
```

**Error Handling**:
- 404: User not found or container doesn't exist
- 400: Server not running (spawner not active)
- 500: Docker API error during restart

### 2. Register Restart Handler

**File**: `config/jupyterhub_config.py`

Update handler registration:
```python
from volume_handler import ResetHomeVolumeHandler, RestartServerHandler

c.JupyterHub.extra_handlers = [
    (r'/api/users/([^/]+)/reset-home-volume', ResetHomeVolumeHandler),
    (r'/api/users/([^/]+)/restart-server', RestartServerHandler),
]
```

### 3. Add Restart Button to Template

**File**: `services/jupyterhub/templates/home.html`

**Button HTML** (add next to existing server controls):
```html
{% if user.server %}
<button id="restart-server-btn"
        class="btn btn-warning btn-sm"
        data-username="{{ user.name }}"
        data-toggle="modal"
        data-target="#restart-server-modal">
    <i class="fa fa-refresh"></i> Restart Server
</button>
{% endif %}
```

### 4. Create Restart Confirmation Modal

**File**: `services/jupyterhub/templates/home.html`

**Modal Content**:
```html
<div class="modal fade" id="restart-server-modal" tabindex="-1" role="dialog">
  <div class="modal-dialog" role="document">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Restart Server</h5>
        <button type="button" class="close" data-dismiss="modal">&times;</button>
      </div>
      <div class="modal-body">
        <div class="alert alert-warning">
          <strong>Notice:</strong> Your server will be temporarily unavailable during restart.
        </div>
        <p>This will restart your JupyterLab container using Docker's native restart:</p>
        <ul>
          <li>Gracefully stops the container</li>
          <li>Restarts the same container (does not recreate)</li>
          <li>Preserves all volumes and configuration</li>
        </ul>
        <p class="mt-3"><strong>Any unsaved work in notebooks will be lost.</strong></p>
        <p class="mt-2">Your files on disk are safe and will remain intact.</p>
        <p>Are you sure you want to restart?</p>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-warning" id="confirm-restart-btn">
          Yes, Restart Server
        </button>
      </div>
    </div>
  </div>
</div>
```

### 5. Implement Restart JavaScript

**File**: `services/jupyterhub/templates/home.html` (add to existing script)

**JavaScript Logic**:
```javascript
// Restart server handler
$('#confirm-restart-btn').on('click', function() {
    const username = "{{ user.name }}";
    const apiUrl = `/hub/api/users/${username}/restart-server`;

    // Disable button and show loading state
    $('#confirm-restart-btn').prop('disabled', true).text('Restarting...');

    $.ajax({
        url: apiUrl,
        type: 'POST',
        headers: {
            'Authorization': 'token ' + window.jhdata.api_token
        },
        success: function(response) {
            $('#restart-server-modal').modal('hide');
            alert('Server successfully restarted. Redirecting to your server...');
            // Redirect to user's server
            window.location.href = `/user/${username}/lab`;
        },
        error: function(xhr) {
            $('#restart-server-modal').modal('hide');
            const errorMsg = xhr.responseJSON?.message || 'Failed to restart server';
            alert(`Error: ${errorMsg}`);
            $('#confirm-restart-btn').prop('disabled', false).text('Yes, Restart Server');
        }
    });
});
```

### 6. Enhanced Status Polling (Optional)

**File**: `services/jupyterhub/templates/home.html`

Add polling to detect when restart completes:
```javascript
function pollServerStatus(username) {
    const interval = setInterval(function() {
        $.ajax({
            url: `/hub/api/users/${username}`,
            type: 'GET',
            headers: {
                'Authorization': 'token ' + window.jhdata.api_token
            },
            success: function(data) {
                if (data.server && data.server.ready) {
                    clearInterval(interval);
                    window.location.href = `/user/${username}/lab`;
                }
            }
        });
    }, 2000); // Poll every 2 seconds

    // Timeout after 60 seconds
    setTimeout(function() {
        clearInterval(interval);
    }, 60000);
}
```

## Files to Create/Modify

### New Files
- `services/jupyterhub/templates/home.html` - Custom user control panel template with both features

### Modified Files
- `config/jupyterhub_config.py` - Register API handlers, add volume reset and restart server handler classes
- `services/jupyterhub/Dockerfile.jupyterhub` - No changes needed (Docker SDK already installed)

### Optional Separate Files
- `services/jupyterhub/conf/bin/volume_handler.py` - API handler logic for both features (can be inline in config instead)

## Testing Plan

### Unit Tests

#### Reset Home Volume Tests
1. **API Handler Tests**:
   - Test permission enforcement (user can only reset own volume)
   - Test admin can reset any user's volume
   - Test rejection when server is running
   - Test volume not found error handling
   - Test Docker API error handling

2. **Volume Operations Tests**:
   - Create test volume
   - Verify volume exists check
   - Verify volume removal
   - Test volume in use scenario

#### Restart Server Tests
1. **API Handler Tests**:
   - Test permission enforcement (user can only restart own server)
   - Test admin can restart any user's server
   - Test rejection when server is not running
   - Test stop operation failure handling
   - Test start operation failure handling

2. **Server Operations Tests**:
   - Verify server status check (running/stopped)
   - Test graceful shutdown
   - Test server restart sequence
   - Test concurrent restart requests

### Integration Tests

#### Reset Home Volume Tests
1. **UI Flow Tests**:
   - Button appears only when server stopped
   - Modal displays correct volume name
   - Confirmation triggers API call
   - Success notification displays
   - Error handling for failed API calls

2. **End-to-End Tests**:
   - User stops server
   - User clicks reset button
   - User confirms in modal
   - Volume is removed
   - User starts server (new volume created)
   - Verify clean home directory

#### Restart Server Tests
1. **UI Flow Tests**:
   - Button appears only when server running
   - Modal displays proper warning
   - Confirmation triggers API call
   - Loading state during restart
   - Redirect to server after restart
   - Error handling for failed restart

2. **End-to-End Tests**:
   - User has running server
   - User clicks restart button
   - User confirms in modal
   - Server stops gracefully
   - Server starts automatically
   - User redirected to new server instance
   - Verify server is functional after restart

#### Combined Features Tests
1. **Button State Management**:
   - Reset button visible when server stopped
   - Restart button visible when server running
   - Both buttons never visible simultaneously
   - Button states update after operations

2. **Workflow Tests**:
   - Restart server -> works normally
   - Stop server -> Reset volume -> Start server -> verify clean home
   - Reset volume -> Start server -> Restart server -> verify functionality

## Security Considerations

### Reset Home Volume
1. **Permission Validation**: Always verify user has permission to reset volume (own volume or admin)
2. **Server State Check**: Prevent volume deletion while container is running
3. **Volume Ownership**: Validate volume name matches expected pattern `jupyterlab-{username}_home`
4. **Docker Socket Access**: Limit Docker operations to volume management only
5. **Input Validation**: Sanitize username parameter to prevent injection attacks
6. **Audit Logging**: Log all volume reset operations with username and timestamp

### Restart Server
1. **Permission Validation**: Verify user can only restart own server (or is admin)
2. **State Validation**: Ensure server is actually running before attempting restart
3. **Resource Limits**: Prevent restart request flooding (rate limiting)
4. **Graceful Shutdown**: Allow proper cleanup before forced termination
5. **Session Integrity**: Invalidate old server tokens after restart
6. **Audit Logging**: Log all restart operations with username, timestamp, and outcome

### Both Features
1. **CSRF Protection**: All API endpoints must validate CSRF tokens
2. **Authentication**: Require valid JupyterHub session token
3. **Authorization**: Implement `@admin_or_self` decorator consistently
4. **Rate Limiting**: Prevent abuse through repeated operations
5. **Error Disclosure**: Don't expose internal system details in error messages

## Edge Cases

### Reset Home Volume
1. **Volume doesn't exist**: Display informative error, don't fail silently
2. **Server starting/stopping**: Disable button during transition states
3. **Volume in use by orphaned container**: Attempt force removal or display cleanup instructions
4. **Multiple concurrent reset requests**: Implement request locking/queuing
5. **Admin resetting admin's volume**: Require additional confirmation
6. **Network errors during API call**: Display retry option
7. **Volume has active snapshots/backups**: Check for dependencies before removal

### Restart Server
1. **Server not responding**: Implement timeout and force stop if graceful shutdown fails
2. **Restart during server startup**: Queue restart request until server is fully running
3. **Container stuck in stopping state**: Detect and handle orphaned containers
4. **Multiple concurrent restart requests**: Prevent duplicate restarts with request locking
5. **Restart fails to start**: Display error and provide manual start option
6. **User opens multiple tabs**: Synchronize state across browser tabs
7. **Network interruption during restart**: Handle client-side timeout gracefully

### Combined Features
1. **Rapid operation switching**: User stops -> resets -> starts -> restarts quickly
2. **Session expires during operation**: Re-authenticate and resume or show clear error
3. **Hub restart during user operation**: Handle hub unavailability gracefully
4. **Docker daemon unavailable**: Detect and display system-level error message

## Future Enhancements

### Reset Home Volume
1. **Backup before reset**: Create automatic backup to `jupyterhub_shared` before deletion
2. **Selective reset**: Allow resetting workspace or cache volumes individually
3. **Reset all volumes**: Single action to reset home, workspace, and cache
4. **Volume size display**: Show current volume size before reset
5. **Reset history**: Log of volume reset operations per user
6. **Scheduled resets**: Allow users to schedule periodic volume resets
7. **Template volumes**: Pre-populate new volumes with template files
8. **Email notification**: Send confirmation email after volume reset

### Restart Server
1. **Scheduled restarts**: Allow users to schedule regular server restarts
2. **Restart with options**: Choose specific image version or resource limits
3. **Pre-restart save**: Automatically save all open notebooks before restart
4. **Restart notifications**: WebSocket-based real-time status updates
5. **Restart analytics**: Track restart frequency and success rates per user
6. **Soft restart**: Restart JupyterLab without container restart (when possible)
7. **Batch restart**: Admin can restart multiple user servers simultaneously
8. **Auto-restart on failure**: Automatically restart server if it crashes

### Combined Features
1. **Workflow presets**: "Clean slate" button that resets volume and restarts server
2. **Operation queue**: Queue multiple operations (stop, reset, restart) in sequence
3. **Health checks**: Automatic server health monitoring with auto-restart option
4. **Resource optimization**: Suggest restart when server uses excessive resources

## Dependencies

- **JupyterHub**: 4.x (current base image: `jupyterhub/jupyterhub:latest`)
- **Docker Python SDK**: Already installed via pip
- **NativeAuthenticator**: Already configured for user management
- **Bootstrap**: Available in JupyterHub default templates for modal styling
- **jQuery**: Available in JupyterHub default templates for AJAX calls

## Rollout Plan

1. **Development**: Implement on local environment
   - Feature 1: Reset Home Volume (priority: high)
   - Feature 2: Restart Server (priority: medium)
2. **Testing**: Verify all test cases pass for both features
3. **Documentation**: Update README.md and `.claude/CLAUDE.md` with feature descriptions
4. **Deployment**: Build new Docker image with both features
5. **User Communication**: Notify users of new self-service capabilities
6. **Monitoring**: Track usage and error rates for both features during first week
7. **Iteration**: Gather user feedback and implement improvements

## Implementation Priority

### Phase 1: Core Features
1. Reset Home Volume API handler and basic UI
2. Restart Server API handler and basic UI
3. Both confirmation modals

### Phase 2: Enhanced UX
1. Status polling for restart operation
2. Better error messages and user feedback
3. Loading states and progress indicators

### Phase 3: Polish
1. Audit logging for both operations
2. Rate limiting implementation
3. Edge case handling
4. Accessibility improvements

## Summary

This feature plan adds two essential self-service capabilities to JupyterHub:

**Reset Home Volume** allows users to cleanly start over by removing their home directory volume when their server is stopped. This is useful for resolving corrupted environments or starting fresh with a clean slate. The operation uses Docker API to safely remove the `jupyterlab-{username}_home` volume after confirming the server is stopped.

**Restart Server** provides a convenient one-click solution to restart a running JupyterLab container using Docker's native restart functionality. Unlike JupyterHub's stop/spawn cycle (which recreates containers), this uses `container.restart()` to preserve the container identity, volumes, and configuration. This helps users quickly recover from server issues or apply certain configuration changes without losing their environment setup.

Both features maintain security through permission validation, provide clear user feedback through confirmation modals, and integrate seamlessly into the existing JupyterHub user control panel.
