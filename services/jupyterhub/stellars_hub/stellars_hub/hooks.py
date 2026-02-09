"""Pre-spawn hook factory and startup callbacks."""

from urllib.parse import urlparse


def make_pre_spawn_hook(branding, builtin_groups, favicon_uri=''):
    """Create a pre_spawn_hook closure that captures branding state.

    Args:
        branding: dict from setup_branding() with icon static names and URLs
        builtin_groups: list of group names that cannot be deleted
        favicon_uri: JUPYTERHUB_FAVICON_URI value (non-empty activates CHP routes)
    """

    async def pre_spawn_hook(spawner):
        """Grant docker access based on group membership, inject favicon + icon routes."""
        from jupyterhub.orm import Group

        # Ensure built-in groups exist (protection against deletion)
        for group_name in builtin_groups:
            existing_group = spawner.db.query(Group).filter(Group.name == group_name).first()
            if not existing_group:
                spawner.log.warning(f"Built-in group '{group_name}' was missing - recreating")
                new_group = Group(name=group_name)
                spawner.db.add(new_group)
                spawner.db.commit()

        username = spawner.user.name
        user_groups = [g.name for g in spawner.user.groups]

        # docker-sock: mount docker.sock for container orchestration
        if 'docker-sock' in user_groups:
            spawner.log.info(f"Granting docker.sock access to user: {username}")
            spawner.volumes['/var/run/docker.sock'] = '/var/run/docker.sock'
        else:
            spawner.volumes.pop('/var/run/docker.sock', None)

        # docker-privileged: run container with --privileged flag
        if 'docker-privileged' in user_groups:
            spawner.log.info(f"Granting privileged container mode to user: {username}")
            spawner.extra_host_config['privileged'] = True
        else:
            spawner.extra_host_config.pop('privileged', None)

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
