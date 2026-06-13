"""Unified group policy model.

One registry of policy types is the single source of truth for every group
permission: defaults, write-coercion, validation, cross-group resolution, the
runtime driver, and UI metadata. See ``registry.py`` for the types and
``engine.py`` for the resolve/validate/coerce entry points.
"""

from .engine import (
    POLICY_TYPES,
    PolicyCtx,
    coerce_config,
    default_config,
    resolve_policies,
    summarize_config,
    validate_all,
)
from .registry import (
    PROTECTED_MOUNTPOINTS,
    PolicyCoerceError,
    PolicyType,
    is_protected_mountpoint,
    is_reserved_env_var,
)

__all__ = [
    'POLICY_TYPES',
    'PolicyCtx',
    'PolicyType',
    'PolicyCoerceError',
    'PROTECTED_MOUNTPOINTS',
    'coerce_config',
    'default_config',
    'resolve_policies',
    'summarize_config',
    'validate_all',
    'is_protected_mountpoint',
    'is_reserved_env_var',
]
