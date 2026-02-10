# Configuration file for JupyterHub
#
# All data (env vars, volumes, groups) is defined here. The stellars_hub
# package provides pure logic functions only - zero hardcoded data, zero
# env var reads at module level. Every parameter is passed explicitly.
#
# Sections:
#   1. Environment Variables   - all os.environ.get() calls with typed defaults
#   2. Data Literals           - volumes, groups, paths, derived values
#   3. Logic Calls             - event registration, GPU detection, branding
#   4. JupyterHub Config       - all c.* settings (SSL, spawner, auth, handlers)
#   5. Services & Callbacks    - background services, startup hooks

import os                       # env var reads

import jupyterhub               # __version__, __file__ for template paths
import nativeauthenticator      # __file__ for template path resolution

# stellars_hub core functions - pure logic, no side effects on import
from stellars_hub import (
    StellarsNativeAuthenticator,            # NativeAuthenticator subclass with custom authorization UI
    get_services_and_roles,                 # builds JupyterHub services list (activity sampler, idle culler)
    get_user_volume_suffixes,               # extracts ['home', 'workspace', 'cache'] from volumes dict
    make_pre_spawn_hook,                    # factory returning async hook for group perms, favicon, icons
    register_events,                        # attaches SQLAlchemy listeners for user rename/delete sync
    resolve_gpu_mode,                       # GPU detection: 0=off, 1=forced, 2=auto-detect via nvidia-smi
    schedule_startup_favicon_callback,      # registers CHP favicon routes for already-running servers
    setup_branding,                         # processes logo/favicon/icon URIs, copies file:// to static dir
)

# Tornado request handlers - registered via c.JupyterHub.extra_handlers
from stellars_hub.handlers import (
    ActivityDataHandler,                    # GET  /api/activity - user activity data with Docker stats
    ActivityPageHandler,                    # GET  /activity - admin activity monitoring dashboard
    ActivityResetHandler,                   # POST /api/activity/reset - clear all activity samples
    ActivitySampleHandler,                  # POST /api/activity/sample - trigger manual activity sampling
    ActiveServersHandler,                   # GET  /api/notifications/active-servers - list running servers
    BroadcastNotificationHandler,           # POST /api/notifications/broadcast - send to all active servers
    ExtendSessionHandler,                   # POST /api/users/{user}/extend-session - add idle culler hours
    GetUserCredentialsHandler,              # GET  /api/admin/credentials - retrieve cached passwords
    ManageVolumesHandler,                   # DELETE /api/users/{user}/manage-volumes - delete user volumes
    NotificationsPageHandler,               # GET  /notifications - admin broadcast UI
    RestartServerHandler,                   # POST /api/users/{user}/restart-server - Docker restart
    SessionInfoHandler,                     # GET  /api/users/{user}/session-info - idle culler status
    SettingsPageHandler,                    # GET  /settings - platform settings display
)

c = get_config()  # noqa: F821  - JupyterHub injects get_config() into config file namespace


# ── Section 1: Environment Variables ─────────────────────────────────────────
# All env var reads in one place. Typed with int() or str defaults.
# See settings_dictionary.yml for full documentation of each variable.

# Core platform toggles (0=disabled, 1=enabled)
JUPYTERHUB_SSL_ENABLED = int(os.environ.get("JUPYTERHUB_SSL_ENABLED", 1))                      # direct SSL termination (disable when behind reverse proxy)
JUPYTERHUB_GPU_ENABLED = int(os.environ.get("JUPYTERHUB_GPU_ENABLED", 2))                      # 0=off, 1=forced, 2=auto-detect
JUPYTERHUB_SERVICE_MLFLOW = int(os.environ.get("JUPYTERHUB_SERVICE_MLFLOW", 1))                 # MLflow tracking in spawned containers
JUPYTERHUB_SERVICE_RESOURCES_MONITOR = int(os.environ.get("JUPYTERHUB_SERVICE_RESOURCES_MONITOR", 1))  # resource monitor widget
JUPYTERHUB_SERVICE_TENSORBOARD = int(os.environ.get("JUPYTERHUB_SERVICE_TENSORBOARD", 1))       # TensorBoard in spawned containers
JUPYTERHUB_SIGNUP_ENABLED = int(os.environ.get("JUPYTERHUB_SIGNUP_ENABLED", 1))                 # user self-registration (0=admin-only)

# Idle culler - automatic server shutdown after inactivity
JUPYTERHUB_IDLE_CULLER_ENABLED = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_ENABLED", 0))       # 0=off, 1=on
JUPYTERHUB_IDLE_CULLER_TIMEOUT = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_TIMEOUT", 86400))   # seconds of inactivity before cull (24h)
JUPYTERHUB_IDLE_CULLER_INTERVAL = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_INTERVAL", 600))   # seconds between cull checks (10min)
JUPYTERHUB_IDLE_CULLER_MAX_AGE = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_MAX_AGE", 0))       # max server lifetime in seconds (0=unlimited)
JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION", 24))  # max user-requested extension hours

# Activity monitor - engagement scoring via periodic sampling
ACTIVITYMON_TARGET_HOURS = int(os.environ.get('JUPYTERHUB_ACTIVITYMON_TARGET_HOURS', 8))        # scoring window in hours
ACTIVITYMON_SAMPLE_INTERVAL = int(os.environ.get('JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL', 600))  # sampling interval in seconds (10min)

# Misc
TF_CPP_MIN_LOG_LEVEL = int(os.environ.get("TF_CPP_MIN_LOG_LEVEL", 3))                          # suppress TensorFlow logging in spawned containers

# Docker spawner settings
JUPYTERHUB_BASE_URL = os.environ.get("JUPYTERHUB_BASE_URL")                                     # URL prefix (e.g. /jupyterhub), None or / for root
JUPYTERHUB_NETWORK_NAME = os.environ.get("JUPYTERHUB_NETWORK_NAME", "jupyterhub_network")       # Docker network for hub + spawned containers
JUPYTERHUB_NOTEBOOK_IMAGE = os.environ.get("JUPYTERHUB_NOTEBOOK_IMAGE", "stellars/stellars-jupyterlab-ds:latest")  # JupyterLab image to spawn
JUPYTERHUB_NVIDIA_IMAGE = os.environ.get("JUPYTERHUB_NVIDIA_IMAGE", "nvidia/cuda:13.0.2-base-ubuntu24.04")  # CUDA image for GPU auto-detection
JUPYTERHUB_ADMIN = os.environ.get("JUPYTERHUB_ADMIN")                                          # admin username (auto-authorized on first signup)

# Branding URIs - file:// copies to static dir, http(s):// passed to templates, empty = stock assets
JUPYTERHUB_LOGO_URI = os.environ.get("JUPYTERHUB_LOGO_URI", "")                                # hub logo (login page, nav bar)
JUPYTERHUB_FAVICON_URI = os.environ.get("JUPYTERHUB_FAVICON_URI", "")                          # browser tab icon (hub + JupyterLab via CHP route)
JUPYTERHUB_LAB_MAIN_ICON_URI = os.environ.get("JUPYTERHUB_LAB_MAIN_ICON_URI", "")             # JupyterLab main area icon
JUPYTERHUB_LAB_SPLASH_ICON_URI = os.environ.get("JUPYTERHUB_LAB_SPLASH_ICON_URI", "")         # JupyterLab splash screen icon

# User environment customization - paths passed through to spawned containers
JUPYTERLAB_AUX_SCRIPTS_PATH = os.environ.get("JUPYTERLAB_AUX_SCRIPTS_PATH", "")             # admin startup scripts executed on container launch
JUPYTERLAB_AUX_MENU_PATH = os.environ.get("JUPYTERLAB_AUX_MENU_PATH", "")                   # admin-managed custom menu definitions for JupyterLab


# ── Section 2: Data Literals ─────────────────────────────────────────────────
# Static data that does not come from environment variables.

# Default working directory inside spawned containers (also used as workspace volume mount point)
DOCKER_NOTEBOOK_DIR = "/home/lab/workspace"

# Normalize base URL prefix - empty string for root path to avoid double slashes (e.g. //hub/home)
if JUPYTERHUB_BASE_URL in ['/', '', None]:
    JUPYTERHUB_BASE_URL_PREFIX = ''
else:
    JUPYTERHUB_BASE_URL_PREFIX = JUPYTERHUB_BASE_URL

# Per-user Docker volumes: {volume_name_template: mount_point}
# jupyterlab-{username}_* volumes are user-resettable via Manage Volumes UI
# jupyterhub_shared is read-write shared storage (can be CIFS via compose_override.yml)
DOCKER_SPAWNER_VOLUMES = {
    "jupyterlab-{username}_home": "/home",
    "jupyterlab-{username}_workspace": DOCKER_NOTEBOOK_DIR,
    "jupyterlab-{username}_cache": "/home/lab/.cache",
    "jupyterhub_shared": "/mnt/shared",
}

# Human-readable descriptions shown in the volume reset UI
VOLUME_DESCRIPTIONS = {
    'home': 'User home directory files, configurations',
    'workspace': 'Project files, notebooks, code',
    'cache': 'Temporary files, pip cache, conda cache',
}

# Groups auto-created at startup and before each spawn (protection against accidental deletion)
# docker-sock: mounts /var/run/docker.sock into user container
# docker-privileged: runs user container with --privileged flag
BUILTIN_GROUPS = ['docker-sock', 'docker-privileged']

# Derived: extract user-resettable volume suffixes ['home', 'workspace', 'cache'] from volumes dict
user_volume_suffixes = get_user_volume_suffixes(DOCKER_SPAWNER_VOLUMES)


# ── Section 3: Logic Calls ───────────────────────────────────────────────────
# Functions with side effects: event listeners, Docker commands, file copies.

# Attach SQLAlchemy event listeners for user rename/delete sync (activity data, NativeAuthenticator)
register_events()

# Detect GPU availability: mode 2 runs nvidia-smi in a CUDA container to auto-detect
# Returns (gpu_enabled: 0|1, nvidia_detected: 0|1)
gpu_enabled, nvidia_detected = resolve_gpu_mode(JUPYTERHUB_GPU_ENABLED, JUPYTERHUB_NVIDIA_IMAGE)

# Process branding URIs: file:// copies to JupyterHub static dir, URLs pass through
# Returns dict with resolved paths/URLs for logo_file, favicon_uri, lab icons
branding = setup_branding(
    logo_uri=JUPYTERHUB_LOGO_URI,
    favicon_uri=JUPYTERHUB_FAVICON_URI,
    lab_main_icon_uri=JUPYTERHUB_LAB_MAIN_ICON_URI,
    lab_splash_icon_uri=JUPYTERHUB_LAB_SPLASH_ICON_URI,
)


# ── Section 4: JupyterHub Configuration ──────────────────────────────────────
# All c.* traitlet settings. Grouped by subsystem.

# ── SSL ──
# Direct SSL termination (certs auto-generated by /mkcert.sh at container startup)
# Disable when running behind a reverse proxy that handles TLS (e.g. Traefik)
if JUPYTERHUB_SSL_ENABLED == 1:
    c.JupyterHub.ssl_cert = '/mnt/certs/server.crt'
    c.JupyterHub.ssl_key = '/mnt/certs/server.key'

# ── Spawner ──
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"

# Environment variables injected into every spawned JupyterLab container
c.DockerSpawner.environment = {
    'TF_CPP_MIN_LOG_LEVEL': TF_CPP_MIN_LOG_LEVEL,          # suppress TF C++ logging
    'TENSORBOARD_LOGDIR': '/tmp/tensorboard',                # TensorBoard log directory
    'MLFLOW_TRACKING_URI': 'http://localhost:5000',          # MLflow tracking server URL
    'MLFLOW_PORT': 5000,                                     # MLflow server port
    'MLFLOW_HOST': '0.0.0.0',                                # MLflow bind address
    'MLFLOW_WORKERS': 1,                                     # MLflow worker count
    'ENABLE_SERVICE_MLFLOW': JUPYTERHUB_SERVICE_MLFLOW,      # toggle MLflow in container startup
    'ENABLE_SERVICE_RESOURCES_MONITOR': JUPYTERHUB_SERVICE_RESOURCES_MONITOR,  # toggle resource monitor widget
    'ENABLE_SERVICE_TENSORBOARD': JUPYTERHUB_SERVICE_TENSORBOARD,  # toggle TensorBoard in container startup
    'ENABLE_GPU_SUPPORT': gpu_enabled,                       # GPU libraries initialization
    'ENABLE_GPUSTAT': gpu_enabled,                           # gpustat monitoring widget
    'NVIDIA_DETECTED': nvidia_detected,                      # GPU hardware availability flag
    'JUPYTERLAB_AUX_SCRIPTS_PATH': JUPYTERLAB_AUX_SCRIPTS_PATH,  # admin startup scripts path
    'JUPYTERLAB_AUX_MENU_PATH': JUPYTERLAB_AUX_MENU_PATH,      # admin-managed custom menu definitions
}

# GPU device passthrough - expose all GPUs to spawned containers
if gpu_enabled == 1:
    c.DockerSpawner.extra_host_config = {
        'device_requests': [
            {'Driver': 'nvidia', 'Count': -1, 'Capabilities': [['gpu']]}
        ]
    }

c.DockerSpawner.image = JUPYTERHUB_NOTEBOOK_IMAGE           # JupyterLab Docker image to spawn
c.DockerSpawner.use_internal_ip = True                       # use container IP on Docker network (not host)
c.DockerSpawner.network_name = JUPYTERHUB_NETWORK_NAME       # Docker network connecting hub and user containers
c.JupyterHub.default_url = JUPYTERHUB_BASE_URL_PREFIX + '/hub/home'  # redirect after login
# c.DockerSpawner.notebook_dir = DOCKER_NOTEBOOK_DIR         # redundant - stellars-jupyterlab-ds image defaults to /home/lab/workspace
c.DockerSpawner.name_template = "jupyterlab-{username}"      # container name pattern (used in volume names too)
c.DockerSpawner.volumes = DOCKER_SPAWNER_VOLUMES             # per-user persistent volumes + shared storage

# ── Branding: logo ──
# Set custom logo file if resolved from file:// URI
if branding['logo_file']:
    c.JupyterHub.logo_file = branding['logo_file']

# ── Template variables ──
# Passed to Jinja2 templates for UI rendering
c.JupyterHub.template_vars = {
    'user_volume_suffixes': user_volume_suffixes,            # ['home', 'workspace', 'cache'] for volume reset UI
    'volume_descriptions': VOLUME_DESCRIPTIONS,              # human-readable volume labels
    'stellars_version': os.environ.get('STELLARS_JUPYTERHUB_VERSION', 'dev'),  # platform version shown in UI
    'server_version': jupyterhub.__version__,                # JupyterHub version shown in UI
    'idle_culler_enabled': JUPYTERHUB_IDLE_CULLER_ENABLED,   # toggle culler UI elements
    'idle_culler_timeout': JUPYTERHUB_IDLE_CULLER_TIMEOUT,   # timeout display in session panel
    'idle_culler_max_extension': JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION,  # max extension hours display
    'activitymon_target_hours': ACTIVITYMON_TARGET_HOURS,    # activity scoring window display
    'activitymon_sample_interval': ACTIVITYMON_SAMPLE_INTERVAL,  # sampling interval display
    'favicon_uri': branding['favicon_uri'],                  # external favicon URL (empty = static_url default)
}

# ── Tornado settings ──
# Handler-accessible config via self.settings['stellars_config']
# Replaces os.environ.get() calls in handlers with explicit typed values
c.JupyterHub.tornado_settings = {
    'stellars_config': {
        'user_volume_suffixes': user_volume_suffixes,        # for ManageVolumesHandler validation
        'idle_culler_enabled': JUPYTERHUB_IDLE_CULLER_ENABLED,  # for SessionInfoHandler, ActivityDataHandler
        'idle_culler_timeout': JUPYTERHUB_IDLE_CULLER_TIMEOUT,  # for SessionInfoHandler, ExtendSessionHandler
        'idle_culler_max_extension': JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION,  # for ExtendSessionHandler limits
    }
}

# ── Pre-spawn hook ──
# Factory returns async closure capturing branding state + group list
# Hook runs before each container spawn: enforces group permissions,
# injects CHP favicon proxy routes, resolves JupyterLab icon URLs
c.DockerSpawner.pre_spawn_hook = make_pre_spawn_hook(
    branding,                                                # icon static names and URLs from setup_branding()
    builtin_groups=BUILTIN_GROUPS,                           # groups to auto-recreate if deleted
    favicon_uri=JUPYTERHUB_FAVICON_URI,                      # non-empty activates CHP favicon routing
)

# ── Spawner args ──
# Command-line arguments passed to the spawned JupyterLab ServerApp
c.DockerSpawner.args = [
    '--ServerApp.allow_origin=*',                            # allow cross-origin requests (required behind proxy)
    '--ServerApp.disable_check_xsrf=True',                   # disable XSRF for API access from hub
]

# ── Networking ──
c.JupyterHub.hub_connect_url = 'http://jupyterhub:8080' + JUPYTERHUB_BASE_URL_PREFIX + '/hub'  # URL spawned containers use to reach hub
c.DockerSpawner.remove = True                                # auto-remove containers after stop (volumes persist)
c.DockerSpawner.debug = False                                # DockerSpawner debug logging
c.JupyterHub.hub_ip = "jupyterhub"                           # bind hub to container hostname
c.JupyterHub.hub_port = 8080                                 # internal hub port (not exposed externally)
c.JupyterHub.base_url = JUPYTERHUB_BASE_URL_PREFIX + '/' if JUPYTERHUB_BASE_URL_PREFIX else '/'  # URL prefix for all hub routes

# ── Persistence ──
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"  # cookie signing key (persisted in jupyterhub_data volume)
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"           # user database (persisted in jupyterhub_data volume)

# ── Authentication ──
c.JupyterHub.authenticator_class = StellarsNativeAuthenticator       # NativeAuthenticator with admin rename sync
c.JupyterHub.template_paths = [
    "/srv/jupyterhub/templates/",                                    # custom Stellars templates (override priority)
    f"{os.path.dirname(nativeauthenticator.__file__)}/templates/",   # NativeAuthenticator signup/authorize templates
    f"{os.path.dirname(jupyterhub.__file__)}/templates",             # JupyterHub default templates (fallback)
]
c.NativeAuthenticator.open_signup = False                            # require admin authorization for new users
c.NativeAuthenticator.enable_signup = bool(JUPYTERHUB_SIGNUP_ENABLED)  # self-registration form (0=admin creates users)
c.Authenticator.allow_all = True                                     # all authorized users may login
c.Authenticator.admin_users = [JUPYTERHUB_ADMIN]                     # admin username list
c.JupyterHub.admin_access = True                                     # admins can access user servers

# ── Extra handlers ──
# Custom API endpoints and admin pages (routes are relative to /hub/)
c.JupyterHub.extra_handlers = [
    (r'/api/users/([^/]+)/manage-volumes', ManageVolumesHandler),    # DELETE - reset user volumes
    (r'/api/users/([^/]+)/restart-server', RestartServerHandler),    # POST - Docker container restart
    (r'/api/users/([^/]+)/session-info', SessionInfoHandler),        # GET - idle culler status
    (r'/api/users/([^/]+)/extend-session', ExtendSessionHandler),    # POST - extend idle timeout
    (r'/api/notifications/active-servers', ActiveServersHandler),     # GET - list running servers
    (r'/api/notifications/broadcast', BroadcastNotificationHandler), # POST - broadcast to all servers
    (r'/api/admin/credentials', GetUserCredentialsHandler),          # GET - cached auto-generated passwords
    (r'/api/activity', ActivityDataHandler),                          # GET - activity data + Docker stats
    (r'/api/activity/reset', ActivityResetHandler),                   # POST - clear activity samples
    (r'/api/activity/sample', ActivitySampleHandler),                 # POST - trigger manual sampling
    (r'/notifications', NotificationsPageHandler),                    # GET - admin broadcast UI page
    (r'/settings', SettingsPageHandler),                              # GET - platform settings page
    (r'/activity', ActivityPageHandler),                              # GET - activity monitoring page
]


# ── Section 5: Services & Startup Callbacks ──────────────────────────────────
# JupyterHub managed services (background processes) and one-time startup hooks.

# Build service definitions: activity sampler (always), idle culler (conditional)
services, roles = get_services_and_roles(
    culler_enabled=JUPYTERHUB_IDLE_CULLER_ENABLED,           # 0=off, 1=on
    culler_timeout=JUPYTERHUB_IDLE_CULLER_TIMEOUT,           # seconds before cull
    culler_interval=JUPYTERHUB_IDLE_CULLER_INTERVAL,         # seconds between checks
    culler_max_age=JUPYTERHUB_IDLE_CULLER_MAX_AGE,           # max server lifetime (0=unlimited)
    sample_interval=ACTIVITYMON_SAMPLE_INTERVAL,             # activity sampling interval
)
c.JupyterHub.services = services                             # register managed services
c.JupyterHub.load_roles = roles                              # service API token scopes

# Register CHP favicon proxy routes for servers that survived a hub restart
# (pre_spawn_hook only fires on new spawns, this catches already-running servers)
schedule_startup_favicon_callback(favicon_uri=JUPYTERHUB_FAVICON_URI)

# EOF
