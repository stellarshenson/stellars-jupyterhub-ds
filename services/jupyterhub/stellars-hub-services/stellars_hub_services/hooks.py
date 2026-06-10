"""Pre-spawn hook factory and startup callbacks."""

import math
from urllib.parse import urlparse

from .docker_proxy import register_user
from .group_resolver import resolve_group_config
from .groups_config import GroupsConfigManager

__all__ = (
    'make_pre_spawn_hook',
    'schedule_startup_docker_proxy_callback',
    'schedule_startup_favicon_callback',
)


def make_pre_spawn_hook(
    branding,
    favicon_uri='',
    favicon_busy_target='',
    gpu_available=False,
    gpu_uuid_by_index=None,
    reserved_env_var_names=frozenset(),
    reserved_env_var_prefixes=(),
    compose_project='',
    docker_proxy_socket_dir='/var/run/jupyterhub-docker-proxy-sockets',
    docker_proxy_volume_name='jupyterhub_docker',
    user_compose_project_template='',
    hub_network_name='',
):
    """Create a pre_spawn_hook closure that captures branding + resolution context.

    Args:
        branding: dict from setup_branding() with icon static names and URLs
        favicon_uri: JUPYTERHUB_FAVICON_URI value (non-empty activates the
            favicon.ico CHP route)
        favicon_busy_target: resolved redirect target for kernel-busy favicon
            frames (hub-relative static path or external URL); non-empty
            activates the favicon-busy CHP route. Empty leaves busy frames to
            the user's own JupyterLab server.
        gpu_available: True when host has GPU hardware (detected or forced) - a
            prerequisite for any per-group GPU grant taking effect.
        gpu_uuid_by_index: dict mapping GPU index string -> UUID, used to set
            CUDA_VISIBLE_DEVICES by UUID (stable across in-container re-indexing).
        reserved_env_var_names: names that groups cannot override (platform env).
        reserved_env_var_prefixes: tuple of prefixes reserved for JupyterHub
            itself (e.g. JUPYTERHUB_, JPY_, MEM_, CPU_).
        compose_project: when set, attaches docker-compose project labels so
            spawned containers are grouped under that project in `docker compose
            ls` and `docker compose -p <project> ps` alongside the hub.
        docker_proxy_socket_dir: path inside the hub container where the
            in-process proxy writes per-user sockets - backed by a named
            docker volume (see docker_proxy_volume_name). Layout is
            <socket_dir>/<user>/docker.sock so the spawner can mount only
            the per-user subdir into each lab via volume-subpath.
        docker_proxy_volume_name: name of the docker volume backing the
            socket directory; the spawner mounts a per-user subpath of this
            volume into each lab as `/run/dockersock`. Empty disables
            limited-docker wiring entirely (the grant resolves but no
            socket is attached).
        user_compose_project_template: Python str.format template with
            {compose_project} and {username} placeholders, used to render
            the per-user compose-project label when a group enables
            docker_limited_user_compose_project_enabled. Default from
            Dockerfile ENV JUPYTERHUB_DOCKER_PROXY_USER_COMPOSE_PROJECT_TEMPLATE.
    """

    async def pre_spawn_hook(spawner):
        """Resolve group config, apply docker/gpu/env, inject favicon + icon routes."""
        username = spawner.user.name
        user_group_names = [g.name for g in spawner.user.groups]

        # Resolve effective configuration by collapsing all user groups
        try:
            all_configs = GroupsConfigManager.get_instance().get_all_configs()
        except Exception as e:
            spawner.log.error(f"[Groups] Failed to load group configs: {e}")
            all_configs = []

        resolved = resolve_group_config(
            user_group_names=user_group_names,
            all_group_configs=all_configs,
            gpu_available=gpu_available,
            reserved_names=reserved_env_var_names,
            reserved_prefixes=reserved_env_var_prefixes,
        )

        # Docker access. Normal (raw socket) supersedes limited (proxy) - the
        # resolver already cleared docker_limited when docker_access is set.
        if resolved['docker_access']:
            # Normal: mount the raw host socket (sees all, no quota).
            spawner.volumes['/var/run/docker.sock'] = '/var/run/docker.sock'
            spawner.environment.pop('DOCKER_HOST', None)
        elif resolved.get('docker_limited'):
            # Limited: the in-process docker-proxy creates a per-user listener
            # at <socket_dir>/<user>/docker.sock in the hub's own filesystem
            # (backed by the named docker volume). The spawner mounts only
            # that user's subdirectory of the volume into their lab as
            # /run/dockersock via Docker's Subpath mount option, then sets
            # DOCKER_HOST. The stock docker CLI in the lab sees only this
            # user's own resources (mount-level isolation, no host path).
            # No fallback: if the proxy setup fails (missing socket dir, empty
            # volume name, register_user raises) the whole spawn fails outright
            # rather than silently downgrading the user to no docker access.
            if not docker_proxy_socket_dir or not docker_proxy_volume_name:
                raise RuntimeError(
                    f"limited docker requested for {username} but proxy is not "
                    f"configured (socket_dir={docker_proxy_socket_dir!r} "
                    f"volume_name={docker_proxy_volume_name!r}). "
                    "Both must be set; see config/jupyterhub_config.py."
                )
            _socket_host_path, mount_dir, docker_host = await register_user(
                username,
                resolved,
                socket_dir=docker_proxy_socket_dir,
                compose_project=compose_project,
                user_compose_project_template=user_compose_project_template,
                hub_network_name=hub_network_name,
            )
            spawner.extra_host_config.setdefault('mounts', []).append({
                'Type': 'volume',
                'Source': docker_proxy_volume_name,
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
                uuid_map = gpu_uuid_by_index or {}
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

        # Inject user-defined env vars from groups (reserved names already filtered)
        if resolved['env_vars']:
            spawner.environment.update(resolved['env_vars'])

        # Group volume mounts: named Docker volumes -> container mountpoints.
        # Spawner objects persist across spawns, so first pop whatever this hook
        # added last time (tracked on the spawner) - leaving a group actually
        # unmounts on the next spawn. Missing volumes are auto-created by Docker.
        for _key in getattr(spawner, '_stellars_group_volume_keys', ()):
            spawner.volumes.pop(_key, None)
        _added_volume_keys = []
        for _vm in resolved.get('volume_mounts') or []:
            spawner.volumes[_vm['volume']] = _vm['mountpoint']
            _added_volume_keys.append(_vm['volume'])
            spawner.log.info("[GroupVolumes] mount user=%s volume=%s -> %s",
                             username, _vm['volume'], _vm['mountpoint'])
        spawner._stellars_group_volume_keys = _added_volume_keys
        for _sk in resolved.get('skipped_volume_mounts') or []:
            spawner.log.warning(
                "[GroupVolumes] skipped user=%s volume=%s mountpoint=%s group=%s reason=%s",
                username, _sk['volume'], _sk['mountpoint'], _sk['group'], _sk['reason'],
            )

        # API keys pool: assign one credential per group pool so no two running
        # containers share a key. The durable Docker label (set below via
        # extra_create_kwargs) carries the slot id - never the secret; the in-use
        # set is rebuilt from running containers, so missed stop events self-heal.
        # Explicit group env_vars win over a pool injecting the same name.
        pools = resolved.get('api_key_pools') or []
        if pools:
            from .api_keys_pool import PoolManager
            try:
                pool_result = await PoolManager.get_instance().assign(username, pools)
            except Exception as e:
                spawner.log.error("[ApiKeys] assignment failed for %s: %s", username, e)
                pool_result = {'env': {}, 'env_sources': {}, 'labels': {}, 'assignments': []}
            # Resolve a pool-var vs plain-env-var clash by group order, not by
            # kind: the value set by the group higher in the ordered list wins
            # (lower index = higher priority). env_var_source carries the index
            # of the group that set each plain env var; env_sources carries the
            # pool's group index. On a tie the plain env var (explicit) wins.
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

        # Memory limit: resolved GB -> bytes for Docker HostConfig.Memory.
        # Swap policy: when the winning group disables swap, pin memswap_limit to
        # the memory limit so total (RAM+swap) == RAM, i.e. zero swap allowance
        # (cgroup v2: memory.swap.max=0) - a hard cap that OOMs at the limit
        # instead of spilling to disk. Otherwise leave swap at Docker's default
        # (memory-swap = 2x memory).
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

        # CPU limit: resolved cores -> spawner.cpu_limit (DockerSpawner maps it
        # to cpu_quota = cpu_limit * cpu_period). Ceil to whole cores so a
        # fractional cap never rounds down to a zero-core quota (which Docker
        # would treat as unlimited); min 1 core whenever a cap is set.
        if resolved.get('cpu_limit_cores'):
            spawner.cpu_limit = float(max(1, math.ceil(float(resolved['cpu_limit_cores']))))
        else:
            spawner.cpu_limit = None

        # Docker Compose project labels: tag the container so `docker compose ls`
        # / `docker compose -p <project> ps` group all spawned user containers
        # under the same project as the hub. Container name stays literal
        # (jupyterlab-{username}); the project label is what compose tooling
        # filters on.
        if compose_project:
            kwargs = dict(spawner.extra_create_kwargs or {})
            labels = dict(kwargs.get('labels') or {})
            labels.update({
                'com.docker.compose.project': compose_project,
                'com.docker.compose.service': f'jupyterlab_{username}',
                'com.docker.compose.container-number': '1',
                'com.docker.compose.oneoff': 'False',
            })
            kwargs['labels'] = labels
            spawner.extra_create_kwargs = kwargs

        gpu_sel = (
            ('all' if resolved.get('gpu_all', True) else resolved.get('gpu_device_ids'))
            if resolved['gpu_access'] else '-'
        )
        # docker_limits is the actual quota/cap set the central proxy will enforce
        # for this user (only populated when the limited branch took effect).
        if resolved.get('docker_limited') and 'DOCKER_HOST' in spawner.environment:
            docker_limits = (
                f"containers={resolved.get('docker_limited_max_containers')} "
                f"volumes={resolved.get('docker_limited_max_volumes')} "
                f"networks={resolved.get('docker_limited_max_networks')} "
                f"storage_gb={resolved.get('docker_limited_max_storage_gb')} "
                f"cpu={resolved.get('docker_limited_cpu_cap_cores')} "
                f"mem_gb={resolved.get('docker_limited_mem_cap_gb')} "
                f"allow_privileged={bool(resolved.get('docker_privileged'))} "
                f"allow_dangerous_flags={bool(resolved.get('docker_limited_allow_dangerous_flags'))}"
            )
        else:
            docker_limits = '-'
        spawner.log.info(
            "[Groups] user=%s groups=%s docker=%s docker_limited=%s docker_limits=[%s] "
            "privileged=%s gpu=%s gpu_sel=%s mem_limit_gb=%s swap_off=%s cpu_limit=%s "
            "env_vars=%d skipped=%s compose_project=%s",
            username,
            resolved['matched_groups'],
            resolved['docker_access'],
            resolved.get('docker_limited'),
            docker_limits,
            resolved['docker_privileged'],
            resolved['gpu_access'],
            gpu_sel,
            resolved.get('mem_limit_gb'),
            bool(resolved.get('mem_swap_disabled')),
            spawner.cpu_limit,
            len(resolved['env_vars']),
            resolved['skipped_env_vars'],
            compose_project or '-',
        )

        # Favicon proxy routes. Only the overridden frames are routed to the hub
        # (exact filenames), so un-overridden frames fall through CHP's
        # longest-prefix match to the user's own server. Without this narrowing
        # the kernel-busy frames (favicon-busy-N.ico) loop on the hub.
        if favicon_uri or favicon_busy_target:
            from jupyterhub.app import JupyterHub
            from .handlers.favicon import FaviconRedirectHandler
            from tornado.web import url

            app = JupyterHub.instance()

            # One-time: inject Tornado handler into app (outside /hub/ prefix).
            # Pattern captures the favicon filename so the handler maps the idle
            # frame vs busy frames; busy_target tells it where busy frames go.
            if not getattr(app, '_favicon_handler_injected', False):
                pattern = app.base_url + r'user/[^/]+/static/favicons/(favicon[^/]*\.ico)'
                rule = url(pattern, FaviconRedirectHandler, dict(busy_target=favicon_busy_target))
                app.tornado_application.wildcard_router.rules.insert(0, rule)
                app._favicon_handler_injected = True
                spawner.log.info(f"[Favicon] Injected Tornado handler for pattern: {pattern}")

            # Per-user: add CHP routes for the overridden frames only (idempotent)
            parsed = urlparse(app.hub.url)
            hub_target = f'{parsed.scheme}://{parsed.netloc}'
            base = f'{app.base_url}user/{username}/static/favicons/'
            routespecs = []
            if favicon_uri:
                routespecs.append(f'{base}favicon.ico')
            if favicon_busy_target:
                routespecs.append(f'{base}favicon-busy')
            for routespec in routespecs:
                # Normalize to the trailing-slash form get_all_routes() returns
                # (validate_routespec is what JupyterHub uses internally). Without
                # this the extra_routes key lacks the slash that
                # _routespec_from_chp_path always appends, so the periodic
                # check_routes() sees the live route as stale and races to delete
                # it in the same gather() as the re-add - the favicon flaps and
                # the lab's stock icon leaks through during the gap.
                routespec = app.proxy.validate_routespec(routespec)
                await app.proxy.add_route(routespec, hub_target, {})
                app.proxy.extra_routes[routespec] = hub_target
                spawner.log.info(f"[Favicon] Added CHP route: {routespec} -> {hub_target}")

        # JupyterLab icon URIs - resolve static filenames to fully qualified URLs
        _main_static = branding.get('lab_main_icon_static', '')
        _main_url = branding.get('lab_main_icon_url', '')
        _splash_static = branding.get('lab_splash_icon_static', '')
        _splash_url = branding.get('lab_splash_icon_url', '')

        if _main_static or _main_url or _splash_static or _splash_url:
            from jupyterhub.app import JupyterHub
            app = JupyterHub.instance()

            if _main_static:
                parsed = urlparse(app.hub.url)
                hub_origin = f'{parsed.scheme}://{parsed.netloc}'
                spawner.environment['JUPYTERLAB_MAIN_ICON_URI'] = f'{hub_origin}{app.base_url}hub/static/{_main_static}'
            elif _main_url:
                spawner.environment['JUPYTERLAB_MAIN_ICON_URI'] = _main_url

            if _splash_static:
                parsed = urlparse(app.hub.url)
                hub_origin = f'{parsed.scheme}://{parsed.netloc}'
                spawner.environment['JUPYTERLAB_SPLASH_ICON_URI'] = f'{hub_origin}{app.base_url}hub/static/{_splash_static}'
            elif _splash_url:
                spawner.environment['JUPYTERLAB_SPLASH_ICON_URI'] = _splash_url

    return pre_spawn_hook


def schedule_startup_docker_proxy_callback(
    *,
    docker_proxy_socket_dir='/var/run/jupyterhub-docker-proxy-sockets',
    docker_proxy_volume_name='jupyterhub_docker',
    gpu_available=False,
    reserved_env_var_names=frozenset(),
    reserved_env_var_prefixes=(),
    compose_project='',
    user_compose_project_template='',
    hub_network_name='',
):
    """Re-register limited-docker users with the in-process docker-proxy after
    a hub restart. The proxy lives inside the hub process: `Manager._listeners`
    is empty on each fresh boot, but per-user socket FILES persist in the
    backing volume from the previous run. A surviving lab container connects
    to its `/run/dockersock/docker.sock` and gets ECONNREFUSED because no
    `UnixSite` is bound. `pre_spawn_hook` only fires on a new spawn so it does
    not heal this case; this callback does, by iterating active spawners,
    re-resolving group config, and calling `register_user` for each one whose
    group membership currently grants `docker_limited`. Arg semantics match
    `make_pre_spawn_hook` (same resolver inputs, same proxy config).
    """
    if not docker_proxy_socket_dir or not docker_proxy_volume_name:
        return

    async def _register_proxy_for_active_servers():
        from jupyterhub.app import JupyterHub
        from jupyterhub import orm

        app = JupyterHub.instance()

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
            user_group_names = [g.name for g in user.groups]
            resolved = resolve_group_config(
                user_group_names=user_group_names,
                all_group_configs=all_configs,
                gpu_available=gpu_available,
                reserved_names=reserved_env_var_names,
                reserved_prefixes=reserved_env_var_prefixes,
            )
            # docker_access (raw socket) supersedes proxy; nothing to re-register.
            if resolved['docker_access'] or not resolved.get('docker_limited'):
                continue
            try:
                await register_user(
                    username,
                    resolved,
                    socket_dir=docker_proxy_socket_dir,
                    compose_project=compose_project,
                    user_compose_project_template=user_compose_project_template,
                    hub_network_name=hub_network_name,
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

    from tornado.ioloop import IOLoop
    IOLoop.current().add_callback(_register_proxy_for_active_servers)


def schedule_startup_favicon_callback(favicon_uri='', favicon_busy_target=''):
    """Schedule startup callback to register CHP routes for already-running servers.

    Args:
        favicon_uri: JUPYTERHUB_FAVICON_URI value (non-empty activates the
            favicon.ico route)
        favicon_busy_target: resolved busy-frame redirect target (non-empty
            activates the favicon-busy route)
    """
    if not (favicon_uri or favicon_busy_target):
        return

    async def _register_favicon_routes_for_active_servers():
        from jupyterhub.app import JupyterHub
        from .handlers.favicon import FaviconRedirectHandler
        from tornado.web import url

        app = JupyterHub.instance()

        # Inject Tornado handler (same as pre_spawn_hook, guarded by flag)
        if not getattr(app, '_favicon_handler_injected', False):
            pattern = app.base_url + r'user/[^/]+/static/favicons/(favicon[^/]*\.ico)'
            rule = url(pattern, FaviconRedirectHandler, dict(busy_target=favicon_busy_target))
            app.tornado_application.wildcard_router.rules.insert(0, rule)
            app._favicon_handler_injected = True
            app.log.info(f"[Favicon Startup] Injected Tornado handler for pattern: {pattern}")

        parsed = urlparse(app.hub.url)
        hub_target = f'{parsed.scheme}://{parsed.netloc}'

        from jupyterhub import orm
        count = 0
        for orm_user in app.db.query(orm.User).all():
            user = app.users.get(orm_user.name)
            if user and user.spawner and user.spawner.active:
                username = user.name
                base = f'{app.base_url}user/{username}/static/favicons/'
                routespecs = []
                if favicon_uri:
                    routespecs.append(f'{base}favicon.ico')
                if favicon_busy_target:
                    routespecs.append(f'{base}favicon-busy')
                for routespec in routespecs:
                    # See pre_spawn_hook: normalize to the trailing-slash form
                    # get_all_routes() returns so check_routes() does not flap
                    # this route.
                    routespec = app.proxy.validate_routespec(routespec)
                    await app.proxy.add_route(routespec, hub_target, {})
                    app.proxy.extra_routes[routespec] = hub_target
                    app.log.info(f"[Favicon Startup] Added CHP route: {routespec} -> {hub_target}")
                count += 1

        if count:
            app.log.info(f"[Favicon Startup] Registered {count} active server(s) with favicon CHP routes")

    from tornado.ioloop import IOLoop
    IOLoop.current().add_callback(_register_favicon_routes_for_active_servers)
