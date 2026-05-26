# Agent 3 - Activity/caches/volumes GC report

## Summary
KEPT=10, DELETED=0, PRUNED=0, INCONCLUSIVE=0

No file in scope had any symbol that was both dead AND safe-to-prune within scope boundaries. The few dead candidates found (`activity/sampler.py` and the `record_activity_sample` helper) have their only consumer in `tests/test_imports.py`, which is out-of-scope for this agent. Per the "Cross-boundary dependencies: flag, don't touch" rule, these are flagged below for a future cross-cutting pass.

## Per-file

### services/jupyterhub/stellars_hub/stellars_hub/activity/__init__.py
- STATUS: KEEP
- Action: none. Pure re-export module; every name is either used in production (helpers consumed by `handlers/activity.py`, `events.py`; `ActivityMonitor` via singleton; `ActivityBase`/`ActivitySample` for ORM) or exercised by tests.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/activity/helpers.py
- STATUS: KEEP (1 cross-boundary symbol flagged)
- Action: none. `calculate_activity_score`, `get_activity_sampling_status`, `get_inactive_after_seconds`, `record_samples_for_all_users`, `reset_all_activity_data` -> `handlers/activity.py`. `rename_activity_user`, `delete_activity_user`, `initialize_activity_for_user` -> `events.py`. `record_activity_sample` has NO production caller (only `tests/test_imports.py`).
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/activity/model.py
- STATUS: KEEP
- Action: none. `ActivityBase.metadata.create_all` in `monitor.py` + `service.py`; `ActivitySample` ORM model is consumed by both processes. Columns kept (DB schema).
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/activity/monitor.py
- STATUS: KEEP
- Action: none. `ActivityMonitor` singleton accessed via `helpers.py`; `prune_old_samples` and `log_activity_tick` exercised by tests / `record_samples_for_all_users` respectively.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/activity/sampler.py
- STATUS: KEEP (whole-file dead in production - cross-boundary flag)
- Action: none. `ActivitySampler` and `start_activity_sampler` have NO production callers. The real periodic sampler is `activity/service.py`, registered via `services.py::get_services_and_roles` as `python -m stellars_hub.activity.service`. Only test refs are in out-of-scope `tests/test_imports.py`.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/activity/service.py
- STATUS: KEEP
- Action: none. Live entrypoint launched by JupyterHub managed-service spec in `services.py` line 28.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/container_size_cache.py
- STATUS: KEEP
- Action: none. `get_container_sizes_with_refresh` + `ContainerSizeRefresher` -> `handlers/activity.py`. `get_cached_container_sizes` is internal helper. Module-level `_size_executor`, `_container_sizes_cache` are state.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/password_cache.py
- STATUS: KEEP
- Action: none. `cache_password` + `clear_cached_password` -> `events.py`. `get_cached_password` -> `handlers/credentials.py`. `_password_cache` consumed by `tests/conftest.py`.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/volume_cache.py
- STATUS: KEEP
- Action: none. `configure_volume_cache` -> `config/jupyterhub_config.py`. `VolumeSizeRefresher` + `get_volume_sizes_with_refresh` -> `handlers/activity.py`. `get_cached_volume_sizes` is internal helper + test smoke.
- Verification: 171 passing

### services/jupyterhub/stellars_hub/stellars_hub/volumes.py
- STATUS: KEEP
- Action: none. All three public functions consumed by `config/jupyterhub_config.py`.
- Verification: 171 passing

## Cross-boundary flags

1. `activity/sampler.py` (entire file, ~115 LOC): `ActivitySampler` class + `start_activity_sampler()` function have zero production callers in this repo. The active sampler is `activity/service.py` (run as a JupyterHub managed service via `services.py`). Only references are in out-of-scope `tests/test_imports.py` (lines 84-86) and `__init__.py` re-export. Recommend: deletion in a follow-up that owns both `sampler.py` and `tests/test_imports.py`.

2. `activity/helpers.py::record_activity_sample` (~3 LOC): unused in production. Only referenced by out-of-scope `tests/test_imports.py` (lines 71, 81) and the `__init__.py` re-export. Trivial wrapper around `ActivityMonitor.get_instance().record_sample()`.

3. `activity/monitor.py::ActivityMonitor.prune_old_samples` is called only by in-scope tests, but the method is part of the public maintenance API of the singleton (matches `reset_all`, `delete_user`, `rename_user` shape). Kept defensively - explicit retention/cleanup hook.

## Tests final state
171 passing
