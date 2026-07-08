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
           'effective_grants', 'apply_policies', 'run_hub_startup', 'default_config',
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


def effective_grants(matched, resolved):
    """Cross-group resolved capability grants with source attribution.

    Backs the per-user "effective policies" view. ``matched`` is the
    priority-descending list of the user's group configs (the same input
    ``resolve_policies`` consumes); ``resolved`` is its output. Returns a list of
    ``{key, label, value, from}`` - one entry per capability the user actually
    gets, each citing the highest-priority group that granted it. Empty when no
    group grants anything special (the honest "platform defaults" state). ``key``
    is a frontend icon name (gpu/memory/cpu/shield/box).
    """
    grants = []

    def winner(predicate):
        # highest-priority (first) matched group whose config satisfies predicate
        for cfg in matched:
            if predicate(cfg.get('config') or {}):
                return cfg.get('group_name')
        return '-'

    def num(x):
        # drop a trailing .0 so 16.0 -> '16', keep 0.5 -> '0.5'
        f = float(x)
        return str(int(f)) if f.is_integer() else str(f)

    # GPU - OR grant, hardware-gated in the resolver; "all" wins over a subset.
    if resolved.get('gpu_access'):
        if resolved.get('gpu_all', True) or not resolved.get('gpu_device_ids'):
            value = 'all devices'
            src = winner(lambda c: c.get('gpu_access') and c.get('gpu_all', True))
        else:
            value = 'GPU ' + ', '.join(resolved['gpu_device_ids'])
            src = winner(lambda c: c.get('gpu_access'))
        grants.append({'key': 'gpu', 'label': 'GPU', 'value': value, 'from': src})

    # Memory - biggest enabled limit wins.
    mem_gb = resolved.get('mem_limit_gb')
    if mem_gb:
        value = f'{num(mem_gb)} GB'
        if resolved.get('mem_swap_disabled'):
            value += ' (no swap)'
        src = winner(lambda c: c.get('mem_limit_enabled')
                     and float(c.get('mem_limit_gb') or 0) == float(mem_gb))
        grants.append({'key': 'memory', 'label': 'Memory', 'value': value, 'from': src})

    # CPU - biggest enabled limit wins.
    cpu_cores = resolved.get('cpu_limit_cores')
    if cpu_cores:
        value = f'{num(cpu_cores)} cores'
        src = winner(lambda c: c.get('cpu_limit_enabled')
                     and float(c.get('cpu_limit_cores') or 0) == float(cpu_cores))
        grants.append({'key': 'cpu', 'label': 'CPU', 'value': value, 'from': src})

    # System env - section-gated (same "System" section as sudo); surfaced when a group
    # configures it, so the resolved-grants panel mirrors the group-config summary badge.
    sys_env = resolved.get('user_env_enable')
    if sys_env is not None:
        src = winner(lambda c: c.get('sudo_active'))
        grants.append({'key': 'code', 'label': 'System env',
                       'value': 'enabled' if sys_env else 'disabled', 'from': src})

    # Sudo - section-gated; surfaced only when a group configures it.
    sudo = resolved.get('sudo_enable')
    if sudo is not None:
        src = winner(lambda c: c.get('sudo_active'))
        grants.append({'key': 'shield', 'label': 'Sudo',
                       'value': 'enabled' if sudo else 'disabled', 'from': src})

    # Docker - raw socket supersedes limited proxy (the resolver already
    # collapsed that); privileged annotates the same row so the icon key stays
    # unique (the frontend keys grant rows by `key`).
    if resolved.get('docker_access'):
        value = 'socket'
        src = winner(lambda c: c.get('docker_active', True) and c.get('docker_access'))
    elif resolved.get('docker_limited'):
        value = 'limited'
        src = winner(lambda c: c.get('docker_active', True) and c.get('docker_limited'))
    elif resolved.get('docker_privileged'):
        value = 'privileged'
        src = winner(lambda c: c.get('docker_active', True) and c.get('docker_privileged'))
    else:
        value = src = None
    if value:
        if resolved.get('docker_privileged') and value != 'privileged':
            value += ' + privileged'
        grants.append({'key': 'box', 'label': 'Docker', 'value': value, 'from': src})

    return grants


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
