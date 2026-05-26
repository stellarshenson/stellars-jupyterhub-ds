# Agent 5 - Build/scripts/conf/extras GC report

## Summary
KEPT=22, DELETED=0, PRUNED=1, INCONCLUSIVE=0

## Per-file

### Makefile
- STATUS: KEEP
- Reachable via: documented in README.md (`make build`), CHANGELOG.md (`make preflight`, `make rebuild`, `make push`); all 14 targets cross-reference each other through deps (preflight gate, build/push chain). `PROJECT_NAME` is computed but never substituted - left in place; it preserves positional alignment of the `pyproject.toml` parse tuple (word 1..4) and removal would obscure intent. No-op cost.
- Action: KEEP

### start.sh
- STATUS: KEEP
- Reachable via: `Makefile::start` (`@./start.sh`), README.md line 45 (documented entry point), docs/medium/self-service-jupyterhub.md.

### stop.sh
- STATUS: KEEP
- Reachable via: README.md line 48 (rendered by the copier template alongside `start.sh`); kept for symmetry with `start.sh`. Not invoked from the Makefile (Makefile stop target inlines the compose-down) but documented in README as a copier-rendered companion script.

### compose.yml
- STATUS: KEEP
- Reachable via: every script (`start.sh`, `stop.sh`, `scripts/start.sh`, `scripts/build.sh`, `scripts/build_verbose.sh`, `Makefile` start/stop/logs/clean), Dockerfile build context, CI workflow. Core artefact.

### scripts/build.sh
- STATUS: KEEP
- Reachable via: `Makefile::build` (`cd ./scripts && ./build.sh`), README.md.

### scripts/build_verbose.sh
- STATUS: KEEP
- Reachable via: `Makefile::build_verbose`.

### scripts/start.sh
- STATUS: KEEP
- Reachable via: not invoked from any script but appears alongside `scripts/build*.sh` as the convenience `cd scripts && ./start.sh` flow; thin wrapper around `docker compose up`. No README mention. Defensive KEEP - aggressive prune candidate flagged below.

### services/jupyterhub/Dockerfile.jupyterhub
- STATUS: KEEP
- Reachable via: `compose.yml::jupyterhub.build.dockerfile`, `Makefile::_rebuild_impl`, CI hadolint job. Core build artefact.

### services/jupyterhub/stellars_hub/Makefile
- STATUS: PRUNE
- Reachable via: documented in `docs/stellars-hub-package.md` (local dev). `lint` target referenced two non-existent files (`stellars_hub/configure.py`, `stellars_hub/constants.py`); pruned those lines. Remaining targets (`install`, `build`, `test`, `clean`, `lint`) all parse and reference real artefacts.

### services/jupyterhub/stellars-docker-proxy/Makefile
- STATUS: KEEP
- Reachable via: local dev convenience for the stellars-docker-proxy package. All `lint` targets reference existing files (`__init__.py`, `config.py`, `filters.py`, `quota.py`, `server.py`, `__main__.py`).

### services/jupyterhub/conf/apt-packages.yml
- STATUS: KEEP
- Reachable via: Dockerfile.jupyterhub line 49 (`COPY ... /apt-packages.yml`), parsed by `yq` inside the image at build time (line 81).

### services/jupyterhub/conf/settings_dictionary.yml
- STATUS: KEEP
- Reachable via: Dockerfile.jupyterhub line 116 (`COPY ... /srv/jupyterhub/settings_dictionary.yml`), consumed by `services/jupyterhub/stellars_hub/stellars_hub/handlers/settings.py` (agent-4 scope).

### services/jupyterhub/conf/volumes_dictionary.yml
- STATUS: KEEP
- Reachable via: Dockerfile.jupyterhub line 117, `config/jupyterhub_config.py::VOLUMES_DICTIONARY_PATH`, `docs/user-volumes.md`.

### services/jupyterhub/conf/bin/mkcert.sh
- STATUS: KEEP
- Reachable via: Dockerfile.jupyterhub line 108 (`COPY services/jupyterhub/conf/bin/*.sh /`), invoked by `00_provision_certificates.sh::auto_generate`, `config/jupyterhub_config.py` comment, `docs/certificates.md`.

### services/jupyterhub/conf/bin/start-platform.sh
- STATUS: KEEP
- Reachable via: Dockerfile.jupyterhub `CMD ["/start-platform.sh"]`, copied via wildcard at line 108.

### services/jupyterhub/conf/bin/start-platform.d/00_provision_certificates.sh
- STATUS: KEEP
- Reachable via: Dockerfile.jupyterhub line 109 (`COPY .../start-platform.d /start-platform.d`), executed by `start-platform.sh` loop, `docs/certificates.md`.

### services/jupyterhub/conf/bin/start-platform.d/01_provision_config.sh
- STATUS: KEEP
- Reachable via: Dockerfile.jupyterhub line 109, executed by `start-platform.sh`, exercised by `tests/test_provision_config.sh`, CI workflow.

### services/jupyterhub/conf/bin/start-platform.d/02_set_timezone.sh
- STATUS: KEEP
- Reachable via: Dockerfile.jupyterhub line 109, executed by `start-platform.sh`. Sets system TZ from `JUPYTERHUB_TIMEZONE`.

### services/jupyterhub/templates/certs/certs.yml
- STATUS: KEEP
- Reachable via: Dockerfile.jupyterhub line 110 (`COPY services/jupyterhub/templates/certs /mnt/certs`), `docs/certificates.md`. Functionally a placeholder (overwritten on first boot by `auto_generate` in `00_provision_certificates.sh`), but documented and copied so it stays as the in-image fallback.

### services/jupyterhub/tests/test_provision_config.sh
- STATUS: KEEP
- Reachable via: CI workflow (`.github/workflows/docker-build.yml::provision_config_tests`). Tests `01_provision_config.sh` across 11 scenarios.

### extra/docker_volume_backupper/docker_volume_backupper.sh
- STATUS: KEEP
- Reachable via: `extra/README.md` documents it as a maintenance tool. Not orphaned.

### extra/docker_volume_backupper/docker_volume_restore.sh
- STATUS: KEEP
- Reachable via: companion to `docker_volume_backupper.sh`; lives in the same documented `extra/docker_volume_backupper` folder. Pairs as backup/restore.

### extra/volume-renamer/rename-user-volumes.sh
- STATUS: KEEP
- Reachable via: `extra/README.md` line 4 (`volume-renamer - scripts to rename volumes and migrate user data between usernames`).

### .github/workflows/docker-build.yml
- STATUS: KEEP
- Reachable via: GitHub Actions itself (on push/PR/dispatch). Runs hadolint on Dockerfile and `test_provision_config.sh`. Both targets exist on disk.

## Cross-boundary flags

- `services/jupyterhub/conf/settings_dictionary.yml` is read by `services/jupyterhub/stellars_hub/stellars_hub/handlers/settings.py` (agent-4 scope). Flag: if that handler is dead, the YAML becomes orphan-able.
- `services/jupyterhub/conf/volumes_dictionary.yml` is referenced from `config/jupyterhub_config.py` (agent-1 scope) via `VOLUMES_DICTIONARY_PATH`.
- `stellars_hub/Makefile::lint` target was referencing `stellars_hub/configure.py` and `stellars_hub/constants.py` - both non-existent files in agent-1's package. Pruned those `py_compile` lines from my Makefile (the lint target itself is mine); the missing files are presumably already gone, no agent-1 action required.
- `Makefile::PROJECT_NAME` is computed but never substituted in any recipe. Defensive KEEP - removing it shifts the `$(word N,...)` indices for `PROJECT_VERSION`/`CUDA_VERSION`/`JH_VERSION` and obscures the tuple shape.

## Verification

- `make help` (top-level) parses and lists all 14 targets.
- `make help` in `services/jupyterhub/stellars_hub` parses; pruned `lint` target shows in listing.
- Dockerfile `COPY services/jupyterhub/conf/bin/start-platform.d /start-platform.d` still has 3 scripts (00, 01, 02) - none deleted.
- Dockerfile `COPY services/jupyterhub/conf/bin/*.sh /` still resolves: `mkcert.sh` and `start-platform.sh` both present.
- Dockerfile `COPY services/jupyterhub/templates/certs /mnt/certs` still resolves: `certs.yml` and `README.md` present.
- No grep references to deleted files remain (none deleted this round).
- `test_provision_config.sh` script-under-test path (`01_provision_config.sh`) still exists.
- CI workflow inputs (Dockerfile, `test_provision_config.sh`) both exist on disk.
