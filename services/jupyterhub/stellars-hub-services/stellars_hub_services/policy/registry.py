"""Policy-type registry - the single source of truth for group permissions.

Every group permission is one ``PolicyType`` declaring four plug points:

- ``default``  - the off-state slice this type contributes to ``default_config()``
- ``coerce``   - normalise + reject an incoming admin write (replaces the
  per-field branch in ``GroupsConfigHandler.put``); may raise ``PolicyCoerceError``
- ``validate`` - coherence check on the merged config, ``(ok, msg)``; the engine
  tags it with ``validate_code``
- ``resolve``  - collapse this type's value across a user's matched groups
  (priority-descending) into the effective slice; owns the combine strategy and
  any internal supersede
- ``summarize`` - optional display facet; ``(config) -> {'badge', 'detail'} | None``
  for one group's stored config, the single source for the admin UI's group badge
  and hover-tooltip line (the client renders these strings, never recomputes them)

This module imports only the standard library and ``api_keys_pool`` (itself
stdlib-only at import time), so it pulls in nothing heavy and has no import cycle
with ``groups_config`` (which imports *this*, never the reverse).
"""

import copy
import re
from dataclasses import dataclass
from typing import Callable, Optional

from ..api_keys_pool import merge_pool_on_save, normalize_pool


# ── Mountpoint protection (leaf constants; re-exported by groups_config) ──────

# Valid Docker volume name (Docker's own constraint)
_VOLUME_NAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$')

# Container paths a group volume may never mount onto. Prefix semantics - a
# mountpoint equal to OR under any of these is rejected (mounting over system
# dirs, the conda env, or the per-user /home tree would break or hijack the lab).
PROTECTED_MOUNTPOINTS = (
    '/bin', '/boot', '/dev', '/etc', '/home', '/lib', '/lib64', '/opt',
    '/proc', '/root', '/run', '/sbin', '/srv', '/sys', '/tmp', '/usr', '/var',
)


def is_protected_mountpoint(path):
    """True when ``path`` is ``/``, a protected dir, or nested under one."""
    norm = '/' + (path or '').strip().strip('/')
    if norm == '/':
        return True
    return any(norm == p or norm.startswith(p + '/') for p in PROTECTED_MOUNTPOINTS)


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


# ── Context + error types ────────────────────────────────────────────────────

@dataclass(frozen=True)
class PolicyCtx:
    """Inputs a resolve/coerce needs that are not in the group config itself."""
    gpu_available: bool = False
    reserved_names: frozenset = frozenset()
    reserved_prefixes: tuple = ()


class PolicyCoerceError(Exception):
    """Raised by a type's ``coerce`` to reject an admin write.

    ``structured`` selects the response shape: structured errors render the
    stable ``{'error': code, 'message': ..., **extra}`` JSON (reserved-name
    rejections); plain errors map to a bare HTTP 400 with the message.
    """

    def __init__(self, message, *, code=None, extra=None, structured=False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.extra = extra or {}
        self.structured = structured


@dataclass(frozen=True)
class PolicyType:
    key: str
    default: dict
    resolve: Callable
    coerce: Optional[Callable] = None
    validate: Optional[Callable] = None
    validate_code: str = ''
    summarize: Optional[Callable] = None


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


# ── env_vars ─────────────────────────────────────────────────────────────────

def _resolve_env_vars(matched, ctx):
    env_vars, skipped, env_var_source = {}, [], {}
    for idx, cfg in enumerate(matched):
        inner = cfg.get('config') or {}
        if not inner.get('env_vars_active', True):
            continue
        for entry in (inner.get('env_vars') or []):
            name = (entry.get('name') or '').strip()
            if not name:
                continue
            if is_reserved_env_var(name, ctx.reserved_names, ctx.reserved_prefixes):
                if name not in skipped:
                    skipped.append(name)
                continue
            if name in env_vars:
                continue
            value = entry.get('value', '')
            env_vars[name] = '' if value is None else str(value)
            env_var_source[name] = idx
    return {'env_vars': env_vars, 'env_var_source': env_var_source,
            'skipped_env_vars': skipped}


def _coerce_env_vars(body, existing, ctx):
    out = {}
    if 'env_vars' in body:
        env_vars = body['env_vars']
        if not isinstance(env_vars, list):
            raise PolicyCoerceError("env_vars must be a list")
        for var in env_vars:
            if not isinstance(var, dict) or 'name' not in var:
                raise PolicyCoerceError("Each env_var must have a 'name' field")
        rejected = sorted({
            var['name'] for var in env_vars
            if is_reserved_env_var(var['name'], ctx.reserved_names, ctx.reserved_prefixes)
        })
        if rejected:
            raise PolicyCoerceError(
                "Reserved variable names cannot be set in group config: "
                + ", ".join(rejected)
                + ". These are controlled by JupyterHub or the platform configuration.",
                code='reserved_env_var_names', extra={'rejected': rejected}, structured=True)
        out['env_vars'] = env_vars
    if 'env_vars_active' in body:
        out['env_vars_active'] = bool(body['env_vars_active'])
    return out


# ── gpu ──────────────────────────────────────────────────────────────────────

def _resolve_gpu(matched, ctx):
    requested = all_gpus = False
    device_ids = set()
    for cfg in matched:
        inner = cfg.get('config') or {}
        if inner.get('gpu_access'):
            requested = True
            if inner.get('gpu_all', True):
                all_gpus = True
            else:
                for did in (inner.get('gpu_device_ids') or []):
                    device_ids.add(str(did))
    if requested and not all_gpus and not device_ids:
        all_gpus = True
    return {
        'gpu_access': bool(requested and ctx.gpu_available),
        'gpu_all': bool(all_gpus),
        'gpu_device_ids': sorted(device_ids, key=lambda x: (len(x), x)),
    }


def _coerce_gpu(body, existing, ctx):
    out = {}
    if 'gpu_access' in body:
        out['gpu_access'] = bool(body['gpu_access'])
    if 'gpu_all' in body:
        out['gpu_all'] = bool(body['gpu_all'])
    if 'gpu_device_ids' in body:
        ids = body['gpu_device_ids']
        if not isinstance(ids, list):
            raise PolicyCoerceError("gpu_device_ids must be a list")
        out['gpu_device_ids'] = [str(x) for x in ids]
    return out


def _validate_gpu(config):
    if not config.get('gpu_access'):
        return True, ''
    if config.get('gpu_all', True):
        return True, ''
    if not (config.get('gpu_device_ids') or []):
        return False, 'Select at least one GPU, or enable "All GPUs".'
    return True, ''


# ── docker ───────────────────────────────────────────────────────────────────

def _resolve_docker(matched, ctx):
    docker_access = docker_limited = docker_privileged = False
    allow_dangerous = compose_enabled = compose_override = hub_network = False
    dl_quota = {k: 0 for k in _DL_DEFAULTS}
    for cfg in matched:
        inner = cfg.get('config') or {}
        docker_active = inner.get('docker_active', True)
        if docker_active and inner.get('docker_access'):
            docker_access = True
        if docker_active and inner.get('docker_limited'):
            docker_limited = True
            for key in _DL_DEFAULTS:
                try:
                    val = float(inner.get(f'docker_limited_{key}') or 0)
                except (TypeError, ValueError):
                    val = 0.0
                if val > dl_quota[key]:
                    dl_quota[key] = val
            if inner.get('docker_limited_allow_dangerous_flags'):
                allow_dangerous = True
            if inner.get('docker_limited_user_compose_project_enabled'):
                compose_enabled = True
            if inner.get('docker_limited_user_compose_project_allow_override'):
                compose_override = True
            if inner.get('docker_limited_hub_network_access'):
                hub_network = True
        if docker_active and inner.get('docker_privileged'):
            docker_privileged = True
    # Raw socket supersedes the filtered proxy: wider wins and a raw socket makes
    # the filtered one moot, so limited and its bypass flags collapse.
    if docker_access:
        docker_limited = allow_dangerous = compose_enabled = compose_override = hub_network = False
    if docker_limited:
        for key, default in _DL_DEFAULTS.items():
            if dl_quota[key] <= 0:
                dl_quota[key] = default
    return {
        'docker_access': docker_access,
        'docker_limited': docker_limited,
        'docker_limited_max_containers': int(dl_quota['max_containers']),
        'docker_limited_max_volumes': int(dl_quota['max_volumes']),
        'docker_limited_max_networks': int(dl_quota['max_networks']),
        'docker_limited_max_storage_gb': dl_quota['max_storage_gb'],
        'docker_limited_cpu_cap_cores': dl_quota['cpu_cap_cores'],
        'docker_limited_mem_cap_gb': dl_quota['mem_cap_gb'],
        'docker_limited_allow_dangerous_flags': allow_dangerous,
        'docker_limited_user_compose_project_enabled': compose_enabled,
        'docker_limited_user_compose_project_allow_override': compose_override,
        'docker_limited_hub_network_access': hub_network,
        'docker_privileged': docker_privileged,
    }


_DL_INT_KEYS = ('docker_limited_max_containers', 'docker_limited_max_volumes',
                'docker_limited_max_networks')
_DL_FLOAT_KEYS = ('docker_limited_max_storage_gb', 'docker_limited_cpu_cap_cores',
                  'docker_limited_mem_cap_gb')
_DL_BOOL_KEYS = ('docker_limited_allow_dangerous_flags',
                 'docker_limited_user_compose_project_enabled',
                 'docker_limited_user_compose_project_allow_override',
                 'docker_limited_hub_network_access')


def _coerce_docker(body, existing, ctx):
    out = {}
    for key in ('docker_active', 'docker_access', 'docker_limited', 'docker_privileged'):
        if key in body:
            out[key] = bool(body[key])
    for key in _DL_INT_KEYS:
        if key in body:
            try:
                out[key] = max(0, int(body[key]))
            except (TypeError, ValueError):
                out[key] = 0
    for key in _DL_FLOAT_KEYS:
        if key in body:
            try:
                out[key] = max(0.0, round(float(body[key]), 1))
            except (TypeError, ValueError):
                out[key] = 0
    for key in _DL_BOOL_KEYS:
        if key in body:
            out[key] = bool(body[key])
    return out


def _validate_docker(config):
    if 'docker_active' in config and not config.get('docker_active'):
        return True, ''
    if config.get('docker_access') and config.get('docker_limited'):
        return False, 'A group cannot grant both normal and limited Docker access - choose one.'
    if config.get('docker_limited'):
        for key in _DL_INT_KEYS + _DL_FLOAT_KEYS:
            try:
                val = float(config.get(key) or 0)
            except (TypeError, ValueError):
                return False, f'{key} must be a number.'
            if val < 0:
                return False, f'{key} cannot be negative.'
    return True, ''


# ── mem ──────────────────────────────────────────────────────────────────────

def _resolve_mem(matched, ctx):
    mem_limit_gb = None
    mem_swap_disabled = False
    for cfg in matched:
        inner = cfg.get('config') or {}
        if inner.get('mem_limit_enabled'):
            try:
                val = float(inner.get('mem_limit_gb') or 0)
            except (TypeError, ValueError):
                val = 0.0
            if val > 0 and (mem_limit_gb is None or val > mem_limit_gb):
                mem_limit_gb = val
                mem_swap_disabled = bool(inner.get('mem_swap_disabled'))
    return {'mem_limit_gb': mem_limit_gb, 'mem_swap_disabled': mem_swap_disabled}


def _coerce_mem(body, existing, ctx):
    out = {}
    if 'mem_limit_enabled' in body:
        out['mem_limit_enabled'] = bool(body['mem_limit_enabled'])
    if 'mem_limit_gb' in body:
        try:
            gb = float(body['mem_limit_gb'])
        except (TypeError, ValueError):
            gb = 0.0
        out['mem_limit_gb'] = max(0.0, round(gb, 1))
    if 'mem_swap_disabled' in body:
        out['mem_swap_disabled'] = bool(body['mem_swap_disabled'])
    return out


def _validate_mem(config):
    if not config.get('mem_limit_enabled'):
        return True, ''
    try:
        gb = float(config.get('mem_limit_gb') or 0)
    except (TypeError, ValueError):
        return False, 'Memory limit (GB) must be a number.'
    if gb <= 0:
        return False, 'Memory limit (GB) must be greater than zero when enabled.'
    return True, ''


# ── cpu ──────────────────────────────────────────────────────────────────────

def _resolve_cpu(matched, ctx):
    cpu_limit_cores = None
    for cfg in matched:
        inner = cfg.get('config') or {}
        if inner.get('cpu_limit_enabled'):
            try:
                cval = float(inner.get('cpu_limit_cores') or 0)
            except (TypeError, ValueError):
                cval = 0.0
            if cval > 0:
                cpu_limit_cores = cval if cpu_limit_cores is None else max(cpu_limit_cores, cval)
    return {'cpu_limit_cores': cpu_limit_cores}


def _coerce_cpu(body, existing, ctx):
    out = {}
    if 'cpu_limit_enabled' in body:
        out['cpu_limit_enabled'] = bool(body['cpu_limit_enabled'])
    if 'cpu_limit_cores' in body:
        try:
            cores = float(body['cpu_limit_cores'])
        except (TypeError, ValueError):
            cores = 0.0
        out['cpu_limit_cores'] = max(0.0, round(cores, 1))
    return out


def _validate_cpu(config):
    if not config.get('cpu_limit_enabled'):
        return True, ''
    try:
        cores = float(config.get('cpu_limit_cores') or 0)
    except (TypeError, ValueError):
        return False, 'CPU limit (cores) must be a number.'
    if cores <= 0:
        return False, 'CPU limit (cores) must be greater than zero when enabled.'
    return True, ''


# ── sudo / downloads (section-gated, priority-wins, None unconfigured) ────────

def _make_gated_resolve(active_key, value_key, out_key):
    def _resolve(matched, ctx):
        value = None
        for cfg in matched:
            inner = cfg.get('config') or {}
            if value is None and inner.get(active_key):
                value = bool(inner.get(value_key))
        return {out_key: value}
    return _resolve


def _make_gated_coerce(active_key, value_key):
    def _coerce(body, existing, ctx):
        out = {}
        if active_key in body:
            out[active_key] = bool(body[active_key])
        if value_key in body:
            out[value_key] = bool(body[value_key])
        return out
    return _coerce


# ── api_keys ─────────────────────────────────────────────────────────────────

def _resolve_api_keys(matched, ctx):
    pools = []
    for idx, cfg in enumerate(matched):
        inner = cfg.get('config') or {}
        pool = normalize_pool(inner.get('api_keys_pool'))
        if pool is not None:
            pool['pool_id'] = cfg.get('group_name')
            pool['group_index'] = idx
            pools.append(pool)
    return {'api_key_pools': pools}


def _coerce_api_keys(body, existing, ctx):
    out = {}
    if 'api_keys_pool' in body:
        pool_in = body['api_keys_pool']
        if not isinstance(pool_in, dict):
            raise PolicyCoerceError("api_keys_pool must be an object")
        names = [pool_in.get('env_var_id'), pool_in.get('env_var_secret'),
                 pool_in.get('env_var_key')]
        rejected = sorted({
            n for n in names
            if n and is_reserved_env_var(n, ctx.reserved_names, ctx.reserved_prefixes)
        })
        if pool_in.get('enabled') and rejected:
            raise PolicyCoerceError(
                "Reserved variable names cannot be used for the API keys pool: "
                + ", ".join(rejected)
                + ". These are controlled by JupyterHub or the platform configuration.",
                code='reserved_env_var_names', extra={'rejected': rejected}, structured=True)
        existing_pool = (existing or {}).get('api_keys_pool') or {}
        out['api_keys_pool'] = merge_pool_on_save(pool_in, existing_pool)
    return out


def _validate_api_keys(config):
    pool = config.get('api_keys_pool') or {}
    if not pool.get('enabled'):
        return True, ''
    mode = pool.get('mode')
    if mode not in ('pair', 'single'):
        return False, 'Select an API keys pool mode: key-id/secret pair or single api key.'
    creds = pool.get('credentials') or []
    if mode == 'pair':
        if not (pool.get('env_var_id') or '').strip() or not (pool.get('env_var_secret') or '').strip():
            return False, 'Pair mode requires both a key-id and a key-secret variable name.'
        for c in creds:
            if not (c.get('id') or '').strip() or not (c.get('secret') or '').strip():
                return False, 'Every pair credential needs both an id and a secret.'
    else:
        if not (pool.get('env_var_key') or '').strip():
            return False, 'Single mode requires an api-key variable name.'
        for c in creds:
            if not (c.get('key') or '').strip():
                return False, 'Every single credential needs a key value.'
    return True, ''


# ── volume_mounts ────────────────────────────────────────────────────────────

def _resolve_volume_mounts(matched, ctx):
    volume_mounts = {}
    skipped = []
    for cfg in matched:
        inner = cfg.get('config') or {}
        if not inner.get('volume_mounts_active', True):
            continue
        for entry in (inner.get('volume_mounts') or []):
            volume = (entry.get('volume') or '').strip()
            mountpoint = (entry.get('mountpoint') or '').strip()
            if not volume or not mountpoint or not mountpoint.startswith('/'):
                continue
            norm = '/' + mountpoint.strip('/')
            if is_protected_mountpoint(norm):
                skipped.append({'volume': volume, 'mountpoint': norm,
                                'group': cfg.get('group_name'), 'reason': 'protected'})
                continue
            if norm in volume_mounts:
                if volume_mounts[norm] != volume:
                    skipped.append({'volume': volume, 'mountpoint': norm,
                                    'group': cfg.get('group_name'), 'reason': 'shadowed'})
                continue
            if volume in volume_mounts.values():
                skipped.append({'volume': volume, 'mountpoint': norm,
                                'group': cfg.get('group_name'), 'reason': 'shadowed'})
                continue
            volume_mounts[norm] = volume
    return {
        'volume_mounts': [{'volume': v, 'mountpoint': m} for m, v in volume_mounts.items()],
        'skipped_volume_mounts': skipped,
    }


def _coerce_volume_mounts(body, existing, ctx):
    out = {}
    if 'volume_mounts_active' in body:
        out['volume_mounts_active'] = bool(body['volume_mounts_active'])
    if 'volume_mounts' in body:
        mounts_in = body['volume_mounts']
        if not isinstance(mounts_in, list):
            raise PolicyCoerceError("volume_mounts must be a list")
        out['volume_mounts'] = [
            {'volume': (m.get('volume') or '').strip(),
             'mountpoint': (m.get('mountpoint') or '').strip()}
            for m in mounts_in if isinstance(m, dict)
        ]
    return out


def _validate_volume_mounts(config):
    if 'volume_mounts_active' in config and not config.get('volume_mounts_active'):
        return True, ''
    seen_mountpoints, seen_volumes = set(), set()
    for entry in (config.get('volume_mounts') or []):
        volume = (entry.get('volume') or '').strip()
        mountpoint = (entry.get('mountpoint') or '').strip()
        if not volume or not mountpoint:
            return False, 'Every volume mount needs both a volume name and a mountpoint.'
        if not _VOLUME_NAME_RE.match(volume):
            return False, f'Invalid volume name "{volume}" - use letters, digits, ".", "_" or "-".'
        if not mountpoint.startswith('/'):
            return False, f'Mountpoint "{mountpoint}" must be an absolute path.'
        if is_protected_mountpoint(mountpoint):
            return False, f'Mountpoint "{mountpoint}" is a protected location - mount under /mnt or /data instead.'
        norm = '/' + mountpoint.strip('/')
        if norm in seen_mountpoints:
            return False, f'Duplicate mountpoint "{norm}" - each mountpoint can hold one volume.'
        if volume in seen_volumes:
            return False, f'Volume "{volume}" is listed twice - a volume can be mounted at one mountpoint only.'
        seen_mountpoints.add(norm)
        seen_volumes.add(volume)
    return True, ''


# ── summarize (display facet: one group's config -> badge + tooltip line) ─────
# Each returns {'badge': <chip>, 'detail': <tooltip line>} when the section is
# active/configured, else None. The admin UI renders these strings verbatim - no
# policy-display logic lives in the browser.

def _summarize_env_vars(c):
    n = len(c.get('env_vars') or [])
    if c.get('env_vars_active') and n:
        return {'badge': f"{n} Var{'s' if n != 1 else ''}",
                'detail': f"Environment Variables: {n} var{'s' if n != 1 else ''}"}
    return None


def _summarize_gpu(c):
    if not c.get('gpu_access'):
        return None
    if c.get('gpu_all', True):
        return {'badge': 'GPU', 'detail': 'GPU: all'}
    ids = c.get('gpu_device_ids') or []
    return {'badge': 'GPU', 'detail': 'GPU: ' + (','.join(str(i) for i in ids) if ids else 'all')}


def _summarize_docker(c):
    if not c.get('docker_active'):
        return None
    parts = []
    if c.get('docker_access'):
        parts.append('Docker: raw socket')
    elif c.get('docker_limited'):
        parts.append('Docker: limited')
    if c.get('docker_privileged'):
        parts.append('privileged')
    if not parts:
        return None
    return {'badge': 'Docker', 'detail': ' + '.join(parts)}


def _summarize_cpu(c):
    if c.get('cpu_limit_enabled') and float(c.get('cpu_limit_cores') or 0) > 0:
        return {'badge': 'CPU', 'detail': f"CPU: {c.get('cpu_limit_cores')} cores"}
    return None


def _summarize_mem(c):
    if c.get('mem_limit_enabled') and float(c.get('mem_limit_gb') or 0) > 0:
        detail = f"Memory: {c.get('mem_limit_gb')}G"
        if c.get('mem_swap_disabled'):
            detail += ' (no swap)'
        return {'badge': 'Mem', 'detail': detail}
    return None


def _summarize_sudo(c):
    if c.get('sudo_active'):
        state = 'on' if c.get('sudo_enable') else 'off'
        return {'badge': f'Sudo {state}', 'detail': f'Sudo: {state}'}
    return None


def _summarize_downloads(c):
    if c.get('downloads_active'):
        on = bool(c.get('downloads_allow'))
        return {'badge': 'Downloads ' + ('on' if on else 'off'),
                'detail': 'Downloads: ' + ('on' if on else 'blocked')}
    return None


def _summarize_api_keys(c):
    pool = c.get('api_keys_pool') or {}
    if pool.get('enabled'):
        n = len(pool.get('credentials') or [])
        return {'badge': 'Keys',
                'detail': f"API Keys pool: {n} credential{'s' if n != 1 else ''}"}
    return None


def _summarize_volume_mounts(c):
    n = len(c.get('volume_mounts') or [])
    if c.get('volume_mounts_active') and n:
        return {'badge': 'Volumes',
                'detail': f"Volume Mounts: {n} mount{'s' if n != 1 else ''}"}
    return None


# ── The registry ─────────────────────────────────────────────────────────────
# Order matters only for validate (first failure wins): the validate-bearing
# types here are gpu, docker, cpu, mem, api_keys, volume_mounts - the same order
# the legacy GroupConfigValidator._ALL used.

POLICY_TYPES = [
    PolicyType(
        key='env_vars',
        default={'env_vars_active': False, 'env_vars': []},
        resolve=_resolve_env_vars, coerce=_coerce_env_vars,
        summarize=_summarize_env_vars,
    ),
    PolicyType(
        key='gpu',
        default={'gpu_access': False, 'gpu_all': True, 'gpu_device_ids': []},
        resolve=_resolve_gpu, coerce=_coerce_gpu,
        summarize=_summarize_gpu,
        validate=_validate_gpu, validate_code='invalid_gpu_selection',
    ),
    PolicyType(
        key='docker',
        default={
            'docker_active': False, 'docker_access': False, 'docker_limited': False,
            'docker_limited_max_containers': 10, 'docker_limited_max_volumes': 10,
            'docker_limited_max_networks': 3, 'docker_limited_max_storage_gb': 50,
            'docker_limited_cpu_cap_cores': 2, 'docker_limited_mem_cap_gb': 8,
            'docker_limited_allow_dangerous_flags': False,
            'docker_limited_user_compose_project_enabled': True,
            'docker_limited_user_compose_project_allow_override': True,
            'docker_limited_hub_network_access': True,
            'docker_privileged': False,
        },
        resolve=_resolve_docker, coerce=_coerce_docker,
        summarize=_summarize_docker,
        validate=_validate_docker, validate_code='invalid_docker_selection',
    ),
    PolicyType(
        key='cpu',
        default={'cpu_limit_enabled': False, 'cpu_limit_cores': 0},
        resolve=_resolve_cpu, coerce=_coerce_cpu,
        summarize=_summarize_cpu,
        validate=_validate_cpu, validate_code='invalid_cpu_limit',
    ),
    PolicyType(
        key='mem',
        default={'mem_limit_enabled': False, 'mem_limit_gb': 0, 'mem_swap_disabled': False},
        resolve=_resolve_mem, coerce=_coerce_mem,
        summarize=_summarize_mem,
        validate=_validate_mem, validate_code='invalid_mem_limit',
    ),
    PolicyType(
        key='sudo',
        default={'sudo_active': False, 'sudo_enable': True},
        resolve=_make_gated_resolve('sudo_active', 'sudo_enable', 'sudo_enable'),
        coerce=_make_gated_coerce('sudo_active', 'sudo_enable'),
        summarize=_summarize_sudo,
    ),
    PolicyType(
        key='downloads',
        default={'downloads_active': False, 'downloads_allow': True},
        resolve=_make_gated_resolve('downloads_active', 'downloads_allow', 'downloads_allow'),
        coerce=_make_gated_coerce('downloads_active', 'downloads_allow'),
        summarize=_summarize_downloads,
    ),
    PolicyType(
        key='api_keys',
        default={'api_keys_pool': {
            'enabled': False, 'mode': '', 'env_var_id': '', 'env_var_secret': '',
            'env_var_key': '', 'credentials': [],
        }},
        resolve=_resolve_api_keys, coerce=_coerce_api_keys,
        summarize=_summarize_api_keys,
        validate=_validate_api_keys, validate_code='invalid_api_keys_pool',
    ),
    PolicyType(
        key='volume_mounts',
        default={'volume_mounts_active': False, 'volume_mounts': []},
        resolve=_resolve_volume_mounts, coerce=_coerce_volume_mounts,
        summarize=_summarize_volume_mounts,
        validate=_validate_volume_mounts, validate_code='invalid_volume_mounts',
    ),
]


def default_config():
    """Assemble the default group config from every type's off-state slice."""
    out = {}
    for pt in POLICY_TYPES:
        out.update(copy.deepcopy(pt.default))
    return out
