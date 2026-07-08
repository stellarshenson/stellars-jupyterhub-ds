"""Shape lock for the config wiring builders (config simplification Batch 3).

The builders assemble c.* dicts the config used to build inline; the config cannot be
unit-booted, so these pin the exact keys and value-mapping. The key SET of
docker_spawner_env is load-bearing (RESERVED_ENV_VAR_NAMES derives from it), so it is
asserted explicitly. Boot confirmation rides the functional suite on a rebuilt image.
"""

import dataclasses
import inspect
from types import SimpleNamespace

import pytest

from duoptimum_hub_services.config.runtime import Runtime, assemble_runtime
from duoptimum_hub_services.config.wiring import docker_spawner_env, pre_spawn_kwargs, stellars_config, template_vars, validator_payload

_SETTINGS = SimpleNamespace(
    tf_cpp_min_log_level=3,
    lab_service_mlflow=1,
    lab_service_resources_monitor=0,
    lab_service_tensorboard=1,
    aux_scripts_path="/mnt/shared/scripts",
    aux_menu_path="/mnt/shared/menu",
    timezone="Europe/Warsaw",
    branding_lab_name="Test Lab",
)


def test_docker_spawner_env_exact_dict():
    got = docker_spawner_env(_SETTINGS, nvidia_detected=True, lab_network="jupyterhub_lab_net")
    assert got == {
        "TF_CPP_MIN_LOG_LEVEL": 3,
        "TENSORBOARD_LOGDIR": "/tmp/tensorboard",
        "MLFLOW_TRACKING_URI": "http://localhost:5000",
        "MLFLOW_PORT": 5000,
        "MLFLOW_HOST": "0.0.0.0",
        "MLFLOW_WORKERS": 1,
        "ENABLE_SERVICE_MLFLOW": 1,
        "ENABLE_SERVICE_RESOURCES_MONITOR": 0,
        "ENABLE_SERVICE_TENSORBOARD": 1,
        "NVIDIA_DETECTED": True,
        "JUPYTERLAB_AUX_SCRIPTS_PATH": "/mnt/shared/scripts",
        "JUPYTERLAB_AUX_MENU_PATH": "/mnt/shared/menu",
        "JUPYTERLAB_TIMEZONE": "Europe/Warsaw",
        "JUPYTERLAB_SYSTEM_NAME": "Test Lab",
        "JUPYTERHUB_NETWORK_NAME": "jupyterhub_lab_net",
    }


def test_docker_spawner_env_key_set_is_load_bearing():
    # RESERVED_ENV_VAR_NAMES = set(this dict's keys) | protected names - a dropped or
    # renamed key silently changes which names groups/users can override.
    keys = set(docker_spawner_env(_SETTINGS, nvidia_detected=False, lab_network="n"))
    assert keys == {
        "TF_CPP_MIN_LOG_LEVEL", "TENSORBOARD_LOGDIR", "MLFLOW_TRACKING_URI", "MLFLOW_PORT",
        "MLFLOW_HOST", "MLFLOW_WORKERS", "ENABLE_SERVICE_MLFLOW", "ENABLE_SERVICE_RESOURCES_MONITOR",
        "ENABLE_SERVICE_TENSORBOARD", "NVIDIA_DETECTED", "JUPYTERLAB_AUX_SCRIPTS_PATH",
        "JUPYTERLAB_AUX_MENU_PATH", "JUPYTERLAB_TIMEZONE", "JUPYTERLAB_SYSTEM_NAME",
        "JUPYTERHUB_NETWORK_NAME",
    }


def test_runtime_values_passthrough():
    got = docker_spawner_env(_SETTINGS, nvidia_detected=False, lab_network="netX")
    assert got["NVIDIA_DETECTED"] is False
    assert got["JUPYTERHUB_NETWORK_NAME"] == "netX"


# ── Runtime (Batch 4 orchestration move) ─────────────────────────────────────
# assemble_runtime has real side effects (starts the gpuinfo sidecar, copies branding)
# and can't run without Docker + a booted hub - the functional suite is its boot gate.
# Locally we lock the Runtime shape + the assemble_runtime contract (which the config
# depends on when it binds runtime.* back to its module names).

def test_runtime_is_frozen_dataclass_with_expected_fields():
    assert dataclasses.is_dataclass(Runtime)
    assert Runtime.__dataclass_params__.frozen
    assert {f.name for f in dataclasses.fields(Runtime)} == {
        "gpu_vendor", "gpuinfo_url", "gpuinfo_sidecar_up", "gpu_enabled", "nvidia_detected",
        "gpu_list", "gpu_uuid_by_index", "gpu_isolation_enforced", "branding",
    }


def test_assemble_runtime_signature():
    # the config calls assemble_runtime(settings, JUPYTERHUB_COMPOSE_PROJECT_NAME)
    assert list(inspect.signature(assemble_runtime).parameters) == ["settings", "compose_project"]


def test_runtime_construct_and_read():
    r = Runtime(
        gpu_vendor=object(), gpuinfo_url="", gpuinfo_sidecar_up=False, gpu_enabled=0,
        nvidia_detected=0, gpu_list=[], gpu_uuid_by_index={}, gpu_isolation_enforced=False,
        branding={"logo_file": ""},
    )
    assert r.gpu_enabled == 0 and r.branding["logo_file"] == ""
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.gpu_enabled = 1  # type: ignore[misc]


# ── validator_payload (Batch 3d) ─────────────────────────────────────────────
# The key SET is security-relevant: validate_hub_config raises on missing required keys,
# so a dropped/renamed key would silently weaken required-config validation.

class _EchoSettings:
    """settings.foo -> 's.foo', so every field mapping is verifiable by name."""
    def __getattr__(self, name):
        return f"s.{name}"


_VP_KWARGS = dict(
    namespace="NS", lab_network_name="LNET", gpuinfo_network_name="GNET",
    shared_volume_name="SHARED", docker_proxy_socket_dir="SOCKDIR",
    docker_proxy_sockets_volume="SOCKVOL", user_compose_project_template="TMPL",
)


def test_validator_payload_key_set():
    p = validator_payload(_EchoSettings(), **_VP_KWARGS)
    assert set(p) == {
        "admin", "lab_image", "namespace", "lab_network_name", "network_role_label_key",
        "volume_role_label_key", "container_role_label_key", "lab_network_role_label",
        "gpuinfo_network_role_label", "shared_volume_role_label", "docker_proxy_volume_role_label",
        "gpuinfo_container_role_label", "lab_container_role_label", "volume_description_label_key",
        "volume_owner_label_key", "container_description_label_key", "docker_proxy_owner_label_key",
        "docker_proxy_owner_label_value", "lab_container_name_template", "gpuinfo_nvidia_image",
        "gpuinfo_nvidia_container_name", "gpuinfo_nvidia_url", "docker_proxy_socket_dir",
        "docker_proxy_sockets_volume", "user_compose_project_template", "gpuinfo_network_name",
        "shared_volume_name", "branding_logo_uri", "branding_favicon_uri",
        "branding_favicon_busy_uri", "branding_lab_main_icon_uri", "branding_lab_splash_uri",
    }


def test_validator_payload_runtime_kwargs_passthrough():
    p = validator_payload(_EchoSettings(), **_VP_KWARGS)
    assert p["namespace"] == "NS"
    assert p["lab_network_name"] == "LNET"
    assert p["gpuinfo_network_name"] == "GNET"
    assert p["shared_volume_name"] == "SHARED"
    assert p["docker_proxy_socket_dir"] == "SOCKDIR"
    assert p["docker_proxy_sockets_volume"] == "SOCKVOL"
    assert p["user_compose_project_template"] == "TMPL"


def test_template_vars_exact_dict():
    s = SimpleNamespace(
        idle_culler_enabled=1, idle_culler_timeout=86400, idle_culler_max_extension=24,
        activitymon_target_hours=8, activitymon_sample_interval=600,
        lab_container_max_extra_space_gb=10, lab_volume_max_total_size_gb=50,
        lab_memory_max_usage_mb=4096, admin_username="admin", branding_hub_name="DuOptimum Hub",
    )
    r = SimpleNamespace(branding={"favicon_uri": "f.ico", "stage": "DEV"}, gpu_enabled=1)
    got = template_vars(
        s, r, user_volume_suffixes=["home"], user_volume_name_templates={"home": "t"},
        user_volumes=[{"suffix": "home"}], stellars_version="1.2.3", server_version="4.0",
        entry_js="app.js", entry_css="app.css",
    )
    assert got == {
        "user_volume_suffixes": ["home"], "user_volume_name_templates": {"home": "t"},
        "user_volumes": [{"suffix": "home"}], "stellars_version": "1.2.3", "server_version": "4.0",
        "idle_culler_enabled": 1, "idle_culler_timeout": 86400, "idle_culler_max_extension": 24,
        "activitymon_target_hours": 8, "activitymon_sample_interval": 600,
        "container_max_extra_space_mb": 10240, "volume_max_total_size_mb": 51200,
        "memory_max_usage_mb": 4096, "favicon_uri": "f.ico", "branding_stage": "DEV",
        "duoptimum_entry_js": "app.js", "duoptimum_entry_css": "app.css",
        "gpu_enabled": True, "admin_user": "admin", "hub_name": "DuOptimum Hub",
    }


def test_stellars_config_key_set_and_lab_volumes():
    s = SimpleNamespace(
        label_volume_role_key="role", label_volume_description="desc",
        idle_culler_enabled=1, idle_culler_timeout=100, idle_culler_max_extension=2,
        lab_container_max_extra_space_gb=10, lab_volume_max_total_size_gb=50,
        lab_memory_max_usage_mb=4096, lab_image="img",
    )
    r = SimpleNamespace(gpu_list=[{"index": 0}], gpu_enabled=1, gpu_isolation_enforced=True)
    user_volumes = [{"suffix": "home", "name_template": "jl-{username}_home", "description": "Home", "role": "lab-home"}]
    got = stellars_config(
        s, r,
        user_volume_suffixes=["home"], user_volume_name_templates={"home": "jl-{username}_home"},
        user_volume_roles={"home": "lab-home"}, user_volumes=user_volumes,
        host_status_provider="HSP", reserved_env_var_names={"A"}, reserved_env_var_prefixes=("P_",),
        shared_volume_name="shared", docker_spawner_volumes={"jl-{username}_home": "/home"},
    )
    assert set(got) == {
        "user_volume_suffixes", "user_volume_name_templates", "user_volume_roles",
        "volume_role_label_key", "volume_description_label_key", "user_volumes",
        "idle_culler_enabled", "idle_culler_timeout", "idle_culler_max_extension",
        "gpu_list", "gpu_available", "gpu_isolation_enforced", "host_status_provider",
        "container_max_extra_space_mb", "volume_max_total_size_mb", "memory_max_usage_mb",
        "reserved_env_var_names", "reserved_env_var_prefixes", "shared_volume_name",
        "lab_image", "lab_volumes",
    }
    assert got["gpu_available"] is True
    assert got["container_max_extra_space_mb"] == 10240
    assert got["host_status_provider"] == "HSP"
    # lab_volumes maps each user volume's name_template through docker_spawner_volumes
    assert got["lab_volumes"] == [
        {"suffix": "home", "mount": "/home", "description": "Home", "role": "lab-home"}
    ]


def _pre_spawn_inputs():
    s = SimpleNamespace(
        branding_favicon_uri="f.ico", label_container_role_key="crk", label_container_role_lab="lab",
        lab_block_file_downloads=0, lab_sudo_enable=1, lab_user_env_enable=1, idle_culler_interval=600,
        label_volume_role_key="vrk", label_volume_owner_key="vok", label_volume_description="vd",
    )
    r = SimpleNamespace(
        branding={"favicon_busy_target": "busy.ico"}, gpu_enabled=1,
        gpu_uuid_by_index={"0": "GPU-x"}, gpu_vendor=object(),
    )
    kw = dict(
        reserved_env_var_names={"A"}, reserved_env_var_prefixes=("P_",), lab_compose_project="proj",
        docker_proxy_socket_dir="/sock", docker_proxy_volume_name="vol",
        user_compose_project_template="{username}_c", lab_network="net", shared_volume_name="shared",
        user_volume_label_templates={"t": {"role": "r"}},
    )
    return s, r, kw


def test_pre_spawn_kwargs_match_hook_signature():
    # every key must be a real make_pre_spawn_hook parameter, and every required
    # (no-default) parameter must be supplied - so make_pre_spawn_hook(**kw) can't TypeError.
    from duoptimum_hub_services.hooks import make_pre_spawn_hook
    params = inspect.signature(make_pre_spawn_hook).parameters
    s, r, kw = _pre_spawn_inputs()
    out = pre_spawn_kwargs(s, r, **kw)
    accepted = set(params)
    assert set(out) <= accepted, set(out) - accepted
    required = {n for n, p in params.items()
                if p.default is inspect.Parameter.empty and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)}
    assert required <= set(out), required - set(out)


def test_pre_spawn_kwargs_mappings():
    s, r, kw = _pre_spawn_inputs()
    out = pre_spawn_kwargs(s, r, **kw)
    assert out["branding"] is r.branding
    assert out["favicon_busy_target"] == "busy.ico"
    assert out["gpu_available"] is True
    assert out["gpu_vendor"] is r.gpu_vendor
    assert out["compose_project"] == "proj"
    assert out["hub_network_name"] == "net"
    assert out["api_keys_reconcile_interval"] == 600
    assert out["container_role_label_value"] == "lab"


def test_validator_payload_settings_mappings():
    p = validator_payload(_EchoSettings(), **_VP_KWARGS)
    # spot-check that settings-derived keys map to the right field (not a swapped one)
    assert p["admin"] == "s.admin_username"
    assert p["lab_image"] == "s.lab_image"
    assert p["network_role_label_key"] == "s.label_network_role_key"
    assert p["gpuinfo_nvidia_image"] == "s.gpuinfo_nvidia_image"
    assert p["branding_lab_splash_uri"] == "s.branding_lab_splash_icon_uri"
