# Configuration file for JupyterHub
#
# All data (env vars, volumes, groups) is defined here. The duoptimum_hub_services
# package provides pure logic functions only - zero hardcoded data, zero
# env var reads at module level. Every parameter is passed explicitly.
#
# Sections:
#   1. Environment Variables   - all os.environ.get() calls with typed defaults
#   2. Data Literals           - volumes, groups, paths, derived values
#   3. Logic Calls             - event registration, GPU detection, branding
#   4. JupyterHub Config       - all c.* settings (SSL, spawner, auth, handlers)
#   5. Services & Callbacks    - background services, startup hooks

from duoptimum_hub_services.logging_setup import log  # platform loguru sink for our own log lines
import os                       # env var reads
import socket                   # boot-time resolvability check on the hub's stable network alias

import jupyterhub               # __version__, __file__ for template paths
import nativeauthenticator      # __file__ for template path resolution

# duoptimum_hub_services core functions - pure logic, no side effects on import
from duoptimum_hub_services import (
    DuoptimumHubAuthenticator,                # platform authenticator: NativeAuth logic + antd login/signup presentation
    DuoptimumSignUpHandler,                   # antd-rendering signup handler (base for the bootstrap signup handler)
    apply_abuse_protection,                 # abuse protection: maps env -> spawn/active caps + login lockout onto c.*
    validate_hub_config,                    # central required/consistency validator: conf gathers raw values, this raises on missing/inconsistent + warns on degraded
    configure_gpu_cache,                    # one-time init: sets the CUDA image the background GPU-utilisation sampler uses
    configure_volume_cache,                 # one-time init: feeds canonical volume-name templates to the activity-monitor sizes cache
    ensure_gpuinfo_sidecar,                 # hub self-starts the gpuinfo-nvidia sidecar (so detection never waits on compose) and returns its runtime-resolved URL
    stop_gpuinfo_sidecar,                   # hub removes the sidecar on shutdown so it never outlives its parent (recreated fresh next boot)
    get_services_and_roles,                 # builds JupyterHub services list (activity sampler)
    schedule_idle_culler,                   # in-hub idle culler (honours per-user session extensions)
    get_user_volume_name_templates,         # maps suffix -> full volume-name template (with {username} placeholder)
    get_user_volume_roles,                  # maps suffix -> hub.volume.role value (lab-home/lab-workspace/lab-cache)
    get_user_volume_suffixes,               # extracts ['home', 'workspace', 'cache'] from volumes dict
    gpu_summary_lines,                      # readable per-GPU capabilities + health snapshot for the startup log
    is_wsl2,                                # host is WSL2 -> per-GPU isolation not enforceable (advisory)
    load_merged_user_volumes,               # loads + merges platform-defaults YAML with operator overrides
    make_pre_spawn_hook,                    # factory returning async hook for group perms, favicon, icons
    make_post_stop_hook,                    # factory returning async post-stop hook: docker-proxy unregister + api-key release + stop event
    prepare_sent_notification_log,          # boot-time self-heal of the sent-notification history table
    register_events,                        # attaches SQLAlchemy listeners for user rename/delete sync
    resolve_gpu_mode,                       # GPU detection: 0=off, otherwise autodetect (default)
    resolve_memory_quota_mb,                # calc: per-user memory warning threshold MB from host-RAM fraction
    schedule_startup_hydration,             # consolidated startup hydration: warms caches + image-update check + survivor favicon routes/policy, all deferred to the IOLoop
    setup_branding,                         # processes logo/favicon/icon URIs, copies file:// to static dir
)

from duoptimum_hub_services.docker_utils import resolve_self_mount_volume_by_label  # exact volume discovery by hub.volume.role among hub's own mounts (rename-safe; raises on duplicate role)
from duoptimum_hub_services.docker_utils import resolve_self_compose_project  # runtime discovery of the hub's own compose project from its own container label (no env needed)
from duoptimum_hub_services.docker_utils import volume_labels  # read a named volume's labels (injected into build_system_volume_rows)
from duoptimum_hub_services.docker_utils import build_system_volume_rows  # pure builder: Lab Setup system-volume rows (shared + docker-proxy)
from duoptimum_hub_services.policy.base import SHARED_MOUNTPOINT  # lab-side shared mount (/mnt/shared)
from duoptimum_hub_services.docker_proxy import SOCK_MOUNT_DIR  # lab-side docker-proxy socket mount (/run/dockersock)
from duoptimum_hub_services.docker_utils import (  # net discovery by role label + {network} token resolve; no net-name env
    resolve_self_network_by_label,
    resolve_network_placeholder,
)
from duoptimum_hub_services.admin_bootstrap import (  # first-admin bootstrap data/decision layer
    query_admin_state,                  # raw sqlite3 at config-load (ORM not up yet)
    bootstrap_window_open,              # pure policy: is the signup-off bootstrap window open
    admin_unreachable,                 # pure policy: no path to a first admin -> fail fast
    provision_admin_userinfo,           # ORM at authenticator-init (env-password path)
    first_admin_self_signup_pending,    # ORM at request-time (auto-authorise the first admin's self-signup)
)

# Tornado request handlers - registered via c.DuoptimumHub.registered_handlers
# (our non-deprecated replacement for JupyterHub.extra_handlers; see app.py)
from duoptimum_hub_services.handlers import (
    ActivityDataHandler,                    # GET  /api/activity - user activity data with Docker stats
    ActivityResetHandler,                   # POST /api/activity/reset - clear all activity samples
    ActivitySampleHandler,                  # POST /api/activity/sample - trigger manual activity sampling
    ActiveServersHandler,                   # GET  /api/notifications/active-servers - list running servers
    BroadcastNotificationHandler,           # POST /api/notifications/broadcast - send to all active servers
    ExtendSessionHandler,                   # POST /api/users/{user}/extend-session - add idle culler hours
    GetUserCredentialsHandler,              # GET  /api/admin/credentials - retrieve cached passwords
    HealthCheckHandler,                     # GET  /health - unauthenticated monitoring endpoint
    LabReadyHandler,                        # GET  /api/users/{user}/lab-ready - silent lab readiness probe
    ManageVolumesHandler,                   # DELETE /api/users/{user}/manage-volumes - delete user volumes
    NativeUsersHandler,                     # GET  /api/native-users - list NativeAuth signups + auth state
    NativeUserAuthorizationHandler,         # POST /api/native-users/{name}/authorization - idempotent set
    RestartServerHandler,                   # POST /api/users/{user}/restart-server - Docker restart
    ServerLogsHandler,                      # GET  /api/users/{user}/server/logs - bounded container-log tail (Start page)
    SessionInfoHandler,                     # GET  /api/users/{user}/session-info - idle culler status
    SettingsDataHandler,                    # GET  /api/settings - platform settings as JSON (read-only)
    EventsDataHandler,                      # GET  /api/events - recent platform events (audit feed)
    SentNotificationsDataHandler,           # GET  /api/notifications/sent - portal "Past Notifications" history
    GroupsDataHandler,                      # GET  /api/admin/groups - list groups with config
    GroupsCreateHandler,                    # POST /api/admin/groups/create - create new group
    GroupsDeleteHandler,                    # DELETE /api/admin/groups/{name}/delete - delete group
    GroupsConfigHandler,                    # GET/PUT /api/admin/groups/{name}/config - group config
    GroupsReorderHandler,                   # POST /api/admin/groups/reorder - update priorities
    UserProfileHandler,                     # GET/PUT /api/users/{user}/profile - first/last name + email
    UserProfilesListHandler,                # GET  /api/user-profiles - all profiles (Users-list sub-names)
    UserForcePasswordChangeHandler,         # POST /api/users/{user}/force-password-change - admin set/clear the gate
    UserRenameHandler,                      # POST /api/users/{user}/rename - admin rename (records who renamed whom)
    UserDisplayPreferencesHandler,          # GET/PUT /api/users/{user}/display-preferences - per-user UI options
    EffectiveGrantsHandler,                 # GET  /api/users/{user}/effective-grants - resolved group policy grants
)

# Duoptimum Hub web portal - hub-served React SPA that replaces the stock home/admin UI.
# Ships its own static bundle + shell template; portal_handlers() returns the
# catch-all route (auto-prefixed with /hub -> the SPA serves at the hub root,
# no /portal segment); template_dir() holds the shell + home/admin redirect stubs.
import duoptimum_hub_web
from duoptimum_hub_web import portal_handlers, PORTAL_URL

c = get_config()  # noqa: F821  - JupyterHub injects get_config() into config file namespace


# ── Section 1: Environment Variables ─────────────────────────────────────────
# All env var reads in one place. Typed with int() or str defaults.
# See settings_dictionary.yml for full documentation of each variable.

# Core platform toggles (0=disabled, 1=enabled)
JUPYTERHUB_SSL_ENABLED = int(os.environ.get("JUPYTERHUB_SSL_ENABLED", 1))                      # direct SSL termination (disable when behind reverse proxy)
JUPYTERHUB_GPU_ENABLED = int(os.environ.get("JUPYTERHUB_GPU_ENABLED", 1))                      # 0=off, 1=autodetect (default); GPU on only when devices are actually detected
JUPYTERHUB_LAB_SERVICE_MLFLOW = int(os.environ.get("JUPYTERHUB_LAB_SERVICE_MLFLOW", 1))                 # MLflow tracking in spawned containers
JUPYTERHUB_LAB_SERVICE_RESOURCES_MONITOR = int(os.environ.get("JUPYTERHUB_LAB_SERVICE_RESOURCES_MONITOR", 1))  # resource monitor widget
JUPYTERHUB_LAB_SERVICE_TENSORBOARD = int(os.environ.get("JUPYTERHUB_LAB_SERVICE_TENSORBOARD", 1))       # TensorBoard in spawned containers
JUPYTERHUB_SIGNUP_ENABLED = int(os.environ.get("JUPYTERHUB_SIGNUP_ENABLED", 1))                 # user self-registration (0=admin-only)

# Idle culler - automatic server shutdown after inactivity
JUPYTERHUB_IDLE_CULLER_ENABLED = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_ENABLED", 0))       # 0=off, 1=on
JUPYTERHUB_IDLE_CULLER_TIMEOUT_MINUTES = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_TIMEOUT_MINUTES", 1440))  # minutes of inactivity before cull (24h)
JUPYTERHUB_IDLE_CULLER_INTERVAL = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_INTERVAL", 600))   # seconds between cull checks (10min)
JUPYTERHUB_IDLE_CULLER_MAX_AGE = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_MAX_AGE", 0))       # max server lifetime in seconds (0=unlimited)
JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION_MINUTES = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION_MINUTES", 1440))  # max user-requested extension in minutes (24h)

# Derived internal units: culler service + handlers consume seconds; extend UI operates in whole hours
JUPYTERHUB_IDLE_CULLER_TIMEOUT = JUPYTERHUB_IDLE_CULLER_TIMEOUT_MINUTES * 60               # seconds before cull
JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION = JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION_MINUTES // 60  # whole hours users can extend
# Activity monitor - engagement scoring via periodic sampling
ACTIVITYMON_TARGET_HOURS = int(os.environ.get('JUPYTERHUB_ACTIVITYMON_TARGET_HOURS', 8))        # scoring window in hours
ACTIVITYMON_SAMPLE_INTERVAL = int(os.environ.get('JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL', 600))  # sampling interval in seconds (10min)

# Docker
JUPYTERHUB_DOCKER_TIMEOUT = int(os.environ.get("JUPYTERHUB_DOCKER_TIMEOUT", 360))               # Docker API timeout in seconds
JUPYTERHUB_LAB_CONTAINER_MAX_EXTRA_SPACE_GB = int(os.environ.get("JUPYTERHUB_LAB_CONTAINER_MAX_EXTRA_SPACE_GB", 10))  # max writable layer in GB before warning
JUPYTERHUB_LAB_VOLUME_MAX_TOTAL_SIZE_GB = int(os.environ.get("JUPYTERHUB_LAB_VOLUME_MAX_TOTAL_SIZE_GB", 50))        # max total volume size in GB before warning
JUPYTERHUB_LAB_MEMORY_MAX_USAGE_FRACTION = float(os.environ.get("JUPYTERHUB_LAB_MEMORY_MAX_USAGE_FRACTION", 0.25))  # per-user memory warning threshold as fraction of host RAM (default 25%)


JUPYTERHUB_LAB_MEMORY_MAX_USAGE_MB = resolve_memory_quota_mb(JUPYTERHUB_LAB_MEMORY_MAX_USAGE_FRACTION)  # host-RAM fraction -> MB (calc helper in services)

# File downloads (best-effort policy). 0=allow everywhere (dormant, no routes),
# 1=block browser downloads from labs unless a user's group grants it via the
# per-group downloads_active flag. Not a security boundary - the lab has a root
# shell with egress, so this stops the download affordances and audits them, it
# does not prevent a determined terminal/kernel exfiltration.
JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS = int(os.environ.get("JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS", 0))

# Member sudo default. Injected into every spawn as JUPYTERLAB_SUDO_ENABLE
# (consumed by the lab image) when no group configures sudo via its per-group
# Sudo Access section; a configuring group overrides this per the priority rule.
JUPYTERHUB_LAB_SUDO_ENABLE = int(os.environ.get("JUPYTERHUB_LAB_SUDO_ENABLE", 1))

# Misc
TF_CPP_MIN_LOG_LEVEL = int(os.environ.get("TF_CPP_MIN_LOG_LEVEL", 3))                          # suppress TensorFlow logging in spawned containers
JUPYTERHUB_TIMEZONE = os.environ.get("JUPYTERHUB_TIMEZONE", "Etc/UTC")                          # IANA timezone (e.g. Europe/Warsaw), applied to hub + spawned containers

# Docker spawner settings
JUPYTERHUB_BASE_URL = os.environ.get("JUPYTERHUB_BASE_URL")                                     # URL prefix (e.g. /jupyterhub), None or / for root
# Net role labels. Hub finds each net by role among own attachments (hub_network + gpuinfo
# net). Key + values baked ENV (single source); empty -> validator fails. Compose stamps
# matching literals on nets (MUST match).
JUPYTERHUB_LABEL_NETWORK_ROLE_KEY = os.environ.get("JUPYTERHUB_LABEL_NETWORK_ROLE_KEY", "").strip()
JUPYTERHUB_LABEL_NETWORK_ROLE_LAB = os.environ.get("JUPYTERHUB_LABEL_NETWORK_ROLE_LAB", "").strip()
JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO = os.environ.get("JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO", "").strip()
# Hub<->lab net the labs join (MUST share with hub - labs hit hub API, CHP proxies them).
# Baked "{network}" token -> role=lab net. Empty after resolve -> validator fails.
JUPYTERHUB_NETWORK_NAME = os.environ.get("JUPYTERHUB_NETWORK_NAME", "").strip()
if "{network}" in JUPYTERHUB_NETWORK_NAME:
    JUPYTERHUB_NETWORK_NAME = resolve_network_placeholder(
        JUPYTERHUB_NETWORK_NAME,
        resolve_self_network_by_label(JUPYTERHUB_LABEL_NETWORK_ROLE_KEY, JUPYTERHUB_LABEL_NETWORK_ROLE_LAB) or "",
    ).strip()  # {network} -> hub<->lab net (role=lab)
JUPYTERHUB_LAB_IMAGE = os.environ.get("JUPYTERHUB_LAB_IMAGE", "").strip()                # JupyterLab image to spawn (baked ENV; empty -> validator fails)
# Deployment NAMESPACE (compose project now; k8s namespace later) - scope every label
# uniqueness check lives in. Drives volume namespace + hub/sidecar/lab compose labels.
# Discovered EXACT from the hub's own com.docker.compose.project label - no env, can't drift
# from the real volume prefix. Empty -> validator fails.
JUPYTERHUB_COMPOSE_PROJECT_NAME = (resolve_self_compose_project() or "").strip()
# Compose project for spawned lab/user containers - the com.docker.compose.project
# label they carry. The {compose} placeholder is filled with the discovered hub
# project (so compose.yml can say "{compose}_labs" to group labs under their own
# project without hardcoding the project name); empty = same project as the hub.
# Volume namespacing is unaffected (it stays on JUPYTERHUB_COMPOSE_PROJECT_NAME) -
# only the user-container compose label changes.
JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME = (
    os.environ.get("JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME", "").strip()
    .replace("{compose}", JUPYTERHUB_COMPOSE_PROJECT_NAME)
    or JUPYTERHUB_COMPOSE_PROJECT_NAME
)
# Lab-container name template ({username}). One source: spawner names from it,
# docker_utils.lab_container_name() finds it again - no hardcoded prefix, so a rename never
# desyncs spawn from lookup. Baked ENV (jupyterlab-{username}); validator requires it
# present + carrying {username}.
JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE = os.environ.get("JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE", "").strip()
JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME = os.environ.get("JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME", "")  # SIMPLE service name (e.g. gpuinfo-nvidia); the hub replicates compose's <project>-<service>-<number> auto-naming at instantiation (see gpuinfo_sidecar._compose_container_name), so the running container is named like a compose-managed one
JUPYTERHUB_GPUINFO_NVIDIA_URL = os.environ.get("JUPYTERHUB_GPUINFO_NVIDIA_URL", "")  # GPU-info sidecar base URL TEMPLATE; the {hostname} placeholder is filled at runtime by ensure_gpuinfo_sidecar with the address it discovers for the running sidecar - no hardcoded host
# Container role label on hub-created sidecar (mirrored on compose gpuinfo-nvidia service).
# Future code finds gpuinfo containers by role. Key + value baked ENV (MUST match compose);
# empty -> validator fails.
JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY = os.environ.get("JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY", "").strip()
JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO = os.environ.get("JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO", "").strip()
# Hub's own container role value. DOUBLES as the hub's stable network ALIAS - compose stamps
# it both as hub.container.role on the hub AND as a `hub_network` alias, so spawned labs + CHP
# reach the hub by this fixed name (see hub_connect_url) instead of the hub's ephemeral
# container id, which changes on every redeploy/watchtower update (DEF-22). Key + value baked
# ENV (MUST match compose label + alias); empty -> validator fails.
JUPYTERHUB_LABEL_CONTAINER_ROLE_HUB = os.environ.get("JUPYTERHUB_LABEL_CONTAINER_ROLE_HUB", "").strip()
# Spawned-lab container role value. pre_spawn_hook stamps hub.container.role=lab on every
# user lab so labs are discoverable by role like the hub + gpuinfo sidecar (uniform container
# management). Baked ENV (MUST match compose env); empty -> validator fails.
JUPYTERHUB_LABEL_CONTAINER_ROLE_LAB = os.environ.get("JUPYTERHUB_LABEL_CONTAINER_ROLE_LAB", "").strip()
# Volume role labels. Hub finds each named volume it mounts by role among own mounts -
# discover, not name (name drifts: jupyterhub_shared -> hub_shared bug). Key + values baked
# ENV (MUST match compose volume labels); empty -> validator fails. Duplicate role -> raises
# (per-namespace).
JUPYTERHUB_LABEL_VOLUME_ROLE_KEY = os.environ.get("JUPYTERHUB_LABEL_VOLUME_ROLE_KEY", "").strip()
JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED = os.environ.get("JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED", "").strip()
JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY = os.environ.get("JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY", "").strip()
JUPYTERHUB_LABEL_VOLUME_DESCRIPTION = os.environ.get("JUPYTERHUB_LABEL_VOLUME_DESCRIPTION", "").strip()  # label key the hub reads a volume's human description from (Lab Setup panel); empty -> no description
# Per-user volume OWNER key (value = the username) + container DESCRIPTION key. Sourced from
# env only - the stamping code (hooks.py / gpuinfo_sidecar.py) and the readers (handlers) take
# them from here, never a hardcoded literal. Key baked ENV (MUST match compose); empty -> validator fails.
JUPYTERHUB_LABEL_VOLUME_OWNER_KEY = os.environ.get("JUPYTERHUB_LABEL_VOLUME_OWNER_KEY", "").strip()
JUPYTERHUB_LABEL_CONTAINER_DESCRIPTION = os.environ.get("JUPYTERHUB_LABEL_CONTAINER_DESCRIPTION", "").strip()
# Docker-proxy ownership key/value - consumed by the in-process proxy package; read here RAW
# only so the hub validator can enforce they are provided (the proxy keeps its own env read).
JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_KEY = os.environ.get("JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_KEY", "").strip()
JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_VALUE = os.environ.get("JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_VALUE", "").strip()
# Shared volume the Groups UI offers as one-click /mnt/shared. Found by role among own mounts
# (rename-safe). Empty when absent - validator WARNS, quick-add hides (manual rows still work).
# Duplicate role -> raises.
JUPYTERHUB_SHARED_VOLUME_NAME = resolve_self_mount_volume_by_label(
    JUPYTERHUB_LABEL_VOLUME_ROLE_KEY, JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED
) or ""
# Hub<->sidecar net (compose owns it) tagged role=gpuinfo. Baked "{network}" token ->
# role=gpuinfo net. Empty = sidecar unplaceable -> GPU off (validator WARNS, sidecar degrades).
JUPYTERHUB_GPUINFO_NETWORK_NAME = os.environ.get("JUPYTERHUB_GPUINFO_NETWORK_NAME", "").strip()
if "{network}" in JUPYTERHUB_GPUINFO_NETWORK_NAME:
    JUPYTERHUB_GPUINFO_NETWORK_NAME = resolve_network_placeholder(
        JUPYTERHUB_GPUINFO_NETWORK_NAME,
        resolve_self_network_by_label(JUPYTERHUB_LABEL_NETWORK_ROLE_KEY, JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO) or "",
    ).strip()  # {network} -> hub<->sidecar net (role=gpuinfo)
JUPYTERHUB_GPUINFO_NVIDIA_IMAGE = os.environ.get("JUPYTERHUB_GPUINFO_NVIDIA_IMAGE", "").strip()  # sidecar image the hub self-starts (baked Dockerfile ENV; empty -> validate_hub_config fails)
JUPYTERHUB_ADMIN = os.environ.get("JUPYTERHUB_ADMIN", "").strip().lower()                      # admin username; .lower() - JupyterHub normalizes usernames to lowercase, bootstrap lookups/compares use this raw so it must match the DB + login form (auto-authorized on first signup; required; baked image ENV - validated by validate_hub_config)

# Branding URIs - file:// copies to static dir, http(s):// passed to templates, empty = stock assets
JUPYTERHUB_BRANDING_LOGO_URI = os.environ.get("JUPYTERHUB_BRANDING_LOGO_URI", "")                          # hub logo (login page, nav bar)
JUPYTERHUB_BRANDING_FAVICON_URI = os.environ.get("JUPYTERHUB_BRANDING_FAVICON_URI", "")                    # browser tab icon (hub + JupyterLab via CHP route)
JUPYTERHUB_BRANDING_FAVICON_BUSY_URI = os.environ.get("JUPYTERHUB_BRANDING_FAVICON_BUSY_URI", "")          # kernel-busy tab icon for JupyterLab; empty = JupyterLab default busy frames
JUPYTERHUB_BRANDING_LAB_MAIN_ICON_URI = os.environ.get("JUPYTERHUB_BRANDING_LAB_MAIN_ICON_URI", "")        # JupyterLab main area icon
JUPYTERHUB_BRANDING_LAB_SPLASH_ICON_URI = os.environ.get("JUPYTERHUB_BRANDING_LAB_SPLASH_ICON_URI", "")    # JupyterLab splash screen icon
JUPYTERHUB_BRANDING_STAGE = os.environ.get("JUPYTERHUB_BRANDING_STAGE", "")                                # environment-stage header badge (DEV/STG/TST/PRD or custom); empty = no badge
JUPYTERHUB_BRANDING_HUB_NAME = os.environ.get("JUPYTERHUB_BRANDING_HUB_NAME", "DuOptimum Hub")             # hub display name: portal logo tooltip + login/signup screen text; default baked in Dockerfile

# User environment customization - paths passed through to spawned containers
JUPYTERLAB_AUX_SCRIPTS_PATH = os.environ.get("JUPYTERLAB_AUX_SCRIPTS_PATH", "")             # admin startup scripts executed on container launch
JUPYTERLAB_AUX_MENU_PATH = os.environ.get("JUPYTERLAB_AUX_MENU_PATH", "")                   # admin-managed custom menu definitions for JupyterLab
JUPYTERHUB_BRANDING_LAB_NAME = os.environ.get("JUPYTERHUB_BRANDING_LAB_NAME", "")           # lab display name; injected into each lab as JUPYTERLAB_SYSTEM_NAME (header/welcome/MOTD); empty = no rebrand


# Required-config validation runs once below (validate_hub_config call), after the
# docker-proxy socket dir/volume resolve - all vars gathered, one pass, one SystemExit.


# ── Section 2: Data Literals ─────────────────────────────────────────────────
# Static data that does not come from environment variables.

# Default working directory inside spawned containers (also used as workspace volume mount point)
DOCKER_NOTEBOOK_DIR = "/home/lab/workspace"

# Normalize base URL prefix - empty string for root path to avoid double slashes (e.g. //hub/home)
if JUPYTERHUB_BASE_URL in ['/', '', None]:
    JUPYTERHUB_BASE_URL_PREFIX = ''
else:
    JUPYTERHUB_BASE_URL_PREFIX = JUPYTERHUB_BASE_URL

# Per-user Docker volumes - master config keyed by volume-name pattern, each
# entry carrying the mount point and the human-readable description shown in
# the volume reset UI. Same pattern as the env-variable dictionary so all
# volume metadata lives in one place. Volumes are namespaced by the compose
# project so distinct deployments do not collide on per-user data. Container
# names follow JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE (default jupyterlab-{username});
# the compose project label provides the grouping in `docker compose ls`.
#
# Loaded from:
#   /srv/jupyterhub/volumes_dictionary.yml          - platform defaults (image-baked)
#   $JUPYTERHUB_USER_VOLUMES_DESCRIPTIONS_FILE (if set + exists) - operator overrides
# Per-suffix, per-field merge: operator wins on conflict, missing fields fall
# back to the platform default, operator-only suffixes are added verbatim.
VOLUMES_DICTIONARY_PATH = '/srv/jupyterhub/volumes_dictionary.yml'
JUPYTERHUB_USER_VOLUMES_DESCRIPTIONS_FILE = os.environ.get('JUPYTERHUB_USER_VOLUMES_DESCRIPTIONS_FILE', '')
USER_VOLUMES = load_merged_user_volumes(
    VOLUMES_DICTIONARY_PATH,
    JUPYTERHUB_USER_VOLUMES_DESCRIPTIONS_FILE,
    JUPYTERHUB_COMPOSE_PROJECT_NAME,
)

# DockerSpawner needs the flat {name: mount} shape. Built from USER_VOLUMES only.
# The shared volume (role hub.volume.role=shared) is NO LONGER
# auto-mounted into every container - it is granted per group via the Volume
# Mounts section of the Groups admin page (applied in pre_spawn_hook).
DOCKER_SPAWNER_VOLUMES = {
    pattern: data['mount'] for pattern, data in USER_VOLUMES.items()
}

# Derived: extract user-resettable volume suffixes ['home', 'workspace', 'cache'] from volumes dict
user_volume_suffixes = get_user_volume_suffixes(DOCKER_SPAWNER_VOLUMES, JUPYTERHUB_COMPOSE_PROJECT_NAME)
# Derived: per-suffix volume-name template (still has {username} placeholder).
# Single source of truth for what the volumes are actually called on disk -
# UI labels, deletion handler, DockerSpawner, and the activity-monitor sizes
# cache all read from this map.
user_volume_name_templates = get_user_volume_name_templates(DOCKER_SPAWNER_VOLUMES, JUPYTERHUB_COMPOSE_PROJECT_NAME)
# Derived: suffix -> hub.volume.role label value (lab-home/lab-workspace/lab-cache).
# Stamped on each per-user volume at spawn (with hub.volume.owner={username} and
# hub.volume.description) so the portal identifies it as a system volume by role,
# not by name, and reads its description off the label. Sourced from USER_VOLUMES (the
# volumes-dictionary role field; defaults to the suffix).
user_volume_roles = get_user_volume_roles(USER_VOLUMES, JUPYTERHUB_COMPOSE_PROJECT_NAME)
# Wire the templates into the volume-sizes cache so its background `docker
# system df` parser knows how to recognise per-user volumes after the
# COMPOSE_PROJECT_NAME-driven namespace refactor (stale match would leave the
# activity monitor's volume-size column empty for every user).
configure_volume_cache(user_volume_name_templates)
# Derived: ordered list of per-user volume records for the reset UI -
# {suffix, name_template, description} per row. Templates iterate this single
# list instead of cross-referencing a suffix list against a separate
# descriptions dict.
_user_volume_prefix = f"{JUPYTERHUB_COMPOSE_PROJECT_NAME}_jupyterlab_{{username}}_"
user_volumes_for_ui = [
    {
        'suffix': pattern[len(_user_volume_prefix):],
        'name_template': pattern,
        'description': data.get('description', ''),
        'role': user_volume_roles.get(pattern[len(_user_volume_prefix):], pattern[len(_user_volume_prefix):]),
    }
    for pattern, data in USER_VOLUMES.items()
]
# name-template -> {role, description} for the spawn-time labelling step. pre_spawn_hook
# stamps hub.volume.role/.owner/.description on each per-user volume so it
# self-describes - the portal reads role + description off the volume, not from settings.
user_volume_label_templates = {
    v['name_template']: {'role': v['role'], 'description': v['description']}
    for v in user_volumes_for_ui
}


# ── Section 3: Logic Calls ───────────────────────────────────────────────────
# Functions with side effects: event listeners, Docker commands, file copies.

# Attach SQLAlchemy event listeners for user rename/delete sync (activity data, NativeAuthenticator)
register_events()

# Self-heal the sent-notification history table at boot: create or rebuild it when the
# /data DB was never initialised or was inherited from an older deploy (logs the heal).
prepare_sent_notification_log()


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
# eagerly insert a User row at startup, which fires duoptimum_hub_services.events' after_insert
# listener and creates a UserInfo with a random xkcd password the operator cannot
# retrieve. Admin role is granted purely at login time via post_auth_hook below.

JUPYTERHUB_ADMIN_PASSWORD = os.environ.get("JUPYTERHUB_ADMIN_PASSWORD", "").strip()

# admin_bootstrap is the data layer; this config drives policy. State is read here at
# config-load (raw sqlite, ORM not up yet); provisioning is deferred to
# BootstrapAdminAuthenticator.__init__, where users_info is guaranteed to exist.
_DB_EMPTY_AT_STARTUP, _ADMIN_PRESENT_AT_STARTUP = query_admin_state(JUPYTERHUB_ADMIN)
_ADMIN_PROVISIONING_REQUESTED = bool(JUPYTERHUB_ADMIN and JUPYTERHUB_ADMIN_PASSWORD)

# Bootstrap window + fail-fast are pure policy in admin_bootstrap (unit-tested across the
# full state matrix); this config just feeds them the startup state and acts on the result.
_BOOTSTRAP_WINDOW_OPEN = bootstrap_window_open(
    JUPYTERHUB_SIGNUP_ENABLED, _ADMIN_PROVISIONING_REQUESTED, _DB_EMPTY_AT_STARTUP, _ADMIN_PRESENT_AT_STARTUP
)
_ADMIN_UNREACHABLE = admin_unreachable(
    JUPYTERHUB_SIGNUP_ENABLED, _ADMIN_PROVISIONING_REQUESTED, _ADMIN_PRESENT_AT_STARTUP, _BOOTSTRAP_WINDOW_OPEN
)
if _ADMIN_UNREACHABLE:
    raise SystemExit(
        f"[Admin Bootstrap] FATAL: admin '{JUPYTERHUB_ADMIN}' does not exist and cannot "
        "be created - signup is disabled (JUPYTERHUB_SIGNUP_ENABLED=0), the bootstrap "
        "self-signup window is closed (database already contains users), and no "
        "JUPYTERHUB_ADMIN_PASSWORD was set. Provide JUPYTERHUB_ADMIN_PASSWORD to "
        "pre-provision the admin, or set JUPYTERHUB_SIGNUP_ENABLED=1 to allow signup."
    )


class BootstrapAdminSignUpHandler(DuoptimumSignUpHandler):
    """Replace NativeAuth's misleading post-signup messages during the bootstrap window.

    Two upstream branches need correcting:

      * Success branch keys off `username in admin_users`, which we deliberately
        leave empty (populating admin_users triggers the eager User insert and
        the random-password trap in duoptimum_hub_services.events). With our create_user
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


class BootstrapAdminAuthenticator(DuoptimumHubAuthenticator):
    """During the bootstrap window, only the admin username is allowed to self-sign-up
    and that signup is auto-authorised on the spot.

    Outside the bootstrap window this class is a transparent passthrough to
    DuoptimumHubAuthenticator (NativeAuth credential logic + antd login/signup
    presentation). The window state is captured once at startup so the class
    behaves stably for the lifetime of the hub process.

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

    def __init__(self, *args, **kwargs):
        # super() runs NativeAuthenticator.__init__ -> add_new_table(), so users_info
        # is guaranteed to exist once it returns. This is the deterministic anchor for
        # env-password provisioning; config-load time is too early (no table on a fresh
        # volume -> the INSERT silently no-ops). Provision once, against our own session.
        super().__init__(*args, **kwargs)
        if _ADMIN_PROVISIONING_REQUESTED:
            provision_admin_userinfo(self.db, JUPYTERHUB_ADMIN, JUPYTERHUB_ADMIN_PASSWORD)

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
        # Auto-authorise the FIRST admin's self-signup regardless of the signup flag
        # (was gated on the signup-off window, so the signup-on default left the admin
        # is_authorized=False with no one to authorise them -> locked out). Non-admin
        # signups still land in the pending queue (is_authorized=False). Decision logic
        # lives in the service layer (admin_bootstrap), this only wires it.
        pending = first_admin_self_signup_pending(self.db, JUPYTERHUB_ADMIN, _ADMIN_PROVISIONING_REQUESTED)
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

# Detect GPU availability: autodetect (the default, any non-zero mode) queries the
# gpuinfo-nvidia sidecar for the host inventory (the hub itself has no GPU access) and
# derives on/off from whether any were found. Mode 0 is deliberately off.
# Returns (gpu_enabled: 0|1, nvidia_detected: 0|1, gpu_list: list of GPU dicts)
# Self-start the gpuinfo sidecar (best-effort) so detection talks to a reachable peer
# on the local docker host instead of waiting on compose - GPU on (autodetect) implies
# the hub manages the sidecar. A missing/failed sidecar degrades cleanly to GPU-off.
# It returns the sidecar's base URL with {hostname} filled in from the address it discovers
# for the container it just created (its IP on the dedicated network) - the host is
# obtained at runtime, never hardcoded - or '' when the sidecar isn't up.
_gpuinfo_url = (
    ensure_gpuinfo_sidecar(
        JUPYTERHUB_GPUINFO_NVIDIA_IMAGE, JUPYTERHUB_GPUINFO_NETWORK_NAME, JUPYTERHUB_GPUINFO_NVIDIA_URL,
        JUPYTERHUB_COMPOSE_PROJECT_NAME, container_name=JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME,
        container_role_label_key=JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY,
        container_role_label_value=JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO,
        container_description_label_key=JUPYTERHUB_LABEL_CONTAINER_DESCRIPTION,  # hub.container.description key (env-sourced, not hardcoded in the sidecar code)
        container_description="GPU-info sidecar - GPU detection, utilisation and per-GPU processes",
    )
    if JUPYTERHUB_GPU_ENABLED != 0 else ""
)
_gpuinfo_sidecar_up = bool(_gpuinfo_url)
# Point the detection client + utilisation sampler at the runtime-resolved URL.
configure_gpu_cache(_gpuinfo_url)
# Tie the sidecar's lifecycle to the hub: remove it when the hub exits so it does not
# linger as an orphan after the hub stops (next boot recreates it fresh from the current
# image). Best-effort - skipped on a hard SIGKILL.
if _gpuinfo_sidecar_up:
    import atexit
    atexit.register(stop_gpuinfo_sidecar, _gpuinfo_url, JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME, JUPYTERHUB_COMPOSE_PROJECT_NAME)
# probe only when the sidecar is actually up; otherwise skip straight to
# last-known/off so a missing sidecar never stalls boot on DNS/connect
gpu_enabled, nvidia_detected, gpu_list = resolve_gpu_mode(JUPYTERHUB_GPU_ENABLED, probe_sidecar=_gpuinfo_sidecar_up)
# index -> UUID map for CUDA_VISIBLE_DEVICES (UUIDs are stable across in-container
# GPU re-indexing, unlike host indices). isolation is only real on native Linux;
# on WSL2 (/dev/dxg) per-GPU selection is advisory, not enforced.
GPU_UUID_BY_INDEX = {str(g.get('index')): g.get('uuid', '') for g in gpu_list if g.get('uuid')}
GPU_ISOLATION_ENFORCED = bool(gpu_list) and not is_wsl2()
log.info(
    f"[GPU] enabled={gpu_enabled} detected={nvidia_detected} "
    f"isolation_enforced={GPU_ISOLATION_ENFORCED} gpus={gpu_list}")
# operator-facing per-card inventory: capabilities (name, total memory) + a live
# health snapshot (utilisation, used memory, temperature, power) from the sidecar.
# The raw inventory line above is the machine-readable summary; these are the readable per-card lines.
if _gpuinfo_sidecar_up:
    for _gpu_line in gpu_summary_lines():
        log.info(f"[GPU] {_gpu_line}")
# The background GPU-utilisation sampler queries the same sidecar periodically
# (gated on a non-empty inventory) so the portal's GPU bar shows real per-device
# utilisation, used memory and the processes holding each device.

# Process branding URIs: file:// copies to JupyterHub static dir, URLs pass through
# Returns dict with resolved paths/URLs for logo_file, favicon_uri, lab icons
branding = setup_branding(
    logo_uri=JUPYTERHUB_BRANDING_LOGO_URI,
    favicon_uri=JUPYTERHUB_BRANDING_FAVICON_URI,
    favicon_busy_uri=JUPYTERHUB_BRANDING_FAVICON_BUSY_URI,
    lab_main_icon_uri=JUPYTERHUB_BRANDING_LAB_MAIN_ICON_URI,
    lab_splash_icon_uri=JUPYTERHUB_BRANDING_LAB_SPLASH_ICON_URI,
    stage=JUPYTERHUB_BRANDING_STAGE,
)


# ── Section 4: JupyterHub Configuration ──────────────────────────────────────
# All c.* traitlet settings. Grouped by subsystem.

# ── SSL ──
# Direct SSL termination (certs auto-generated by /mkcert.sh at container startup)
# Disable when running behind a reverse proxy that handles TLS (e.g. Traefik)
if JUPYTERHUB_SSL_ENABLED == 1:
    c.JupyterHub.ssl_cert = '/certs/server.crt'
    c.JupyterHub.ssl_key = '/certs/server.key'

# ── Spawner ──
# TimingDockerSpawner is a thin subclass of DockerSpawner that logs
# `[Timing]` lines around start/stop/remove_object/poll. Helpful for
# diagnosing where time goes during stop/restart (Docker side vs hub
# polling lag). Drop back to stock dockerspawner.DockerSpawner if you
# want to silence the timing probes.
c.JupyterHub.spawner_class = "duoptimum_hub_services.timing_spawner.TimingDockerSpawner"

# Environment variables injected into every spawned JupyterLab container
c.DockerSpawner.environment = {
    'TF_CPP_MIN_LOG_LEVEL': TF_CPP_MIN_LOG_LEVEL,          # suppress TF C++ logging
    'TENSORBOARD_LOGDIR': '/tmp/tensorboard',                # TensorBoard log directory
    'MLFLOW_TRACKING_URI': 'http://localhost:5000',          # MLflow tracking server URL
    'MLFLOW_PORT': 5000,                                     # MLflow server port
    'MLFLOW_HOST': '0.0.0.0',                                # MLflow bind address
    'MLFLOW_WORKERS': 1,                                     # MLflow worker count
    'ENABLE_SERVICE_MLFLOW': JUPYTERHUB_LAB_SERVICE_MLFLOW,      # toggle MLflow in container startup
    'ENABLE_SERVICE_RESOURCES_MONITOR': JUPYTERHUB_LAB_SERVICE_RESOURCES_MONITOR,  # toggle resource monitor widget
    'ENABLE_SERVICE_TENSORBOARD': JUPYTERHUB_LAB_SERVICE_TENSORBOARD,  # toggle TensorBoard in container startup
    'NVIDIA_DETECTED': nvidia_detected,                      # GPU hardware availability flag (informational)
    'JUPYTERLAB_AUX_SCRIPTS_PATH': JUPYTERLAB_AUX_SCRIPTS_PATH,  # admin startup scripts path
    'JUPYTERLAB_AUX_MENU_PATH': JUPYTERLAB_AUX_MENU_PATH,      # admin-managed custom menu definitions
    'JUPYTERLAB_TIMEZONE': JUPYTERHUB_TIMEZONE,                  # IANA timezone for JupyterLab extensions
    'JUPYTERLAB_SYSTEM_NAME': JUPYTERHUB_BRANDING_LAB_NAME,                              # lab header/welcome/MOTD display name (from hub knob JUPYTERHUB_BRANDING_LAB_NAME)
    'JUPYTERHUB_NETWORK_NAME': JUPYTERHUB_NETWORK_NAME,                                   # Docker network connecting hub + user containers; needed by in-container scripts that attach sidecars to the same net
}

# Reserved env var names groups cannot override - every key we inject globally
# plus the GPU vars the pre-spawn hook sets per-user (NVIDIA_VISIBLE_DEVICES is
# the GPU selector and must not be settable by a group).
RESERVED_ENV_VAR_PREFIXES = ('JUPYTERHUB_', 'JPY_', 'MEM_', 'CPU_')
RESERVED_ENV_VAR_NAMES = set(c.DockerSpawner.environment.keys()) | {
    'ENABLE_GPU_SUPPORT', 'ENABLE_GPUSTAT', 'NVIDIA_VISIBLE_DEVICES', 'CUDA_VISIBLE_DEVICES',
    'DOCKER_HOST',  # set per-user by the limited-docker proxy wiring; groups must not override
}

# GPU device_requests is set per-user by the pre-spawn hook based on resolved
# group config. Left empty here so a user who is not in a GPU-enabled group
# does not receive the device.

c.DockerSpawner.image = JUPYTERHUB_LAB_IMAGE           # JupyterLab Docker image to spawn
c.DockerSpawner.use_internal_ip = True                       # use container IP on Docker network (not host)
c.DockerSpawner.network_name = JUPYTERHUB_NETWORK_NAME       # Docker network connecting hub and user containers
c.JupyterHub.default_url = JUPYTERHUB_BASE_URL_PREFIX + PORTAL_URL  # land everyone on the Duoptimum Hub portal after login
# c.DockerSpawner.notebook_dir = DOCKER_NOTEBOOK_DIR         # redundant - stellars-jupyterlab-ds image defaults to /home/lab/workspace
c.DockerSpawner.name_template = JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE  # env-driven; lab_container_name() reads the same var so hub lookups never desync. compose project label (pre_spawn_hook) provides the grouping namespace
c.DockerSpawner.volumes = DOCKER_SPAWNER_VOLUMES             # per-user persistent volumes + shared storage

# ── Branding: logo ──
# Set custom logo file if resolved from file:// URI
if branding['logo_file']:
    c.JupyterHub.logo_file = branding['logo_file']

# ── Template variables ──
# Passed to Jinja2 templates for UI rendering
c.JupyterHub.template_vars = {
    'user_volume_suffixes': user_volume_suffixes,            # ['home', 'workspace', 'cache'] for volume reset UI (kept for any existing consumers)
    'user_volume_name_templates': user_volume_name_templates, # suffix -> volume-name template (with {username}) for UI labels
    'user_volumes': user_volumes_for_ui,                     # ordered list of {suffix, name_template, description} for the reset UI loop
    'stellars_version': os.environ.get('STELLARS_JUPYTERHUB_VERSION', 'dev'),  # platform version shown in UI
    'server_version': jupyterhub.__version__,                # JupyterHub version shown in UI
    'idle_culler_enabled': JUPYTERHUB_IDLE_CULLER_ENABLED,   # toggle culler UI elements
    'idle_culler_timeout': JUPYTERHUB_IDLE_CULLER_TIMEOUT,   # timeout display in session panel
    'idle_culler_max_extension': JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION,  # max extension hours display
    'activitymon_target_hours': ACTIVITYMON_TARGET_HOURS,    # activity scoring window display
    'activitymon_sample_interval': ACTIVITYMON_SAMPLE_INTERVAL,  # sampling interval display
    'container_max_extra_space_mb': JUPYTERHUB_LAB_CONTAINER_MAX_EXTRA_SPACE_GB * 1024,  # threshold in MB for container size warning
    'volume_max_total_size_mb': JUPYTERHUB_LAB_VOLUME_MAX_TOTAL_SIZE_GB * 1024,        # threshold in MB for volume size warning
    'memory_max_usage_mb': JUPYTERHUB_LAB_MEMORY_MAX_USAGE_MB,                         # threshold in MB for per-user memory warning (0 GB -> 30% of host RAM)
    'favicon_uri': branding['favicon_uri'],                  # external favicon URL (empty = static_url default)
    'branding_stage': branding['stage'],                     # environment-stage badge text for the portal header (window.jhdata.stage); empty = no badge
    # Duoptimum Hub SPA entry chunk (hashed) so the overridden login/signup
    # templates can load the same bundle as the portal shell; resolved from the
    # vite manifest in the installed wheel ('' if unreadable -> stock-ish fallback).
    'duoptimum_entry_js': duoptimum_hub_web.entry_assets()[0],
    'duoptimum_entry_css': duoptimum_hub_web.entry_assets()[1],
    # Authoritative "this platform has GPU" flag for the portal shell -> window.jhdata.
    # The SPA gates every GPU widget on this instead of inferring from a (lazy) device list.
    'gpu_enabled': bool(gpu_enabled),
    # The platform admin username (JUPYTERHUB_ADMIN). The SPA needs this to recognise
    # the built-in admin and the hook-promoted admin (whose persistent User.admin row
    # is False), instead of guessing from a mock fixture.
    'admin_user': JUPYTERHUB_ADMIN or '',
    # Display name -> window.jhdata.hub_name. SPA shows it as the logo tooltip and as
    # the login/signup screen text; default "Duoptimum Hub" (baked in the Dockerfile).
    'hub_name': JUPYTERHUB_BRANDING_HUB_NAME,
}

# ── Tornado settings ──
# Handler-accessible config via self.settings['stellars_config']
# Replaces os.environ.get() calls in handlers with explicit typed values
c.JupyterHub.tornado_settings = {
    'stellars_config': {
        'user_volume_suffixes': user_volume_suffixes,        # for ManageVolumesHandler validation
        'user_volume_name_templates': user_volume_name_templates,  # for ManageVolumesHandler to construct correct on-disk volume names
        'user_volume_roles': user_volume_roles,              # suffix -> hub.volume.role; ManageVolumesHandler GET tags each volume so the portal IDs system volumes by role
        'volume_role_label_key': JUPYTERHUB_LABEL_VOLUME_ROLE_KEY,           # handlers read a volume's role off this label key (env-sourced, never a hardcoded literal)
        'volume_description_label_key': JUPYTERHUB_LABEL_VOLUME_DESCRIPTION,  # handlers read a volume's human description off this label key (env-sourced)
        'user_volumes': user_volumes_for_ui,                 # for ManageVolumesHandler GET to attach descriptions to existing volumes
        'idle_culler_enabled': JUPYTERHUB_IDLE_CULLER_ENABLED,  # for SessionInfoHandler, ActivityDataHandler
        'idle_culler_timeout': JUPYTERHUB_IDLE_CULLER_TIMEOUT,  # for SessionInfoHandler, ExtendSessionHandler
        'idle_culler_max_extension': JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION,  # for ExtendSessionHandler limits
        'gpu_list': gpu_list,                                 # host GPUs enumerated at startup (GroupsDataHandler, ActivityDataHandler)
        'gpu_available': bool(gpu_enabled),                   # hardware-present gate for resolve_policies (EffectiveGrantsHandler)
        'gpu_isolation_enforced': GPU_ISOLATION_ENFORCED,     # False on WSL2 -> the portal GPU policy section shows the advisory note
        'container_max_extra_space_mb': JUPYTERHUB_LAB_CONTAINER_MAX_EXTRA_SPACE_GB * 1024,  # threshold in MB for container size warning
        'volume_max_total_size_mb': JUPYTERHUB_LAB_VOLUME_MAX_TOTAL_SIZE_GB * 1024,        # threshold in MB for volume size warning
        'memory_max_usage_mb': JUPYTERHUB_LAB_MEMORY_MAX_USAGE_MB,                         # threshold in MB for per-user memory warning
        'reserved_env_var_names': RESERVED_ENV_VAR_NAMES,                              # names groups cannot override
        'reserved_env_var_prefixes': RESERVED_ENV_VAR_PREFIXES,                        # prefixes reserved for JupyterHub/platform
        'shared_volume_name': JUPYTERHUB_SHARED_VOLUME_NAME,                          # shared volume for groups volume-mounts UI; discovered by hub.volume.role=shared
        'lab_image': JUPYTERHUB_LAB_IMAGE,                                             # image every lab spawns from (for the Lab Container page)
        'lab_volumes': [                                                              # standard per-user volumes mounted into every lab
            {'suffix': v['suffix'], 'mount': DOCKER_SPAWNER_VOLUMES.get(v['name_template'], ''), 'description': v['description'], 'role': v['role']}
            for v in user_volumes_for_ui
        ],
    }
}

# ── Pre-spawn hook ──
# Factory returns async closure capturing branding + group resolution state.
# Hook runs before each container spawn: resolves all user's groups into one
# effective config (docker/gpu/env vars), applies it to spawner, then injects
# CHP favicon proxy routes and JupyterLab icon URLs.
# Docker-proxy (limited-docker users): in-process in this hub. Named volume mounted at the
# socket dir; spawner subpath-mounts the SAME volume into each lab, so hub needs the EXACT
# daemon volume name. Found by role among own mounts (rename-safe) - one source, no fallback;
# empty -> validator fails (a guessed name would 404 every limited-docker spawn). Socket dir
# baked ENV. Duplicate role -> raises (per-namespace).
JUPYTERHUB_DOCKER_PROXY_SOCKET_DIR = os.environ.get("JUPYTERHUB_DOCKER_PROXY_SOCKET_DIR", "").strip()
JUPYTERHUB_DOCKER_PROXY_SOCKETS_VOLUME = resolve_self_mount_volume_by_label(
    JUPYTERHUB_LABEL_VOLUME_ROLE_KEY, JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY
) or ""
# System volumes (shared + docker-proxy) for the Lab Setup page. Both resolved by role among
# hub's OWN mounts (rename-safe, above). Mount = lab-side path (constants). Description read off
# the JUPYTERHUB_LABEL_VOLUME_DESCRIPTION label key compose stamps - NOT volumes_dictionary.yml
# (stays lab-only). Unresolved name -> row omitted. Merged into stellars_config (dict built above).
c.JupyterHub.tornado_settings["stellars_config"]["system_volumes"] = build_system_volume_rows(
    [
        (JUPYTERHUB_SHARED_VOLUME_NAME, SHARED_MOUNTPOINT, JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED),
        (JUPYTERHUB_DOCKER_PROXY_SOCKETS_VOLUME, SOCK_MOUNT_DIR, JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY),
    ],
    JUPYTERHUB_LABEL_VOLUME_DESCRIPTION,
    volume_labels,
)
# Per-user com.docker.compose.project label when a docker-limited group opts in. {compose},
# {username}. Baked ENV ({username}_containers); validator requires present + {username}.
JUPYTERHUB_DOCKER_PROXY_USER_COMPOSE_PROJECT_TEMPLATE = os.environ.get(
    "JUPYTERHUB_DOCKER_PROXY_USER_COMPOSE_PROJECT_TEMPLATE", ""
)

# ── Required-config validation (single pass) ─────────────────────────────────
# All required vars now gathered (docker-proxy socket dir/volume were last). Validator raises
# one SystemExit listing every missing/inconsistent var, logs warnings for degraded-but-
# bootable config (gpuinfo net unresolved -> GPU off; shared volume unresolved -> quick-add
# hidden; branding file:// missing). Keeps this file thin - no scattered fail-fast.
validate_hub_config({
    "admin": JUPYTERHUB_ADMIN,
    "lab_image": JUPYTERHUB_LAB_IMAGE,
    "namespace": JUPYTERHUB_COMPOSE_PROJECT_NAME,
    "lab_network_name": JUPYTERHUB_NETWORK_NAME,
    "network_role_label_key": JUPYTERHUB_LABEL_NETWORK_ROLE_KEY,
    "volume_role_label_key": JUPYTERHUB_LABEL_VOLUME_ROLE_KEY,
    "container_role_label_key": JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY,
    "lab_network_role_label": JUPYTERHUB_LABEL_NETWORK_ROLE_LAB,
    "gpuinfo_network_role_label": JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO,
    "shared_volume_role_label": JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED,
    "docker_proxy_volume_role_label": JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY,
    "gpuinfo_container_role_label": JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO,
    "hub_container_role_label": JUPYTERHUB_LABEL_CONTAINER_ROLE_HUB,
    "lab_container_role_label": JUPYTERHUB_LABEL_CONTAINER_ROLE_LAB,
    "volume_description_label_key": JUPYTERHUB_LABEL_VOLUME_DESCRIPTION,
    "volume_owner_label_key": JUPYTERHUB_LABEL_VOLUME_OWNER_KEY,
    "container_description_label_key": JUPYTERHUB_LABEL_CONTAINER_DESCRIPTION,
    "docker_proxy_owner_label_key": JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_KEY,
    "docker_proxy_owner_label_value": JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_VALUE,
    "lab_container_name_template": JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE,
    "gpuinfo_nvidia_image": JUPYTERHUB_GPUINFO_NVIDIA_IMAGE,
    "gpuinfo_nvidia_container_name": JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME,
    "gpuinfo_nvidia_url": JUPYTERHUB_GPUINFO_NVIDIA_URL,
    "docker_proxy_socket_dir": JUPYTERHUB_DOCKER_PROXY_SOCKET_DIR,
    "docker_proxy_sockets_volume": JUPYTERHUB_DOCKER_PROXY_SOCKETS_VOLUME,
    "user_compose_project_template": JUPYTERHUB_DOCKER_PROXY_USER_COMPOSE_PROJECT_TEMPLATE,
    # resolved/optional - drive warnings, never block boot
    "gpuinfo_network_name": JUPYTERHUB_GPUINFO_NETWORK_NAME,
    "shared_volume_name": JUPYTERHUB_SHARED_VOLUME_NAME,
    "branding_logo_uri": JUPYTERHUB_BRANDING_LOGO_URI,
    "branding_favicon_uri": JUPYTERHUB_BRANDING_FAVICON_URI,
    "branding_favicon_busy_uri": JUPYTERHUB_BRANDING_FAVICON_BUSY_URI,
    "branding_lab_main_icon_uri": JUPYTERHUB_BRANDING_LAB_MAIN_ICON_URI,
    "branding_lab_splash_uri": JUPYTERHUB_BRANDING_LAB_SPLASH_ICON_URI,
}).raise_if_errors(log=log)

c.DockerSpawner.pre_spawn_hook = make_pre_spawn_hook(
    branding,                                                # icon static names and URLs from setup_branding()
    favicon_uri=JUPYTERHUB_BRANDING_FAVICON_URI,             # non-empty activates the favicon.ico CHP route
    favicon_busy_target=branding['favicon_busy_target'],    # non-empty activates the favicon-busy CHP route; empty = JupyterLab default busy frames
    gpu_available=bool(gpu_enabled),                         # hardware present - required for per-group GPU grant
    gpu_uuid_by_index=GPU_UUID_BY_INDEX,                     # index->UUID for CUDA_VISIBLE_DEVICES
    reserved_env_var_names=RESERVED_ENV_VAR_NAMES,           # names groups cannot override
    reserved_env_var_prefixes=RESERVED_ENV_VAR_PREFIXES,     # prefixes reserved for JupyterHub/platform
    compose_project=JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME,     # compose project label on spawned labs (defaults to the hub project; overridable to differ)
    container_role_label_key=JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY,   # hub.container.role key stamped on the spawned lab
    container_role_label_value=JUPYTERHUB_LABEL_CONTAINER_ROLE_LAB, # role value 'lab' - makes spawned labs discoverable by role like the hub + gpuinfo sidecar
    docker_proxy_socket_dir=JUPYTERHUB_DOCKER_PROXY_SOCKET_DIR,   # path inside hub where per-user sockets live (backed by named volume)
    docker_proxy_volume_name=JUPYTERHUB_DOCKER_PROXY_SOCKETS_VOLUME,      # named docker volume; the spawner subpath-mounts this into each lab
    user_compose_project_template=JUPYTERHUB_DOCKER_PROXY_USER_COMPOSE_PROJECT_TEMPLATE,  # rendered per-user when a docker-limited group enables it
    hub_network_name=JUPYTERHUB_NETWORK_NAME,                     # revealed in user's `docker network ls` when their group enables it (default on)
    block_file_downloads=JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS,        # master switch: overlay per-user download-block CHP routes for non-granted users
    lab_sudo_enable_default=JUPYTERHUB_LAB_SUDO_ENABLE,  # default JUPYTERLAB_SUDO_ENABLE when no group configures sudo
    api_keys_reconcile_interval=JUPYTERHUB_IDLE_CULLER_INTERVAL,  # periodic api-keys-pool reconcile cadence (reuses the cull interval, default 600s)
    shared_volume_name=JUPYTERHUB_SHARED_VOLUME_NAME,  # role=shared volume the group "standard shared" mount resolves to at spawn (label-resolved, rename-safe; '' = absent)
    volume_role_label_key=JUPYTERHUB_LABEL_VOLUME_ROLE_KEY,  # hub.volume.role key stamped on per-user volumes at spawn
    volume_owner_label_key=JUPYTERHUB_LABEL_VOLUME_OWNER_KEY,  # hub.volume.owner key; value = the username, stamped per-user at spawn (env-sourced)
    volume_description_label_key=JUPYTERHUB_LABEL_VOLUME_DESCRIPTION,  # hub.volume.description key stamped per-user at spawn (env-sourced)
    user_volume_label_templates=user_volume_label_templates,  # name-template -> {role, description}; hook pre-creates each labelled per-user volume (role/owner/description)
)


c.DockerSpawner.post_stop_hook = make_post_stop_hook(socket_dir=JUPYTERHUB_DOCKER_PROXY_SOCKET_DIR)  # docker-proxy unregister + api-key release + stop event

# ── Spawner args ──
# Command-line arguments passed to the spawned JupyterLab ServerApp
c.DockerSpawner.args = [
    '--ServerApp.allow_origin=*',                            # allow cross-origin requests (required behind proxy)
    '--ServerApp.disable_check_xsrf=True',                   # disable XSRF for API access from hub
]

# ── Networking ──
# Spawned labs + CHP reach the hub by a STABLE network alias, not the hub's container id.
# The previous socket.gethostname() baked the hub's ephemeral short id into every lab's
# JUPYTERHUB_API_URL; on a hub redeploy/watchtower update the id changes and already-running
# labs are stranded with "Name or service not known" (DEF-22). The role value is stamped as a
# hub_network alias by compose, so this name resolves to the hub across redeploys.
_HUB_HOST = JUPYTERHUB_LABEL_CONTAINER_ROLE_HUB
# Fail LOUD if the alias is missing. gethostname() always resolved (just to a drifting id);
# this name resolves only if compose actually stamped the hub_network alias. Surface a dropped
# alias (e.g. an override that reshapes the hub networks) at boot, not as a cryptic per-spawn
# "Name or service not known" - the exact silent-strand failure DEF-22 fixed.
try:
    socket.gethostbyname(_HUB_HOST)
except OSError:
    # error, not warning: a missing alias breaks EVERY spawn (bigger blast radius than the
    # validator's optional-feature warnings); the hub still serves its UI, so do not refuse boot.
    log.error(f"[networking] hub alias '{_HUB_HOST}' does not resolve - spawned labs will fail "
              f"to reach the hub; ensure compose stamps it as a hub_network alias (DEF-22)")
c.JupyterHub.hub_connect_url = f'http://{_HUB_HOST}:8080' + JUPYTERHUB_BASE_URL_PREFIX + '/hub'  # URL spawned containers/CHP use to reach hub
c.DockerSpawner.remove = True                                # auto-remove containers after stop (volumes persist)
c.DockerSpawner.debug = False                                # DockerSpawner debug logging
c.JupyterHub.hub_ip = "0.0.0.0"                              # bind/listen on all interfaces (no name resolution -> no DNS race)
c.JupyterHub.hub_port = 8080                                 # internal hub port (not exposed externally)
c.JupyterHub.base_url = JUPYTERHUB_BASE_URL_PREFIX + '/' if JUPYTERHUB_BASE_URL_PREFIX else '/'  # URL prefix for all hub routes

# Leave running user servers up across a hub restart (the hub re-discovers them
# on boot; schedule_policy_startup already re-imposes policy on survivors). Makes
# config/portal restarts non-disruptive for active users.
c.JupyterHub.cleanup_servers = False

# ── Persistence ──
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"  # cookie signing key (persisted in jupyterhub_data volume)
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"           # user database (persisted in jupyterhub_data volume)

# ── Authentication ──
c.JupyterHub.authenticator_class = BootstrapAdminAuthenticator       # bootstrap-window admin-only signup + admin rename sync
c.JupyterHub.template_paths = [
    duoptimum_hub_web.template_dir(),                                  # Duoptimum Hub portal: home.html = SPA shell, admin/token = redirect stubs (highest priority)
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

# ── Abuse protection (Layer B) ──
# Env-mapped in the library: spawn-storm / capacity caps + NativeAuth login lockout.
# Layer A (Traefik rateLimit) is configured in compose.yml via JUPYTERHUB_RATELIMIT_*.
apply_abuse_protection(c)

# ── Extra handlers ──
# Custom API endpoints and admin pages (routes are relative to /hub/).
# Registered via c.DuoptimumHub.registered_handlers - the platform's supported
# replacement for the deprecated c.JupyterHub.extra_handlers. DuoptimumHub splices
# these into the hub's handler list in the same first-match-wins slot extra_handlers
# used (after built-ins, before the /logo + /api 404 catch-alls). See app.py.
c.DuoptimumHub.registered_handlers = [
    (r'/api/users/([^/]+)/manage-volumes', ManageVolumesHandler),    # DELETE - reset user volumes
    (r'/api/users/([^/]+)/restart-server', RestartServerHandler),    # POST - Docker container restart
    (r'/api/users/([^/]+)/server/logs', ServerLogsHandler),          # GET - bounded container-log tail (Start page)
    (r'/api/users/([^/]+)/lab-ready', LabReadyHandler),              # GET - silent lab readiness probe (always 200)
    (r'/api/users/([^/]+)/session-info', SessionInfoHandler),        # GET - idle culler status
    (r'/api/users/([^/]+)/profile', UserProfileHandler),             # GET/PUT - first/last name + email
    (r'/api/users/([^/]+)/force-password-change', UserForcePasswordChangeHandler), # POST - admin set/clear force-pw gate
    (r'/api/users/([^/]+)/rename', UserRenameHandler),               # POST - admin rename (records who renamed whom)
    (r'/api/users/([^/]+)/display-preferences', UserDisplayPreferencesHandler), # GET/PUT - per-user UI options
    (r'/api/users/([^/]+)/effective-grants', EffectiveGrantsHandler), # GET - resolved group policy grants
    (r'/api/user-profiles', UserProfilesListHandler),                # GET - all profiles (Users-list sub-names)
    (r'/api/settings', SettingsDataHandler),                          # GET - platform settings (read-only JSON)
    (r'/api/events', EventsDataHandler),                              # GET - recent platform events (audit feed)
    (r'/api/users/([^/]+)/extend-session', ExtendSessionHandler),    # POST - extend idle timeout
    (r'/api/notifications/active-servers', ActiveServersHandler),     # GET - list running servers
    (r'/api/notifications/broadcast', BroadcastNotificationHandler), # POST - broadcast to all servers
    (r'/api/notifications/sent', SentNotificationsDataHandler),       # GET - sent-broadcast history ("Past Notifications")
    (r'/api/admin/credentials', GetUserCredentialsHandler),          # GET - cached auto-generated passwords
    (r'/api/activity', ActivityDataHandler),                          # GET - activity data + Docker stats
    (r'/api/activity/reset', ActivityResetHandler),                   # POST - clear activity samples
    (r'/api/activity/sample', ActivitySampleHandler),                 # POST - trigger manual sampling
    (r'/api/admin/groups', GroupsDataHandler),                        # GET - list groups with config
    (r'/api/admin/groups/create', GroupsCreateHandler),               # POST - create new group
    (r'/api/admin/groups/reorder', GroupsReorderHandler),             # POST - update group priorities
    (r'/api/admin/groups/([^/]+)/delete', GroupsDeleteHandler),       # DELETE - delete group
    (r'/api/admin/groups/([^/]+)/config', GroupsConfigHandler),       # GET/PUT - group configuration
    (r'/api/native-users', NativeUsersHandler),                       # GET - list NativeAuth signups + auth state
    (r'/api/native-users/([^/]+)/authorization', NativeUserAuthorizationHandler),  # POST - idempotent set
    # Legacy server-rendered page handlers (/notifications, /settings, /activity,
    # /groups) were removed - the React portal owns these features as client
    # routes. Their /api/* data handlers above stay. Unregistering them frees the
    # bare paths so the hub-root portal (no /portal segment) can serve those SPA
    # routes without the old pages shadowing them. See docs/acceptance-criteria/acc-crit-drop-portal-path.md.
    (r'/health', HealthCheckHandler),                                 # GET - unauthenticated monitoring endpoint
]
# Duoptimum Hub portal: catch-all serving the SPA shell + bundled assets at the hub root.
# Appended last so it is ordered after the API/page routes above (and the negative-lookahead
# route never shadows them); still ahead of the /logo + /api 404 catch-alls after splicing.
c.DuoptimumHub.registered_handlers += portal_handlers()


# ── Section 5: Services & Startup Callbacks ──────────────────────────────────
# JupyterHub managed services (background processes) and one-time startup hooks.

# Build service definitions: activity sampler (always enabled)
services, roles = get_services_and_roles(
    sample_interval=ACTIVITYMON_SAMPLE_INTERVAL,             # activity sampling interval
)
c.JupyterHub.services = services                             # register managed services
c.JupyterHub.load_roles = roles                              # service API token scopes

# Idle culler runs in-process (not a managed service) so it can read each
# server's granted extension from spawner state and actually delay the cull.
if JUPYTERHUB_IDLE_CULLER_ENABLED == 1:
    schedule_idle_culler(
        base_seconds=JUPYTERHUB_IDLE_CULLER_TIMEOUT,        # derived seconds (from _MINUTES)
        ceiling_seconds=JUPYTERHUB_IDLE_CULLER_TIMEOUT + JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION * 3600,  # base + max extension = absolute cap on remaining/lifetime
        interval_seconds=JUPYTERHUB_IDLE_CULLER_INTERVAL,   # seconds between cull sweeps
        max_age_seconds=JUPYTERHUB_IDLE_CULLER_MAX_AGE,     # max server lifetime (0=unlimited)
    )

# Consolidated startup hydration (deferred to the IOLoop, after the hub is
# serving - never blocks boot). One call warms everything that previously only
# came alive lazily on the first /activity request, so a (re)started hub shows a
# populated portal immediately, including servers that survived the restart:
#   - the activity refreshers (volume sizes, container sizes, GPU utilisation) +
#     live stats for surviving servers
#   - the image-update snapshot, so "update available" is known up front
#   - survivor CHP favicon routes (pre_spawn_hook only fires on new spawns)
#   - every policy model's on_hub_startup (docker-proxy re-bind, download-block
#     route re-registration, api-keys reconcile + periodic) for survivors
log.info(f"[Config] File-download policy: {'BLOCK (per-group downloads_active grants)' if JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS else 'ALLOW (dormant)'}")
schedule_startup_hydration(
    stellars_config=c.JupyterHub.tornado_settings['stellars_config'],
    favicon_uri=JUPYTERHUB_BRANDING_FAVICON_URI,
    favicon_busy_target=branding['favicon_busy_target'],
    policy_actx=c.DockerSpawner.pre_spawn_hook._stellars_apply_context,
)

# EOF
