"""In-process docker-proxy wiring.

The proxy runs inside the JupyterHub process - same asyncio event loop,
same container, no HTTP, no token, no second compose service. One module
singleton `Manager` holds N per-user `UnixSite` listeners under a named
docker volume mounted into the hub at the configured socket dir (the spawner
discovers that volume from its own mounts; no name is hardcoded). The volume is
shared with each user lab via `Subpath: <user>` so each lab sees only its own
subdirectory and the single `docker.sock` inside it - mount-level isolation, no
host path.

`pre_spawn_hook` calls `register_user` directly (it's async, same loop);
`post_stop_hook` calls `unregister_user`. Quotas are re-applied on every
spawn because `pre_spawn_hook` resolves group config from the live DB
right before calling register - so admin group edits take effect on the
user's next lab start, no manual operator step.
"""

import os

from .logging_setup import log

SOCK_MOUNT_DIR = '/run/dockersock'
SOCK_FILENAME = 'docker.sock'

_manager = None


def get_manager(socket_dir):
    """Process-singleton Manager. Lazy-init on first call.

    ``socket_dir`` is required - the caller resolves it (no hardcoded default, so
    a missing value fails loud instead of silently writing sockets to a stale
    path). Import is deferred so module import doesn't require duoptimum_docker_proxy
    to be on path (it always is in the production image; in local dev test
    suites for duoptimum_hub_services it doesn't need to be).
    """
    global _manager
    if _manager is None:
        from duoptimum_docker_proxy.manager import Manager
        _manager = Manager(socket_dir=socket_dir)
    return _manager


def docker_host_url():
    """DOCKER_HOST value pointing at the proxied socket inside the user container."""
    return f"unix://{SOCK_MOUNT_DIR}/{SOCK_FILENAME}"


def _socket_host_path(socket_dir, user):
    return os.path.join(socket_dir, user, "docker.sock")


def _render_user_compose_project(template, *, compose_project, username):
    """Render the per-user compose-project template. Empty template -> ''."""
    if not template:
        return ''
    try:
        return template.format(compose=compose_project or '', username=username)
    except (KeyError, IndexError) as e:
        log.warning(
            f"user_compose_project_template render failed ({e}); falling back to hub project"
        )
        return compose_project or ''


def _build_overrides(resolved, *, username, compose_project='',
                     user_compose_project_template='', hub_network_name=''):
    """Map the resolved policy dict to ProxyConfig field names."""
    enforce = bool(resolved.get('docker_limited_user_compose_project_enabled'))
    allow_override = bool(resolved.get('docker_limited_user_compose_project_allow_override'))
    if enforce:
        effective_project = _render_user_compose_project(
            user_compose_project_template,
            compose_project=compose_project,
            username=username,
        )
    else:
        # Enforcement off => ad-hoc `docker run`s carry NO compose project at
        # all (free-floating). The user's own `docker compose` projects are
        # unaffected (their label is set by compose itself, not by us).
        effective_project = ''
    overrides = {
        'max_containers': int(resolved.get('docker_limited_max_containers', 10)),
        'max_volumes': int(resolved.get('docker_limited_max_volumes', 10)),
        'max_networks': int(resolved.get('docker_limited_max_networks', 3)),
        'max_storage_gb': float(resolved.get('docker_limited_max_storage_gb', 50.0)),
        'cpu_cap_cores': float(resolved.get('docker_limited_cpu_cap_cores', 2.0)),
        'mem_cap_gb': float(resolved.get('docker_limited_mem_cap_gb', 8.0)),
        # allow_privileged from docker_privileged (lab is already kernel-root);
        # allow_dangerous_flags from the independent limited toggle.
        'allow_privileged': bool(resolved.get('docker_privileged')),
        'allow_dangerous_flags': bool(resolved.get('docker_limited_allow_dangerous_flags')),
        'allow_compose_project_override': allow_override,
    }
    if effective_project:
        overrides['compose_project'] = effective_project
    # Hub network access: grants full access to the hub's docker network
    # (list + container create attach + network connect/disconnect) for users
    # in a group that opts in. Hub network name comes from env; an empty value
    # falls back to no extra access even when the toggle is on. When the toggle
    # is off, attempts to use the hub network are 403-rejected on container
    # create and 404-rejected on connect/disconnect actions.
    if resolved.get('docker_limited_hub_network_access') and hub_network_name:
        overrides['extra_accessible_networks'] = (hub_network_name,)
    return overrides


async def register_user(username, resolved, *, socket_dir,
                        compose_project='', user_compose_project_template='',
                        hub_network_name=''):
    """Register a limited user - in-process. Idempotent: re-registers replace.

    Returns ``(socket_host_path, mount_dir, docker_host)`` so the spawn hook
    can wire `spawner.volumes` + `spawner.environment` directly. Raises on
    failure (caller logs + falls back to no docker access).
    """
    overrides = _build_overrides(
        resolved,
        username=username,
        compose_project=compose_project,
        user_compose_project_template=user_compose_project_template,
        hub_network_name=hub_network_name,
    )
    mgr = get_manager(socket_dir)
    await mgr.register(username, overrides=overrides)
    socket_host_path = _socket_host_path(socket_dir, username)
    log.info(
        f"registered docker-proxy for owner={username} socket={socket_host_path} "
        f"limits: containers={overrides['max_containers']} "
        f"volumes={overrides['max_volumes']} networks={overrides['max_networks']} "
        f"storage_gb={overrides['max_storage_gb']} cpu={overrides['cpu_cap_cores']} "
        f"mem_gb={overrides['mem_cap_gb']} "
        f"allow_privileged={overrides['allow_privileged']} "
        f"allow_dangerous_flags={overrides['allow_dangerous_flags']} "
        f"compose_project={overrides.get('compose_project') or '<none>'} "
        f"allow_compose_project_override={overrides['allow_compose_project_override']} "
        f"extra_accessible_networks={overrides.get('extra_accessible_networks') or ()}"
    )
    return socket_host_path, SOCK_MOUNT_DIR, docker_host_url()


async def unregister_user(username, *, socket_dir):
    """Unregister a limited user (idempotent). Logs but never raises."""
    try:
        mgr = get_manager(socket_dir)
        removed = await mgr.unregister(username)
        if removed:
            log.info(f"unregistered docker-proxy for owner={username}")
    except Exception as e:
        log.warning(f"unregister docker-proxy for {username} failed: {e}")
