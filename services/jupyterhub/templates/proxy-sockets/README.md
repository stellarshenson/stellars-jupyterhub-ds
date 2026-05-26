# Stellars JupyterHub - Per-user Docker proxy sockets

This volume holds the per-user unix sockets the in-process docker-proxy binds for each limited-docker user. The same volume is mounted into each user's JupyterLab container via Docker's `Subpath` option, so each lab sees only its own subdirectory under `/run/dockersock/` and the single `docker.sock` inside it.

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

Each `<username>/docker.sock` is an aiohttp `UnixSite` listener bound to a per-user `ProxyApp` with that user's quotas baked in. It forwards filtered Docker API calls to the host's `/var/run/docker.sock`, stamps owner labels on create, narrows list/prune to the owner, and rejects dangerous flags.

## Lifecycle

- Subdirectories appear when a user spawns a server (`pre_spawn_hook` -> `register_user` -> `Manager.register`)
- They disappear on stop (`post_stop_hook` -> `unregister_user`); the socket and the now-empty subdir are removed
- Hub restart wipes the in-memory listener state; sockets reappear on the user's next spawn

## Operator notes

- Volume declared in `compose.yml` as `jupyterhub_docker:`; compose namespaces it on the daemon to `${COMPOSE_PROJECT_NAME}_jupyterhub_docker` (same convention as every other named volume in this stack)
- Container path: `/var/run/stellars-docker-proxy-sockets` (set by `JUPYTERHUB_DOCKER_PROXY_SOCKET_DIR` in `Dockerfile.jupyterhub`)
- The spawner references the same namespaced name when subpath-mounting into each lab; the name is computed in `config/jupyterhub_config.py` from `COMPOSE_PROJECT_NAME`. Empty `COMPOSE_PROJECT_NAME` aborts hub startup
- This README is shipped inside the image at the same path; Docker copies it into the volume on first creation (volume-content-init). Subsequent restarts preserve it
- Wipe state: `docker volume rm ${COMPOSE_PROJECT_NAME}_jupyterhub_docker` (compose must be down first)

## References

- [docs/limited-docker-access.md](https://github.com/stellarshenson/stellars-jupyterhub-ds/blob/main/docs/limited-docker-access.md) - architecture, mermaid, quota rules
- [docs/jupyterhub-working-with-docker.md](https://github.com/stellarshenson/stellars-jupyterhub-ds/blob/main/docs/jupyterhub-working-with-docker.md) - operator-facing overview
- [services/jupyterhub/stellars-docker-proxy/](https://github.com/stellarshenson/stellars-jupyterhub-ds/tree/main/services/jupyterhub/stellars-docker-proxy) - the proxy library (`Manager`, `create_app`)
- [services/jupyterhub/stellars-hub-services/stellars_hub_services/docker_proxy.py](https://github.com/stellarshenson/stellars-jupyterhub-ds/blob/main/services/jupyterhub/stellars-hub-services/stellars_hub_services/docker_proxy.py) - hub-side wiring (`register_user`, `unregister_user`)
