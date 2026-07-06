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
from duoptimum_hub_services.config.wiring import docker_spawner_env

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
