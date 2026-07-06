# Configuration file for JupyterHub
#
# All data (env vars, volumes, groups) is defined here. The duoptimum_hub_services
# package provides pure logic functions only - zero hardcoded data, zero
# env var reads at module level. Every parameter is passed explicitly.
#
# Sections:
#   1. Environment Variables   - operator settings via the config.settings loader
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
    configure_volume_cache,                 # one-time init: feeds canonical volume-name templates to the activity-monitor sizes cache
    get_services_and_roles,                 # builds JupyterHub services list (activity sampler)
    schedule_idle_culler,                   # in-hub idle culler (honours per-user session extensions)
    get_user_volume_name_templates,         # maps suffix -> full volume-name template (with {username} placeholder)
    get_user_volume_roles,                  # maps suffix -> hub.volume.role value (lab-home/lab-workspace/lab-cache)
    get_user_volume_suffixes,               # extracts ['home', 'workspace', 'cache'] from volumes dict
    load_merged_user_volumes,               # loads + merges platform-defaults YAML with operator overrides
    make_pre_spawn_hook,                    # factory returning async hook for group perms, favicon, icons
    make_post_stop_hook,                    # factory returning async post-stop hook: docker-proxy unregister + api-key release + stop event
    prepare_sent_notification_log,          # boot-time self-heal of the sent-notification history table
    register_events,                        # attaches SQLAlchemy listeners for user rename/delete sync
    resolve_host_status_provider,           # reads c.JupyterHub.spawner_class -> instantiates its declared host-status provider (home-screen CPU/MEM/GPU aggregate)
    schedule_startup_hydration,             # consolidated startup hydration: warms caches + image-update check + survivor favicon routes/policy, all deferred to the IOLoop
    # GPU/sidecar/branding orchestration (resolve_gpu_mode/vendor, ensure/stop sidecar,
    # configure_gpu_cache, gpu_summary_lines, is_wsl2, setup_branding) moved to
    # config/runtime.py::assemble_runtime.
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
from duoptimum_hub_services.config import (  # settings loader + c.* dict builders + boot runtime (GPU/sidecar/branding)
    load_settings, assemble_runtime, docker_spawner_env, template_vars, stellars_config, validator_payload,
)

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

# Operator-tunable settings are parsed once - with their defaults, types and
# transforms - in the tested config.settings loader (the single env-read site).
# See settings_dictionary.yml for per-variable documentation. Bound below to the
# historical JUPYTERHUB_* names the rest of this file references (behaviour-neutral:
# each binding == the old inline read, proven by test_settings_loader).
settings = load_settings()

JUPYTERHUB_SSL_ENABLED = settings.ssl_enabled
JUPYTERHUB_GPU_ENABLED = settings.gpu_enabled
JUPYTERHUB_SIGNUP_ENABLED = settings.signup_enabled
JUPYTERHUB_IDLE_CULLER_ENABLED = settings.idle_culler_enabled
JUPYTERHUB_IDLE_CULLER_TIMEOUT_MINUTES = settings.idle_culler_timeout_minutes
JUPYTERHUB_IDLE_CULLER_INTERVAL = settings.idle_culler_interval
JUPYTERHUB_IDLE_CULLER_MAX_AGE = settings.idle_culler_max_age
JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION_MINUTES = settings.idle_culler_max_extension_minutes
JUPYTERHUB_IDLE_CULLER_TIMEOUT = settings.idle_culler_timeout                # derived: seconds before cull
JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION = settings.idle_culler_max_extension    # derived: whole hours users can extend
ACTIVITYMON_SAMPLE_INTERVAL = settings.activitymon_sample_interval
JUPYTERHUB_HUB_DOCKER_API_TIMEOUT = settings.hub_docker_api_timeout
JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS = settings.lab_block_file_downloads
JUPYTERHUB_LAB_SUDO_ENABLE = settings.lab_sudo_enable
JUPYTERHUB_BASE_URL = settings.base_url
# Only the bindings still referenced by Section 2-4 remain; the rest now flow through
# settings.* inside the config.* builders (docker_spawner_env / validator_payload / runtime).
JUPYTERHUB_LAB_IMAGE = settings.lab_image
JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE = settings.lab_container_name_template
JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY = settings.label_container_role_key
JUPYTERHUB_LABEL_CONTAINER_ROLE_LAB = settings.label_container_role_lab
JUPYTERHUB_LABEL_VOLUME_ROLE_KEY = settings.label_volume_role_key
JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED = settings.label_volume_role_shared
JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY = settings.label_volume_role_docker_proxy
JUPYTERHUB_LABEL_VOLUME_DESCRIPTION = settings.label_volume_description
JUPYTERHUB_LABEL_VOLUME_OWNER_KEY = settings.label_volume_owner_key
JUPYTERHUB_ADMIN_USERNAME = settings.admin_username
JUPYTERHUB_BRANDING_FAVICON_URI = settings.branding_favicon_uri

# ── Runtime-discovered values (NOT env reads - stay here, not in the loader) ──
# Deployment NAMESPACE (compose project now; k8s namespace later). Discovered EXACT from
# the hub's own com.docker.compose.project label - no env, can't drift from the real volume
# prefix. Drives volume namespace + hub/sidecar/lab compose labels. Empty -> validator fails.
JUPYTERHUB_COMPOSE_PROJECT_NAME = (resolve_self_compose_project() or "").strip()
# Compose project for spawned lab/user containers - the com.docker.compose.project label they
# carry. {compose} is filled with the discovered hub project (so compose.yml can say
# "{compose}_labs"); empty = same project as the hub. HYBRID: reads its own env then applies
# the runtime-discovered project, so it stays here (the one config-level env read).
JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME = (
    os.environ.get("JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME", "").strip()
    .replace("{compose}", JUPYTERHUB_COMPOSE_PROJECT_NAME)
    or JUPYTERHUB_COMPOSE_PROJECT_NAME
)
# Shared volume the Groups UI offers as one-click /mnt/shared. Found by role among own mounts
# (rename-safe). Empty when absent - validator WARNS, quick-add hides (manual rows still work).
# Duplicate role -> raises. Uses the volume role-key/shared bindings above.
JUPYTERHUB_SHARED_VOLUME_NAME = resolve_self_mount_volume_by_label(
    JUPYTERHUB_LABEL_VOLUME_ROLE_KEY, JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED
) or ""


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


# Runtime detection + branding, run once at boot (see config/runtime.py::assemble_runtime):
# GPU vendor -> gpuinfo sidecar lifecycle -> gpu-cache -> GPU inventory -> branding assets.
# A verbatim move of the old inline block - same calls, same order, same side effects
# (self-starts the sidecar, registers the atexit teardown, copies branding). The produced
# values are bound back to the module names the rest of this file references.
runtime = assemble_runtime(settings, JUPYTERHUB_COMPOSE_PROJECT_NAME)
GPU_VENDOR = runtime.gpu_vendor
_gpuinfo_url = runtime.gpuinfo_url
_gpuinfo_sidecar_up = runtime.gpuinfo_sidecar_up
gpu_enabled = runtime.gpu_enabled
nvidia_detected = runtime.nvidia_detected
gpu_list = runtime.gpu_list
GPU_UUID_BY_INDEX = runtime.gpu_uuid_by_index
branding = runtime.branding


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

# Environment variables injected into every spawned JupyterLab container (built from
# settings + the two runtime values; see config/wiring.py::docker_spawner_env). The
# key set is load-bearing - RESERVED_ENV_VAR_NAMES below derives from it.
c.DockerSpawner.environment = docker_spawner_env(settings, nvidia_detected, resolve_lab_network())

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
# Values the Jinja2 templates + the portal shell (window.jhdata) read - see
# config/wiring.py::template_vars. Settings + runtime GPU/branding + the data/version
# values the config resolves (volume metadata, platform/hub versions, SPA entry chunk).
c.JupyterHub.template_vars = template_vars(
    settings, runtime,
    user_volume_suffixes=user_volume_suffixes,
    user_volume_name_templates=user_volume_name_templates,
    user_volumes=user_volumes_for_ui,
    stellars_version=os.environ.get('STELLARS_JUPYTERHUB_VERSION', 'dev'),
    server_version=jupyterhub.__version__,
    entry_js=duoptimum_hub_web.entry_assets()[0],
    entry_css=duoptimum_hub_web.entry_assets()[1],
)

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
# Handler-accessible config via self.settings['stellars_config'] - see
# config/wiring.py::stellars_config. system_volumes is merged in below (needs the
# late docker-proxy volume resolution).
c.JupyterHub.tornado_settings = {'stellars_config': stellars_config(
    settings, runtime,
    user_volume_suffixes=user_volume_suffixes,
    user_volume_name_templates=user_volume_name_templates,
    user_volume_roles=user_volume_roles,
    user_volumes=user_volumes_for_ui,
    host_status_provider=_host_status_provider,
    reserved_env_var_names=RESERVED_ENV_VAR_NAMES,
    reserved_env_var_prefixes=RESERVED_ENV_VAR_PREFIXES,
    shared_volume_name=JUPYTERHUB_SHARED_VOLUME_NAME,
    docker_spawner_volumes=DOCKER_SPAWNER_VOLUMES,
)}

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
validate_hub_config(validator_payload(
    settings,
    namespace=JUPYTERHUB_COMPOSE_PROJECT_NAME,
    lab_network_name=resolve_lab_network(),
    gpuinfo_network_name=resolve_gpuinfo_network(),
    shared_volume_name=JUPYTERHUB_SHARED_VOLUME_NAME,
    docker_proxy_socket_dir=JUPYTERHUB_DOCKER_PROXY_SOCKET_DIR,
    docker_proxy_sockets_volume=JUPYTERHUB_DOCKER_PROXY_SOCKETS_VOLUME,
    user_compose_project_template=JUPYTERHUB_DOCKER_PROXY_USER_COMPOSE_PROJECT_TEMPLATE,
)).raise_if_errors(log=log)

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
