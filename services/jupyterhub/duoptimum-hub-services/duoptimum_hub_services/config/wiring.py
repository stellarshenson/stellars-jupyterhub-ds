"""Pure builders for the config's larger c.* dicts (config simplification Batch 3).

Each builder takes the settings object + the runtime values it needs and returns the
exact dict the config used to assemble inline, so the config file reads like
configuration. Builders are pure (no env reads, no side effects) and unit-tested
against the shipped shape - behaviour-neutral; the boot-level --show-config
confirmation rides the functional suite on a rebuilt image.
"""


def docker_spawner_env(settings, nvidia_detected, lab_network):
    """Env injected into every spawned JupyterLab container.

    Literals (MLflow/TensorBoard wiring) + operator settings + the two runtime values
    (GPU-detection flag, resolved hub<->lab network). The key SET is load-bearing:
    RESERVED_ENV_VAR_NAMES derives from it, so the globally-injected names never drift.
    """
    return {
        'TF_CPP_MIN_LOG_LEVEL': settings.tf_cpp_min_log_level,          # suppress TF C++ logging
        'TENSORBOARD_LOGDIR': '/tmp/tensorboard',                       # TensorBoard log directory
        'MLFLOW_TRACKING_URI': 'http://localhost:5000',                 # MLflow tracking server URL
        'MLFLOW_PORT': 5000,                                            # MLflow server port
        'MLFLOW_HOST': '0.0.0.0',                                       # MLflow bind address
        'MLFLOW_WORKERS': 1,                                            # MLflow worker count
        'ENABLE_SERVICE_MLFLOW': settings.lab_service_mlflow,           # toggle MLflow in container startup
        'ENABLE_SERVICE_RESOURCES_MONITOR': settings.lab_service_resources_monitor,  # toggle resource monitor widget
        'ENABLE_SERVICE_TENSORBOARD': settings.lab_service_tensorboard,  # toggle TensorBoard in container startup
        'NVIDIA_DETECTED': nvidia_detected,                             # GPU hardware availability flag (informational)
        'JUPYTERLAB_AUX_SCRIPTS_PATH': settings.aux_scripts_path,       # admin startup scripts path
        'JUPYTERLAB_AUX_MENU_PATH': settings.aux_menu_path,             # admin-managed custom menu definitions
        'JUPYTERLAB_TIMEZONE': settings.timezone,                       # IANA timezone for JupyterLab extensions
        'JUPYTERLAB_SYSTEM_NAME': settings.branding_lab_name,           # lab header/welcome/MOTD display name
        'JUPYTERHUB_NETWORK_NAME': lab_network,                         # Docker network connecting hub + user containers
    }


def template_vars(settings, runtime, *, user_volume_suffixes, user_volume_name_templates,
                  user_volumes, stellars_version, server_version, entry_js, entry_css):
    """c.JupyterHub.template_vars - values the Jinja2 templates + the portal shell
    (window.jhdata) read. Operator settings + runtime GPU/branding + the data/version
    kwargs the config resolves (volume metadata, platform/hub versions, SPA entry chunk)."""
    return {
        'user_volume_suffixes': user_volume_suffixes,            # ['home','workspace','cache'] for volume reset UI
        'user_volume_name_templates': user_volume_name_templates,  # suffix -> volume-name template for UI labels
        'user_volumes': user_volumes,                            # ordered {suffix, name_template, description} for the reset UI
        'stellars_version': stellars_version,                    # platform version shown in UI
        'server_version': server_version,                        # JupyterHub version shown in UI
        'idle_culler_enabled': settings.idle_culler_enabled,     # toggle culler UI elements
        'idle_culler_timeout': settings.idle_culler_timeout,     # timeout display in session panel
        'idle_culler_max_extension': settings.idle_culler_max_extension,  # max extension hours display
        'activitymon_target_hours': settings.activitymon_target_hours,    # activity scoring window display
        'activitymon_sample_interval': settings.activitymon_sample_interval,  # sampling interval display
        'container_max_extra_space_mb': settings.lab_container_max_extra_space_gb * 1024,  # container size warning threshold (MB)
        'volume_max_total_size_mb': settings.lab_volume_max_total_size_gb * 1024,          # volume size warning threshold (MB)
        'memory_max_usage_mb': settings.lab_memory_max_usage_mb,                           # per-user memory warning threshold (MB)
        'favicon_uri': runtime.branding['favicon_uri'],          # external favicon URL (empty = static_url default)
        'branding_stage': runtime.branding['stage'],             # environment-stage badge text for the portal header
        'duoptimum_entry_js': entry_js,                          # SPA entry chunk (hashed) for the overridden login/signup templates
        'duoptimum_entry_css': entry_css,
        'gpu_enabled': bool(runtime.gpu_enabled),                # authoritative "platform has GPU" flag -> window.jhdata
        'admin_user': settings.admin_username or '',             # platform admin username -> SPA admin recognition
        'hub_name': settings.branding_hub_name,                  # hub display name -> window.jhdata.hub_name
    }


def stellars_config(settings, runtime, *, user_volume_suffixes, user_volume_name_templates,
                    user_volume_roles, user_volumes, host_status_provider,
                    reserved_env_var_names, reserved_env_var_prefixes, shared_volume_name,
                    docker_spawner_volumes):
    """The handler-accessible config exposed via self.settings['stellars_config'].
    Settings + runtime GPU/host + the data/computed kwargs the config resolves (volume
    metadata, reserved env names, host-status provider, shared volume). The config
    merges system_volumes into the returned dict afterwards (needs late volume resolution)."""
    return {
        'user_volume_suffixes': user_volume_suffixes,        # ManageVolumesHandler validation
        'user_volume_name_templates': user_volume_name_templates,  # on-disk volume names
        'user_volume_roles': user_volume_roles,              # suffix -> hub.volume.role (portal tags system volumes)
        'volume_role_label_key': settings.label_volume_role_key,           # handlers read a volume's role off this label key
        'volume_description_label_key': settings.label_volume_description,  # handlers read a volume's description off this label key
        'user_volumes': user_volumes,                        # ManageVolumesHandler GET description attach
        'idle_culler_enabled': settings.idle_culler_enabled,  # SessionInfoHandler, ActivityDataHandler
        'idle_culler_timeout': settings.idle_culler_timeout,  # SessionInfoHandler, ExtendSessionHandler
        'idle_culler_max_extension': settings.idle_culler_max_extension,  # ExtendSessionHandler limits
        'gpu_list': runtime.gpu_list,                        # host GPUs (GroupsDataHandler, ActivityDataHandler)
        'gpu_available': bool(runtime.gpu_enabled),          # hardware-present gate for resolve_policies
        'gpu_isolation_enforced': runtime.gpu_isolation_enforced,  # False on WSL2 -> portal advisory note
        'host_status_provider': host_status_provider,        # ActivityDataHandler host CPU/MEM/GPU aggregate
        'container_max_extra_space_mb': settings.lab_container_max_extra_space_gb * 1024,  # container size warning (MB)
        'volume_max_total_size_mb': settings.lab_volume_max_total_size_gb * 1024,          # volume size warning (MB)
        'memory_max_usage_mb': settings.lab_memory_max_usage_mb,                           # per-user memory warning (MB)
        'reserved_env_var_names': reserved_env_var_names,    # names groups cannot override
        'reserved_env_var_prefixes': reserved_env_var_prefixes,  # prefixes reserved for JupyterHub/platform
        'shared_volume_name': shared_volume_name,            # role=shared volume for the groups volume-mounts UI
        'lab_image': settings.lab_image,                     # image every lab spawns from (Lab Container page)
        'lab_volumes': [                                     # standard per-user volumes mounted into every lab
            {'suffix': v['suffix'], 'mount': docker_spawner_volumes.get(v['name_template'], ''),
             'description': v['description'], 'role': v['role']}
            for v in user_volumes
        ],
    }


def pre_spawn_kwargs(settings, runtime, *, reserved_env_var_names, reserved_env_var_prefixes,
                     lab_compose_project, docker_proxy_socket_dir, docker_proxy_volume_name,
                     user_compose_project_template, lab_network, shared_volume_name,
                     user_volume_label_templates):
    """Kwargs for make_pre_spawn_hook(**...). Settings + runtime GPU/branding + the
    reserved-env / docker-proxy / compose / volume-template values the config resolves.
    Keys match make_pre_spawn_hook's parameter names exactly."""
    return {
        'branding': runtime.branding,                        # icon static names + URLs from setup_branding()
        'favicon_uri': settings.branding_favicon_uri,        # non-empty activates the favicon.ico CHP route
        'favicon_busy_target': runtime.branding['favicon_busy_target'],  # non-empty activates the favicon-busy CHP route
        'gpu_available': bool(runtime.gpu_enabled),          # hardware present - required for per-group GPU grant
        'gpu_uuid_by_index': runtime.gpu_uuid_by_index,      # index->UUID for CUDA_VISIBLE_DEVICES
        'gpu_vendor': runtime.gpu_vendor,                    # GPU vendor provider threaded to the GPU policy
        'reserved_env_var_names': reserved_env_var_names,    # names groups cannot override
        'reserved_env_var_prefixes': reserved_env_var_prefixes,  # prefixes reserved for JupyterHub/platform
        'compose_project': lab_compose_project,              # compose project label on spawned labs
        'container_role_label_key': settings.label_container_role_key,   # hub.container.role key stamped on the lab
        'container_role_label_value': settings.label_container_role_lab,  # role value 'lab'
        'docker_proxy_socket_dir': docker_proxy_socket_dir,  # per-user socket path inside hub (named volume)
        'docker_proxy_volume_name': docker_proxy_volume_name,  # named docker volume subpath-mounted into each lab
        'user_compose_project_template': user_compose_project_template,  # per-user when a docker-limited group enables it
        'hub_network_name': lab_network,                     # shown in the user's docker network ls when enabled
        'block_file_downloads': settings.lab_block_file_downloads,  # master switch for per-user download-block routes
        'lab_sudo_enable_default': settings.lab_sudo_enable,  # default JUPYTERLAB_SUDO_ENABLE when no group configures sudo
        'api_keys_reconcile_interval': settings.idle_culler_interval,  # api-keys-pool reconcile cadence (reuses cull interval)
        'shared_volume_name': shared_volume_name,            # role=shared volume the group standard-shared mount resolves to
        'volume_role_label_key': settings.label_volume_role_key,  # hub.volume.role key stamped per-user at spawn
        'volume_owner_label_key': settings.label_volume_owner_key,  # hub.volume.owner key (value = username)
        'volume_description_label_key': settings.label_volume_description,  # hub.volume.description key
        'user_volume_label_templates': user_volume_label_templates,  # name-template -> {role, description} for pre-create
    }


def validator_payload(settings, *, namespace, lab_network_name, gpuinfo_network_name,
                      shared_volume_name, docker_proxy_socket_dir, docker_proxy_sockets_volume,
                      user_compose_project_template):
    """The dict fed once to validate_hub_config().raise_if_errors(). Most keys are
    operator settings; the 7 keyword args are runtime-discovered/late values (compose
    project, resolved networks, role-resolved volumes, docker-proxy socket dir/volume,
    per-user compose template). No downstream consumer - built, validated, discarded."""
    return {
        "admin": settings.admin_username,
        "lab_image": settings.lab_image,
        "namespace": namespace,
        "lab_network_name": lab_network_name,
        "network_role_label_key": settings.label_network_role_key,
        "volume_role_label_key": settings.label_volume_role_key,
        "container_role_label_key": settings.label_container_role_key,
        "lab_network_role_label": settings.label_network_role_lab,
        "gpuinfo_network_role_label": settings.label_network_role_gpuinfo,
        "shared_volume_role_label": settings.label_volume_role_shared,
        "docker_proxy_volume_role_label": settings.label_volume_role_docker_proxy,
        "gpuinfo_container_role_label": settings.label_container_role_gpuinfo,
        "lab_container_role_label": settings.label_container_role_lab,
        "volume_description_label_key": settings.label_volume_description,
        "volume_owner_label_key": settings.label_volume_owner_key,
        "container_description_label_key": settings.label_container_description,
        "docker_proxy_owner_label_key": settings.label_docker_proxy_owner_key,
        "docker_proxy_owner_label_value": settings.label_docker_proxy_owner_value,
        "lab_container_name_template": settings.lab_container_name_template,
        "gpuinfo_nvidia_image": settings.gpuinfo_nvidia_image,
        "gpuinfo_nvidia_container_name": settings.gpuinfo_nvidia_container_name,
        "gpuinfo_nvidia_url": settings.gpuinfo_nvidia_url,
        "docker_proxy_socket_dir": docker_proxy_socket_dir,
        "docker_proxy_sockets_volume": docker_proxy_sockets_volume,
        "user_compose_project_template": user_compose_project_template,
        # resolved/optional - drive warnings, never block boot
        "gpuinfo_network_name": gpuinfo_network_name,
        "shared_volume_name": shared_volume_name,
        "branding_logo_uri": settings.branding_logo_uri,
        "branding_favicon_uri": settings.branding_favicon_uri,
        "branding_favicon_busy_uri": settings.branding_favicon_busy_uri,
        "branding_lab_main_icon_uri": settings.branding_lab_main_icon_uri,
        "branding_lab_splash_uri": settings.branding_lab_splash_icon_uri,
    }
