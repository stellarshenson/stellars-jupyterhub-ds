# Dead-Code GC Round (v3.10.15)

Checkpoint tag: `CHECKPOINT_BEFORE_GC_3.10.15` (revertable).

## Status legend

- [ ] pending
- [~] in progress
- [x] reviewed - KEEP (defended)
- [-] reviewed - DELETED (file removed)
- [!] reviewed - PRUNED (dead symbols removed in place)
- [?] reviewed - INCONCLUSIVE (flag for operator)

Per-file note format: `STATUS path - one-line reason`.

## Agent 1 - Core orchestration & hooks

Owner files:
- [x] `config/jupyterhub_config.py` - exec'd hub config, all top-level statements wire into c.* or hooks
- [x] `services/jupyterhub/stellars_hub/stellars_hub/__init__.py` - public API re-exports, exercised by tests + config
- [x] `services/jupyterhub/stellars_hub/stellars_hub/hooks.py` - both functions wired into spawner + IOLoop callback
- [x] `services/jupyterhub/stellars_hub/stellars_hub/services.py` - get_services_and_roles populates c.JupyterHub.services
- [x] `services/jupyterhub/stellars_hub/stellars_hub/auth.py` - parent class for BootstrapAdminAuthenticator + handler injection
- [?] `services/jupyterhub/stellars_hub/stellars_hub/admin_bootstrap.py` - imported by config but shadowed by inline copies; refactor in progress
- [x] `services/jupyterhub/stellars_hub/stellars_hub/events.py` - register_events() called from config, listeners kept alive by SQLAlchemy
- [x] `services/jupyterhub/stellars_hub/stellars_hub/branding.py` - setup_branding() called from config

Report: `.claude/gc/agent-1.md`

## Agent 2 - Groups, GPU, Docker proxy, idle-culler, docker utils

Owner files:
- [x] `services/jupyterhub/stellars_hub/stellars_hub/group_resolver.py` - KEEP: `resolve_group_config`/`is_reserved_env_var` consumed by hooks + groups handler
- [x] `services/jupyterhub/stellars_hub/stellars_hub/groups_config.py` - KEEP: all CRUD + validators consumed by handlers and hooks
- [x] `services/jupyterhub/stellars_hub/stellars_hub/gpu.py` - KEEP: `is_wsl2`/`resolve_gpu_mode`/`enumerate_gpus` consumed by config; `detect_nvidia` exercised by out-of-scope test
- [x] `services/jupyterhub/stellars_hub/stellars_hub/docker_proxy.py` - KEEP: sidecar orchestration consumed by config + hooks
- [x] `services/jupyterhub/stellars_hub/stellars_hub/docker_utils.py` - KEEP: encoder + stats + executor consumed by handlers and caches
- [x] `services/jupyterhub/stellars_hub/stellars_hub/idle_culler.py` - KEEP: pure calcs consumed by session/activity handlers; runtime scheduled from config
- [x] `services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/__init__.py` - KEEP: documented public re-export surface
- [x] `services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/__main__.py` - KEEP: invoked as `python -m stellars_docker_proxy` by sidecar
- [x] `services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/config.py` - KEEP: ProxyConfig + label constants used everywhere in package
- [x] `services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/filters.py` - KEEP: all transforms called by server.py and tests
- [x] `services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/quota.py` - KEEP: all helpers called by server.py and tests
- [x] `services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/server.py` - KEEP: classify/create_app/run are CLI + documented public API

Report: `.claude/gc/agent-2.md`

## Agent 3 - Activity, caches, volumes

Owner files:
- [x] `services/jupyterhub/stellars_hub/stellars_hub/activity/__init__.py` - KEEP re-export hub
- [x] `services/jupyterhub/stellars_hub/stellars_hub/activity/helpers.py` - KEEP (record_activity_sample dead but cross-boundary; flagged)
- [x] `services/jupyterhub/stellars_hub/stellars_hub/activity/model.py` - KEEP ORM
- [x] `services/jupyterhub/stellars_hub/stellars_hub/activity/monitor.py` - KEEP singleton
- [?] `services/jupyterhub/stellars_hub/stellars_hub/activity/sampler.py` - whole-file dead in prod, cross-boundary test_imports.py refs; flagged
- [x] `services/jupyterhub/stellars_hub/stellars_hub/activity/service.py` - KEEP live JupyterHub managed service
- [x] `services/jupyterhub/stellars_hub/stellars_hub/container_size_cache.py` - KEEP, used by handlers/activity.py
- [x] `services/jupyterhub/stellars_hub/stellars_hub/password_cache.py` - KEEP, used by events.py + handlers/credentials.py
- [x] `services/jupyterhub/stellars_hub/stellars_hub/volume_cache.py` - KEEP, used by jupyterhub_config.py + handlers/activity.py
- [x] `services/jupyterhub/stellars_hub/stellars_hub/volumes.py` - KEEP, all three functions consumed by jupyterhub_config.py

Report: `.claude/gc/agent-3.md`

## Agent 4 - Handlers, HTML templates, static assets

Owner files:
- [x] `services/jupyterhub/stellars_hub/stellars_hub/handlers/__init__.py`
- [x] `services/jupyterhub/stellars_hub/stellars_hub/handlers/activity.py`
- [x] `services/jupyterhub/stellars_hub/stellars_hub/handlers/credentials.py`
- [x] `services/jupyterhub/stellars_hub/stellars_hub/handlers/favicon.py`
- [x] `services/jupyterhub/stellars_hub/stellars_hub/handlers/groups.py`
- [x] `services/jupyterhub/stellars_hub/stellars_hub/handlers/health.py`
- [x] `services/jupyterhub/stellars_hub/stellars_hub/handlers/notifications.py`
- [x] `services/jupyterhub/stellars_hub/stellars_hub/handlers/server.py`
- [!] `services/jupyterhub/stellars_hub/stellars_hub/handlers/session.py` - pruned dead `calc_*` re-exports from `__all__`
- [x] `services/jupyterhub/stellars_hub/stellars_hub/handlers/settings.py`
- [x] `services/jupyterhub/stellars_hub/stellars_hub/handlers/volumes.py`
- [x] `services/jupyterhub/html_templates_enhanced/*.html` (21 files)
- [x] `services/jupyterhub/html_templates_enhanced/static/custom.css`
- [x] `services/jupyterhub/html_templates_enhanced/static/mobile.js`
- [x] `services/jupyterhub/html_templates_enhanced/static/session-timer.js`

Report: `.claude/gc/agent-4.md`

## Agent 5 - Build, scripts, compose, Dockerfile, conf, extra, workflows

Owner files:
- [x] `Makefile` - KEEP; all targets reachable (README/CHANGELOG/preflight chain)
- [x] `start.sh`, `stop.sh` - KEEP; documented entrypoints (README/Makefile)
- [x] `compose.yml` - KEEP; core artefact referenced by every script
- [x] `scripts/build.sh`, `scripts/build_verbose.sh`, `scripts/start.sh` - KEEP; Makefile/README
- [x] `services/jupyterhub/Dockerfile.jupyterhub` - KEEP; core image
- [!] `services/jupyterhub/stellars_hub/Makefile` - PRUNE; removed lint refs to non-existent configure.py/constants.py
- [x] `services/jupyterhub/stellars-docker-proxy/Makefile` - KEEP; all lint refs exist
- [x] `services/jupyterhub/conf/apt-packages.yml` - KEEP; Dockerfile yq input
- [x] `services/jupyterhub/conf/settings_dictionary.yml` - KEEP; Dockerfile COPY + agent-4 handler
- [x] `services/jupyterhub/conf/volumes_dictionary.yml` - KEEP; Dockerfile COPY + agent-1 config
- [x] `services/jupyterhub/conf/bin/mkcert.sh` - KEEP; called by 00_provision_certificates.sh
- [x] `services/jupyterhub/conf/bin/start-platform.sh` - KEEP; Dockerfile CMD
- [x] `services/jupyterhub/conf/bin/start-platform.d/00_provision_certificates.sh` - KEEP; boot loop
- [x] `services/jupyterhub/conf/bin/start-platform.d/01_provision_config.sh` - KEEP; boot loop + CI test
- [x] `services/jupyterhub/conf/bin/start-platform.d/02_set_timezone.sh` - KEEP; boot loop
- [x] `services/jupyterhub/templates/certs/certs.yml` - KEEP; Dockerfile COPY (in-image fallback)
- [x] `services/jupyterhub/tests/test_provision_config.sh` - KEEP; CI workflow runs it
- [x] `extra/docker_volume_backupper/docker_volume_backupper.sh` - KEEP; extra/README documents
- [x] `extra/docker_volume_backupper/docker_volume_restore.sh` - KEEP; companion to backupper
- [x] `extra/volume-renamer/rename-user-volumes.sh` - KEEP; extra/README documents
- [x] `.github/workflows/docker-build.yml` - KEEP; CI trigger itself

Report: `.claude/gc/agent-5.md`

## Ground rules for all agents

1. **Scope discipline**: only modify/delete files in your owner list. If a symbol in your file is referenced ONLY from another agent's file, flag it but DO NOT prune across boundaries.
2. **Aggressive pruning**: dead = no production call site (not just test-only); orphan = no caller and no template/yaml/shell reference. Delete it.
3. **Cross-repo search before pruning**: grep across all `.py .html .yml .yaml .sh .js .css Dockerfile* Makefile* .toml .md` in the repo (excluding `.venv`, `__pycache__`, `.git`, `@archive`, `.ipynb_checkpoints`).
4. **Tests follow code**: if you delete a production symbol, delete or update its tests too. Run `pytest -q` for the affected package after your edits. The build must still pass.
5. **No git commits, no version bumps, no docker builds, no docker compose, no makefiles that publish**. Do not push. Do not tag.
6. **Report** your findings to `.claude/gc/agent-N.md` with one section per file (KEEP/DELETE/PRUNE + one line reason + diff-summary if pruned). Aggregate count: KEPT=N, DELETED=N, PRUNED=N, INCONCLUSIVE=N.
7. **Update this checklist** by setting the status box on each line you reviewed.
