"""Protected environment variable dictionary loader.

Single source of truth for the env var names + prefixes a user or group must never
set (owned by JupyterHub or imposed per-user by a policy at spawn). The baked YAML
(conf/protected_env_dictionary.yml -> /srv/jupyterhub/protected_env_dictionary.yml)
is authoritative. The DEFAULT_* constants are a boot-safety net: a missing file
falls back to them rather than silently booting with an empty blacklist. The config
unions in the 16 globally-injected names (derived from c.DockerSpawner.environment)
so those never drift from what the platform actually injects.
"""

import os

from .logging_setup import log

# Fail-safe fallback - mirrors the YAML, used ONLY when the dictionary file is absent
# (an old image). A partial or empty blacklist would be a security regression.
DEFAULT_PROTECTED_NAMES = frozenset({
    'ENABLE_GPU_SUPPORT', 'ENABLE_GPUSTAT', 'NVIDIA_VISIBLE_DEVICES',
    'CUDA_VISIBLE_DEVICES', 'DOCKER_HOST', 'JUPYTERLAB_SUDO_ENABLE',
    # docker-stacks root-time privilege levers (honoured by the base image's start.sh
    # while still root) - a user setting these would self-escalate or bypass the sudo policy
    'GRANT_SUDO', 'NB_UID', 'NB_GID', 'NB_USER', 'NB_GROUP', 'NB_UMASK',
    'CHOWN_HOME', 'CHOWN_HOME_OPTS', 'CHOWN_EXTRA', 'CHOWN_EXTRA_OPTS',
})
DEFAULT_PROTECTED_PREFIXES = ('JUPYTERHUB_', 'JPY_', 'MEM_', 'CPU_')


def load_protected_env(path):
    """Load the protected-env dictionary -> (names:set, prefixes:tuple).

    File absent -> DEFAULTS (warn; never an empty blacklist). File present but
    malformed -> raise (fail loud; a broken blacklist is a security bug, not a
    degrade). YAML shape: ``{names: [str, ...], prefixes: [str, ...]}``.
    """
    if not path or not os.path.exists(path):
        log.warning(f"[ProtectedEnv] dictionary {path!r} not found - using built-in defaults")
        return set(DEFAULT_PROTECTED_NAMES), tuple(DEFAULT_PROTECTED_PREFIXES)
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Protected-env dictionary at {path!r} must be a mapping (got {type(data).__name__})")
    names = data.get('names') or []
    prefixes = data.get('prefixes') or []
    if not isinstance(names, list) or not isinstance(prefixes, list):
        raise ValueError(f"Protected-env dictionary at {path!r}: 'names' and 'prefixes' must be lists")
    return {str(n) for n in names}, tuple(str(p) for p in prefixes)
