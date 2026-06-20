"""Policy models - the single source of truth for group permissions.

Every group permission is one ``Policy`` subclass (a model) owning its whole
lifecycle: ``default`` (data), ``coerce``/``validate`` (write), ``resolve``
(combine across a user's groups), ``summarize`` (display), ``apply`` (impose on
a spawning server - the controller) and ``on_hub_startup`` (re-impose for
servers that survived a hub restart). ``POLICY_TYPES`` is the ordered list of
model instances the engine loops over.

Top-level imports stay light (``base`` + ``api_keys_pool``, both stdlib-only at
import); the ``apply``/``on_hub_startup`` bodies import docker / jupyterhub /
tornado lazily, so importing this module pulls in nothing heavy and there is no
cycle with ``groups_config`` (which imports *this*, never the reverse).
"""

import copy
import math
from urllib.parse import urlparse

from ..api_keys_pool import merge_pool_on_save, normalize_pool
from .base import (
    _VOLUME_NAME_RE,
    DEFAULT_VOLUME_MODE,
    SHARED_MOUNTPOINT,
    VOLUME_MODES,
    Policy,
    PolicyCoerceError,
    is_protected_mountpoint,
    is_reserved_env_var,
)


def _coerce_mode(value):
    """Normalise an access-mode value to 'ro'/'rw' (default rw)."""
    v = (value or '').strip().lower()
    return v if v in VOLUME_MODES else DEFAULT_VOLUME_MODE


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
_DL_INT_KEYS = ('docker_limited_max_containers', 'docker_limited_max_volumes',
                'docker_limited_max_networks')
_DL_FLOAT_KEYS = ('docker_limited_max_storage_gb', 'docker_limited_cpu_cap_cores',
                  'docker_limited_mem_cap_gb')
_DL_BOOL_KEYS = ('docker_limited_allow_dangerous_flags',
                 'docker_limited_user_compose_project_enabled',
                 'docker_limited_user_compose_project_allow_override',
                 'docker_limited_hub_network_access')


# ── Download-block CHP overlay helpers (owned by DownloadsPolicy) ─────────────
# Per-user CHP route prefixes overlaid onto a download-blocked user's lab so the
# download surfaces route to the hub instead of the container. files/ and
# nbconvert/ are mixed inline+download (FilesGuardHandler proxies the inline
# part); the two extension prefixes are pure downloads (DownloadBlockHandler
# 403s them). Suffixes are relative to `{base_url}user/{username}/`.
_DOWNLOAD_BLOCK_SUFFIXES = (
    'files/',
    'nbconvert/',
    'jupyterlab-export-markdown-extension/export/',
    'jupyterlab-share-files-extension/public/share/',
)


def _inject_download_handlers(app):
    """Inject the download-guard Tornado handlers once, outside the /hub/ prefix
    (same technique as the favicon handler). Idempotent via a flag on the app."""
    if getattr(app, '_downloads_handlers_injected', False):
        return
    from tornado.web import url
    from ..handlers.downloads import DownloadBlockHandler, FilesGuardHandler

    rules = [
        url(app.base_url + r'user/([^/]+)/(files/.*)', FilesGuardHandler),
        url(app.base_url + r'user/([^/]+)/(nbconvert/.*)', FilesGuardHandler),
        url(app.base_url + r'user/([^/]+)/(jupyterlab-export-markdown-extension/export/.*)',
            DownloadBlockHandler),
        url(app.base_url + r'user/([^/]+)/(jupyterlab-share-files-extension/public/share/.*)',
            DownloadBlockHandler),
    ]
    for rule in rules:
        app.tornado_application.wildcard_router.rules.insert(0, rule)
    app._downloads_handlers_injected = True
    app.log.info("[Downloads] Injected download-guard handlers")


async def _register_download_block(app, username, hub_target):
    """Overlay the per-user download-block CHP routes (idempotent). Registered in
    extra_routes so the periodic check_routes() does not reap them."""
    for suffix in _DOWNLOAD_BLOCK_SUFFIXES:
        routespec = app.proxy.validate_routespec(f'{app.base_url}user/{username}/{suffix}')
        await app.proxy.add_route(routespec, hub_target, {})
        app.proxy.extra_routes[routespec] = hub_target


async def _unregister_download_block(app, username):
    """Remove any per-user download-block CHP routes (e.g. the user moved into a
    downloads-allowed group). Best-effort - a missing route is fine."""
    for suffix in _DOWNLOAD_BLOCK_SUFFIXES:
        routespec = app.proxy.validate_routespec(f'{app.base_url}user/{username}/{suffix}')
        app.proxy.extra_routes.pop(routespec, None)
        try:
            await app.proxy.delete_route(routespec)
        except Exception:
            pass


# ── env_vars ─────────────────────────────────────────────────────────────────

class EnvVarsPolicy(Policy):
    key = 'env_vars'

    def default(self):
        return {'env_vars_active': False, 'env_vars': []}

    def resolve(self, matched, ctx):
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

    def coerce(self, body, existing, ctx):
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

    def summarize(self, c):
        n = len(c.get('env_vars') or [])
        if c.get('env_vars_active') and n:
            return {'badge': f"{n} Var{'s' if n != 1 else ''}",
                    'detail': f"Environment Variables: {n} var{'s' if n != 1 else ''}"}
        return None

    async def apply(self, spawner, resolved, actx):
        # Inject user-defined env vars from groups (reserved names already filtered)
        if resolved['env_vars']:
            spawner.environment.update(resolved['env_vars'])


# ── gpu ──────────────────────────────────────────────────────────────────────

class GpuPolicy(Policy):
    key = 'gpu'
    validate_code = 'invalid_gpu_selection'

    def default(self):
        return {'gpu_access': False, 'gpu_all': True, 'gpu_device_ids': []}

    def resolve(self, matched, ctx):
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

    def coerce(self, body, existing, ctx):
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

    def validate(self, config):
        if not config.get('gpu_access'):
            return True, ''
        if config.get('gpu_all', True):
            return True, ''
        if not (config.get('gpu_device_ids') or []):
            return False, 'Select at least one GPU, or enable "All GPUs".'
        return True, ''

    def summarize(self, c):
        if not c.get('gpu_access'):
            return None
        if c.get('gpu_all', True):
            return {'badge': 'GPU', 'detail': 'GPU: all'}
        ids = c.get('gpu_device_ids') or []
        return {'badge': 'GPU', 'detail': 'GPU: ' + (','.join(str(i) for i in ids) if ids else 'all')}

    async def apply(self, spawner, resolved, actx):
        # GPU device passthrough (per-user). gpu_access is already gated on
        # hardware availability in the resolver, so on a GPU-less host this branch
        # is skipped entirely and no device_requests are set - spawns never crash.
        # All GPUs -> Count -1; specific GPUs -> DeviceIDs (index strings). Empty
        # selection falls back to all (the resolver/validator prevent that state).
        if resolved['gpu_access']:
            if resolved.get('gpu_all', True) or not resolved.get('gpu_device_ids'):
                gpu_request = {'Driver': 'nvidia', 'Count': -1, 'Capabilities': [['gpu']]}
                spawner.environment['NVIDIA_VISIBLE_DEVICES'] = 'all'
                spawner.environment.pop('CUDA_VISIBLE_DEVICES', None)  # no restriction
            else:
                ids = list(resolved['gpu_device_ids'])
                gpu_request = {'Driver': 'nvidia', 'DeviceIDs': ids, 'Capabilities': [['gpu']]}
                # NVIDIA_VISIBLE_DEVICES (host indices) is the toolkit's authoritative
                # selector and overrides the image's baked-in 'all'. It enforces the
                # subset on native Linux (per-GPU /dev/nvidiaN nodes); on WSL2/Docker
                # Desktop GPUs come through a single /dev/dxg and it is NOT enforced.
                spawner.environment['NVIDIA_VISIBLE_DEVICES'] = ','.join(ids)
                # CUDA_VISIBLE_DEVICES by UUID so CUDA targets the right physical GPU
                # whether it was re-indexed to 0 (native Linux, only the subset
                # injected) or all GPUs are visible (WSL2). Soft, app-level: nvidia-smi
                # still shows all on WSL2 and a user can override it. UUIDs are
                # order-independent, unlike host indices which break once re-indexed.
                uuid_map = actx.gpu_uuid_by_index or {}
                uuids = [uuid_map[i] for i in ids if i in uuid_map]
                spawner.environment['CUDA_VISIBLE_DEVICES'] = ','.join(uuids) if uuids else ','.join(ids)
            spawner.extra_host_config['device_requests'] = [gpu_request]
            spawner.environment['ENABLE_GPU_SUPPORT'] = '1'
            spawner.environment['ENABLE_GPUSTAT'] = '1'
        else:
            spawner.extra_host_config.pop('device_requests', None)
            spawner.environment['NVIDIA_VISIBLE_DEVICES'] = 'void'  # override image default 'all'
            spawner.environment.pop('CUDA_VISIBLE_DEVICES', None)
            spawner.environment['ENABLE_GPU_SUPPORT'] = '0'
            spawner.environment['ENABLE_GPUSTAT'] = '0'


# ── docker ───────────────────────────────────────────────────────────────────

class DockerPolicy(Policy):
    key = 'docker'
    validate_code = 'invalid_docker_selection'

    def default(self):
        return {
            'docker_active': False, 'docker_access': False, 'docker_limited': False,
            'docker_limited_max_containers': 10, 'docker_limited_max_volumes': 10,
            'docker_limited_max_networks': 3, 'docker_limited_max_storage_gb': 50,
            'docker_limited_cpu_cap_cores': 2, 'docker_limited_mem_cap_gb': 8,
            'docker_limited_allow_dangerous_flags': False,
            'docker_limited_user_compose_project_enabled': True,
            'docker_limited_user_compose_project_allow_override': True,
            'docker_limited_hub_network_access': True,
            'docker_privileged': False,
        }

    def resolve(self, matched, ctx):
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

    def coerce(self, body, existing, ctx):
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

    def validate(self, config):
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

    def summarize(self, c):
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

    async def apply(self, spawner, resolved, actx):
        username = actx.username
        # Docker access. Normal (raw socket) supersedes limited (proxy) - the
        # resolver already cleared docker_limited when docker_access is set.
        if resolved['docker_access']:
            # Normal: mount the raw host socket (sees all, no quota).
            spawner.volumes['/var/run/docker.sock'] = '/var/run/docker.sock'
            spawner.environment.pop('DOCKER_HOST', None)
        elif resolved.get('docker_limited'):
            # Limited: the in-process docker-proxy creates a per-user listener at
            # <socket_dir>/<user>/docker.sock in the hub's filesystem (backed by
            # the named docker volume). The spawner mounts only that user's
            # subdirectory into their lab as /run/dockersock via Docker's Subpath
            # mount option, then sets DOCKER_HOST. No fallback: a proxy-setup
            # failure fails the spawn rather than silently downgrading access.
            if not actx.docker_proxy_socket_dir or not actx.docker_proxy_volume_name:
                raise RuntimeError(
                    f"limited docker requested for {username} but proxy is not "
                    f"configured (socket_dir={actx.docker_proxy_socket_dir!r} "
                    f"volume_name={actx.docker_proxy_volume_name!r}). "
                    "Both must be set; see config/jupyterhub_config.py."
                )
            from ..docker_proxy import register_user
            _socket_host_path, mount_dir, docker_host = await register_user(
                username,
                resolved,
                socket_dir=actx.docker_proxy_socket_dir,
                compose_project=actx.compose_project,
                user_compose_project_template=actx.user_compose_project_template,
                hub_network_name=actx.hub_network_name,
            )
            spawner.extra_host_config.setdefault('mounts', []).append({
                'Type': 'volume',
                'Source': actx.docker_proxy_volume_name,
                'Target': mount_dir,
                'ReadOnly': False,
                'VolumeOptions': {'Subpath': username},
            })
            spawner.environment['DOCKER_HOST'] = docker_host
            spawner.volumes.pop('/var/run/docker.sock', None)
        else:
            spawner.volumes.pop('/var/run/docker.sock', None)
            spawner.environment.pop('DOCKER_HOST', None)

        # Privileged container mode
        if resolved['docker_privileged']:
            spawner.extra_host_config['privileged'] = True
        else:
            spawner.extra_host_config.pop('privileged', None)

    async def on_hub_startup(self, app, actx):
        """Re-register limited-docker users with the in-process docker-proxy after
        a hub restart (the proxy lives in the hub process; per-user socket files
        survive in the backing volume but no UnixSite is bound on a fresh boot).
        pre_spawn_hook only fires on new spawns, so this heals survivors."""
        if not actx.docker_proxy_socket_dir or not actx.docker_proxy_volume_name:
            return
        from jupyterhub import orm
        from ..docker_proxy import register_user
        from ..groups_config import GroupsConfigManager
        from .engine import resolve_policies

        try:
            all_configs = GroupsConfigManager.get_instance().get_all_configs()
        except Exception as e:
            app.log.error(f"[DockerProxy Startup] Failed to load group configs: {e}")
            all_configs = []

        count = 0
        for orm_user in app.db.query(orm.User).all():
            user = app.users.get(orm_user.name)
            if not (user and user.spawner and user.spawner.active):
                continue
            username = user.name
            resolved = resolve_policies(
                user_group_names=[g.name for g in user.groups],
                all_group_configs=all_configs,
                gpu_available=actx.gpu_available,
                reserved_names=actx.reserved_names,
                reserved_prefixes=actx.reserved_prefixes,
            )
            # docker_access (raw socket) supersedes proxy; nothing to re-register.
            if resolved['docker_access'] or not resolved.get('docker_limited'):
                continue
            try:
                await register_user(
                    username,
                    resolved,
                    socket_dir=actx.docker_proxy_socket_dir,
                    compose_project=actx.compose_project,
                    user_compose_project_template=actx.user_compose_project_template,
                    hub_network_name=actx.hub_network_name,
                )
                count += 1
                app.log.info(
                    f"[DockerProxy Startup] Re-registered user={username} "
                    f"(container survived hub restart)"
                )
            except Exception as e:
                app.log.error(
                    f"[DockerProxy Startup] Failed to re-register user={username}: {e}"
                )
        if count:
            app.log.info(
                f"[DockerProxy Startup] Re-registered {count} limited-docker "
                "user(s) with in-process proxy"
            )


# ── cpu ──────────────────────────────────────────────────────────────────────

class CpuPolicy(Policy):
    key = 'cpu'
    validate_code = 'invalid_cpu_limit'

    def default(self):
        return {'cpu_limit_enabled': False, 'cpu_limit_cores': 0}

    def resolve(self, matched, ctx):
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

    def coerce(self, body, existing, ctx):
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

    def validate(self, config):
        if not config.get('cpu_limit_enabled'):
            return True, ''
        try:
            cores = float(config.get('cpu_limit_cores') or 0)
        except (TypeError, ValueError):
            return False, 'CPU limit (cores) must be a number.'
        if cores <= 0:
            return False, 'CPU limit (cores) must be greater than zero when enabled.'
        return True, ''

    def summarize(self, c):
        if c.get('cpu_limit_enabled') and float(c.get('cpu_limit_cores') or 0) > 0:
            return {'badge': 'CPU', 'detail': f"CPU: {c.get('cpu_limit_cores')} cores"}
        return None

    async def apply(self, spawner, resolved, actx):
        # resolved cores -> spawner.cpu_limit (DockerSpawner maps it to
        # cpu_quota = cpu_limit * cpu_period). Ceil to whole cores so a fractional
        # cap never rounds down to a zero-core quota (Docker treats 0 as
        # unlimited); min 1 core whenever a cap is set.
        if resolved.get('cpu_limit_cores'):
            spawner.cpu_limit = float(max(1, math.ceil(float(resolved['cpu_limit_cores']))))
        else:
            spawner.cpu_limit = None


# ── mem ──────────────────────────────────────────────────────────────────────

class MemPolicy(Policy):
    key = 'mem'
    validate_code = 'invalid_mem_limit'

    def default(self):
        return {'mem_limit_enabled': False, 'mem_limit_gb': 0, 'mem_swap_disabled': False}

    def resolve(self, matched, ctx):
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

    def coerce(self, body, existing, ctx):
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

    def validate(self, config):
        if not config.get('mem_limit_enabled'):
            return True, ''
        try:
            gb = float(config.get('mem_limit_gb') or 0)
        except (TypeError, ValueError):
            return False, 'Memory limit (GB) must be a number.'
        if gb <= 0:
            return False, 'Memory limit (GB) must be greater than zero when enabled.'
        return True, ''

    def summarize(self, c):
        if c.get('mem_limit_enabled') and float(c.get('mem_limit_gb') or 0) > 0:
            detail = f"Memory: {c.get('mem_limit_gb')}G"
            if c.get('mem_swap_disabled'):
                detail += ' (no swap)'
            return {'badge': 'Mem', 'detail': detail}
        return None

    async def apply(self, spawner, resolved, actx):
        # resolved GB -> bytes for Docker HostConfig.Memory. Swap policy: when the
        # winning group disables swap, pin memswap_limit to the memory limit so
        # total (RAM+swap) == RAM (cgroup v2: memory.swap.max=0) - a hard cap that
        # OOMs at the limit instead of spilling to disk. Otherwise leave swap at
        # Docker's default (memory-swap = 2x memory).
        if resolved.get('mem_limit_gb'):
            mem_bytes = int(float(resolved['mem_limit_gb']) * 1024 ** 3)
            spawner.mem_limit = mem_bytes
            if resolved.get('mem_swap_disabled'):
                spawner.extra_host_config['memswap_limit'] = mem_bytes
            else:
                spawner.extra_host_config.pop('memswap_limit', None)
        else:
            spawner.mem_limit = None
            spawner.extra_host_config.pop('memswap_limit', None)


# ── sudo ───────────────────────────────────────────────────────────────────────

class SudoPolicy(Policy):
    key = 'sudo'

    def default(self):
        return {'sudo_active': False, 'sudo_enable': True}

    def resolve(self, matched, ctx):
        value = None
        for cfg in matched:
            inner = cfg.get('config') or {}
            if value is None and inner.get('sudo_active'):
                value = bool(inner.get('sudo_enable'))
        return {'sudo_enable': value}

    def coerce(self, body, existing, ctx):
        out = {}
        if 'sudo_active' in body:
            out['sudo_active'] = bool(body['sudo_active'])
        if 'sudo_enable' in body:
            out['sudo_enable'] = bool(body['sudo_enable'])
        return out

    def summarize(self, c):
        if c.get('sudo_active'):
            state = 'on' if c.get('sudo_enable') else 'off'
            return {'badge': f'Sudo {state}', 'detail': f'Sudo: {state}'}
        return None

    async def apply(self, spawner, resolved, actx):
        # Resolved value (highest-priority configuring group) when set, else the
        # platform default. Always injected so the image gets an explicit
        # JUPYTERLAB_SUDO_ENABLE every spawn.
        if resolved.get('sudo_enable') is not None:
            sudo_enabled = resolved['sudo_enable']
        else:
            sudo_enabled = bool(actx.lab_sudo_enable_default)
        spawner.environment['JUPYTERLAB_SUDO_ENABLE'] = '1' if sudo_enabled else '0'


# ── downloads ────────────────────────────────────────────────────────────────

class DownloadsPolicy(Policy):
    key = 'downloads'

    def default(self):
        return {'downloads_active': False, 'downloads_allow': True}

    def resolve(self, matched, ctx):
        value = None
        for cfg in matched:
            inner = cfg.get('config') or {}
            if value is None and inner.get('downloads_active'):
                value = bool(inner.get('downloads_allow'))
        return {'downloads_allow': value}

    def coerce(self, body, existing, ctx):
        out = {}
        if 'downloads_active' in body:
            out['downloads_active'] = bool(body['downloads_active'])
        if 'downloads_allow' in body:
            out['downloads_allow'] = bool(body['downloads_allow'])
        return out

    def summarize(self, c):
        if c.get('downloads_active'):
            on = bool(c.get('downloads_allow'))
            return {'badge': 'Downloads ' + ('on' if on else 'off'),
                    'detail': 'Downloads: ' + ('on' if on else 'blocked')}
        return None

    def _is_blocked(self, resolved, actx):
        downloads_allow = resolved.get('downloads_allow')
        if downloads_allow is not None:
            return not downloads_allow
        return bool(actx.block_file_downloads)

    async def apply(self, spawner, resolved, actx):
        # Best-effort, hub-side. Section-gated, priority-wins: the highest-priority
        # group whose File Downloads section is on decides; else the platform
        # default (block_file_downloads). A blocked user gets per-user CHP block
        # routes + guard handlers; an allowed user gets any stale routes removed
        # (membership change between spawns). Whole block skipped only when the
        # default is allow AND no group configures it.
        downloads_allow = resolved.get('downloads_allow')
        if not (actx.block_file_downloads or downloads_allow is not None):
            return
        app = actx.app
        username = actx.username
        if self._is_blocked(resolved, actx):
            parsed = urlparse(app.hub.url)
            hub_target = f'{parsed.scheme}://{parsed.netloc}'
            _inject_download_handlers(app)
            await _register_download_block(app, username, hub_target)
            spawner.log.info("[Downloads] block routes registered for user=%s", username)
        else:
            await _unregister_download_block(app, username)

    async def on_hub_startup(self, app, actx):
        """Re-apply download-block CHP routes for servers that survived a hub
        restart (the routes live in the hub's in-memory extra_routes, rebuilt
        only here). Dormant unless the default blocks or some group configures
        downloads."""
        from jupyterhub import orm
        from ..groups_config import GroupsConfigManager
        from .engine import resolve_policies

        try:
            all_configs = GroupsConfigManager.get_instance().get_all_configs()
        except Exception as e:
            app.log.error(f"[Downloads Startup] Failed to load group configs: {e}")
            all_configs = []

        any_configures = any(
            (c.get('config') or {}).get('downloads_active') for c in all_configs
        )
        if not actx.block_file_downloads and not any_configures:
            return

        _inject_download_handlers(app)
        parsed = urlparse(app.hub.url)
        hub_target = f'{parsed.scheme}://{parsed.netloc}'

        count = 0
        for orm_user in app.db.query(orm.User).all():
            user = app.users.get(orm_user.name)
            if not (user and user.spawner and user.spawner.active):
                continue
            resolved = resolve_policies(
                user_group_names=[g.name for g in user.groups],
                all_group_configs=all_configs,
                gpu_available=actx.gpu_available,
                reserved_names=actx.reserved_names,
                reserved_prefixes=actx.reserved_prefixes,
            )
            if self._is_blocked(resolved, actx):
                await _register_download_block(app, user.name, hub_target)
                count += 1
            else:
                await _unregister_download_block(app, user.name)
        if count:
            app.log.info(
                f"[Downloads Startup] Re-registered block routes for {count} "
                "surviving server(s)"
            )


# ── api_keys ─────────────────────────────────────────────────────────────────

class ApiKeysPolicy(Policy):
    key = 'api_keys'
    validate_code = 'invalid_api_keys_pool'

    def default(self):
        return {'api_keys_pool': {
            'enabled': False, 'mode': '', 'env_var_id': '', 'env_var_secret': '',
            'env_var_key': '', 'credentials': [],
        }}

    def resolve(self, matched, ctx):
        pools = []
        for idx, cfg in enumerate(matched):
            inner = cfg.get('config') or {}
            pool = normalize_pool(inner.get('api_keys_pool'))
            if pool is not None:
                pool['pool_id'] = cfg.get('group_name')
                pool['group_index'] = idx
                pools.append(pool)
        return {'api_key_pools': pools}

    def coerce(self, body, existing, ctx):
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

    def validate(self, config):
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

    def summarize(self, c):
        pool = c.get('api_keys_pool') or {}
        if pool.get('enabled'):
            n = len(pool.get('credentials') or [])
            return {'badge': 'Keys',
                    'detail': f"API Keys pool: {n} credential{'s' if n != 1 else ''}"}
        return None

    async def apply(self, spawner, resolved, actx):
        # Assign one credential per group pool so no two running containers share
        # a key. The durable Docker label (set via extra_create_kwargs) carries
        # the slot id - never the secret; the in-use set is rebuilt from running
        # containers, so missed stop events self-heal. Explicit group env_vars win
        # over a pool injecting the same name.
        username = actx.username
        pools = resolved.get('api_key_pools') or []
        if not pools:
            return
        from ..api_keys_pool import PoolManager
        try:
            pool_result = await PoolManager.get_instance().assign(username, pools)
        except Exception as e:
            spawner.log.error("[ApiKeys] assignment failed for %s: %s", username, e)
            pool_result = {'env': {}, 'env_sources': {}, 'labels': {}, 'assignments': []}
        # Resolve a pool-var vs plain-env-var clash by group order, not by kind:
        # the value set by the group higher in the ordered list wins (lower index =
        # higher priority). env_var_source carries the index of the group that set
        # each plain env var; env_sources carries the pool's group index. On a tie
        # the plain env var (explicit) wins.
        _env_src = resolved.get('env_var_source', {})
        for _name, _val in pool_result['env'].items():
            _plain_idx = _env_src.get(_name)
            _pool_idx = pool_result.get('env_sources', {}).get(_name, 0)
            if _plain_idx is not None and _plain_idx <= _pool_idx:
                spawner.log.info(
                    "[ApiKeys] var %s set by higher-priority group env_vars; pool value not applied", _name
                )
                continue
            if _name in resolved['env_vars']:
                spawner.log.info("[ApiKeys] var %s from pool shadows a lower-priority group env_var", _name)
            spawner.environment[_name] = _val
        if pool_result['labels']:
            _kwargs = dict(spawner.extra_create_kwargs or {})
            _labels = dict(_kwargs.get('labels') or {})
            _labels.update(pool_result['labels'])
            _kwargs['labels'] = _labels
            spawner.extra_create_kwargs = _kwargs
        for _a in pool_result['assignments']:
            if _a['slot'] is None:
                spawner.log.warning(
                    "[ApiKeys] pool=%s user=%s EXHAUSTED - env vars set empty", _a['pool_id'], username
                )
            else:
                spawner.log.info(
                    "[ApiKeys] assigned user=%s pool=%s slot=%s %s",
                    username, _a['pool_id'], _a['slot'], _a['masked'],
                )

    async def on_hub_startup(self, app, actx):
        """Rebuild the in-use slot view from running containers on hub startup and
        start the periodic reconcile. The in-use set is always re-derived from
        durable container labels, so a lab that survived the restart keeps its
        slot and a new spawn never collides with it."""
        from tornado.ioloop import PeriodicCallback
        from ..api_keys_pool import PoolManager

        try:
            summary = await PoolManager.get_instance().reconcile()
            app.log.info(
                f"[ApiKeys Startup] Observed {summary['in_use']} in-use key(s) "
                f"across {summary['pools']} pool(s)"
            )
        except Exception as e:
            app.log.warning(f"[ApiKeys Startup] reconcile failed: {e}")

        interval = actx.api_keys_reconcile_interval
        if interval and not getattr(app, '_stellars_apikeys_pc', None):
            async def _pass():
                try:
                    await PoolManager.get_instance().reconcile()
                except Exception:
                    app.log.exception("[ApiKeys] reconcile pass failed")
            pc = PeriodicCallback(_pass, interval * 1000)
            pc.start()
            app._stellars_apikeys_pc = pc  # keep a reference alive
            app.log.info(f"[ApiKeys] periodic reconcile started - interval={interval}s")


# ── volume_mounts ────────────────────────────────────────────────────────────

class VolumeMountsPolicy(Policy):
    key = 'volume_mounts'
    validate_code = 'invalid_volume_mounts'

    def default(self):
        # shared_mount_* gates the standard shared volume (resolved by label at
        # spawn, mounted at SHARED_MOUNTPOINT); volume_mounts holds custom extras.
        return {'volume_mounts_active': False,
                'shared_mount_allow': False, 'shared_mount_mode': DEFAULT_VOLUME_MODE,
                'volume_mounts': []}

    def resolve(self, matched, ctx):
        # `matched` is priority-ordered (highest first); first grant wins on any
        # conflict. The standard shared mount is collapsed to a single allow+mode
        # (applied once even via several groups); custom mounts keep volume+mode.
        shared_allow = False
        shared_mode = DEFAULT_VOLUME_MODE
        volume_mounts = {}  # mountpoint -> {'volume', 'mode'}
        skipped = []
        for cfg in matched:
            inner = cfg.get('config') or {}
            if not inner.get('volume_mounts_active', True):
                continue
            if inner.get('shared_mount_allow') and not shared_allow:
                shared_allow = True
                shared_mode = _coerce_mode(inner.get('shared_mount_mode'))
            for entry in (inner.get('volume_mounts') or []):
                volume = (entry.get('volume') or '').strip()
                mountpoint = (entry.get('mountpoint') or '').strip()
                if not volume or not mountpoint or not mountpoint.startswith('/'):
                    continue
                norm = '/' + mountpoint.strip('/')
                mode = _coerce_mode(entry.get('mode'))
                # legacy migration: a custom mount at the standard mountpoint is the
                # old one-click quick-add (stored the literal shared-volume name).
                # Fold it into the standard allow so the stale name is never mounted -
                # the standard row resolves the current name by label at apply.
                if norm == SHARED_MOUNTPOINT:
                    if not shared_allow:
                        shared_allow = True
                        shared_mode = mode
                    continue
                if is_protected_mountpoint(norm):
                    skipped.append({'volume': volume, 'mountpoint': norm,
                                    'group': cfg.get('group_name'), 'reason': 'protected'})
                    continue
                if norm in volume_mounts:
                    if volume_mounts[norm]['volume'] != volume:
                        skipped.append({'volume': volume, 'mountpoint': norm,
                                        'group': cfg.get('group_name'), 'reason': 'shadowed'})
                    continue
                if any(vm['volume'] == volume for vm in volume_mounts.values()):
                    skipped.append({'volume': volume, 'mountpoint': norm,
                                    'group': cfg.get('group_name'), 'reason': 'shadowed'})
                    continue
                volume_mounts[norm] = {'volume': volume, 'mode': mode}
        return {
            'shared_mount': {'allow': shared_allow, 'mode': shared_mode} if shared_allow else None,
            'volume_mounts': [{'volume': vm['volume'], 'mountpoint': m, 'mode': vm['mode']}
                              for m, vm in volume_mounts.items()],
            'skipped_volume_mounts': skipped,
        }

    def coerce(self, body, existing, ctx):
        out = {}
        if 'volume_mounts_active' in body:
            out['volume_mounts_active'] = bool(body['volume_mounts_active'])
        if 'shared_mount_allow' in body:
            out['shared_mount_allow'] = bool(body['shared_mount_allow'])
        if 'shared_mount_mode' in body:
            out['shared_mount_mode'] = _coerce_mode(body['shared_mount_mode'])
        if 'volume_mounts' in body:
            mounts_in = body['volume_mounts']
            if not isinstance(mounts_in, list):
                raise PolicyCoerceError("volume_mounts must be a list")
            out['volume_mounts'] = [
                {'volume': (m.get('volume') or '').strip(),
                 'mountpoint': (m.get('mountpoint') or '').strip(),
                 'mode': _coerce_mode(m.get('mode'))}
                for m in mounts_in if isinstance(m, dict)
            ]
        return out

    def validate(self, config):
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
            norm = '/' + mountpoint.strip('/')
            # a custom mount may not shadow the standard shared mount - that row owns
            # SHARED_MOUNTPOINT and is granted via the allow toggle, not a custom row
            if norm == SHARED_MOUNTPOINT:
                return False, f'Mountpoint "{SHARED_MOUNTPOINT}" is the standard shared volume - grant it with the shared toggle, not a custom mount.'
            if is_protected_mountpoint(mountpoint):
                return False, f'Mountpoint "{mountpoint}" is a protected location - mount under /mnt or /data instead.'
            if norm in seen_mountpoints:
                return False, f'Duplicate mountpoint "{norm}" - each mountpoint can hold one volume.'
            if volume in seen_volumes:
                return False, f'Volume "{volume}" is listed twice - a volume can be mounted at one mountpoint only.'
            seen_mountpoints.add(norm)
            seen_volumes.add(volume)
        return True, ''

    def summarize(self, c):
        if not c.get('volume_mounts_active'):
            return None
        n = len(c.get('volume_mounts') or [])
        shared = bool(c.get('shared_mount_allow'))
        if not n and not shared:
            return None
        parts = []
        if shared:
            parts.append('shared')
        if n:
            parts.append(f"{n} mount{'s' if n != 1 else ''}")
        return {'badge': 'Volumes', 'detail': f"Volume Mounts: {' + '.join(parts)}"}

    async def apply(self, spawner, resolved, actx):
        # Named Docker volumes -> container mountpoints. Spawner objects persist
        # across spawns, so first pop whatever this hook added last time (tracked
        # on the spawner) - leaving a group actually unmounts on the next spawn.
        # Missing volumes are auto-created by Docker. Read-only mounts use the
        # {'bind', 'mode'} form; read-write keeps the bare-string form (= rw).
        username = actx.username
        for _key in getattr(spawner, '_stellars_group_volume_keys', ()):
            spawner.volumes.pop(_key, None)
        _added_volume_keys = []

        def _mount(volume, mountpoint, mode):
            spawner.volumes[volume] = ({'bind': mountpoint, 'mode': 'ro'}
                                       if mode == 'ro' else mountpoint)
            _added_volume_keys.append(volume)
            spawner.log.info("[GroupVolumes] mount user=%s volume=%s -> %s (%s)",
                             username, volume, mountpoint, mode)

        # standard shared mount: resolve the role=shared volume by label fresh each
        # spawn (never a saved name), so a rename never strands the group.
        shared = resolved.get('shared_mount')
        shared_name = ''
        if shared and shared.get('allow'):
            shared_name = getattr(actx, 'shared_volume_name', '') or ''
            if shared_name:
                _mount(shared_name, SHARED_MOUNTPOINT, shared.get('mode') or DEFAULT_VOLUME_MODE)
            else:
                spawner.log.warning(
                    "[GroupVolumes] shared mount allowed for user=%s but no role=shared "
                    "volume resolved - skipping (set the shared volume label)", username)

        for _vm in resolved.get('volume_mounts') or []:
            # spawner.volumes is keyed by volume NAME: a custom row reusing the resolved
            # shared volume name would clobber the /mnt/shared mount above and bypass its
            # policy mode (e.g. force rw over a ro shared grant). The shared grant owns its
            # volume - skip the colliding custom row (granted via the shared toggle, not here).
            if shared_name and _vm['volume'] == shared_name:
                spawner.log.warning(
                    "[GroupVolumes] custom mount user=%s volume=%s -> %s reuses the standard "
                    "shared volume - skipped (grant it with the shared toggle, not a custom row)",
                    username, _vm['volume'], _vm['mountpoint'])
                continue
            _mount(_vm['volume'], _vm['mountpoint'], _vm.get('mode') or DEFAULT_VOLUME_MODE)
        spawner._stellars_group_volume_keys = _added_volume_keys
        for _sk in resolved.get('skipped_volume_mounts') or []:
            spawner.log.warning(
                "[GroupVolumes] skipped user=%s volume=%s mountpoint=%s group=%s reason=%s",
                username, _sk['volume'], _sk['mountpoint'], _sk['group'], _sk['reason'],
            )


# ── The registry ─────────────────────────────────────────────────────────────
# Order matters for two things: apply order (env_vars before api_keys, so the
# pool's env-precedence check sees the group env vars already set) and validate
# order (first failure wins - gpu, docker, cpu, mem, api_keys, volume_mounts,
# the order the legacy GroupConfigValidator._ALL used). Instances, not classes.

POLICY_TYPES = [
    EnvVarsPolicy(),
    GpuPolicy(),
    DockerPolicy(),
    CpuPolicy(),
    MemPolicy(),
    SudoPolicy(),
    DownloadsPolicy(),
    ApiKeysPolicy(),
    VolumeMountsPolicy(),
]


def default_config():
    """Assemble the default group config from every model's off-state slice."""
    out = {}
    for p in POLICY_TYPES:
        out.update(copy.deepcopy(p.default()))
    return out
