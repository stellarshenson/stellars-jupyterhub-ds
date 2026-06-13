"""Policy engine - drive the registry to resolve, validate, and coerce.

Pure functions over ``POLICY_TYPES``. No JupyterHub imports, unit-testable.

``resolve_policies`` is the drop-in replacement for the legacy
``resolve_group_config``: same signature, same output key set. Each type
contributes its slice; the engine assembles them plus ``matched_groups``.

Resolution rules (owned per type, see ``registry.py``):
- GRANTS (gpu/docker/privileged) - OR across all groups; once granted, not
  revoked. GPU is hardware-gated; among GPU-granting groups "all" wins, else
  device ids union.
- ENV VARS - higher priority wins on name conflict (priority-descending walk).
- MEM/CPU - biggest enabled value wins; a disabled group never un-caps.
- SUDO/DOWNLOADS - section-gated, highest-priority configuring group wins;
  ``None`` when unconfigured (the hook applies the platform default).
- API KEYS POOLS - priority-ordered list, one per matched group with a pool.
- VOLUME MOUNTS - union keyed by mountpoint, higher priority wins on conflict.
- RESERVED env names are stripped and reported in ``skipped_env_vars``.
"""

from .registry import POLICY_TYPES, PolicyCtx, default_config

__all__ = ['resolve_policies', 'validate_all', 'coerce_config', 'summarize_config',
           'default_config', 'POLICY_TYPES', 'PolicyCtx']


def resolve_policies(user_group_names, all_group_configs, gpu_available,
                     reserved_names, reserved_prefixes):
    """Collapse a user's groups into the effective user-policy object.

    Args mirror the legacy resolver. ``all_group_configs`` is the
    priority-descending list from ``GroupsConfigManager.get_all_configs()``.
    """
    ctx = PolicyCtx(
        gpu_available=gpu_available,
        reserved_names=frozenset(reserved_names or ()),
        reserved_prefixes=tuple(reserved_prefixes or ()),
    )
    user_set = set(user_group_names or [])
    # Priority order (descending) - input is already sorted by the manager.
    matched = [c for c in (all_group_configs or []) if c.get('group_name') in user_set]

    result = {}
    for pt in POLICY_TYPES:
        result.update(pt.resolve(matched, ctx))
    result['matched_groups'] = [c['group_name'] for c in matched]
    return result


def validate_all(config):
    """Run every type's validate. Returns ``(valid, error_code, message)`` -
    first failure wins so the user sees one error at a time."""
    for pt in POLICY_TYPES:
        if pt.validate is None:
            continue
        ok, msg = pt.validate(config)
        if not ok:
            return False, pt.validate_code, msg
    return True, '', ''


def summarize_config(config):
    """Per-type display summaries for one group's stored config.

    Returns a list of ``{key, badge, detail}`` in registry order, one per
    active/configured section. The admin UI renders these strings directly for
    the group badges and hover tooltip - no policy-display logic in the browser.
    """
    out = []
    for pt in POLICY_TYPES:
        if pt.summarize is None:
            continue
        s = pt.summarize(config or {})
        if s:
            out.append({'key': pt.key, 'badge': s['badge'], 'detail': s['detail']})
    return out


def coerce_config(body, existing_config, ctx):
    """Normalise an admin write body into a config slice, looping every type.

    ``existing_config`` is the group's current config dict (api-keys needs it to
    preserve stored secrets by slot). May raise ``registry.PolicyCoerceError``.
    """
    out = {}
    for pt in POLICY_TYPES:
        if pt.coerce is None:
            continue
        out.update(pt.coerce(body, existing_config, ctx))
    return out
