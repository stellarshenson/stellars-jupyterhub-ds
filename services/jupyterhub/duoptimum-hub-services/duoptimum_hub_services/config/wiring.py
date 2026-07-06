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
