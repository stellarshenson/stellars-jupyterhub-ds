# Acceptance Criteria - Compose Project Naming

Two explicit compose-project env vars replace the bare `COMPOSE_PROJECT_NAME` inside the hub: `JUPYTERHUB_COMPOSE_PROJECT_NAME` (the hub's own project - volume namespace + hub-infra labels) and `JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME` (the label stamped on spawned lab containers). They may differ; the lab var defaults to the hub project (empty suffix = same).

- [x] **Hub var read** - config reads `JUPYTERHUB_COMPOSE_PROJECT_NAME`, falling back to `COMPOSE_PROJECT_NAME` during transition; required non-empty (raises otherwise)
  - log: 2026-06-17 implemented (config:158); fallback keeps a not-yet-updated compose booting
- [x] **Volume namespacing unchanged** - per-user + shared + docker-proxy volume names stay on the hub var with the same value, so existing volumes still resolve (rename only, no re-namespacing)
  - log: 2026-06-17 verified - same value via compose mapping; would only change if the project name/suffix changed
- [x] **Lab var** - `JUPYTERHUB_LAB_COMPOSE_PROJECT_NAME` is the `com.docker.compose.project` label on spawned labs; defaults to the hub project (empty = same), set to group labs under a different project
  - log: 2026-06-17 implemented (config:176 default, config:703 -> pre_spawn_hook compose_project)
- [x] **Hub-infra labels use the hub var** - the gpuinfo sidecar the hub self-starts is labelled with `JUPYTERHUB_COMPOSE_PROJECT_NAME`
  - log: 2026-06-17 (config:518 ensure_gpuinfo_sidecar)
- [x] **Configured in compose** - both vars passed to the hub in compose.yml (hub mapped from compose's `COMPOSE_PROJECT_NAME`; lab empty -> same project)
  - log: 2026-06-17 compose.yml:125-126
- [x] **Baked in Dockerfile** - both `ENV`s present (empty defaults)
  - log: 2026-06-17 Dockerfile:277,280
- [x] **In settings dictionary** - both on the Settings page (old `COMPOSE_PROJECT_NAME` entry renamed)
  - log: 2026-06-17 settings_dictionary.yml:11,15
- [ ] **Edge: stale wrapper compose** - wrapper compose.yml (gitignored download) still passes `COMPOSE_PROJECT_NAME`; the fallback boots the hub correctly until it is refreshed to pass `JUPYTERHUB_COMPOSE_PROJECT_NAME`
  - log: 2026-06-17 documented; fallback covers it, no boot failure
- [x] **Verified** - `python -m py_compile` config clean; `make test` 566 + 63 pass
  - log: 2026-06-17
