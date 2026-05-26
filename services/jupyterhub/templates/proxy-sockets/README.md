# Stellars JupyterHub - Per-user Docker proxy sockets

This volume holds the unix sockets that the in-process docker-proxy (running inside the JupyterHub container) binds for each limited-docker user. The same volume is mounted into each user's JupyterLab container via Docker's `Subpath` option, so each lab sees only its own subdirectory.

## Layout

```
/var/run/stellars-docker-proxy-sockets/
    README.md                         <- this file
    <username>/                       <- one directory per registered user
        docker.sock                   <- the unix socket the lab connects to
    <other-user>/
        docker.sock
    ...
```

Each `<username>/docker.sock` is an aiohttp `UnixSite` listener bound to a per-user `ProxyApp` with the user's quotas baked in. The listener forwards filtered Docker API calls to the host's `/var/run/docker.sock`, stamping owner labels on create, narrowing list/prune to the owner, and rejecting dangerous flags.

## Lifecycle

- Subdirectories appear when a user spawns a server (pre_spawn_hook -> register_user -> Manager.register).
- They disappear when the user stops their server (post_stop_hook -> unregister_user) - the socket file is removed and the empty subdir is cleaned up.
- A hub restart wipes the in-memory listener state; sockets are stale until the user spawns again (which re-registers).

## Diagnostics

To see what users are currently registered:

```sh
docker exec <hub-container> ls -la /var/run/stellars-docker-proxy-sockets/
```

Each `<user>/docker.sock` shown as `srw-rw-rw-` is a live listener. A directory without a socket file inside means a stale subdir (rare; pre_spawn_hook should clean it on next register).

## Operator notes

- Volume name: `jupyterhub_docker` (declared in `compose.yml`)
- Container path: `/var/run/stellars-docker-proxy-sockets` (set by `JUPYTERHUB_DOCKER_PROXY_SOCKET_DIR` in `Dockerfile.jupyterhub`)
- Wipe state: `docker volume rm jupyterhub_docker` (must be compose-down first)
- The volume is pre-populated with this README from the image on first creation (Docker's documented "volume content initialization" behaviour). Subsequent restarts preserve it

## References

- `docs/limited-docker-access.md` - architecture, mermaid, quota rules
- `docs/jupyterhub-working-with-docker.md` - operator-facing overview
- `services/jupyterhub/stellars-docker-proxy/` - the proxy library (`Manager`, `create_app`)
- `services/jupyterhub/stellars-hub-services/stellars_hub_services/docker_proxy.py` - hub-side wiring (`register_user`, `unregister_user`)
