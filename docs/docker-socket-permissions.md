# Docker Access Control

Group-based Docker access for user containers. Three orthogonal-but-coupled config fields on any admin-managed group at `/hub/groups`.

| Field | Effect |
|---|---|
| `docker_access` | Mounts raw `/var/run/docker.sock` into the user container - sees all containers, no quota |
| `docker_limited` | Mounts a per-user filtered socket served by a sidecar; user sees and manages only their own containers up to a quota. See [limited-docker-access.md](limited-docker-access.md) |
| `docker_privileged` | **UI label: "Docker (root)"** - runs the user container with `--privileged`. Requires `docker_access` or `docker_limited` to be on in the same group. Raises the privilege of an existing grant, does not bypass the limited proxy |

Valid combinations:

| Normal | Limited | Root | UI shorthand |
|---|---|---|---|
| 1 | 0 | 0 | Docker |
| 0 | 1 | 0 | Docker limited |
| 1 | 0 | 1 | Docker + Docker root |
| 0 | 1 | 1 | Docker limited + Docker root |

Rules enforced server-side (`stellars_hub_services.groups_config.validate_docker_selection`) and client-side in the Groups UI:

- Normal XOR limited within one group
- Docker (root) requires normal or limited on the same group
- Across groups: normal supersedes limited; grants OR; limited quotas max-wins

The groups table shows a single `Docker` features chip whenever any of the three fields is on - it indicates "this group has Docker config" without revealing the flavour.

**Implementation**: `services/jupyterhub/stellars_hub_services/stellars_hub_services/hooks.py::pre_spawn_hook` reads the resolved config and applies the volume mount / sidecar / `privileged=True` accordingly. Changes require a server restart (stop/start cycle).

**Security**: All three fields grant significant privileges. Only grant to trusted users.
