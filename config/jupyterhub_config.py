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
    BootstrapAdminAuthenticator,            # NativeAuth subclass with bootstrap-window admin signup
    StellarsNativeAuthenticator,            # parent class for the inline BootstrapAdminAuthenticator (refactor in progress)
    compute_bootstrap_window_open,          # truth-table predicate for the bootstrap-by-signup window
    get_services_and_roles,                 # builds JupyterHub services list (activity sampler, idle culler)
    get_user_volume_suffixes,               # extracts ['home', 'workspace', 'cache'] from volumes dict
    make_admin_post_auth_hook,              # async closure that flips authentication['admin']=True for JUPYTERHUB_ADMIN
    make_pre_spawn_hook,                    # factory returning async hook for group perms, favicon, icons
    provision_admin_userinfo,               # bootstrap-by-env: seed admin UserInfo from JUPYTERHUB_ADMIN_PASSWORD
    query_admin_state,                      # (db_empty, admin_present) inspection of users_info
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
    HealthCheckHandler,                     # GET  /health - unauthenticated monitoring endpoint
    ManageVolumesHandler,                   # DELETE /api/users/{user}/manage-volumes - delete user volumes
    NotificationsPageHandler,               # GET  /notifications - admin broadcast UI
    RestartServerHandler,                   # POST /api/users/{user}/restart-server - Docker restart
    SessionInfoHandler,                     # GET  /api/users/{user}/session-info - idle culler status
    SettingsPageHandler,                    # GET  /settings - platform settings display
    GroupsPageHandler,                      # GET  /groups - group management page
    GroupsDataHandler,                      # GET  /api/admin/groups - list groups with config
    GroupsCreateHandler,                    # POST /api/admin/groups/create - create new group
    GroupsDeleteHandler,                    # DELETE /api/admin/groups/{name}/delete - delete group
    GroupsConfigHandler,                    # GET/PUT /api/admin/groups/{name}/config - group config
    GroupsReorderHandler,                   # POST /api/admin/groups/reorder - update priorities
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

# Docker
JUPYTERHUB_DOCKER_TIMEOUT = int(os.environ.get("JUPYTERHUB_DOCKER_TIMEOUT", 360))               # Docker API timeout in seconds
JUPYTERHUB_CONTAINER_MAX_EXTRA_SPACE_GB = int(os.environ.get("JUPYTERHUB_CONTAINER_MAX_EXTRA_SPACE_GB", 10))  # max writable layer in GB before warning
JUPYTERHUB_VOLUME_MAX_TOTAL_SIZE_GB = int(os.environ.get("JUPYTERHUB_VOLUME_MAX_TOTAL_SIZE_GB", 50))        # max total volume size in GB before warning
JUPYTERHUB_MEMORY_MAX_USAGE_FRACTION = float(os.environ.get("JUPYTERHUB_MEMORY_MAX_USAGE_FRACTION", 0.25))  # per-user memory warning threshold as fraction of host RAM (default 25%)


def _resolve_memory_quota_mb(fraction):
    """Return per-user memory warning threshold in MB as a fraction of host total RAM."""
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    total_kb = int(line.split()[1])
                    return int((total_kb / 1024) * fraction)
    except Exception:
        pass
    return 4096  # fallback: 4 GB if /proc/meminfo unavailable


JUPYTERHUB_MEMORY_MAX_USAGE_MB = _resolve_memory_quota_mb(JUPYTERHUB_MEMORY_MAX_USAGE_FRACTION)

# Misc
TF_CPP_MIN_LOG_LEVEL = int(os.environ.get("TF_CPP_MIN_LOG_LEVEL", 3))                          # suppress TensorFlow logging in spawned containers
JUPYTERHUB_TIMEZONE = os.environ.get("JUPYTERHUB_TIMEZONE", "Etc/UTC")                          # IANA timezone (e.g. Europe/Warsaw), applied to hub + spawned containers

# Docker spawner settings
JUPYTERHUB_BASE_URL = os.environ.get("JUPYTERHUB_BASE_URL")                                     # URL prefix (e.g. /jupyterhub), None or / for root
JUPYTERHUB_NETWORK_NAME = os.environ.get("JUPYTERHUB_NETWORK_NAME", "jupyterhub_network")       # Docker network for hub + spawned containers
JUPYTERHUB_NOTEBOOK_IMAGE = os.environ.get("JUPYTERHUB_NOTEBOOK_IMAGE", "stellars/stellars-jupyterlab-ds:latest")  # JupyterLab image to spawn
COMPOSE_PROJECT_NAME = os.environ.get("COMPOSE_PROJECT_NAME", "jupyterhub")                    # passed through by compose - drives docker compose project label and volume namespace; defaults to "jupyterhub" when running outside compose
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
JUPYTERLAB_SYSTEM_NAME = os.environ.get("JUPYTERLAB_SYSTEM_NAME", "")                       # rebrand stellars-jupyterlab-ds in welcome page, MOTD, toolbar header badge; empty = no rebrand
JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME = os.environ.get("JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME", "1")  # uppercase the toolbar header badge (0/1)
JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR = os.environ.get("JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR", "")            # CSS color for toolbar header badge text; empty = --jp-ui-font-color2


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
# Volumes are namespaced by the compose project so distinct deployments do not
# collide on per-user data. Container names stay literal (jupyterlab-{username})
# - the compose project label provides the grouping in `docker compose ls`.
# <project>_shared is read-write shared storage (can be CIFS via override).
DOCKER_SPAWNER_VOLUMES = {
    f"{COMPOSE_PROJECT_NAME}_jupyterlab_{{username}}_home": "/home",
    f"{COMPOSE_PROJECT_NAME}_jupyterlab_{{username}}_workspace": DOCKER_NOTEBOOK_DIR,
    f"{COMPOSE_PROJECT_NAME}_jupyterlab_{{username}}_cache": "/home/lab/.cache",
    f"{COMPOSE_PROJECT_NAME}_shared": "/mnt/shared",
}

# Human-readable descriptions shown in the volume reset UI
VOLUME_DESCRIPTIONS = {
    'home': 'User home directory files, configurations',
    'workspace': 'Project files, notebooks, code',
    'cache': 'Temporary files, pip cache, conda cache',
}

# Derived: extract user-resettable volume suffixes ['home', 'workspace', 'cache'] from volumes dict
user_volume_suffixes = get_user_volume_suffixes(DOCKER_SPAWNER_VOLUMES, COMPOSE_PROJECT_NAME)


# ── Section 3: Logic Calls ───────────────────────────────────────────────────
# Functions with side effects: event listeners, Docker commands, file copies.

# Attach SQLAlchemy event listeners for user rename/delete sync (activity data, NativeAuthenticator)
register_events()


# ── Admin bootstrap ──────────────────────────────────────────────────────────
# Two operating modes share this code:
#
#   1. Bootstrap-by-signup (default): operator sets only JUPYTERHUB_ADMIN. On a
#      fresh deployment the signup form is silently re-opened just for the admin
#      name (BootstrapAdminAuthenticator below rejects every other username with a
#      clear message). The admin signs up with their own password and our
#      create_user override flips is_authorized=True directly on the new UserInfo
#      row (no email, no SMTP, no approval URL). They log in, the post auth hook
#      promotes them to admin role. Once their UserInfo is in the DB the
#      bootstrap window closes and signup falls back to the operator's setting.
#
#   2. Bootstrap-by-env: operator also sets JUPYTERHUB_ADMIN_PASSWORD. The hub
#      pre-creates the admin UserInfo with that password on startup. The env value
#      is INITIAL ONLY: bcrypt.checkpw determines whether the stored hash was
#      generated from the env value; the moment the admin changes their password
#      verification fails and env is permanently ignored. JUPYTERHUB_ADMIN_PASSWORD
#      is intentionally absent from settings_dictionary.yml and so is not exposed
#      on the Settings page.
#
# c.Authenticator.admin_users is intentionally NOT set: setting it makes JupyterHub
# eagerly insert a User row at startup, which fires stellars_hub.events' after_insert
# listener and creates a UserInfo with a random xkcd password the operator cannot
# retrieve. Admin role is granted purely at login time via post_auth_hook below.

JUPYTERHUB_ADMIN_PASSWORD = os.environ.get("JUPYTERHUB_ADMIN_PASSWORD", "").strip()

_DB_PATH = '/data/jupyterhub.sqlite'


def _query_admin_state(admin_username, db_path=_DB_PATH):
    """Return (db_empty, admin_present) at startup.

    db_empty is True iff users_info has zero rows (or doesn't exist yet).
    admin_present is True iff a UserInfo row for admin_username exists.
    First-ever boot (no DB file) reports (True, False) so the bootstrap window opens.
    """
    import sqlite3
    if not admin_username or not os.path.exists(db_path):
        return True, False
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users_info'")
        if not cur.fetchone():
            return True, False
        cur.execute("SELECT COUNT(*) FROM users_info")
        empty = cur.fetchone()[0] == 0
        cur.execute("SELECT 1 FROM users_info WHERE username = ?", (admin_username,))
        present = cur.fetchone() is not None
        return empty, present
    finally:
        conn.close()


def _provision_admin_userinfo(admin_username, admin_password, db_path=_DB_PATH):
    """Bootstrap-by-env: seed admin UserInfo from JUPYTERHUB_ADMIN_PASSWORD.

    Initial-only semantics:
      - missing UserInfo                        -> INSERT bcrypt(env), is_authorized=1
      - exists, env still verifies against hash -> no-op (already initial)
      - exists, env does NOT verify             -> leave alone (admin has changed it)
    """
    import sqlite3
    import bcrypt
    if not admin_username or not admin_password or not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users_info'")
        if not cur.fetchone():
            return
        cur.execute("SELECT password FROM users_info WHERE username = ?", (admin_username,))
        row = cur.fetchone()
        if row is None:
            hashed = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
            cur.execute(
                "INSERT INTO users_info (username, password, is_authorized) VALUES (?, ?, 1)",
                (admin_username, hashed),
            )
            conn.commit()
            print(f"[Admin Bootstrap] Provisioned '{admin_username}' from JUPYTERHUB_ADMIN_PASSWORD", flush=True)
            return
        stored = row[0].encode('utf-8') if isinstance(row[0], str) else row[0]
        try:
            still_initial = bcrypt.checkpw(admin_password.encode('utf-8'), stored)
        except Exception:
            still_initial = False
        if not still_initial:
            print(f"[Admin Bootstrap] '{admin_username}' has changed their password; JUPYTERHUB_ADMIN_PASSWORD ignored", flush=True)
    finally:
        conn.close()


_DB_EMPTY_AT_STARTUP, _ADMIN_PRESENT_AT_STARTUP = _query_admin_state(JUPYTERHUB_ADMIN)
_ADMIN_PROVISIONING_REQUESTED = bool(JUPYTERHUB_ADMIN and JUPYTERHUB_ADMIN_PASSWORD)

# Bootstrap window: signup off, no env password, no users yet, no admin yet.
# In this exact state the upstream silently re-opens signup, scoped to the admin name.
_BOOTSTRAP_WINDOW_OPEN = (
    JUPYTERHUB_SIGNUP_ENABLED == 0
    and not _ADMIN_PROVISIONING_REQUESTED
    and _DB_EMPTY_AT_STARTUP
    and not _ADMIN_PRESENT_AT_STARTUP
)

if _ADMIN_PROVISIONING_REQUESTED:
    _provision_admin_userinfo(JUPYTERHUB_ADMIN, JUPYTERHUB_ADMIN_PASSWORD)


from nativeauthenticator.handlers import SignUpHandler as _NativeSignUpHandler


class BootstrapAdminSignUpHandler(_NativeSignUpHandler):
    """Replace NativeAuth's misleading post-signup messages during the bootstrap window.

    Two upstream branches need correcting:

      * Success branch keys off `username in admin_users`, which we deliberately
        leave empty (populating admin_users triggers the eager User insert and
        the random-password trap in stellars_hub.events). With our create_user
        override flagging is_authorized=True, the row is correct but the message
        still drops to "Your information has been sent to the admin." Treat
        is_authorized as the success signal here.

      * Generic error branch on `not user` shows "Be sure your username does
        not contain spaces, commas or slashes..." which is misleading when the
        real reason create_user returned None is our bootstrap-window
        validate_username block. Substitute a clearer message in that case.
    """

    def get_result_message(self, user, assume_user_is_human, username_already_taken,
                           confirmation_matches, user_is_admin):
        if user is not None and getattr(user, 'is_authorized', False):
            user_is_admin = True
        alert, message = super().get_result_message(
            user, assume_user_is_human, username_already_taken,
            confirmation_matches, user_is_admin,
        )
        if (
            user is None
            and self.authenticator._bootstrap_admin_pending()
            and assume_user_is_human
            and not username_already_taken
            and confirmation_matches
        ):
            submitted = self.get_body_argument("username", "", strip=False)
            if submitted and submitted != JUPYTERHUB_ADMIN:
                alert = "alert-warning"
                message = (
                    "Only the admin user can sign up during the initial "
                    "bootstrap window."
                )
        return alert, message


class BootstrapAdminAuthenticator(StellarsNativeAuthenticator):
    """During the bootstrap window, only the admin username is allowed to self-sign-up
    and that signup is auto-authorised on the spot.

    Outside the bootstrap window this class is a transparent passthrough to
    StellarsNativeAuthenticator. The window state is captured once at startup so the
    class behaves stably for the lifetime of the hub process.

    For auto-authorisation we override create_user instead of using NativeAuth's
    allow_self_approval_for: that path forces ask_email_on_signup=True, matches the
    regex against the email field (not the username), generates a signed approval URL
    and tries to send it via SMTP - which the hub container has no server for, so the
    admin signup ends up pending without any way to confirm it. Combined with the
    BootstrapAdminSignUpHandler injected via get_handlers below, the admin signup
    completes with a clean success message and any non-admin attempt during the
    window gets a clear "only admin can sign up" rejection instead of NativeAuth's
    generic spaces/commas/password message.
    """

    def _bootstrap_admin_pending(self):
        """The bootstrap window only takes effect while it was open at startup
        AND the admin row has not yet been inserted in the DB. Checked at
        request time so admin user creation works as soon as the admin signs up
        (rather than requiring a hub restart to recapture the flag).
        """
        if not _BOOTSTRAP_WINDOW_OPEN or not JUPYTERHUB_ADMIN:
            return False
        return self.get_user(JUPYTERHUB_ADMIN) is None

    @property
    def enable_signup(self):
        """Dynamic so the Sign Up link and /hub/signup form disappear the moment
        the bootstrap admin row appears, even though the hub process started
        with the window open. Operator's JUPYTERHUB_SIGNUP_ENABLED still wins
        if it is True. Overrides the inherited Bool trait with a property; the
        no-op setter keeps traitlets' config assignment (`c.NativeAuthenticator.
        enable_signup = ...`) from raising.
        """
        if JUPYTERHUB_SIGNUP_ENABLED:
            return True
        return self._bootstrap_admin_pending()

    @enable_signup.setter
    def enable_signup(self, value):
        # Computed dynamically; ignore static assignments from config.
        pass

    def validate_username(self, username):
        if not super().validate_username(username):
            return False
        if self._bootstrap_admin_pending() and username and username != JUPYTERHUB_ADMIN:
            return False
        return True

    def get_handlers(self, app):
        return [
            (path, BootstrapAdminSignUpHandler if path == r"/signup" else handler)
            for path, handler in super().get_handlers(app)
        ]

    def create_user(self, username, password, **kwargs):
        pending = self._bootstrap_admin_pending()
        user_info = super().create_user(username, password, **kwargs)
        if (
            user_info is not None
            and pending
            and self.normalize_username(username) == self.normalize_username(JUPYTERHUB_ADMIN)
        ):
            user_info.is_authorized = True
            self.db.commit()
        return user_info


async def _admin_post_auth_hook(authenticator, handler, authentication):
    """Promote JUPYTERHUB_ADMIN to admin role on every successful authentication."""
    if authentication and authentication.get('name') == JUPYTERHUB_ADMIN:
        authentication['admin'] = True
    return authentication

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
    'NVIDIA_DETECTED': nvidia_detected,                      # GPU hardware availability flag (informational)
    'JUPYTERLAB_AUX_SCRIPTS_PATH': JUPYTERLAB_AUX_SCRIPTS_PATH,  # admin startup scripts path
    'JUPYTERLAB_AUX_MENU_PATH': JUPYTERLAB_AUX_MENU_PATH,      # admin-managed custom menu definitions
    'JUPYTERLAB_TIMEZONE': JUPYTERHUB_TIMEZONE,                  # IANA timezone for JupyterLab extensions
    'JUPYTERLAB_SYSTEM_NAME': JUPYTERLAB_SYSTEM_NAME,                                    # rebrand stellars-jupyterlab-ds in welcome page, MOTD, toolbar header badge
    'JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME': JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME, # uppercase toolbar header badge (0/1)
    'JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR': JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR,           # CSS color for toolbar header badge text
    'JUPYTERHUB_NETWORK_NAME': JUPYTERHUB_NETWORK_NAME,                                   # Docker network connecting hub + user containers; needed by in-container scripts that attach sidecars to the same net
}

# Reserved env var names groups cannot override - every key we inject globally
# plus ENABLE_GPU_SUPPORT/ENABLE_GPUSTAT which the pre-spawn hook sets per-user.
RESERVED_ENV_VAR_PREFIXES = ('JUPYTERHUB_', 'JPY_', 'MEM_', 'CPU_')
RESERVED_ENV_VAR_NAMES = set(c.DockerSpawner.environment.keys()) | {
    'ENABLE_GPU_SUPPORT', 'ENABLE_GPUSTAT',
}

# GPU device_requests is set per-user by the pre-spawn hook based on resolved
# group config. Left empty here so a user who is not in a GPU-enabled group
# does not receive the device.

c.DockerSpawner.image = JUPYTERHUB_NOTEBOOK_IMAGE           # JupyterLab Docker image to spawn
c.DockerSpawner.use_internal_ip = True                       # use container IP on Docker network (not host)
c.DockerSpawner.network_name = JUPYTERHUB_NETWORK_NAME       # Docker network connecting hub and user containers
c.JupyterHub.default_url = JUPYTERHUB_BASE_URL_PREFIX + '/hub/home'  # redirect after login
# c.DockerSpawner.notebook_dir = DOCKER_NOTEBOOK_DIR         # redundant - stellars-jupyterlab-ds image defaults to /home/lab/workspace
c.DockerSpawner.name_template = "jupyterlab-{username}"  # literal - compose project label (set in pre_spawn_hook) provides the grouping namespace
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
    'container_max_extra_space_mb': JUPYTERHUB_CONTAINER_MAX_EXTRA_SPACE_GB * 1024,  # threshold in MB for container size warning
    'volume_max_total_size_mb': JUPYTERHUB_VOLUME_MAX_TOTAL_SIZE_GB * 1024,        # threshold in MB for volume size warning
    'memory_max_usage_mb': JUPYTERHUB_MEMORY_MAX_USAGE_MB,                         # threshold in MB for per-user memory warning (0 GB -> 30% of host RAM)
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
        'container_max_extra_space_mb': JUPYTERHUB_CONTAINER_MAX_EXTRA_SPACE_GB * 1024,  # threshold in MB for container size warning
        'volume_max_total_size_mb': JUPYTERHUB_VOLUME_MAX_TOTAL_SIZE_GB * 1024,        # threshold in MB for volume size warning
        'memory_max_usage_mb': JUPYTERHUB_MEMORY_MAX_USAGE_MB,                         # threshold in MB for per-user memory warning
        'reserved_env_var_names': RESERVED_ENV_VAR_NAMES,                              # names groups cannot override
        'reserved_env_var_prefixes': RESERVED_ENV_VAR_PREFIXES,                        # prefixes reserved for JupyterHub/platform
    }
}

# ── Pre-spawn hook ──
# Factory returns async closure capturing branding + group resolution state.
# Hook runs before each container spawn: resolves all user's groups into one
# effective config (docker/gpu/env vars), applies it to spawner, then injects
# CHP favicon proxy routes and JupyterLab icon URLs.
c.DockerSpawner.pre_spawn_hook = make_pre_spawn_hook(
    branding,                                                # icon static names and URLs from setup_branding()
    favicon_uri=JUPYTERHUB_FAVICON_URI,                      # non-empty activates CHP favicon routing
    gpu_available=bool(gpu_enabled),                         # hardware present - required for per-group GPU grant
    reserved_env_var_names=RESERVED_ENV_VAR_NAMES,           # names groups cannot override
    reserved_env_var_prefixes=RESERVED_ENV_VAR_PREFIXES,     # prefixes reserved for JupyterHub/platform
    compose_project=COMPOSE_PROJECT_NAME,                    # docker compose project label so user containers group with the hub in `docker compose ls`
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
c.JupyterHub.authenticator_class = BootstrapAdminAuthenticator       # bootstrap-window admin-only signup + admin rename sync
c.JupyterHub.template_paths = [
    "/srv/jupyterhub/templates/",                                    # custom Stellars templates (override priority)
    f"{os.path.dirname(nativeauthenticator.__file__)}/templates/",   # NativeAuthenticator signup/authorize templates
    f"{os.path.dirname(jupyterhub.__file__)}/templates",             # JupyterHub default templates (fallback)
]
c.NativeAuthenticator.open_signup = False                            # other users still require admin authorization
# enable_signup is a dynamic Python property on BootstrapAdminAuthenticator that
# re-evaluates JUPYTERHUB_SIGNUP_ENABLED + the bootstrap-pending state on every
# access, so the Sign Up link and /hub/signup form disappear the moment the
# admin row appears in the DB - no static `c.NativeAuthenticator.enable_signup`
# assignment here, that would be frozen at config-load time.
# Bootstrap admin auto-authorisation is implemented inside BootstrapAdminAuthenticator.create_user.
# We deliberately do NOT use NativeAuthenticator.allow_self_approval_for: it forces
# ask_email_on_signup=True, matches the regex against the email field rather than the
# username, generates a signed approval URL, and tries to dispatch it via SMTP - none
# of which fits a hub container without an MTA.
c.Authenticator.allow_all = True                                     # all authorized users may login
c.Authenticator.post_auth_hook = _admin_post_auth_hook               # grant admin role at login (replaces the old eager admin_users that auto-created the User and triggered the random-password trap)
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
    (r'/api/admin/groups', GroupsDataHandler),                        # GET - list groups with config
    (r'/api/admin/groups/create', GroupsCreateHandler),               # POST - create new group
    (r'/api/admin/groups/reorder', GroupsReorderHandler),             # POST - update group priorities
    (r'/api/admin/groups/([^/]+)/delete', GroupsDeleteHandler),       # DELETE - delete group
    (r'/api/admin/groups/([^/]+)/config', GroupsConfigHandler),       # GET/PUT - group configuration
    (r'/notifications', NotificationsPageHandler),                    # GET - admin broadcast UI page
    (r'/settings', SettingsPageHandler),                              # GET - platform settings page
    (r'/activity', ActivityPageHandler),                              # GET - activity monitoring page
    (r'/groups', GroupsPageHandler),                                  # GET - group management page
    (r'/health', HealthCheckHandler),                                 # GET - unauthenticated monitoring endpoint
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
