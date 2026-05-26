# Agent 2 - Groups/GPU/Docker-proxy/idle-culler GC report

## Summary
KEPT=12, DELETED=0, PRUNED=0, INCONCLUSIVE=0

Every public symbol within scope has at least one non-test production caller
or is a documented public-API surface (re-exports listed in
`docs/limited-docker-access.md`, `docs/stellars-hub-package.md`,
`docs/gpu-detection-and-configuration.md`). No file was changed.

## Per-file

### services/jupyterhub/stellars_hub/stellars_hub/group_resolver.py
- STATUS: KEEP
- `resolve_group_config` consumed by `hooks.py::pre_spawn_hook` and tests; `is_reserved_env_var` consumed by `handlers/groups.py` and tests; `_DL_DEFAULTS` is module-private and used in the same file. Cross-boundary signature locked.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/groups_config.py
- STATUS: KEEP
- `GroupConfig`, `GroupsConfigBase`, `GroupsConfigManager`, `default_config`, `validate_group_name`, `validate_gpu_selection`, `validate_docker_selection` all consumed by `handlers/groups.py`, `hooks.py`, and tests. Internal helpers (`_GROUP_NAME_RE`, `_row_to_dict`) used in-module.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/gpu.py
- STATUS: KEEP
- `is_wsl2`, `resolve_gpu_mode` consumed by `config/jupyterhub_config.py` (out-of-scope, signature locked); `enumerate_gpus` consumed by `resolve_gpu_mode` and tests. `detect_nvidia` not in `__init__.py` exports but exercised by `test_imports.py` (out-of-scope test file) - kept rather than break that.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/docker_proxy.py
- STATUS: KEEP
- `detect_self_image`, `ensure_user_proxy`, `stop_user_proxy` consumed by `config/jupyterhub_config.py` and `hooks.py`. Constants `SOCK_MOUNT_DIR`, `SOCK_FILENAME`, `HOST_DOCKER_SOCK`, helper `docker_host_url`, `_client`, `_names` used in-module.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/docker_utils.py
- STATUS: KEEP
- `encode_username_for_docker` consumed by `handlers/{server,activity,volumes,notifications}.py` and HTML templates (comments in `home.html`, `admin.html`); `get_container_stats` (sync) and `get_container_stats_async` consumed by `handlers/activity.py`; `get_executor` consumed by `container_size_cache.py`, `volume_cache.py`. `_docker_executor` is the module-private singleton.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/idle_culler.py
- STATUS: KEEP
- All `calc_*`, `should_cull` consumed by `handlers/session.py`, `handlers/activity.py`, and `run_cull_pass` itself; `run_cull_pass` + `schedule_idle_culler` consumed by `config/jupyterhub_config.py` (signature locked). `_as_utc` private helper.
- Verification: 171 passing

### services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/__init__.py
- STATUS: KEEP
- Re-exports (`ProxyConfig`, `OWNER_LABEL`, `MANAGED_LABEL`, `LABEL_NAMESPACE`, `create_app`, `run`, `classify`, `filters`, `quota`) are the public surface documented in `docs/limited-docker-access.md` and `docs/stellars-hub-package.md`. `LABEL_NAMESPACE` has no in-repo consumer of the re-export, but it is a natural namespace primitive and documented; default-to-KEEP rule applies.
- Verification: 26 passing

### services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/__main__.py
- STATUS: KEEP
- `main` invoked by the sidecar (`python -m stellars_docker_proxy` in `stellars_hub/docker_proxy.py::ensure_user_proxy` command line) and by the console_scripts entry in `pyproject.toml`.
- Verification: 26 passing

### services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/config.py
- STATUS: KEEP
- `ProxyConfig` consumed by `__main__.py`, `server.py`, tests. `OWNER_LABEL`/`MANAGED_LABEL`/`LABEL_NAMESPACE`/`BYTES_PER_GB`/`NANO_PER_CORE` consumed by `filters.py`, `quota.py`, `server.py`, tests. All dataclass fields (`socket_mode`, `image_allowlist`, `block_dangerous`, `compose_project`, `name_prefix`, caps) read by `server.py` and `__main__.py`.
- Verification: 26 passing

### services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/filters.py
- STATUS: KEEP
- Every public function (`has_compose_project`, `inject_compose_project`, `owner_labels`, `inject_labels`, `ensure_name_prefix`, `merge_label_filter`, `is_owned`, `caps_violation`, `apply_caps`, `dangerous_reason`) called by `server.py` and/or tests; `COMPOSE_PROJECT_LABEL` re-exported through `filters` and used by `server.py` + tests.
- Verification: 26 passing

### services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/quota.py
- STATUS: KEEP
- `list_count`, `over_count`, `storage_used_bytes`, `over_storage_budget` all called by `server.py` and exercised by `tests/test_quota.py`.
- Verification: 26 passing

### services/jupyterhub/stellars-docker-proxy/stellars_docker_proxy/server.py
- STATUS: KEEP
- `classify`, `create_app`, `run` are the public entrypoints (CLI + tests + documented public API with the `owner_resolver` seam). `ProxyApp` class and all helpers (`_strip_version`, `_err`, `_HOP_BY_HOP`, `_VERSION_RE`) used in-module.
- Verification: 26 passing

## Cross-boundary flags

- `group_resolver.resolve_group_config` signature consumed by `hooks.py` (Agent 1 scope).
- `gpu.is_wsl2`, `gpu.resolve_gpu_mode`, `gpu.enumerate_gpus`, `gpu.detect_nvidia` consumed by `config/jupyterhub_config.py` (Agent 5? - config is Agent 1's). Signatures preserved.
- `docker_proxy.{detect_self_image, ensure_user_proxy, stop_user_proxy}` consumed by `config/jupyterhub_config.py` and `hooks.py` (Agent 1).
- `idle_culler.{run_cull_pass, schedule_idle_culler, calc_*}` consumed by `config/jupyterhub_config.py`, `handlers/session.py`, `handlers/activity.py` (Agent 4).
- `docker_utils.{encode_username_for_docker, get_container_stats_async, get_executor}` consumed by Agent 3 (`container_size_cache.py`, `volume_cache.py`) and Agent 4 (handlers).
- `__init__.py` re-export of `LABEL_NAMESPACE` has no external consumer in-repo; kept under the public-API default-KEEP rule. Flag for operator if a stricter pass wants it pruned.
- `pytest-asyncio` was missing on the host; installed via `pip install --user --break-system-packages pytest-asyncio` (per task brief). No code change.

## Tests final state
stellars_hub: 171 passing; stellars-docker-proxy: 26 passing
