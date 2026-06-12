"""Resolve a user's effective configuration from all their groups.

Pure functions - no JupyterHub imports, unit-testable.

Resolution rules:
- GRANTS (gpu/docker/privileged): OR across all groups. Once any group grants,
  it cannot be revoked by another. GPU is additionally gated on hardware
  availability.
- GPU SELECTION: among the groups that grant GPU access, "all GPUs" is the most
  permissive and wins - if any such group selects all, the user gets all GPUs.
  Otherwise the specific device ids are unioned across those groups. As a
  defensive fallback, a grant with neither "all" nor any device id resolves to
  "all" (the save-time validator already rejects that state).
- ENV VARS: higher priority wins on name conflict. Groups are scanned in
  descending priority order and the first occurrence of each name is kept.
- MEM_LIMIT_GB: biggest enabled value wins across all groups. A group with
  mem_limit_enabled=False does NOT remove a cap granted by another group.
  The swap policy (mem_swap_disabled) travels with the winning limit: the
  group that owns the largest cap also decides whether swap is allowed.
- CPU_LIMIT_CORES: biggest enabled value wins across all groups, same rule as
  memory. The spawn-time application ceils to whole cores so a container is
  never assigned a sub-core (or zero-core) quota.
- RESERVED NAMES: env vars with reserved names are stripped and reported in
  skipped_env_vars. The handler is expected to reject at save time; this is
  defence-in-depth.
- API KEYS POOLS: collected as a priority-ordered LIST (not scalar-merged) -
  one entry per matched group with an enabled pool. Each pool assigns
  independently at spawn; on target-var-name collision the higher-priority pool
  wins (first in the list), consistent with the env-vars rule.
"""

from .api_keys_pool import normalize_pool
from .groups_config import is_protected_mountpoint


# Fallback per-group limited-Docker quota/caps when a granting group stored a
# zero/unset value (defensive - save-time defaults already seed these).
_DL_DEFAULTS = {
    'max_containers': 10,
    'max_volumes': 10,
    'max_networks': 3,
    'max_storage_gb': 50,
    'cpu_cap_cores': 2,
    'mem_cap_gb': 8,
}


def is_reserved_env_var(name, reserved_names, reserved_prefixes):
    """Return True if the env var name is reserved (cannot be set by a group)."""
    if not name:
        return True
    if name in reserved_names:
        return True
    for prefix in reserved_prefixes:
        if name.startswith(prefix):
            return True
    return False


def resolve_group_config(
    user_group_names,
    all_group_configs,
    gpu_available,
    reserved_names,
    reserved_prefixes,
):
    """Collapse a user's groups into effective access and env vars.

    Args:
        user_group_names: list of group names the user belongs to.
        all_group_configs: list of dicts as returned by GroupsConfigManager
            .get_all_configs() - already sorted by priority descending.
        gpu_available: whether GPU hardware is present on the host.
        reserved_names: set of env var names that must not be overridden.
        reserved_prefixes: tuple of prefixes (e.g. "JUPYTERHUB_") that reserve
            every matching variable.

    Returns:
        {
          'env_vars': dict[str, str],
          'gpu_access': bool,
          'gpu_all': bool,               # all GPUs (True) vs specific device ids
          'gpu_device_ids': list[str],   # selected GPU indices when gpu_all False
          'docker_access': bool,          # normal raw-socket access
          'docker_limited': bool,         # proxy access (False if docker_access)
          'docker_limited_max_containers': int,
          'docker_limited_max_volumes': int,
          'docker_limited_max_networks': int,
          'docker_limited_max_storage_gb': float,
          'docker_limited_cpu_cap_cores': float,
          'docker_limited_mem_cap_gb': float,
          'docker_limited_allow_dangerous_flags': bool,  # OR across limited groups
          'docker_limited_user_compose_project_enabled': bool,
          'docker_limited_user_compose_project_allow_override': bool,
          'docker_limited_hub_network_access': bool,
          'docker_privileged': bool,
          'mem_limit_gb': float | None,  # biggest enabled value, None if no cap
          'mem_swap_disabled': bool,     # swap policy of the winning mem-limit group
          'cpu_limit_cores': float | None,  # biggest enabled value, None if no cap
          'downloads_allowed': bool,     # True iff any group grants downloads
          'matched_groups': list[str],   # ordered by priority desc
          'skipped_env_vars': list[str], # names stripped because reserved
        }
    """
    user_set = set(user_group_names or [])

    # Walk in priority order (descending) - input is already sorted by the manager.
    matched = [c for c in (all_group_configs or []) if c.get('group_name') in user_set]

    env_vars = {}
    skipped = []
    gpu_requested = False
    gpu_all = False
    gpu_device_ids = set()
    docker_access = False
    docker_limited = False
    dl_quota = {k: 0 for k in _DL_DEFAULTS}
    docker_limited_allow_dangerous_flags = False
    docker_limited_user_compose_project_enabled = False
    docker_limited_user_compose_project_allow_override = False
    docker_limited_hub_network_access = False
    docker_privileged = False
    mem_limit_gb = None
    mem_swap_disabled = False
    cpu_limit_cores = None
    # File downloads: grant-style OR across groups. True iff ANY matched group
    # has downloads_active. Absent key = not granted (this flag IS the grant,
    # not a section gate), so it never defaults active.
    downloads_allowed = False
    api_key_pools = []
    # mountpoint -> volume name; highest-priority group wins on a mountpoint
    # conflict (same rule as env vars). Shadowed entries land in skipped_volume_mounts.
    volume_mounts = {}
    skipped_volume_mounts = []
    # name -> index in `matched` (lower = higher priority) of the group that set
    # it. Lets the spawn-time apply resolve a plain-env-var vs pool-var clash by
    # group order, not by kind. Pools carry their own group_index for the same.
    env_var_source = {}

    for idx, cfg in enumerate(matched):
        inner = cfg.get('config') or {}
        # Section active flags: an inactive section reads as unconfigured while
        # its data persists in the DB. Missing flag (legacy dict that bypassed
        # _row_to_dict inference) defaults to active to preserve behaviour.
        env_vars_active = inner.get('env_vars_active', True)
        docker_active = inner.get('docker_active', True)
        volume_mounts_active = inner.get('volume_mounts_active', True)
        if inner.get('gpu_access'):
            gpu_requested = True
            # all-GPUs is most permissive and wins; otherwise union device ids
            if inner.get('gpu_all', True):
                gpu_all = True
            else:
                for did in (inner.get('gpu_device_ids') or []):
                    gpu_device_ids.add(str(did))
        if docker_active and inner.get('docker_access'):
            docker_access = True
        if docker_active and inner.get('docker_limited'):
            # Limited (proxy) access: granted if any group grants it; quota/caps
            # are the most-generous (max) across the granting groups.
            docker_limited = True
            for key in _DL_DEFAULTS:
                try:
                    val = float(inner.get(f'docker_limited_{key}') or 0)
                except (TypeError, ValueError):
                    val = 0.0
                if val > dl_quota[key]:
                    dl_quota[key] = val
            # OR-accumulate the dangerous-flags bypass: if ANY granting group
            # turns it on, the user gets it. Independent of docker_privileged.
            if inner.get('docker_limited_allow_dangerous_flags'):
                docker_limited_allow_dangerous_flags = True
            # OR-accumulate compose-project enforcement and allow-override.
            # Both have True defaults in default_config so a freshly created
            # limited group automatically opts the user in to per-user grouping
            # while still respecting the user's own `docker compose -p`.
            if inner.get('docker_limited_user_compose_project_enabled'):
                docker_limited_user_compose_project_enabled = True
            if inner.get('docker_limited_user_compose_project_allow_override'):
                docker_limited_user_compose_project_allow_override = True
            if inner.get('docker_limited_hub_network_access'):
                docker_limited_hub_network_access = True
        if docker_active and inner.get('docker_privileged'):
            docker_privileged = True

        # File downloads grant: OR across groups. The flag is its own grant
        # (no section-gate), so read it directly without an active-flag guard.
        if inner.get('downloads_active'):
            downloads_allowed = True

        # Memory limit: biggest enabled value wins; disabled groups do not un-cap.
        # The swap policy follows the winning limit - the group that owns the
        # largest cap also decides whether swap is allowed. Strict > so ties keep
        # the higher-priority group (matched is priority-descending).
        if inner.get('mem_limit_enabled'):
            try:
                val = float(inner.get('mem_limit_gb') or 0)
            except (TypeError, ValueError):
                val = 0.0
            if val > 0 and (mem_limit_gb is None or val > mem_limit_gb):
                mem_limit_gb = val
                mem_swap_disabled = bool(inner.get('mem_swap_disabled'))

        # CPU limit: biggest enabled value wins; disabled groups do not un-cap
        if inner.get('cpu_limit_enabled'):
            try:
                cval = float(inner.get('cpu_limit_cores') or 0)
            except (TypeError, ValueError):
                cval = 0.0
            if cval > 0:
                cpu_limit_cores = cval if cpu_limit_cores is None else max(cpu_limit_cores, cval)

        for entry in (inner.get('env_vars') or []) if env_vars_active else []:
            name = (entry.get('name') or '').strip()
            if not name:
                continue
            if is_reserved_env_var(name, reserved_names, reserved_prefixes):
                if name not in skipped:
                    skipped.append(name)
                continue
            if name in env_vars:
                # higher priority already claimed this name
                continue
            value = entry.get('value', '')
            env_vars[name] = '' if value is None else str(value)
            env_var_source[name] = idx

        # API keys pool (per-group, NOT merged): collect priority-ordered so the
        # spawn-time apply makes the higher-priority pool win on a var collision.
        pool = normalize_pool(inner.get('api_keys_pool'))
        if pool is not None:
            pool['pool_id'] = cfg.get('group_name')
            pool['group_index'] = idx
            api_key_pools.append(pool)

        # Volume mounts: union across groups keyed by mountpoint; the higher-
        # priority group keeps a contested mountpoint, the shadowed entry is
        # reported. Defense in depth: the save-time blacklist is re-checked here
        # so a stale/legacy config row can never mount over a protected path.
        for entry in (inner.get('volume_mounts') or []) if volume_mounts_active else []:
            volume = (entry.get('volume') or '').strip()
            mountpoint = (entry.get('mountpoint') or '').strip()
            if not volume or not mountpoint or not mountpoint.startswith('/'):
                continue
            norm = '/' + mountpoint.strip('/')
            if is_protected_mountpoint(norm):
                skipped_volume_mounts.append({'volume': volume, 'mountpoint': norm,
                                              'group': cfg.get('group_name'), 'reason': 'protected'})
                continue
            if norm in volume_mounts:
                if volume_mounts[norm] != volume:
                    skipped_volume_mounts.append({'volume': volume, 'mountpoint': norm,
                                                  'group': cfg.get('group_name'), 'reason': 'shadowed'})
                continue
            # Docker mounts are keyed by volume name - a volume already claimed
            # at another mountpoint by a higher-priority group cannot re-mount.
            if volume in volume_mounts.values():
                skipped_volume_mounts.append({'volume': volume, 'mountpoint': norm,
                                              'group': cfg.get('group_name'), 'reason': 'shadowed'})
                continue
            volume_mounts[norm] = volume

    # Defensive: a grant with neither "all" nor specific ids falls back to all.
    if gpu_requested and not gpu_all and not gpu_device_ids:
        gpu_all = True

    # Normal (raw) Docker access supersedes limited (proxy): wider wins, and a
    # raw socket makes the filtered one moot. So limited only takes effect when
    # no group grants normal access. Same applies to the limited-only bypass:
    # collapses to False when docker_access wins (it has no limited proxy to
    # relax).
    if docker_access:
        docker_limited = False
        docker_limited_allow_dangerous_flags = False
        docker_limited_user_compose_project_enabled = False
        docker_limited_user_compose_project_allow_override = False
        docker_limited_hub_network_access = False
    if docker_limited:
        for key, default in _DL_DEFAULTS.items():
            if dl_quota[key] <= 0:
                dl_quota[key] = default

    return {
        'env_vars': env_vars,
        'gpu_access': bool(gpu_requested and gpu_available),
        'gpu_all': bool(gpu_all),
        'gpu_device_ids': sorted(gpu_device_ids, key=lambda x: (len(x), x)),
        'docker_access': docker_access,
        'docker_limited': docker_limited,
        'docker_limited_max_containers': int(dl_quota['max_containers']),
        'docker_limited_max_volumes': int(dl_quota['max_volumes']),
        'docker_limited_max_networks': int(dl_quota['max_networks']),
        'docker_limited_max_storage_gb': dl_quota['max_storage_gb'],
        'docker_limited_cpu_cap_cores': dl_quota['cpu_cap_cores'],
        'docker_limited_mem_cap_gb': dl_quota['mem_cap_gb'],
        'docker_limited_allow_dangerous_flags': docker_limited_allow_dangerous_flags,
        'docker_limited_user_compose_project_enabled': docker_limited_user_compose_project_enabled,
        'docker_limited_user_compose_project_allow_override': docker_limited_user_compose_project_allow_override,
        'docker_limited_hub_network_access': docker_limited_hub_network_access,
        'docker_privileged': docker_privileged,
        'mem_limit_gb': mem_limit_gb,
        'mem_swap_disabled': mem_swap_disabled,
        'cpu_limit_cores': cpu_limit_cores,
        'downloads_allowed': downloads_allowed,
        'api_key_pools': api_key_pools,
        'volume_mounts': [{'volume': v, 'mountpoint': m} for m, v in volume_mounts.items()],
        'skipped_volume_mounts': skipped_volume_mounts,
        'env_var_source': env_var_source,
        'matched_groups': [c['group_name'] for c in matched],
        'skipped_env_vars': skipped,
    }
