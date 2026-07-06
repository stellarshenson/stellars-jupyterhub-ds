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
