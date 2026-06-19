# JupyterHub Platform Fixes

Fixes applied to the Duoptimum Hub platform after the service rename and React-portal cutover. Each entry is the problem, the fix, and the files touched.

## Env-driven lab-container naming

The lab-container name was a literal `jupyterlab-{username}` in the spawner and hardcoded again in 9 hub lookups; a rename would desync spawn from lookup. Naming is now a single env-driven source of truth.

- **Variable** - `JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE` ({username} placeholder); default `jupyterlab-{username}`, baked image ENV, compose-exposed, on the Settings page
- **Forward** - `c.DockerSpawner.name_template` reads it; `docker_utils.lab_container_name(username)` renders it with the docker-encoded username
- **Reverse** - `docker_utils.encoded_username_from_lab_container(name)` recovers the username from a running container; prefix/suffix derived from the same template (returns None for non-lab containers)
- **Call sites** - server logs/restart, container stats cache, container size cache, api-keys pool, notification + download proxy hosts all derive the name from the helpers, none hardcode `jupyterlab-`
- **Tests** - 8 in `tests/test_docker_utils.py` (forward, reverse, custom template with suffix, forward/reverse consistency)

## Lab compose project

Spawned labs carry a `com.docker.compose.project` label so they group under `docker compose ls`.

- **Variable** - `JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME`; empty = same project as the hub, set to group labs separately
- **Applied** - `pre_spawn_hook` stamps the label; volume namespacing stays on `JUPYTERHUB_COMPOSE_PROJECT_NAME` (unchanged)

## Base URL canonical /hub

The hub serves `base_url=/hub`, but Traefik's alias-redirect was left pointing the new path at the old one - it 302'd `/hub` -> `/jupyterhub`, a path the hub no longer serves.

- **Hub** - `JUPYTERHUB_BASE_URL=/hub` (baked + compose); `settings_dictionary.yml` default corrected to `/hub`
- **Traefik** - `/jupyterhub` and `/duoptimum-hub` are the transition aliases; `hub-alias-redirect` now 302s them to canonical `/hub`
- **Scope** - the live wrapper uses its own host-routing Traefik; this is the standalone `compose.yml` path-routing block

## Docker-proxy label prefix

`compose.yml` set `JUPYTERHUB_DOCKER_PROXY_LABEL_PREFIX={COMPOSE_PROJECT_NAME...}` with a missing `$`, baking the literal `{COMPOSE_PROJECT_NAME:-duoptimum-hub}.docker.proxy` - an invalid Docker label key that would reject proxy-managed `docker run`.

- **Fix** - added the `$`; resolves to `stellars-jupyterhub-ds.docker.proxy` (valid label key)

## Admin-bootstrap SQL moved to the service layer

Raw-sqlite bootstrap queries lived inline in `jupyterhub_config.py`; the config now only drives policy.

- **Module** - `duoptimum_hub_services/admin_bootstrap.py` holds `query_admin_state` and `provision_admin_userinfo` (stdlib sqlite3, runs at config-load before the ORM exists)
- **Path override** - `STELLARS_JUPYTERHUB_DB_PATH` (tests point it at a temp file); default `/data/jupyterhub.sqlite`
- **Tests** - 12 in `tests/test_admin_bootstrap.py` (window open/closed, insert, initial-only no-op, changed-password left alone)

## Required-config validation (no flaky defaults)

Key variables masked emptiness with a default, so a misconfigured environment limped on instead of failing. They now hard-fail.

- **De-defaulted** - `JUPYTERHUB_ADMIN`, `JUPYTERHUB_LAB_IMAGE`, `JUPYTERHUB_NETWORK_NAME` read with no masking default (all three are baked image ENV + set in compose)
- **Validator** - `_validate_required_config()` raises listing every empty key var; runs at the end of the env-load section
- **Already hard-failing** - `JUPYTERHUB_COMPOSE_PROJECT_NAME` and the docker-proxy socket dir/volume validate at their own resolution points

## Event-schema version warning

JupyterHub's bundled `event-schemas/server-actions/v1.yaml` ships `version: 1` (int); `jupyter_events >= 0.11` requires a string, logging a `JupyterEventsVersionWarning` on every hub start.

- **Module** - `duoptimum_hub_services/event_schema_fix.py::fix_event_schema_versions()` quotes the integer version in each bundled schema (idempotent, logs what it changed)
- **Build** - `Dockerfile.jupyterhub` calls it once after jupyterhub + the package are installed
- **Tests** - 5 in `tests/test_event_schema_fix.py` (quotes int, idempotent on quoted, other lines untouched, nested files, empty base)

## Makefile build version from the image

The build banner recomputed the version from `pyproject.toml`; it now reports what was actually built.

- **Source** - `docker inspect` of `stellars/duoptimum-hub:latest` reads the baked `version` label, the `STELLARS_JUPYTERHUB_VERSION` env, and the image id
- **Fallback** - prints the pyproject-computed version only when the image is absent
- **Used by** - `make build`, `make build_verbose`, `make rebuild`
