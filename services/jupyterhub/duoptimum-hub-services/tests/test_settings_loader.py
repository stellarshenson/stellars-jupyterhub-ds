"""Behaviour-neutrality proof for the settings loader (config simplification Batch 2).

load_settings() replaces the inline "Section 1" env block in jupyterhub_config.py.
The config file cannot be unit-booted, so `_original(env)` below re-computes every
field using the EXACT original inline expression and asserts load_settings() matches
- for an empty env (all defaults) and for a sample env carrying whitespace + mixed
case (so a dropped .strip()/.lower() is caught). If this passes, the loaded object
is byte-identical to the old inline reads; only the downstream c.* wiring is left to
the operator's --show-config on a rebuilt image.
"""

import dataclasses
import os

import pytest

from duoptimum_hub_services.config.settings import Settings, load_settings
from duoptimum_hub_services.host import resolve_memory_quota_mb


def _original(env):
    """Every field as jupyterhub_config.py computed it inline (source of truth)."""
    g = env.get
    tmin = int(g("JUPYTERHUB_IDLE_CULLER_TIMEOUT_MINUTES", 1440))
    xmin = int(g("JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION_MINUTES", 1440))
    frac = float(g("JUPYTERHUB_LAB_MEMORY_MAX_USAGE_FRACTION", 0.25))
    return {
        "ssl_enabled": int(g("JUPYTERHUB_SSL_ENABLED", 1)),
        "gpu_enabled": int(g("JUPYTERHUB_GPU_ENABLED", 1)),
        "lab_service_mlflow": int(g("JUPYTERHUB_LAB_SERVICE_MLFLOW", 1)),
        "lab_service_resources_monitor": int(g("JUPYTERHUB_LAB_SERVICE_RESOURCES_MONITOR", 1)),
        "lab_service_tensorboard": int(g("JUPYTERHUB_LAB_SERVICE_TENSORBOARD", 1)),
        "signup_enabled": int(g("JUPYTERHUB_SIGNUP_ENABLED", 1)),
        "idle_culler_enabled": int(g("JUPYTERHUB_IDLE_CULLER_ENABLED", 0)),
        "idle_culler_timeout_minutes": tmin,
        "idle_culler_interval": int(g("JUPYTERHUB_IDLE_CULLER_INTERVAL", 600)),
        "idle_culler_max_age": int(g("JUPYTERHUB_IDLE_CULLER_MAX_AGE", 0)),
        "idle_culler_max_extension_minutes": xmin,
        "idle_culler_timeout": tmin * 60,
        "idle_culler_max_extension": xmin // 60,
        "activitymon_target_hours": int(g("JUPYTERHUB_ACTIVITYMON_TARGET_HOURS", 8)),
        "activitymon_sample_interval": int(g("JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL", 600)),
        "hub_docker_api_timeout": int(g("JUPYTERHUB_HUB_DOCKER_API_TIMEOUT", 360)),
        "lab_container_max_extra_space_gb": int(g("JUPYTERHUB_LAB_CONTAINER_MAX_EXTRA_SPACE_GB", 10)),
        "lab_volume_max_total_size_gb": int(g("JUPYTERHUB_LAB_VOLUME_MAX_TOTAL_SIZE_GB", 50)),
        "lab_memory_max_usage_fraction": frac,
        "lab_memory_max_usage_mb": resolve_memory_quota_mb(frac),
        "lab_block_file_downloads": int(g("JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS", 0)),
        "lab_sudo_enable": int(g("JUPYTERHUB_LAB_SUDO_ENABLE", 1)),
        "tf_cpp_min_log_level": int(g("TF_CPP_MIN_LOG_LEVEL", 3)),
        "timezone": g("JUPYTERHUB_TIMEZONE", "Etc/UTC"),
        "base_url": g("JUPYTERHUB_BASE_URL"),
        "label_network_role_key": g("JUPYTERHUB_LABEL_NETWORK_ROLE_KEY", "").strip(),
        "label_network_role_lab": g("JUPYTERHUB_LABEL_NETWORK_ROLE_LAB", "").strip(),
        "label_network_role_gpuinfo": g("JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO", "").strip(),
        "lab_image": g("JUPYTERHUB_LAB_IMAGE", "").strip(),
        "lab_container_name_template": g("JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE", "").strip(),
        "gpuinfo_nvidia_container_name": g("JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME", ""),
        "gpuinfo_nvidia_url": g("JUPYTERHUB_GPUINFO_NVIDIA_URL", ""),
        "gpuinfo_nvidia_image": g("JUPYTERHUB_GPUINFO_NVIDIA_IMAGE", "").strip(),
        "label_container_role_key": g("JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY", "").strip(),
        "label_container_role_gpuinfo": g("JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO", "").strip(),
        "label_container_role_lab": g("JUPYTERHUB_LABEL_CONTAINER_ROLE_LAB", "").strip(),
        "label_volume_role_key": g("JUPYTERHUB_LABEL_VOLUME_ROLE_KEY", "").strip(),
        "label_volume_role_shared": g("JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED", "").strip(),
        "label_volume_role_docker_proxy": g("JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY", "").strip(),
        "label_volume_description": g("JUPYTERHUB_LABEL_VOLUME_DESCRIPTION", "").strip(),
        "label_volume_owner_key": g("JUPYTERHUB_LABEL_VOLUME_OWNER_KEY", "").strip(),
        "label_container_description": g("JUPYTERHUB_LABEL_CONTAINER_DESCRIPTION", "").strip(),
        "label_docker_proxy_owner_key": g("JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_KEY", "").strip(),
        "label_docker_proxy_owner_value": g("JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_VALUE", "").strip(),
        "admin_username": g("JUPYTERHUB_ADMIN_USERNAME", "").strip().lower(),
        "branding_logo_uri": g("JUPYTERHUB_BRANDING_LOGO_URI", ""),
        "branding_favicon_uri": g("JUPYTERHUB_BRANDING_FAVICON_URI", ""),
        "branding_favicon_busy_uri": g("JUPYTERHUB_BRANDING_FAVICON_BUSY_URI", ""),
        "branding_lab_main_icon_uri": g("JUPYTERHUB_BRANDING_LAB_MAIN_ICON_URI", ""),
        "branding_lab_splash_icon_uri": g("JUPYTERHUB_BRANDING_LAB_SPLASH_ICON_URI", ""),
        "branding_stage": g("JUPYTERHUB_BRANDING_STAGE", ""),
        "branding_hub_name": g("JUPYTERHUB_BRANDING_HUB_NAME", "DuOptimum Hub"),
        "branding_lab_name": g("JUPYTERHUB_BRANDING_LAB_NAME", ""),
        "aux_scripts_path": g("JUPYTERLAB_AUX_SCRIPTS_PATH", ""),
        "aux_menu_path": g("JUPYTERLAB_AUX_MENU_PATH", ""),
    }


def _assert_matches(monkeypatch, env):
    monkeypatch.setattr(os, "environ", dict(env))
    got = load_settings()
    expected = _original(env)
    # every declared field is covered by the source-of-truth map (no field escapes the check)
    field_names = {f.name for f in dataclasses.fields(Settings)}
    assert field_names == set(expected), field_names ^ set(expected)
    for name, want in expected.items():
        assert getattr(got, name) == want, f"{name}: got {getattr(got, name)!r} != {want!r}"


def test_matches_original_empty_env(monkeypatch):
    # all defaults
    _assert_matches(monkeypatch, {})


def test_matches_original_sample_env(monkeypatch):
    # distinct values + leading/trailing whitespace (proves .strip()) + UPPER admin (proves .lower())
    env = {
        "JUPYTERHUB_SSL_ENABLED": "0",
        "JUPYTERHUB_GPU_ENABLED": "0",
        "JUPYTERHUB_LAB_SERVICE_MLFLOW": "0",
        "JUPYTERHUB_LAB_SERVICE_RESOURCES_MONITOR": "0",
        "JUPYTERHUB_LAB_SERVICE_TENSORBOARD": "0",
        "JUPYTERHUB_SIGNUP_ENABLED": "0",
        "JUPYTERHUB_IDLE_CULLER_ENABLED": "1",
        "JUPYTERHUB_IDLE_CULLER_TIMEOUT_MINUTES": "120",
        "JUPYTERHUB_IDLE_CULLER_INTERVAL": "300",
        "JUPYTERHUB_IDLE_CULLER_MAX_AGE": "99",
        "JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION_MINUTES": "180",
        "JUPYTERHUB_ACTIVITYMON_TARGET_HOURS": "6",
        "JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL": "900",
        "JUPYTERHUB_HUB_DOCKER_API_TIMEOUT": "120",
        "JUPYTERHUB_LAB_CONTAINER_MAX_EXTRA_SPACE_GB": "5",
        "JUPYTERHUB_LAB_VOLUME_MAX_TOTAL_SIZE_GB": "25",
        "JUPYTERHUB_LAB_MEMORY_MAX_USAGE_FRACTION": "0.5",
        "JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS": "1",
        "JUPYTERHUB_LAB_SUDO_ENABLE": "0",
        "TF_CPP_MIN_LOG_LEVEL": "1",
        "JUPYTERHUB_TIMEZONE": "Europe/Warsaw",
        "JUPYTERHUB_BASE_URL": "/jupyterhub",
        "JUPYTERHUB_LABEL_NETWORK_ROLE_KEY": "  duoptimum-hub.network.role  ",
        "JUPYTERHUB_LABEL_NETWORK_ROLE_LAB": " lab ",
        "JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO": " gpuinfo ",
        "JUPYTERHUB_LAB_IMAGE": "  stellars/lab:latest  ",
        "JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE": " jupyterlab-{username} ",
        "JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME": "  gpuinfo-nvidia  ",
        "JUPYTERHUB_GPUINFO_NVIDIA_URL": " http://{hostname}:8000 ",
        "JUPYTERHUB_GPUINFO_NVIDIA_IMAGE": "  stellars/gpuinfo:latest  ",
        "JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY": " duoptimum-hub.container.role ",
        "JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO": " gpuinfo ",
        "JUPYTERHUB_LABEL_CONTAINER_ROLE_LAB": " lab ",
        "JUPYTERHUB_LABEL_VOLUME_ROLE_KEY": " duoptimum-hub.volume.role ",
        "JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED": " shared ",
        "JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY": " docker-proxy ",
        "JUPYTERHUB_LABEL_VOLUME_DESCRIPTION": " duoptimum-hub.volume.description ",
        "JUPYTERHUB_LABEL_VOLUME_OWNER_KEY": " duoptimum-hub.volume.owner ",
        "JUPYTERHUB_LABEL_CONTAINER_DESCRIPTION": " duoptimum-hub.container.description ",
        "JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_KEY": " duoptimum-hub.docker-proxy.owner ",
        "JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_VALUE": " hub ",
        "JUPYTERHUB_ADMIN_USERNAME": "  ADMIN  ",
        "JUPYTERHUB_BRANDING_LOGO_URI": "file:///logo.png",
        "JUPYTERHUB_BRANDING_FAVICON_URI": "file:///fav.ico",
        "JUPYTERHUB_BRANDING_FAVICON_BUSY_URI": "file:///busy.ico",
        "JUPYTERHUB_BRANDING_LAB_MAIN_ICON_URI": "file:///main.svg",
        "JUPYTERHUB_BRANDING_LAB_SPLASH_ICON_URI": "file:///splash.svg",
        "JUPYTERHUB_BRANDING_STAGE": "DEV",
        "JUPYTERHUB_BRANDING_HUB_NAME": "Test Hub",
        "JUPYTERHUB_BRANDING_LAB_NAME": "Test Lab",
        "JUPYTERLAB_AUX_SCRIPTS_PATH": "/mnt/shared/scripts",
        "JUPYTERLAB_AUX_MENU_PATH": "/mnt/shared/menu",
    }
    _assert_matches(monkeypatch, env)


def test_key_defaults_explicit(monkeypatch):
    # independent value assertions (guards against a wrong default in BOTH maps)
    monkeypatch.setattr(os, "environ", {})
    s = load_settings()
    assert s.ssl_enabled == 1
    assert s.idle_culler_enabled == 0
    assert s.idle_culler_timeout == 1440 * 60
    assert s.idle_culler_max_extension == 24
    assert s.timezone == "Etc/UTC"
    assert s.base_url is None
    assert s.branding_hub_name == "DuOptimum Hub"
    assert s.admin_username == ""


def test_admin_username_lowercased(monkeypatch):
    monkeypatch.setattr(os, "environ", {"JUPYTERHUB_ADMIN_USERNAME": "  Root.User  "})
    assert load_settings().admin_username == "root.user"


def test_frozen():
    s = load_settings()
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.ssl_enabled = 999  # type: ignore[misc]


def test_admin_password_never_a_field():
    # the secret must NEVER be a settings field (stays an os.environ read in the authenticator)
    names = {f.name for f in dataclasses.fields(Settings)}
    assert not any("password" in n for n in names)
