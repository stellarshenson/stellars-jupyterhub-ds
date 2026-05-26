# Agent 1 - Core orchestration GC report

## Summary
KEPT=7, DELETED=0, PRUNED=0, INCONCLUSIVE=1

## Per-file

### config/jupyterhub_config.py
- STATUS: KEEP
- Action: none
- Rationale: this is an exec'd hub config script. Every top-level statement either assigns `c.JupyterHub.*` / `c.DockerSpawner.*` / `c.Authenticator.*` (consumed by JupyterHub at startup), defines a callback wired into a hook (`_post_stop_cleanup` -> `c.DockerSpawner.post_stop_hook`, `_admin_post_auth_hook` -> `c.Authenticator.post_auth_hook`), or feeds derived values into the Tornado/template settings. The inline helpers `_query_admin_state`, `_provision_admin_userinfo`, `_resolve_memory_quota_mb`, `BootstrapAdminAuthenticator`, `BootstrapAdminSignUpHandler` are all referenced later in the same module. Note: lines 21-23, 33, 35-36 import `BootstrapAdminAuthenticator`, `compute_bootstrap_window_open`, `make_admin_post_auth_hook`, `provision_admin_userinfo`, `query_admin_state` from `stellars_hub` but the symbols are shadowed by inline reimplementations - flagged below.
- Verification: 171 passing.

### services/jupyterhub/stellars_hub/stellars_hub/__init__.py
- STATUS: KEEP
- Action: none
- Rationale: all 30+ re-exports are part of the package's declared public API (`__all__`). Three external consumers exist: `config/jupyterhub_config.py` (the runtime config) and the test suites `test_imports.py`, `test_idle_culler.py`, `test_volume_cache.py`. Even the symbols only consumed by config-via-imported-then-shadowed pattern (admin bootstrap family) are kept because they belong to an in-progress refactor (see admin_bootstrap.py below).
- Verification: 171 passing.

### services/jupyterhub/stellars_hub/stellars_hub/hooks.py
- STATUS: KEEP
- Action: none
- Rationale: `make_pre_spawn_hook` is wired into `c.DockerSpawner.pre_spawn_hook` at `jupyterhub_config.py:590` and exercised by `test_imports.py:164,194`. `schedule_startup_favicon_callback` is invoked at `jupyterhub_config.py:707`. No internal-only helpers.
- Verification: 171 passing.

### services/jupyterhub/stellars_hub/stellars_hub/services.py
- STATUS: KEEP
- Action: none
- Rationale: `get_services_and_roles(sample_interval)` is invoked at `jupyterhub_config.py:690` to populate `c.JupyterHub.services` + `c.JupyterHub.load_roles`. Covered by `test_services.py` and `test_imports.py`.
- Verification: 171 passing.

### services/jupyterhub/stellars_hub/stellars_hub/auth.py
- STATUS: KEEP
- Action: none
- Rationale: `StellarsNativeAuthenticator` is the parent class of the inline `BootstrapAdminAuthenticator` at `jupyterhub_config.py:377` and of `admin_bootstrap.BootstrapAdminAuthenticator`. `CustomAuthorizationAreaHandler` is injected by `StellarsNativeAuthenticator.get_handlers()` (called by NativeAuthenticator framework). `test_imports.py:134` validates both.
- Verification: 171 passing.

### services/jupyterhub/stellars_hub/stellars_hub/admin_bootstrap.py
- STATUS: INCONCLUSIVE (kept)
- Action: none
- Rationale: every symbol in this module (`BootstrapAdminAuthenticator`, `BootstrapAdminSignUpHandler`, `compute_bootstrap_window_open`, `make_admin_post_auth_hook`, `provision_admin_userinfo`, `query_admin_state`) is imported by `config/jupyterhub_config.py` at the top but then SHADOWED by inline reimplementations (`_query_admin_state`, `_provision_admin_userinfo`, `_admin_post_auth_hook`, local `BootstrapAdminAuthenticator` on line 377, local `BootstrapAdminSignUpHandler` on line 334). The runtime hub uses the inline copies; the imported ones are dead. HOWEVER, `jupyterhub_config.py:22` comments explicitly call this "refactor in progress" - the module is the migration target. The package's test_imports also indirectly loads it via `from stellars_hub import ...`. Removing it now would discard half-completed refactor work. Flag for operator: decide whether to (a) complete the refactor by deleting the inline copies in `jupyterhub_config.py` and using the imported symbols, or (b) abandon the refactor and delete `admin_bootstrap.py` + its `__init__.py` re-exports.
- Verification: 171 passing.

### services/jupyterhub/stellars_hub/stellars_hub/events.py
- STATUS: KEEP
- Action: none
- Rationale: `register_events()` is called once at `jupyterhub_config.py:217`. The three closures (`sync_nativeauth_on_rename`, `create_nativeauth_on_user_insert`, `remove_nativeauth_on_user_delete`) are decorated `@event.listens_for(orm.User...)` so SQLAlchemy keeps them alive via its event registry - they would still be required even if no direct caller appeared in grep.
- Verification: 171 passing.

### services/jupyterhub/stellars_hub/stellars_hub/branding.py
- STATUS: KEEP
- Action: none
- Rationale: `setup_branding()` is the sole public symbol, called from `jupyterhub_config.py:471` and exercised by `test_branding.py` (11 tests) and `test_imports.py:150`.
- Verification: 171 passing.

## Cross-boundary flags

- `stellars_hub.handlers.favicon.FaviconRedirectHandler` is imported lazily inside `hooks.py:219,289` (Agent 4 owns `handlers/favicon.py`). Confirmed alive - do not let Agent 4 prune it.
- `stellars_hub.group_resolver.resolve_group_config` and `stellars_hub.groups_config.GroupsConfigManager` imported by `hooks.py:7-8` (Agent 2 scope). Confirmed alive.
- `stellars_hub.docker_proxy.ensure_user_proxy` imported by `hooks.py:6` (Agent 2 scope). Confirmed alive.
- `stellars_hub.activity.helpers.{rename_activity_user, initialize_activity_for_user, delete_activity_user}` imported lazily in `events.py:36,76,110` (Agent 3 scope). Confirmed alive.
- `stellars_hub.password_cache.{cache_password, clear_cached_password}` imported lazily in `events.py:72,102` (Agent 3 scope). Confirmed alive.
- Admin bootstrap refactor: see INCONCLUSIVE above. If operator decides to complete it, `config/jupyterhub_config.py` lines 250-454 (the inline reimplementations and the inline `BootstrapAdminAuthenticator`/`BootstrapAdminSignUpHandler` classes) become deletable. If operator decides to abandon it, `admin_bootstrap.py` + the 6 corresponding lines in `__init__.py` (imports and `__all__` entries) become deletable.

## Tests final state
171 passing
