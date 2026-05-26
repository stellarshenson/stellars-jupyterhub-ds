# Dead-Code GC Round - final report (v3.10.15)

Checkpoint tag (revertable): `CHECKPOINT_BEFORE_GC_3.10.15`.

## Aggregate across 5 agents

| Agent | Scope | Kept | Pruned | Deleted | Inconclusive |
|---|---|---:|---:|---:|---:|
| 1 | Core orchestration / hooks | 7 | 0 | 0 | 1 (`admin_bootstrap.py`) |
| 2 | Groups / GPU / docker proxy / idle-culler | 12 | 0 | 0 | 0 |
| 3 | Activity / caches / volumes | 8 | 0 | 0 | 2 cross-boundary flags |
| 4 | Handlers / HTML / static | 33 | 1 (`handlers/session.py` `__all__`) | 0 | 0 |
| 5 | Build / scripts / conf / extras | 21 | 1 (`stellars_hub/Makefile` lint dead targets) | 0 | 0 |

## Aggressive prune round (per operator: "if not used in production -> goes")

After the agents reported, the cross-boundary flags + the admin-bootstrap inconclusive were resolved as deletions:

### Files deleted

| File | Reason |
|---|---|
| `services/jupyterhub/stellars_hub/stellars_hub/admin_bootstrap.py` | Every symbol shadowed by inline reimplementations in `config/jupyterhub_config.py`. Module had zero production callers (`tests/test_imports.py` had no references either). |
| `services/jupyterhub/stellars_hub/stellars_hub/activity/sampler.py` | Whole file dead in production - superseded by `activity/service.py` which runs the sampler as a JupyterHub managed service. Only refs were in `__init__.py` re-export + `tests/test_imports.py` smoke test. |

### Symbols pruned

| Symbol | Reason |
|---|---|
| `activity/helpers.py::record_activity_sample` (3 LOC) | Trivial wrapper over `ActivityMonitor.get_instance().record_sample(...)`. No production caller. |
| `gpu.py::detect_nvidia` (8 LOC) | Thin wrapper: `1 if enumerate_gpus(...) else 0`. Not exported by `stellars_hub/__init__.py`. No production caller - `config/jupyterhub_config.py` uses `resolve_gpu_mode` which calls `enumerate_gpus` directly. |
| `handlers/session.py::__all__` calc_* re-exports | Legacy back-compat shim, no external consumer (Agent 4). |
| `stellars_hub/Makefile` lint targets pointing at non-existent files | `configure.py` / `constants.py` never existed in current tree (Agent 5). |

### Re-exports cleaned up

- `stellars_hub/__init__.py`: dropped 6 admin-bootstrap exports + their `__all__` entries.
- `stellars_hub/activity/__init__.py`: dropped `ActivitySampler`, `start_activity_sampler`, `record_activity_sample` imports + `__all__` entries.
- `config/jupyterhub_config.py`: dropped the 5 admin-bootstrap symbols from the `from stellars_hub import (...)` block; kept `StellarsNativeAuthenticator` (still the parent of the inline class).

### Tests adjusted

- `tests/test_imports.py`: dropped `test_activity_sampler`; rewrote `test_activity_helpers` to no longer import `record_activity_sample` (asserts `calculate_activity_score` callable instead); rewrote `test_gpu` to import `enumerate_gpus` instead of `detect_nvidia`; removed `stellars_hub.activity.sampler` from `test_all_modules_importable`.
- `tests/test_gpu.py`: dropped `TestDetectNvidia` class (2 tests).

## Verification (critical-functionality gates)

- `cd services/jupyterhub/stellars_hub && python -m pytest tests/ -q` -> **168 passing** (was 171; -3 dead-symbol tests).
- `cd services/jupyterhub/stellars-docker-proxy && python -m pytest tests/ -q` -> **26 passing**.
- `python -m py_compile config/jupyterhub_config.py` -> OK.
- Runtime `import stellars_hub` smoke - clean public surface, no orphan re-exports.
- Static grep: zero references to deleted symbols anywhere in the live tree (excluding `.claude/`).
- The inline admin-bootstrap production path in `config/jupyterhub_config.py` is intact and self-contained:
  - `StellarsNativeAuthenticator` still imported from `stellars_hub`
  - `_NativeSignUpHandler` still imported from `nativeauthenticator.handlers`
  - inline `BootstrapAdminAuthenticator`, `BootstrapAdminSignUpHandler`, `_admin_post_auth_hook`, `_query_admin_state`, `_provision_admin_userinfo`, `_BOOTSTRAP_WINDOW_OPEN`, `_DB_EMPTY_AT_STARTUP`, `_ADMIN_PRESENT_AT_STARTUP`, `_ADMIN_PROVISIONING_REQUESTED` all present and unmodified
  - `c.JupyterHub.authenticator_class = BootstrapAdminAuthenticator` (line 634) resolves to the inline class
  - `c.Authenticator.post_auth_hook = _admin_post_auth_hook` (line 652) resolves to the inline hook
- SQLAlchemy `register_events` listeners' lazy imports of `activity.helpers.{rename,initialize,delete}_activity_user` + `password_cache.{cache,clear_cached}_password` still resolve.

## Rollback

If anything goes wrong on the next image rebuild + boot: `git reset --hard CHECKPOINT_BEFORE_GC_3.10.15`.
