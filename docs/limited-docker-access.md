# Limited Docker Access

Per-user filtered Docker socket. A user in a `docker-limited` group manages only their own containers/volumes/networks up to a quota. All resources run on the host Docker daemon, so the operator sees everything in Docker Desktop; the user sees only theirs.

## Architecture

```mermaid
flowchart LR
    CLI[docker CLI in<br/>user's JupyterLab]
    VOL[(named volume<br/>jupyterhub_docker)]
    HUB[JupyterHub container<br/>+ in-process Manager<br/>+ N per-user UnixSite listeners]
    DAEMON[Host Docker daemon]
    DESKTOP[Docker Desktop<br/>operator sees all]

    HUB ---|/var/run/stellars-docker-proxy-sockets| VOL
    CLI -->|DOCKER_HOST<br/>unix:///run/dockersock/docker.sock<br/>Subpath: user| VOL
    HUB -->|/var/run/docker.sock| DAEMON
    DAEMON --- DESKTOP
    HUB -.->|spawns| CLI
```

## Group config (admin UI: `/hub/groups`)

Three Docker fields. All valid within-a-group combinations:

| `docker_access` | `docker_limited` | `docker_privileged` | UI shorthand |
|---|---|---|---|
| 1 | 0 | 0 | Docker |
| 0 | 1 | 0 | Docker limited |
| 0 | 0 | 1 | Docker root (privileged container only, no socket) |
| 1 | 0 | 1 | Docker + Docker root |
| 0 | 1 | 1 | Docker limited + Docker root |

- `docker_access` - normal access: raw `/var/run/docker.sock` (sees all, no quota)
- `docker_limited` - per-user filtered socket (this feature)
- `docker_privileged` - **"Docker (root)"**: runs the user container with `--privileged`. Fully orthogonal: standalone in a group it gives kernel-root inside the lab with no Docker socket; combined with normal or limited (same group or another the user belongs to) it escalates that access mode. It does **not** bypass the proxy on a limited grant
- limited quota/caps: `max_containers` (10), `max_volumes` (10), `max_networks` (3), `max_storage_gb` (50, soft), `cpu_cap_cores` (2), `mem_cap_gb` (8 per created container)

The UI rule: normal and limited are mutually exclusive within a group; Docker (root) is freely selectable on its own or with either. The features pill on the groups table is a single `Docker` chip whenever any of the three is on - it indicates "this group has Docker config" without revealing flavour.

## Precedence

- Across groups: normal supersedes limited (raw socket makes the proxy moot); grants OR; quotas max-wins
- Within a group: normal XOR limited
- Docker (root) is fully orthogonal: it OR-accumulates across groups and may stand alone in a group (granting `--privileged` with no Docker socket)

## Labels stamped on every create

- `stellars.owner=<user>` - identity, used for all filtering
- `stellars.managed=true` - proxy-created (for janitors)
- `com.docker.compose.project=<configured>` - ad-hoc grouping in Docker Desktop; **not** overridden if the user is running their own `docker compose` (project + names preserved)

## Request flow

```mermaid
flowchart TD
    REQ[Docker API request] --> CL{classify}
    CL -- create --> CR[inject owner+managed labels<br/>prefix name 'user-owner-...'<br/>reject privileged / host-mount / host-net / cap-add<br/>count quota<br/>storage budget<br/>cap CPU and mem]
    CL -- list --> LS[merge owner-label filter into ?filters=]
    CL -- "action id" --> AC{target owner<br/>equals caller?}
    AC -- yes --> FW
    AC -- no --> NF[404 not found]
    CL -- prune --> PR[scope prune to owner label]
    CL -- other --> FW[forward to dockerd<br/>stream response]
    CR --> FW
    LS --> FW
    PR --> FW
```

## Endpoint behaviour

| Endpoint | Behaviour |
|---|---|
| `POST /containers\|volumes\|networks/create` | inject labels; count quota; storage budget (containers, volumes); containers also: name prefix, dangerous-flag check, image allowlist, CPU/mem cap |
| `GET /containers/json`, `/volumes`, `/networks` | inject `label=stellars.owner=<user>` into `?filters=` |
| `GET/POST/DELETE /containers\|volumes\|networks/{id}/...` | inspect target, 404 if not owned, else forward |
| `POST /containers\|volumes\|networks/prune` | inject owner label into `?filters=` so prune is owner-scoped |
| `POST /images/create` (`docker pull`) | image allowlist (if configured), else forward |
| everything else | streamed pass-through |

## Lifecycle

- The proxy is **embedded in the hub container** - no second compose service, no admin HTTP, no token. The module-singleton `Manager` lives in the hub's own asyncio event loop alongside the activity sampler and idle culler
- The socket directory `/var/run/stellars-docker-proxy-sockets` inside the hub is backed by a named docker volume `jupyterhub_docker` (declared in `compose.yml`, managed by Docker, no host path)
- On `pre_spawn_hook` the hub does `await register_user(...)` directly - the Manager creates a per-user `UnixSite` listener at `/var/run/stellars-docker-proxy-sockets/<user>/docker.sock` with the resolved quotas. Re-register is idempotent: replaces the previous listener so quota changes apply on the user's next spawn
- The spawner mounts the same named volume into the user container with `Subpath: <user>`, so each lab sees ONLY its own subdirectory under `/run/dockersock/` containing the single `docker.sock` it's allowed to talk to. Mount-level isolation, no cross-user visibility
- On `post_stop_hook` the hub does `await unregister_user(...)`; the listener tears down, the socket file is removed, and the now-empty per-user subdirectory is cleaned up too
- Hub restart wipes all listeners (stateless); the next spawn re-registers automatically via `pre_spawn_hook`

## Modules

| Module | Role |
|---|---|
| `stellars_docker_proxy.config` | `ProxyConfig` + label constants |
| `stellars_docker_proxy.filters` | pure transforms (label injection, list filter, caps check/apply, dangerous, ownership, compose project) |
| `stellars_docker_proxy.quota` | pure accounting (counts, `/system/df` storage per owner) |
| `stellars_docker_proxy.server` | aiohttp reverse proxy: classify -> mutate/guard/quota -> stream; `create_app(ProxyConfig)` returns a per-owner app |
| `stellars_docker_proxy.manager` | `Manager` holds N per-user listeners in one process; register/unregister lifecycle |
| `stellars_hub_services.docker_proxy` | module-singleton `Manager` + `register_user`/`unregister_user` (async, direct Manager calls) |
| `stellars_hub_services.group_resolver` | `docker_limited` + quota max-wins + normal-supersedes-limited precedence |
| `stellars_hub_services.groups_config` | default fields + `validate_docker_selection` (mutual exclusivity) |
| `stellars_hub_services.hooks` | 3-branch docker block (normal / limited / none); awaits `register_user` |

## Configuration

One Dockerfile `ENV` and one Python-computed constant. Operators do nothing:

| Setting | Where | Value | Purpose |
|---|---|---|---|
| `JUPYTERHUB_DOCKER_PROXY_SOCKET_DIR` | `Dockerfile.jupyterhub` `ENV` | `/var/run/stellars-docker-proxy-sockets` | Path inside the hub container where the in-process proxy writes per-user listener sockets. Backed by a named docker volume - not a host path |
| `JUPYTERHUB_DOCKER_PROXY_SOCKETS_VOLUME` | `config/jupyterhub_config.py` (computed) | `f"{COMPOSE_PROJECT_NAME}_jupyterhub_docker"` | Actual on-daemon name of the named docker volume that backs the socket directory. Not operator-configurable - computed to match compose's automatic project-prefix namespacing of the `jupyterhub_docker:` volume declared in `compose.yml`. Follows the same convention as `f"{COMPOSE_PROJECT_NAME}_jupyterhub_shared"` in `DOCKER_SPAWNER_VOLUMES`. The spawner subpath-mounts this volume into each lab so each lab sees only its own subdirectory |
| `COMPOSE_PROJECT_NAME` | compose-passthrough env | required, no default | Drives docker compose project label and volume namespacing. Empty raises `RuntimeError` at hub startup - silent fallback would mismatch compose's namespacing and fail spawns at Subpath resolution |

Compose-side: a single named volume `jupyterhub_docker` is declared at the bottom of `compose.yml`; compose namespaces it on the daemon to `${COMPOSE_PROJECT_NAME}_jupyterhub_docker` and mounts it on the hub at the socket-dir path. No host bind, no second container, no token, no `.env` change. To wipe state, operator can `docker volume rm ${COMPOSE_PROJECT_NAME}_jupyterhub_docker` (must be down first).

## Caveats

- Name prefix avoids cross-user collisions on the shared daemon; `docker stop foo` won't match - users reference the name shown in `docker ps`
- `DOCKER_HOST` points at `unix:///run/dockersock/docker.sock` (not literally `/var/run/docker.sock` - mounting a volume at `/var/run` would clobber it)
- `/system/df` is queried per create for the storage budget - latency on busy hosts
- Interactive TTY hijack (`exec -it`, `attach`) is not specially handled in v1; non-interactive streams work
- Hub restart wipes all listeners; running limited users need to restart their labs to be re-registered. Acceptable since a hub restart already stops all user spawners
- Process-compromise blast radius: a proxy bug inside the hub process can affect the hub itself. v1 acceptable trade-off for the convenience-driven model; the proxy code is small, well-tested, and entirely on the same loop as the hub's existing services

## Diagnostic endpoint (planned)

A future authenticated `GET /hub/api/admin/docker-proxy/status` (admin-only) will expose proxy state as JSON for triage and a possible future status page:

```json
{
  "socket_dir": "/var/run/stellars-docker-proxy-sockets",
  "registered": [
    {
      "user": "konrad.jelen",
      "socket_path": "/var/run/stellars-docker-proxy-sockets/konrad.jelen.sock",
      "since": "2026-05-26T15:14:06Z",
      "config": {
        "max_containers": 4,
        "max_volumes": 4,
        "max_networks": 1,
        "max_storage_gb": 50.0,
        "cpu_cap_cores": 4.0,
        "mem_cap_gb": 16.0,
        "compose_project": "stellars-tech-ai-lab"
      }
    }
  ]
}
```

Backed by `Manager.registered()` which already returns this shape. Auth uses the same admin-required decorator the existing `/hub/api/admin/*` handlers use. Until the endpoint lands, the same data is reachable via `docker exec <hub> ls -la /var/run/stellars-docker-proxy-sockets/` (one socket file per registered user) and the per-spawn `[Groups]` log line that carries `docker_limits=[...]` inline. Not yet implemented.

## Identity model

The proxy library itself knows only an `owner` string; no JupyterHub notion. Inside the hub process, the `Manager` holds N per-user `ProxyApp` instances, each bound to its own unix listener at `/var/run/stellars-docker-proxy-sockets/<owner>.sock`. Identity is baked into the listener: whichever container mounts a given socket file acts as that owner. There is no per-request authentication on the data path; access control is the bind-mount choice the spawner makes.

## Related

- `gpu-detection-and-configuration.md`
- `gpu-selection-jupyterlab-containers.md`
