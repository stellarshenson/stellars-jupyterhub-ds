"""Unified group policy model.

Every group permission is a ``Policy`` model (``registry.py``) owning its whole
lifecycle - default, coerce/validate, resolve, summarize, apply (impose on a
spawning server), on_hub_startup (re-impose for restart survivors). ``engine.py``
holds the thin loops over the model registry; ``base.py`` the model interface
and shared contexts.
"""

from .base import (
    PROTECTED_MOUNTPOINTS,
    ApplyContext,
    Policy,
    PolicyCoerceError,
    PolicyCtx,
    is_protected_mountpoint,
    is_reserved_env_var,
)
from .engine import (
    POLICY_TYPES,
    apply_policies,
    coerce_config,
    default_config,
    effective_grants,
    resolve_policies,
    run_hub_startup,
    summarize_config,
    validate_all,
)

__all__ = [
    'POLICY_TYPES',
    'Policy',
    'PolicyCtx',
    'ApplyContext',
    'PolicyCoerceError',
    'PROTECTED_MOUNTPOINTS',
    'apply_policies',
    'coerce_config',
    'default_config',
    'effective_grants',
    'resolve_policies',
    'run_hub_startup',
    'summarize_config',
    'validate_all',
    'is_protected_mountpoint',
    'is_reserved_env_var',
]
