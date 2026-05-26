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
"""


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
          'docker_privileged': bool,
          'mem_limit_gb': float | None,  # biggest enabled value, None if no cap
          'mem_swap_disabled': bool,     # swap policy of the winning mem-limit group
          'cpu_limit_cores': float | None,  # biggest enabled value, None if no cap
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
    docker_privileged = False
    mem_limit_gb = None
    mem_swap_disabled = False
    cpu_limit_cores = None

    for cfg in matched:
        inner = cfg.get('config') or {}
        if inner.get('gpu_access'):
            gpu_requested = True
            # all-GPUs is most permissive and wins; otherwise union device ids
            if inner.get('gpu_all', True):
                gpu_all = True
            else:
                for did in (inner.get('gpu_device_ids') or []):
                    gpu_device_ids.add(str(did))
        if inner.get('docker_access'):
            docker_access = True
        if inner.get('docker_limited'):
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
        if inner.get('docker_privileged'):
            docker_privileged = True

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

        for entry in (inner.get('env_vars') or []):
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

    # Defensive: a grant with neither "all" nor specific ids falls back to all.
    if gpu_requested and not gpu_all and not gpu_device_ids:
        gpu_all = True

    # Normal (raw) Docker access supersedes limited (proxy): wider wins, and a
    # raw socket makes the filtered one moot. So limited only takes effect when
    # no group grants normal access.
    if docker_access:
        docker_limited = False
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
        'docker_privileged': docker_privileged,
        'mem_limit_gb': mem_limit_gb,
        'mem_swap_disabled': mem_swap_disabled,
        'cpu_limit_cores': cpu_limit_cores,
        'matched_groups': [c['group_name'] for c in matched],
        'skipped_env_vars': skipped,
    }
