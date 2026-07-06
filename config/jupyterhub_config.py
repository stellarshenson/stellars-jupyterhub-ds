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

import jupyterhub               # __version__, __file__ for template paths
import nativeauthenticator      # __file__ for template path resolution

# duoptimum_hub_services core functions - pure logic, no side effects on import
from duoptimum_hub_services import (
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
    resolve_gpu_vendor_provider,            # GPU vendor provider (driver/runtime/visibility-env); NVIDIA reference today, threaded to GPU policy + sidecar
    NvidiaGpuProvider,                       # reference GPU vendor; boot fallback so vendor resolution never strands boot (mirrors the GpuPolicy.apply fallback)
    resolve_host_status_provider,           # reads c.JupyterHub.spawner_class -> instantiates its declared host-status provider (home-screen CPU/MEM/GPU aggregate)
    resolve_memory_quota_mb,                # calc: per-user memory warning threshold MB from host-RAM fraction
    schedule_startup_hydration,             # consolidated startup hydration: warms caches + image-update check + survivor favicon routes/policy, all deferred to the IOLoop
    setup_branding,                         # processes logo/favicon/icon URIs, copies file:// to static dir
)

from duoptimum_hub_services.docker_utils import resolve_self_mount_volume_by_label  # exact volume discovery by hub.volume.role among hub's own mounts (rename-safe; raises on duplicate role)
from duoptimum_hub_services.docker_utils import resolve_self_compose_project  # runtime discovery of the hub's own compose project from its own container label (no env needed)
from duoptimum_hub_services.docker_utils import resolve_self_compose_service  # runtime discovery of the hub's own compose SERVICE name (stable DNS alias) from its own container label - the hub_connect_ip labs reach the hub by
from duoptimum_hub_services.docker_utils import volume_labels  # read a named volume's labels (injected into build_system_volume_rows)
from duoptimum_hub_services.docker_utils import build_system_volume_rows  # pure builder: Lab Setup system-volume rows (shared + docker-proxy)
from duoptimum_hub_services.policy.base import SHARED_MOUNTPOINT  # lab-side shared mount (/mnt/shared)
from duoptimum_hub_services.docker_proxy import SOCK_MOUNT_DIR  # lab-side docker-proxy socket mount (/run/dockersock)
from duoptimum_hub_services.docker_utils import (  # {network}-token net resolution, memoized in the package; no net-name env mutated here
    resolve_lab_network,        # role=lab net (hub<->lab), required
    resolve_gpuinfo_network,    # role=gpuinfo net (hub<->sidecar), optional (GPU off when absent)
)
from duoptimum_hub_services.protected_env import load_protected_env  # protected-env dictionary -> reserved names/prefixes (single source)

# The platform's custom API/page route table - registered via
# c.DuoptimumHub.registered_handlers (our non-deprecated replacement for the
# deprecated JupyterHub.extra_handlers; see app.py). The 30-name import block and
# the route table moved into the handlers-package builder so this file reads like
# configuration; see handlers/registry.py for the routes.
from duoptimum_hub_services.handlers.registry import registered_handlers

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
JUPYTERHUB_HUB_DOCKER_API_TIMEOUT = int(os.environ.get("JUPYTERHUB_HUB_DOCKER_API_TIMEOUT", 360))               # Docker API timeout in seconds
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
# The env carries the baked "{network}" token; resolve_lab_network() (memoized, in the
# package) resolves it to the role=lab net at each push-boundary below - the env is never
# mutated here. Empty after resolve -> validator fails (the lab net is required).
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
# Hub<->sidecar net (compose owns it) tagged role=gpuinfo. The env carries the baked
# "{network}" token; resolve_gpuinfo_network() (memoized, in the package) resolves it at
# the sidecar + validator call sites - never mutated here. Empty = sidecar unplaceable ->
# GPU off (validator WARNS, sidecar degrades).
JUPYTERHUB_GPUINFO_NVIDIA_IMAGE = os.environ.get("JUPYTERHUB_GPUINFO_NVIDIA_IMAGE", "").strip()  # sidecar image the hub self-starts (baked Dockerfile ENV; empty -> validate_hub_config fails)
JUPYTERHUB_ADMIN_USERNAME = os.environ.get("JUPYTERHUB_ADMIN_USERNAME", "").strip().lower()                      # admin username; .lower() - JupyterHub normalizes usernames to lowercase, bootstrap lookups/compares use this raw so it must match the DB + login form (auto-authorized on first signup; required; baked image ENV - validated by validate_hub_config)

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
#   $JUPYTERHUB_LAB_VOLUMES_DESCRIPTIONS_FILE (if set + exists) - operator overrides
# Per-suffix, per-field merge: operator wins on conflict, missing fields fall
# back to the platform default, operator-only suffixes are added verbatim.
VOLUMES_DICTIONARY_PATH = '/srv/jupyterhub/volumes_dictionary.yml'
JUPYTERHUB_LAB_VOLUMES_DESCRIPTIONS_FILE = os.environ.get('JUPYTERHUB_LAB_VOLUMES_DESCRIPTIONS_FILE', '')
USER_VOLUMES = load_merged_user_volumes(
    VOLUMES_DICTIONARY_PATH,
    JUPYTERHUB_LAB_VOLUMES_DESCRIPTIONS_FILE,
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
        'label': data.get('label') or None,  # friendly display name; None -> UI falls back to the volume name
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


# ── Admin bootstrap ──
# First-admin bootstrap (env-provision / signup-off self-signup window / normal-signup
# auto-authorise, with fail-fast when unreachable) lives entirely in
# DuoptimumNativeAuthenticator (duoptimum_hub_services/auth.py). The config feeds it two
# trait inputs (admin_username / signup_enabled) under Authentication below; the INITIAL-ONLY
# admin password is read by the authenticator straight from os.environ['JUPYTERHUB_ADMIN_PASSWORD']
# - deliberately NOT a config trait, so the secret never reaches --show-config or the Settings page.


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
# GPU vendor provider (NVIDIA reference today) - resolved once at boot, threaded to
# the per-user GPU policy (device request + visibility env, via ApplyContext) and to
# the sidecar launcher (its container runtime). A second vendor = register it in
# gpu_vendor._VENDORS and drive the selection; nothing else in the spawn path changes.
# Falls back to NVIDIA (mirrors the GpuPolicy.apply fallback) so resolution can never
# return None and crash boot - the subsystem degrades, never dies. The no-arg call is
# total today (nvidia always registered); when selection becomes env/detection-driven,
# decide the unknown-vendor policy here (fail-loud or GPU-off), not this silent default.
GPU_VENDOR = resolve_gpu_vendor_provider() or NvidiaGpuProvider()
_gpuinfo_url = (
    ensure_gpuinfo_sidecar(
        JUPYTERHUB_GPUINFO_NVIDIA_IMAGE, resolve_gpuinfo_network(), JUPYTERHUB_GPUINFO_NVIDIA_URL,
        JUPYTERHUB_COMPOSE_PROJECT_NAME, container_name=JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME,
        container_role_label_key=JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY,
        container_role_label_value=JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO,
        container_description_label_key=JUPYTERHUB_LABEL_CONTAINER_DESCRIPTION,  # hub.container.description key (env-sourced, not hardcoded in the sidecar code)
        container_description="GPU-info sidecar - GPU detection, utilisation and per-GPU processes",
        gpu_runtime=GPU_VENDOR.runtime_name(),  # vendor's docker runtime (nvidia today); requested only if the host registers it
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
# autodetect asked but sidecar never came up -> GPU NOT autodetected (nvidia), labs CPU-only.
# say it plainly; the [GPUInfo] lines above carry the specific cause (no name/net/image/docker).
# enabled=0 on the summary line alone is too implicit for the operator to read the cause from.
if JUPYTERHUB_GPU_ENABLED != 0 and not _gpuinfo_sidecar_up:
    log.warning(
        "[GPU] gpuinfo-nvidia sidecar did not start -> GPU not detected (nvidia) -> "
        "GPU disabled; labs start CPU-only (see [GPUInfo] above for the cause)")
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
# DuoptimumDockerSpawner is the canonical DockerSpawner subclass: `[Timing]`
# lines around start/stop/remove_object (diagnosing Docker-side vs hub-polling
# lag) AND a declared host_status_provider_class (the home-screen CPU/MEM/GPU
# aggregate for this environment, resolved below). Drop back to stock
# dockerspawner.DockerSpawner to silence the probes (and forgo the host-status panel).
c.JupyterHub.spawner_class = "duoptimum_hub_services.spawner.DuoptimumDockerSpawner"

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
    'JUPYTERHUB_NETWORK_NAME': resolve_lab_network(),                                    # Docker network connecting hub + user containers; needed by in-container scripts that attach sidecars to the same net
}

# Reserved env var names/prefixes a user or group must NOT override. Loaded from the
# baked protected-env dictionary (single source of truth, operator-extensible) and
# unioned with every key we inject globally (derived from c.DockerSpawner.environment,
# so those never drift). Fans out unchanged to stellars_config + the pre-spawn hook +
# the per-user env handler + the group policy env validator.
_protected_names, RESERVED_ENV_VAR_PREFIXES = load_protected_env('/srv/jupyterhub/protected_env_dictionary.yml')
RESERVED_ENV_VAR_NAMES = set(c.DockerSpawner.environment.keys()) | _protected_names

# GPU device_requests is set per-user by the pre-spawn hook based on resolved
# group config. Left empty here so a user who is not in a GPU-enabled group
# does not receive the device.

c.DockerSpawner.image = JUPYTERHUB_LAB_IMAGE           # JupyterLab Docker image to spawn
c.DockerSpawner.use_internal_ip = True                       # use container IP on Docker network (not host)
c.DockerSpawner.network_name = resolve_lab_network()        # Docker network connecting hub and user containers (resolved as we push it to the spawner)
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
    # The platform admin username (JUPYTERHUB_ADMIN_USERNAME). The SPA needs this to recognise
    # the built-in admin and the hook-promoted admin (whose persistent User.admin row
    # is False), instead of guessing from a mock fixture.
    'admin_user': JUPYTERHUB_ADMIN_USERNAME or '',
    # Display name -> window.jhdata.hub_name. SPA shows it as the logo tooltip and as
    # the login/signup screen text; default "Duoptimum Hub" (baked in the Dockerfile).
    'hub_name': JUPYTERHUB_BRANDING_HUB_NAME,
}

# ── Host-status provider ──
# Resolve THIS environment's host-status provider off the configured spawner
# (DuoptimumDockerSpawner -> DockerHostStatusProvider). The activity handler
# delegates the home-screen host aggregate (CPU/MEM/GPU) to it; a spawner that
# declares none yields no host-status panel. gpu_enabled gates the GPU dimension.
_host_status_provider = resolve_host_status_provider(
    c.JupyterHub.spawner_class,
    {'gpu_enabled': bool(gpu_enabled), 'gpu_list': gpu_list},
)

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
        'host_status_provider': _host_status_provider,        # ActivityDataHandler delegates the host CPU/MEM/GPU aggregate to this (None -> no host-status panel)
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
    "admin": JUPYTERHUB_ADMIN_USERNAME,
    "lab_image": JUPYTERHUB_LAB_IMAGE,
    "namespace": JUPYTERHUB_COMPOSE_PROJECT_NAME,
    "lab_network_name": resolve_lab_network(),
    "network_role_label_key": JUPYTERHUB_LABEL_NETWORK_ROLE_KEY,
    "volume_role_label_key": JUPYTERHUB_LABEL_VOLUME_ROLE_KEY,
    "container_role_label_key": JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY,
    "lab_network_role_label": JUPYTERHUB_LABEL_NETWORK_ROLE_LAB,
    "gpuinfo_network_role_label": JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO,
    "shared_volume_role_label": JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED,
    "docker_proxy_volume_role_label": JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY,
    "gpuinfo_container_role_label": JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO,
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
    "gpuinfo_network_name": resolve_gpuinfo_network(),
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
    gpu_vendor=GPU_VENDOR,                                   # GPU vendor provider (device request + visibility env) threaded to the GPU policy
    reserved_env_var_names=RESERVED_ENV_VAR_NAMES,           # names groups cannot override
    reserved_env_var_prefixes=RESERVED_ENV_VAR_PREFIXES,     # prefixes reserved for JupyterHub/platform
    compose_project=JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME,     # compose project label on spawned labs (defaults to the hub project; overridable to differ)
    container_role_label_key=JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY,   # hub.container.role key stamped on the spawned lab
    container_role_label_value=JUPYTERHUB_LABEL_CONTAINER_ROLE_LAB, # role value 'lab' - makes spawned labs discoverable by role like the hub + gpuinfo sidecar
    docker_proxy_socket_dir=JUPYTERHUB_DOCKER_PROXY_SOCKET_DIR,   # path inside hub where per-user sockets live (backed by named volume)
    docker_proxy_volume_name=JUPYTERHUB_DOCKER_PROXY_SOCKETS_VOLUME,      # named docker volume; the spawner subpath-mounts this into each lab
    user_compose_project_template=JUPYTERHUB_DOCKER_PROXY_USER_COMPOSE_PROJECT_TEMPLATE,  # rendered per-user when a docker-limited group enables it
    hub_network_name=resolve_lab_network(),                      # revealed in user's `docker network ls` when their group enables it (default on)
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
# Labs + CHP reach the hub by its compose SERVICE NAME - the stable Docker DNS alias compose
# registers on every net the hub joins. A peer on a shared net resolves it to the hub's IP on
# THAT net, so it is redeploy-proof (unlike socket.gethostname()'s ephemeral container id,
# which stranded running labs with "Name or service not known" on a hub redeploy - DEF-22).
# Discovered from the hub's own built-in com.docker.compose.service label (self-by-label, like
# resolve_self_compose_project) - no hand-stamped alias, no env.
#
# Advertise via hub_connect_ip (advertise-ONLY). Do NOT use hub_connect_url: it ALSO drives the
# API bind, and JupyterHub resolves its host FROM THE HUB - on the multi-homed hub that name
# lands on the gpuinfo IP, binding the API off the lab net so labs get connection refused (the
# regression). hub_ip stays 0.0.0.0 so the API listens on ALL the hub's interfaces (incl. the
# lab net) and the hub never resolves its own name to pick one.
_HUB_SERVICE_NAME = resolve_self_compose_service()
if _HUB_SERVICE_NAME:
    c.JupyterHub.hub_connect_ip = _HUB_SERVICE_NAME          # stable service-name DNS labs/CHP reach the hub by
else:
    # degrade, do not refuse boot: JupyterHub falls back to the container id - labs still reach
    # the hub this boot but a later hub redeploy (new id) can strand them (the DEF-22 failure).
    log.error("[networking] hub compose service name undiscoverable - falling back to the "
              "container id (NOT redeploy-proof); spawned labs may strand on a hub redeploy")
c.DockerSpawner.remove = True                                # auto-remove containers after stop (volumes persist)
c.DockerSpawner.debug = False                                # DockerSpawner debug logging
c.JupyterHub.hub_ip = "0.0.0.0"                              # listen on ALL interfaces incl. lab net; advertise via hub_connect_ip
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
# Selected by dotted-path string, exactly like the spawner - swap the line below (and add
# the matching c.<Authenticator>.* block) to use a different authenticator. The native flow
# (NativeAuth credential store + antd login/signup + first-admin bootstrap + admin-role
# promotion) is fully self-contained in DuoptimumNativeAuthenticator, so any other
# authenticator runs none of it - no conditionals here.
c.JupyterHub.authenticator_class = "duoptimum_hub_services.auth.DuoptimumNativeAuthenticator"
c.DuoptimumNativeAuthenticator.admin_username = JUPYTERHUB_ADMIN_USERNAME           # promoted to admin at login; bootstrap-window self-signup name
c.DuoptimumNativeAuthenticator.signup_enabled = bool(JUPYTERHUB_SIGNUP_ENABLED)     # operator self-registration switch; the authenticator re-opens it for the admin during bootstrap
# admin password is INITIAL-ONLY: read by the authenticator from os.environ['JUPYTERHUB_ADMIN_PASSWORD'],
# never set as a config trait (so the secret stays out of --show-config / trait_values / Settings)

# Future OAuth/OIDC (e.g. Keycloak) - `oauthenticator` ships in the image; swap the
# selection above for the stock GenericOAuthenticator. The native bootstrap above does NOT
# apply: set admin via c.Authenticator.admin_users (or an OAuth claim), and signup/approval
# is owned by the identity provider.
#   c.JupyterHub.authenticator_class = "generic-oauth"
#   c.GenericOAuthenticator.client_id = "jupyterhub"
#   c.GenericOAuthenticator.client_secret = "..."
#   c.GenericOAuthenticator.oauth_callback_url = "https://hub.example.com/hub/oauth_callback"
#   c.GenericOAuthenticator.authorize_url = "https://auth.example.com/realms/main/protocol/openid-connect/auth"
#   c.GenericOAuthenticator.token_url    = "https://auth.example.com/realms/main/protocol/openid-connect/token"
#   c.GenericOAuthenticator.userdata_url = "https://auth.example.com/realms/main/protocol/openid-connect/userinfo"
#   c.GenericOAuthenticator.username_claim = "preferred_username"
#   c.Authenticator.admin_users = {"<admin-username>"}

c.JupyterHub.template_paths = [
    duoptimum_hub_web.template_dir(),                                  # Duoptimum Hub portal: home.html = SPA shell, admin/token = redirect stubs (highest priority)
    "/srv/jupyterhub/templates/",                                    # custom Stellars templates (override priority)
    f"{os.path.dirname(nativeauthenticator.__file__)}/templates/",   # NativeAuthenticator signup/authorize templates
    f"{os.path.dirname(jupyterhub.__file__)}/templates",             # JupyterHub default templates (fallback)
]
c.NativeAuthenticator.open_signup = False                            # other users still require admin authorization
# enable_signup is a dynamic property on DuoptimumNativeAuthenticator: it re-evaluates
# signup_enabled + the bootstrap-pending state on each access, so the Sign Up link and
# /hub/signup form disappear the moment the admin row appears - no static
# c.NativeAuthenticator.enable_signup here (that would freeze at config-load). Admin-role
# promotion is the authenticator's run_post_auth_hook (was a loose c.Authenticator.post_auth_hook);
# the reasons we avoid allow_self_approval_for + eager admin_users live in auth.py.
c.Authenticator.allow_all = True                                     # all authorized users may login
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
c.DuoptimumHub.registered_handlers = registered_handlers()
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
