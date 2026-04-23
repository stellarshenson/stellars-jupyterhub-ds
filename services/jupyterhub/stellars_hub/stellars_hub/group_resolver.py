"""Resolve a user's effective configuration from all their groups.

Pure functions - no JupyterHub imports, unit-testable.

Resolution rules:
- GRANTS (gpu/docker/privileged): OR across all groups. Once any group grants,
  it cannot be revoked by another. GPU is additionally gated on hardware
  availability.
- ENV VARS: higher priority wins on name conflict. Groups are scanned in
  descending priority order and the first occurrence of each name is kept.
- MEM_LIMIT_GB: biggest enabled value wins across all groups. A group with
  mem_limit_enabled=False does NOT remove a cap granted by another group.
- RESERVED NAMES: env vars with reserved names are stripped and reported in
  skipped_env_vars. The handler is expected to reject at save time; this is
  defence-in-depth.
"""


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
          'docker_access': bool,
          'docker_privileged': bool,
          'mem_limit_gb': float | None,  # biggest enabled value, None if no cap
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
    docker_access = False
    docker_privileged = False
    mem_limit_gb = None

    for cfg in matched:
        inner = cfg.get('config') or {}
        if inner.get('gpu_access'):
            gpu_requested = True
        if inner.get('docker_access'):
            docker_access = True
        if inner.get('docker_privileged'):
            docker_privileged = True

        # Memory limit: biggest enabled value wins; disabled groups do not un-cap
        if inner.get('mem_limit_enabled'):
            try:
                val = float(inner.get('mem_limit_gb') or 0)
            except (TypeError, ValueError):
                val = 0.0
            if val > 0:
                mem_limit_gb = val if mem_limit_gb is None else max(mem_limit_gb, val)

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

    return {
        'env_vars': env_vars,
        'gpu_access': bool(gpu_requested and gpu_available),
        'docker_access': docker_access,
        'docker_privileged': docker_privileged,
        'mem_limit_gb': mem_limit_gb,
        'matched_groups': [c['group_name'] for c in matched],
        'skipped_env_vars': skipped,
    }
