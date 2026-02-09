## stellars_hub Package

The `stellars_hub` package provides all platform logic for the Stellars JupyterHub deployment. It is a pip-installable Python package installed into the JupyterHub container during Docker build. The package is a pure logic library - it contains zero hardcoded data, zero environment variable reads at module level, and zero configuration state. All data flows in through explicit function parameters from `jupyterhub_config.py`.

**Package version**: defined in `stellars_hub/__init__.py`

**Build system**: hatchling via `pyproject.toml`

**Dependencies**: docker, dockerspawner, nativeauthenticator, idle-culler, pyyaml, xkcdpass, aiohttp, escapism

### Architecture

The package follows a declarative configuration pattern. `jupyterhub_config.py` reads all environment variables, defines all data literals (volumes, groups, paths), and calls package functions with explicit parameters. Handlers access runtime config through `self.settings['stellars_config']` (Tornado settings dict), never through `os.environ` or module constants.

```
jupyterhub_config.py          (data + orchestration)
  |
  +-- stellars_hub/           (pure logic)
  |     +-- auth.py           (authenticator)
  |     +-- branding.py       (logo, favicon, icons)
  |     +-- events.py         (SQLAlchemy event listeners)
  |     +-- gpu.py            (NVIDIA detection)
  |     +-- groups.py         (built-in group management)
  |     +-- hooks.py          (pre-spawn hook factory)
  |     +-- services.py       (activity sampler, idle culler)
  |     +-- volumes.py        (volume suffix extraction)
  |     +-- docker_utils.py   (username encoding, container stats)
  |     +-- password_cache.py (in-memory credential cache)
  |     +-- volume_cache.py   (volume size refresher)
  |     +-- handlers/         (14 Tornado request handlers)
  |     +-- activity/         (activity monitoring subsystem)
```

### Module Reference

#### Core Modules

**`branding.py`** - `setup_branding(logo_uri, favicon_uri, lab_main_icon_uri, lab_splash_icon_uri)` processes branding URIs. `file://` URIs copy files to JupyterHub's static directory, URL URIs pass through for template rendering. Returns a dict with resolved paths and URLs.

**`services.py`** - `get_services_and_roles(culler_enabled, culler_timeout, culler_interval, culler_max_age, sample_interval)` builds JupyterHub service and role definitions. Activity sampler is always enabled. Idle culler is conditional.

**`hooks.py`** - `make_pre_spawn_hook(branding, builtin_groups, favicon_uri)` returns an async closure that grants Docker access based on group membership, injects CHP favicon proxy routes, and resolves JupyterLab icon URIs at spawn time. `schedule_startup_favicon_callback(favicon_uri)` registers CHP routes for servers already running when hub restarts.

**`groups.py`** - `ensure_groups(builtin_groups)` creates JupyterHub groups at startup by querying the database directly. Called from `01_ensure_groups.py` startup script before JupyterHub starts.

**`volumes.py`** - `get_user_volume_suffixes(volumes_dict)` extracts user volume suffixes (home, workspace, cache) from the spawner volumes dictionary.

**`gpu.py`** - `resolve_gpu_mode(gpu_enabled, nvidia_image)` handles three modes: 0 (disabled), 1 (forced), 2 (auto-detect via `nvidia-smi` in a CUDA container).

**`events.py`** - `register_events()` attaches SQLAlchemy event listeners for user lifecycle management (rename sync, activity data transfer).

**`auth.py`** - `StellarsNativeAuthenticator` extends NativeAuthenticator with custom authorization area handler.

**`docker_utils.py`** - `encode_username_for_docker(username)` escapes special characters for Docker volume/container names. `get_container_stats_async(username)` fetches CPU/memory stats from Docker API.

**`password_cache.py`** - In-memory TTL cache for temporarily storing auto-generated user passwords after admin creation.

**`volume_cache.py`** - `VolumeSizeRefresher` singleton with periodic callback that calculates per-user Docker volume sizes in the background.

#### Handlers Package

All handlers extend `jupyterhub.handlers.BaseHandler` and access configuration through `self.settings['stellars_config']`.

| Handler | Route | Purpose |
|---------|-------|---------|
| `ManageVolumesHandler` | `/api/users/{user}/manage-volumes` | Delete user volumes (server must be stopped) |
| `RestartServerHandler` | `/api/users/{user}/restart-server` | Docker container restart without recreation |
| `SessionInfoHandler` | `/api/users/{user}/session-info` | Idle culler status and time remaining |
| `ExtendSessionHandler` | `/api/users/{user}/extend-session` | Add hours to idle culler timeout |
| `ActiveServersHandler` | `/api/notifications/active-servers` | List running user servers |
| `BroadcastNotificationHandler` | `/api/notifications/broadcast` | Send notifications to all active servers |
| `GetUserCredentialsHandler` | `/api/admin/credentials` | Retrieve cached auto-generated passwords |
| `ActivityDataHandler` | `/api/activity` | User activity data with Docker stats |
| `ActivityResetHandler` | `/api/activity/reset` | Clear all activity samples |
| `ActivitySampleHandler` | `/api/activity/sample` | Trigger manual activity sampling |
| `NotificationsPageHandler` | `/notifications` | Admin broadcast UI |
| `SettingsPageHandler` | `/settings` | Platform settings display |
| `ActivityPageHandler` | `/activity` | Activity monitoring dashboard |
| `FaviconRedirectHandler` | (injected at runtime) | 302 redirect for JupyterLab favicon requests |

#### Activity Subpackage

The activity monitoring subsystem tracks user engagement through periodic sampling with exponential decay scoring.

- **`model.py`** - SQLAlchemy model for `activity_samples` table (username, timestamp, is_active)
- **`monitor.py`** - `ActivityMonitor` singleton managing sample recording, scoring, pruning, and user lifecycle
- **`helpers.py`** - Convenience functions wrapping `ActivityMonitor` methods for use in handlers and services
- **`sampler.py`** - `ActivitySampler` with periodic callback for automatic sampling
- **`service.py`** - `ActivitySamplerService` runs as a JupyterHub managed service, polling the hub API

### Configuration Flow

The `stellars_config` dict passed through `tornado_settings` provides handler-accessible configuration:

```python
c.JupyterHub.tornado_settings = {
    'stellars_config': {
        'user_volume_suffixes': ['home', 'workspace', 'cache'],
        'idle_culler_enabled': 0,
        'idle_culler_timeout': 86400,
        'idle_culler_max_extension': 24,
    }
}
```

Handlers read this via `self.settings['stellars_config']['key']` instead of `os.environ.get()`. This eliminates hidden runtime dependencies and makes handler behavior testable without environment variable patching.

### Testing

The package includes 65 tests across 8 test files. Tests run during Docker build (builder stage) and locally via:

```bash
cd services/jupyterhub/stellars_hub
python3 -m pytest tests/ -v
```

Test files cover imports, branding, services, GPU detection, activity monitoring, password cache, Docker utilities, and volume management. Service and branding tests call functions directly with explicit parameters - no `unittest.mock.patch` required.
