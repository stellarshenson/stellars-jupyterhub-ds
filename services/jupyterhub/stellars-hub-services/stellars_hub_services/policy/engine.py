"""Policy engine - drive the model registry to resolve, validate, coerce,
summarize, apply, and run hub-startup.

Thin loops over ``POLICY_TYPES`` (model instances). No JupyterHub imports in the
pure functions; ``apply_policies``/``run_hub_startup`` just await each model's
``apply``/``on_hub_startup`` (the models do the heavy lifting and lazy imports).

``resolve_policies`` is the drop-in replacement for the legacy
``resolve_group_config``: same signature, same output key set.

Resolution rules (owned per model, see ``registry.py``):
- GRANTS (gpu/docker/privileged) - OR across all groups; once granted, not
  revoked. GPU is hardware-gated; among GPU-granting groups "all" wins, else
  device ids union.
- ENV VARS - higher priority wins on name conflict (priority-descending walk).
- MEM/CPU - biggest enabled value wins; a disabled group never un-caps.
- SUDO/DOWNLOADS - section-gated, highest-priority configuring group wins;
  ``None`` when unconfigured (the controller applies the platform default).
- API KEYS POOLS - priority-ordered list, one per matched group with a pool.
- VOLUME MOUNTS - union keyed by mountpoint, higher priority wins on conflict.
- RESERVED env names are stripped and reported in ``skipped_env_vars``.
"""

from .base import ApplyContext, PolicyCtx  # noqa: F401  (re-exported)
from .registry import POLICY_TYPES, default_config

__all__ = ['resolve_policies', 'validate_all', 'coerce_config', 'summarize_config',
           'apply_policies', 'run_hub_startup', 'default_config',
           'POLICY_TYPES', 'PolicyCtx', 'ApplyContext']


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
    for p in POLICY_TYPES:
        result.update(p.resolve(matched, ctx))
    result['matched_groups'] = [c['group_name'] for c in matched]
    return result


def validate_all(config):
    """Run every model's validate. Returns ``(valid, error_code, message)`` -
    first failure wins so the user sees one error at a time."""
    for p in POLICY_TYPES:
        ok, msg = p.validate(config)
        if not ok:
            return False, p.validate_code, msg
    return True, '', ''


def coerce_config(body, existing_config, ctx):
    """Normalise an admin write body into a config slice, looping every model.

    ``existing_config`` is the group's current config dict (api-keys needs it to
    preserve stored secrets by slot). May raise ``base.PolicyCoerceError``.
    """
    out = {}
    for p in POLICY_TYPES:
        out.update(p.coerce(body, existing_config, ctx))
    return out


def summarize_config(config):
    """Per-model display summaries for one group's stored config.

    Returns a list of ``{key, badge, detail}`` in registry order, one per
    active/configured section. The admin UI renders these strings directly for
    the group badges and hover tooltip - no policy-display logic in the browser.
    """
    out = []
    for p in POLICY_TYPES:
        s = p.summarize(config or {})
        if s:
            out.append({'key': p.key, 'badge': s['badge'], 'detail': s['detail']})
    return out


async def apply_policies(spawner, resolved, actx):
    """Impose the resolved policy object on a spawning server - each model's
    ``apply`` in registry order (env_vars before api_keys for env-precedence)."""
    for p in POLICY_TYPES:
        await p.apply(spawner, resolved, actx)


async def run_hub_startup(app, actx):
    """Re-impose / reconcile each model for servers that survived a hub restart."""
    for p in POLICY_TYPES:
        await p.on_hub_startup(app, actx)
