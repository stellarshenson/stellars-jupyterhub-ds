"""Operator-tunable settings, loaded once from the environment.

`load_settings()` is the SINGLE module-level env-read site for the config file's
operator-tunable values - it replaces the ~140-line "Section 1" env block in
jupyterhub_config.py. Every field's default, type and transform (.strip() /
.strip().lower() / int / float) is byte-identical to the original inline reads, so
the loaded object is behaviour-neutral (proven by test_settings_loader, which
re-runs each original expression and asserts equality).

NOT here (deliberately):
- JUPYTERHUB_ADMIN_PASSWORD - never a settings field; stays an os.environ read
  inside DuoptimumNativeAuthenticator.__init__ so the secret never reaches
  --show-config / trait_values() / the Settings page.
- Runtime-discovered values (compose project, shared/docker-proxy volumes, GPU
  detection, branding, network resolution) - these are not env reads; they run in
  the config/runtime layer and feed the same consumers as before.

See settings_dictionary.yml for the operator-facing documentation of each variable.
"""

import os
from dataclasses import dataclass

from ..host import resolve_memory_quota_mb


@dataclass(frozen=True)
class Settings:
    # ── Core platform toggles (0=disabled, 1=enabled) ──
    ssl_enabled: int
    gpu_enabled: int
    lab_service_mlflow: int
    lab_service_resources_monitor: int
    lab_service_tensorboard: int
    signup_enabled: int

    # ── Idle culler ──
    idle_culler_enabled: int
    idle_culler_timeout_minutes: int
    idle_culler_interval: int
    idle_culler_max_age: int
    idle_culler_max_extension_minutes: int
    # derived (units the culler service + handlers / extend UI actually consume)
    idle_culler_timeout: int              # seconds before cull
    idle_culler_max_extension: int        # whole hours users can extend

    # ── Activity monitor ──
    activitymon_target_hours: int
    activitymon_sample_interval: int

    # ── Docker + resource thresholds ──
    hub_docker_api_timeout: int
    lab_container_max_extra_space_gb: int
    lab_volume_max_total_size_gb: int
    lab_memory_max_usage_fraction: float
    lab_memory_max_usage_mb: int          # derived: host-RAM fraction -> MB
    lab_block_file_downloads: int
    lab_sudo_enable: int
    lab_user_env_enable: int
    tf_cpp_min_log_level: int

    # ── Misc ──
    timezone: str
    base_url: "str | None"                # None or / for root (no default -> None)

    # ── Network role labels (baked ENV; empty -> validator fails) ──
    label_network_role_key: str
    label_network_role_lab: str
    label_network_role_gpuinfo: str

    # ── Images + container/name templates ──
    lab_image: str
    lab_container_name_template: str
    gpuinfo_nvidia_container_name: str
    gpuinfo_nvidia_url: str
    gpuinfo_nvidia_image: str

    # ── Container role labels ──
    label_container_role_key: str
    label_container_role_gpuinfo: str
    label_container_role_lab: str

    # ── Volume role / owner / description labels ──
    label_volume_role_key: str
    label_volume_role_shared: str
    label_volume_role_docker_proxy: str
    label_volume_description: str
    label_volume_owner_key: str
    label_container_description: str
    label_docker_proxy_owner_key: str
    label_docker_proxy_owner_value: str

    # ── Auth ──
    admin_username: str                   # normalized .strip().lower()

    # ── Branding ──
    branding_logo_uri: str
    branding_favicon_uri: str
    branding_favicon_busy_uri: str
    branding_lab_main_icon_uri: str
    branding_lab_splash_icon_uri: str
    branding_stage: str
    branding_hub_name: str
    branding_lab_name: str

    # ── User environment passthrough ──
    aux_scripts_path: str
    aux_menu_path: str


def load_settings():
    """Read the operator-tunable settings from the environment, once.

    Byte-for-byte the same reads/defaults/transforms that lived inline in
    jupyterhub_config.py Section 1 - do not change a default here without changing
    settings_dictionary.yml (the operator-facing doc) too.
    """
    e = os.environ.get

    idle_culler_timeout_minutes = int(e("JUPYTERHUB_IDLE_CULLER_TIMEOUT_MINUTES", 1440))
    idle_culler_max_extension_minutes = int(e("JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION_MINUTES", 1440))
    lab_memory_max_usage_fraction = float(e("JUPYTERHUB_LAB_MEMORY_MAX_USAGE_FRACTION", 0.25))

    return Settings(
        ssl_enabled=int(e("JUPYTERHUB_SSL_ENABLED", 1)),
        gpu_enabled=int(e("JUPYTERHUB_GPU_ENABLED", 1)),
        lab_service_mlflow=int(e("JUPYTERHUB_LAB_SERVICE_MLFLOW", 1)),
        lab_service_resources_monitor=int(e("JUPYTERHUB_LAB_SERVICE_RESOURCES_MONITOR", 1)),
        lab_service_tensorboard=int(e("JUPYTERHUB_LAB_SERVICE_TENSORBOARD", 1)),
        signup_enabled=int(e("JUPYTERHUB_SIGNUP_ENABLED", 1)),

        idle_culler_enabled=int(e("JUPYTERHUB_IDLE_CULLER_ENABLED", 0)),
        idle_culler_timeout_minutes=idle_culler_timeout_minutes,
        idle_culler_interval=int(e("JUPYTERHUB_IDLE_CULLER_INTERVAL", 600)),
        idle_culler_max_age=int(e("JUPYTERHUB_IDLE_CULLER_MAX_AGE", 0)),
        idle_culler_max_extension_minutes=idle_culler_max_extension_minutes,
        idle_culler_timeout=idle_culler_timeout_minutes * 60,
        idle_culler_max_extension=idle_culler_max_extension_minutes // 60,

        activitymon_target_hours=int(e("JUPYTERHUB_ACTIVITYMON_TARGET_HOURS", 8)),
        activitymon_sample_interval=int(e("JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL", 600)),

        hub_docker_api_timeout=int(e("JUPYTERHUB_HUB_DOCKER_API_TIMEOUT", 360)),
        lab_container_max_extra_space_gb=int(e("JUPYTERHUB_LAB_CONTAINER_MAX_EXTRA_SPACE_GB", 10)),
        lab_volume_max_total_size_gb=int(e("JUPYTERHUB_LAB_VOLUME_MAX_TOTAL_SIZE_GB", 50)),
        lab_memory_max_usage_fraction=lab_memory_max_usage_fraction,
        lab_memory_max_usage_mb=resolve_memory_quota_mb(lab_memory_max_usage_fraction),
        lab_block_file_downloads=int(e("JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS", 0)),
        lab_sudo_enable=int(e("JUPYTERHUB_LAB_SUDO_ENABLE", 1)),
        lab_user_env_enable=int(e("JUPYTERHUB_LAB_USER_ENV_ENABLE", 1)),
        tf_cpp_min_log_level=int(e("TF_CPP_MIN_LOG_LEVEL", 3)),

        timezone=e("JUPYTERHUB_TIMEZONE", "Etc/UTC"),
        base_url=e("JUPYTERHUB_BASE_URL"),

        label_network_role_key=e("JUPYTERHUB_LABEL_NETWORK_ROLE_KEY", "").strip(),
        label_network_role_lab=e("JUPYTERHUB_LABEL_NETWORK_ROLE_LAB", "").strip(),
        label_network_role_gpuinfo=e("JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO", "").strip(),

        lab_image=e("JUPYTERHUB_LAB_IMAGE", "").strip(),
        lab_container_name_template=e("JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE", "").strip(),
        gpuinfo_nvidia_container_name=e("JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME", ""),
        gpuinfo_nvidia_url=e("JUPYTERHUB_GPUINFO_NVIDIA_URL", ""),
        gpuinfo_nvidia_image=e("JUPYTERHUB_GPUINFO_NVIDIA_IMAGE", "").strip(),

        label_container_role_key=e("JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY", "").strip(),
        label_container_role_gpuinfo=e("JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO", "").strip(),
        label_container_role_lab=e("JUPYTERHUB_LABEL_CONTAINER_ROLE_LAB", "").strip(),

        label_volume_role_key=e("JUPYTERHUB_LABEL_VOLUME_ROLE_KEY", "").strip(),
        label_volume_role_shared=e("JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED", "").strip(),
        label_volume_role_docker_proxy=e("JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY", "").strip(),
        label_volume_description=e("JUPYTERHUB_LABEL_VOLUME_DESCRIPTION", "").strip(),
        label_volume_owner_key=e("JUPYTERHUB_LABEL_VOLUME_OWNER_KEY", "").strip(),
        label_container_description=e("JUPYTERHUB_LABEL_CONTAINER_DESCRIPTION", "").strip(),
        label_docker_proxy_owner_key=e("JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_KEY", "").strip(),
        label_docker_proxy_owner_value=e("JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_VALUE", "").strip(),

        admin_username=e("JUPYTERHUB_ADMIN_USERNAME", "").strip().lower(),

        branding_logo_uri=e("JUPYTERHUB_BRANDING_LOGO_URI", ""),
        branding_favicon_uri=e("JUPYTERHUB_BRANDING_FAVICON_URI", ""),
        branding_favicon_busy_uri=e("JUPYTERHUB_BRANDING_FAVICON_BUSY_URI", ""),
        branding_lab_main_icon_uri=e("JUPYTERHUB_BRANDING_LAB_MAIN_ICON_URI", ""),
        branding_lab_splash_icon_uri=e("JUPYTERHUB_BRANDING_LAB_SPLASH_ICON_URI", ""),
        branding_stage=e("JUPYTERHUB_BRANDING_STAGE", ""),
        branding_hub_name=e("JUPYTERHUB_BRANDING_HUB_NAME", "DuOptimum Hub"),
        branding_lab_name=e("JUPYTERHUB_BRANDING_LAB_NAME", ""),

        aux_scripts_path=e("JUPYTERLAB_AUX_SCRIPTS_PATH", ""),
        aux_menu_path=e("JUPYTERLAB_AUX_MENU_PATH", ""),
    )
