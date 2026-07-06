"""Config assembly for the DuOptimum hub (config simplification).

Moves the mechanical bulk out of jupyterhub_config.py so the config file reads like
configuration. `load_settings()` is the single module-level env-read site for the
operator-tunable settings; runtime-discovered values (compose project, mounted
volumes, GPU/sidecar/branding) stay in the config/runtime layer, not here.
"""

from .settings import Settings, load_settings
from .wiring import docker_spawner_env, template_vars, stellars_config, validator_payload, pre_spawn_kwargs
from .runtime import Runtime, assemble_runtime

__all__ = [
    "Settings", "load_settings", "Runtime", "assemble_runtime",
    "docker_spawner_env", "template_vars", "stellars_config", "validator_payload", "pre_spawn_kwargs",
]
