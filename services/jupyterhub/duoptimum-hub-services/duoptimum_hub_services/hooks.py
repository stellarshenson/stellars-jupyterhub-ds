"""Pre-spawn hook factory and startup wiring.

The hook is thin: resolve the user's groups into one effective policy object,
then let every policy model impose itself (`apply_policies`). Only the
non-group-scoped spawn concerns stay inline here - docker-compose project
labels, the aggregate resolution log line, favicon CHP routes, and JupyterLab
icon URIs. Each policy model owns its own apply + restart lifecycle in
`policy/registry.py`; `schedule_policy_startup` re-imposes them for servers that
survived a hub restart.
"""

import html
from dataclasses import replace
from urllib.parse import urlparse

from tornado import web

from .api_keys_pool import PoolManager
from .docker_proxy import unregister_user
from .event_log import record_event
from .groups_config import GroupsConfigManager
from .policy import ApplyContext, apply_policies, resolve_policies, run_hub_startup
from .user_profiles import UserProfileManager

__all__ = (
    'make_pre_spawn_hook',
    'make_post_stop_hook',
    'schedule_policy_startup',
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
    docker_proxy_socket_dir='',
    docker_proxy_volume_name='',
    user_compose_project_template='',
    hub_network_name='',
    block_file_downloads=0,
    lab_sudo_enable_default=1,
    api_keys_reconcile_interval=0,
):
    """Create a pre_spawn_hook closure capturing branding + the apply context.

    Resolution context (gpu_available, reserved names/prefixes) and the apply
    context (docker proxy config, compose project, sudo/downloads defaults, the
    gpu uuid map) are captured once and threaded to the policy models via an
    ``ApplyContext``. ``branding`` and the favicon args drive the non-policy
    favicon/icon spawn steps that stay in this hook.
    """

    # Static apply context (per-spawn fields app/username are filled in the hook).
    base_actx = ApplyContext(
        gpu_uuid_by_index=gpu_uuid_by_index,
        compose_project=compose_project,
        docker_proxy_socket_dir=docker_proxy_socket_dir,
        docker_proxy_volume_name=docker_proxy_volume_name,
        user_compose_project_template=user_compose_project_template,
        hub_network_name=hub_network_name,
        block_file_downloads=block_file_downloads,
        lab_sudo_enable_default=lab_sudo_enable_default,
        gpu_available=gpu_available,
        reserved_names=reserved_env_var_names,
        reserved_prefixes=reserved_env_var_prefixes,
        api_keys_reconcile_interval=api_keys_reconcile_interval,
    )

    async def pre_spawn_hook(spawner):
        """Resolve group policy, let each model impose it, then the non-policy
        favicon/compose/icon spawn steps."""
        from jupyterhub.app import JupyterHub

        username = spawner.user.name
        # Force-password-change gate (no escape): a flagged user - or an admin
        # starting them - cannot spawn a lab until the password is changed. The
        # flag clears on a successful self-service change (see auth.change_password).
        # Fail OPEN on a flag-store error: never block a spawn because the profiles
        # DB was momentarily unreadable (that would lock the whole platform out).
        try:
            must_change = UserProfileManager.get_instance().get_must_change_password(username)
        except Exception as e:
            spawner.log.warning(f"[force-pw] flag check failed for {username}, allowing spawn: {e}")
            must_change = False
        if must_change:
            raise web.HTTPError(
                403,
                "You must change your password before starting your server. "
                "Open Change password, set a new password, then start the server.",
            )
        record_event('server', f'<b>{html.escape(str(username))}</b> server starting')
        user_group_names = [g.name for g in spawner.user.groups]

        # Resolve effective configuration by collapsing all of the user's groups.
        try:
            all_configs = GroupsConfigManager.get_instance().get_all_configs()
        except Exception as e:
            spawner.log.error(f"[Groups] Failed to load group configs: {e}")
            all_configs = []

        resolved = resolve_policies(
            user_group_names=user_group_names,
            all_group_configs=all_configs,
            gpu_available=gpu_available,
            reserved_names=reserved_env_var_names,
            reserved_prefixes=reserved_env_var_prefixes,
        )

        app = JupyterHub.instance()
        actx = replace(base_actx, app=app, username=username)

        # Each policy model imposes its own resolved slice (docker, gpu, sudo,
        # env, volumes, api-keys, mem, cpu, downloads), in registry order.
        await apply_policies(spawner, resolved, actx)

        # ── Non-policy spawn steps (not group-scoped) ────────────────────────

        # Docker Compose project labels: tag every container so `docker compose
        # ls` / `docker compose -p <project> ps` group all spawned user
        # containers under the same project as the hub.
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

        # Aggregate resolution log line (recompute the human-facing summaries
        # from the resolved object + the spawner state the models just set).
        if resolved.get('sudo_enable') is not None:
            sudo_enabled, sudo_source = resolved['sudo_enable'], 'group'
        else:
            sudo_enabled, sudo_source = bool(lab_sudo_enable_default), 'default'
        gpu_sel = (
            ('all' if resolved.get('gpu_all', True) else resolved.get('gpu_device_ids'))
            if resolved['gpu_access'] else '-'
        )
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
            "sudo=%s/%s env_vars=%d skipped=%s compose_project=%s",
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
            '1' if sudo_enabled else '0',
            sudo_source,
            len(resolved['env_vars']),
            resolved['skipped_env_vars'],
            compose_project or '-',
        )

        # Favicon proxy routes. Only the overridden frames are routed to the hub
        # (exact filenames), so un-overridden frames fall through CHP's
        # longest-prefix match to the user's own server. Without this narrowing
        # the kernel-busy frames (favicon-busy-N.ico) loop on the hub.
        if favicon_uri or favicon_busy_target:
            from tornado.web import url
            from .handlers.favicon import FaviconRedirectHandler

            # One-time: inject Tornado handler into app (outside /hub/ prefix).
            if not getattr(app, '_favicon_handler_injected', False):
                pattern = app.base_url + r'user/[^/]+/static/favicons/(favicon[^/]*\.ico)'
                rule = url(pattern, FaviconRedirectHandler, dict(busy_target=favicon_busy_target))
                app.tornado_application.wildcard_router.rules.insert(0, rule)
                app._favicon_handler_injected = True
                spawner.log.info(f"[Favicon] Injected Tornado handler for pattern: {pattern}")

            # Per-user: add CHP routes for the overridden frames only (idempotent).
            parsed = urlparse(app.hub.url)
            hub_target = f'{parsed.scheme}://{parsed.netloc}'
            base = f'{app.base_url}user/{username}/static/favicons/'
            routespecs = []
            if favicon_uri:
                routespecs.append(f'{base}favicon.ico')
            if favicon_busy_target:
                routespecs.append(f'{base}favicon-busy')
            for routespec in routespecs:
                # Normalize to the trailing-slash form get_all_routes() returns so
                # the periodic check_routes() does not race to delete the live route.
                routespec = app.proxy.validate_routespec(routespec)
                await app.proxy.add_route(routespec, hub_target, {})
                app.proxy.extra_routes[routespec] = hub_target
                spawner.log.info(f"[Favicon] Added CHP route: {routespec} -> {hub_target}")

        # JupyterLab icon URIs - resolve static filenames to fully qualified URLs.
        _main_static = branding.get('lab_main_icon_static', '')
        _main_url = branding.get('lab_main_icon_url', '')
        _splash_static = branding.get('lab_splash_icon_static', '')
        _splash_url = branding.get('lab_splash_icon_url', '')

        if _main_static or _main_url or _splash_static or _splash_url:
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

    pre_spawn_hook._stellars_apply_context = base_actx  # exposed for schedule_policy_startup
    return pre_spawn_hook


def make_post_stop_hook(socket_dir):
    """Factory: async post-stop hook (twin of ``make_pre_spawn_hook``).

    On server stop it unregisters the user from the in-process docker-proxy,
    releases any in-flight api-key reservation, and records a server-stop event -
    all best-effort so a cleanup failure never blocks the stop. ``socket_dir`` is
    where the per-user proxy sockets live (the config's resolved value).
    """
    async def post_stop_hook(spawner):
        # Unregister from the in-process docker-proxy. No-op for users without a
        # registered listener; user-created containers are independent of the
        # proxy and keep running - the listener is re-created on the next spawn.
        try:
            await unregister_user(spawner.user.name, socket_dir=socket_dir)
        except Exception as e:  # never block a stop on cleanup
            spawner.log.warning("[Groups] docker-proxy unregister failed: %s", e)
        # Release any in-flight api-key reservation (best-effort; the real release
        # is the container leaving the running set, picked up by the periodic
        # reconcile - stop events are never the source of truth).
        try:
            PoolManager.get_instance().release_tentative(spawner.user.name)
        except Exception as e:
            spawner.log.warning("[ApiKeys] tentative release failed: %s", e)
        # Record a server-stop event for the portal events feed (best-effort).
        try:
            record_event('server', f'<b>{html.escape(str(spawner.user.name))}</b> server stopped')
        except Exception:
            pass

    return post_stop_hook


def schedule_policy_startup(actx):
    """Re-impose every policy model for servers that survived a hub restart.

    pre_spawn_hook only fires on new spawns; this runs each model's
    ``on_hub_startup`` once at boot (docker-proxy survivor re-registration,
    download-block route re-registration, api-keys reconcile + periodic). Replaces
    the previous per-feature startup callbacks. ``actx`` is the static
    ApplyContext from ``make_pre_spawn_hook`` (``pre_spawn_hook._stellars_apply_context``).
    """
    from tornado.ioloop import IOLoop

    async def _startup():
        from jupyterhub.app import JupyterHub
        app = JupyterHub.instance()
        await run_hub_startup(app, actx)

    IOLoop.current().add_callback(_startup)


def schedule_startup_favicon_callback(favicon_uri='', favicon_busy_target=''):
    """Register CHP favicon routes for already-running servers after a hub
    restart (non-policy; pre_spawn_hook only fires for new spawns).

    Args:
        favicon_uri: JUPYTERHUB_BRANDING_FAVICON_URI value (non-empty activates the
            favicon.ico route)
        favicon_busy_target: resolved busy-frame redirect target (non-empty
            activates the favicon-busy route)
    """
    if not (favicon_uri or favicon_busy_target):
        return

    async def _register_favicon_routes_for_active_servers():
        from jupyterhub.app import JupyterHub
        from tornado.web import url
        from .handlers.favicon import FaviconRedirectHandler

        app = JupyterHub.instance()

        # Inject Tornado handler (same as pre_spawn_hook, guarded by flag).
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
                    routespec = app.proxy.validate_routespec(routespec)
                    await app.proxy.add_route(routespec, hub_target, {})
                    app.proxy.extra_routes[routespec] = hub_target
                    app.log.info(f"[Favicon Startup] Added CHP route: {routespec} -> {hub_target}")
                count += 1

        if count:
            app.log.info(f"[Favicon Startup] Registered {count} active server(s) with favicon CHP routes")

    from tornado.ioloop import IOLoop
    IOLoop.current().add_callback(_register_favicon_routes_for_active_servers)
