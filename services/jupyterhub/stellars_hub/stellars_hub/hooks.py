"""Pre-spawn hook factory and startup callbacks."""

from urllib.parse import urlparse

from .group_resolver import resolve_group_config
from .groups_config import GroupsConfigManager


def make_pre_spawn_hook(
    branding,
    favicon_uri='',
    gpu_available=False,
    reserved_env_var_names=frozenset(),
    reserved_env_var_prefixes=(),
):
    """Create a pre_spawn_hook closure that captures branding + resolution context.

    Args:
        branding: dict from setup_branding() with icon static names and URLs
        favicon_uri: JUPYTERHUB_FAVICON_URI value (non-empty activates CHP routes)
        gpu_available: True when host has GPU hardware (detected or forced) - a
            prerequisite for any per-group GPU grant taking effect.
        reserved_env_var_names: names that groups cannot override (platform env).
        reserved_env_var_prefixes: tuple of prefixes reserved for JupyterHub
            itself (e.g. JUPYTERHUB_, JPY_, MEM_, CPU_).
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

        # Docker socket mount
        if resolved['docker_access']:
            spawner.volumes['/var/run/docker.sock'] = '/var/run/docker.sock'
        else:
            spawner.volumes.pop('/var/run/docker.sock', None)

        # Privileged container mode
        if resolved['docker_privileged']:
            spawner.extra_host_config['privileged'] = True
        else:
            spawner.extra_host_config.pop('privileged', None)

        # GPU device passthrough (per-user, replaces old global config)
        if resolved['gpu_access']:
            spawner.extra_host_config['device_requests'] = [
                {'Driver': 'nvidia', 'Count': -1, 'Capabilities': [['gpu']]}
            ]
            spawner.environment['ENABLE_GPU_SUPPORT'] = '1'
            spawner.environment['ENABLE_GPUSTAT'] = '1'
        else:
            spawner.extra_host_config.pop('device_requests', None)
            spawner.environment['ENABLE_GPU_SUPPORT'] = '0'
            spawner.environment['ENABLE_GPUSTAT'] = '0'

        # Inject user-defined env vars from groups (reserved names already filtered)
        if resolved['env_vars']:
            spawner.environment.update(resolved['env_vars'])

        # Memory limit: resolved GB -> bytes for Docker HostConfig.Memory
        if resolved.get('mem_limit_gb'):
            spawner.mem_limit = int(float(resolved['mem_limit_gb']) * 1024 ** 3)
        else:
            spawner.mem_limit = None

        spawner.log.info(
            "[Groups] user=%s groups=%s docker=%s privileged=%s gpu=%s mem_limit_gb=%s env_vars=%d skipped=%s",
            username,
            resolved['matched_groups'],
            resolved['docker_access'],
            resolved['docker_privileged'],
            resolved['gpu_access'],
            resolved.get('mem_limit_gb'),
            len(resolved['env_vars']),
            resolved['skipped_env_vars'],
        )

        # Favicon proxy route
        if favicon_uri:
            from jupyterhub.app import JupyterHub
            from .handlers.favicon import FaviconRedirectHandler
            from tornado.web import url

            app = JupyterHub.instance()

            # One-time: inject Tornado handler into app (outside /hub/ prefix)
            if not getattr(app, '_favicon_handler_injected', False):
                pattern = app.base_url + r'user/[^/]+/static/favicons/favicon\.ico'
                rule = url(pattern, FaviconRedirectHandler)
                app.tornado_application.wildcard_router.rules.insert(0, rule)
                app._favicon_handler_injected = True
                spawner.log.info(f"[Favicon] Injected Tornado handler for pattern: {pattern}")

            # Per-user: add CHP route for favicon path -> hub (idempotent)
            parsed = urlparse(app.hub.url)
            hub_target = f'{parsed.scheme}://{parsed.netloc}'
            routespec = f'{app.base_url}user/{username}/static/favicons/'
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


def schedule_startup_favicon_callback(favicon_uri=''):
    """Schedule startup callback to register CHP routes for already-running servers.

    Args:
        favicon_uri: JUPYTERHUB_FAVICON_URI value (non-empty activates callback)
    """
    if not favicon_uri:
        return

    async def _register_favicon_routes_for_active_servers():
        from jupyterhub.app import JupyterHub
        from .handlers.favicon import FaviconRedirectHandler
        from tornado.web import url

        app = JupyterHub.instance()

        # Inject Tornado handler (same as pre_spawn_hook, guarded by flag)
        if not getattr(app, '_favicon_handler_injected', False):
            pattern = app.base_url + r'user/[^/]+/static/favicons/favicon\.ico'
            rule = url(pattern, FaviconRedirectHandler)
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
                routespec = f'{app.base_url}user/{username}/static/favicons/'
                await app.proxy.add_route(routespec, hub_target, {})
                app.proxy.extra_routes[routespec] = hub_target
                count += 1
                app.log.info(f"[Favicon Startup] Added CHP route: {routespec} -> {hub_target}")

        if count:
            app.log.info(f"[Favicon Startup] Registered {count} CHP route(s) for active servers")

    from tornado.ioloop import IOLoop
    IOLoop.current().add_callback(_register_favicon_routes_for_active_servers)
