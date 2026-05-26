# Admin-bootstrap refactor: criteria + guardrails

Goal: stop shadowing `stellars_hub.admin_bootstrap` symbols with inline reimplementations in `config/jupyterhub_config.py`. Use the module symbols. Behaviour must not change.

## Equivalence criteria (must all hold after refactor)

For each replacement, the inline copy and the module symbol are equivalent iff:

1. **`_query_admin_state` -> `query_admin_state`**
   - Same `(db_empty, admin_present)` return type, same edge cases (no admin_username -> `(True, False)`; missing DB file -> `(True, False)`; missing `users_info` table -> `(True, False)`).
   - Same SQL queries, identical control flow.
   - Caller passes `_DB_PATH` explicitly (module version has no default).

2. **`_provision_admin_userinfo` -> `provision_admin_userinfo`**
   - Same three-branch behaviour: missing UserInfo -> INSERT with `bcrypt.gensalt()` and `is_authorized=1`; matching hash -> silent no-op; non-matching -> "password changed; env ignored" log.
   - Same `[Admin Bootstrap]` print prefixes.
   - Caller passes `_DB_PATH` explicitly.

3. **Inline `_BOOTSTRAP_WINDOW_OPEN` boolean -> `compute_bootstrap_window_open(...)`**
   - Function takes `(signup_enabled, admin_password, db_empty, admin_present)` and returns `not signup_enabled and not admin_password and db_empty and not admin_present`.
   - Note: inline expression compares `JUPYTERHUB_SIGNUP_ENABLED == 0`; module compares `not signup_enabled`. Equivalent for ints (0/1) and bools because `not 0 == not False`, `not 1 == not True`. Caller must keep passing the int.

4. **Inline `BootstrapAdminSignUpHandler` -> module `BootstrapAdminSignUpHandler`**
   - Same `get_result_message` override; same two patch points (success-with-is_authorized; bootstrap-window-only-admin error).
   - The module version reads admin name from `self.authenticator.bootstrap_admin_username` (trait) rather than a module global. Hub config sets the trait on the imported `BootstrapAdminAuthenticator` class -> equivalent.

5. **Inline `BootstrapAdminAuthenticator` -> module `BootstrapAdminAuthenticator`**
   - Module class uses three `config=True` traitlets (`bootstrap_window_open: Bool`, `bootstrap_admin_username: Unicode`, `operator_signup_enabled: Bool`). Hub config sets them via `c.BootstrapAdminAuthenticator.* = ...` before `c.JupyterHub.authenticator_class = BootstrapAdminAuthenticator` is assigned.
   - Inherits from `StellarsNativeAuthenticator` (same as inline).
   - Overrides: `_bootstrap_admin_pending`, `enable_signup` (property + no-op setter), `validate_username`, `get_handlers`, `create_user` - all logically identical to inline.

6. **`_admin_post_auth_hook` -> `make_admin_post_auth_hook(JUPYTERHUB_ADMIN)`**
   - Factory returns an async closure `(authenticator, handler, authentication) -> authentication` that flips `authentication['admin']=True` when `authentication.get('name') == admin_username`.
   - Assigned to `c.Authenticator.post_auth_hook` unchanged.

## Guardrails (executed in order)

1. **Read the module class** to verify it accepts the traits the way I expect (`Bool`, `Unicode`, `config=True`). Confirmed by Read above.
2. **Add the c.* trait assignments** BEFORE removing inline code. (Net behaviour with traits set is the same as inline reading globals.)
3. **Swap call sites one at a time**: helpers first, then handler/authenticator, then post-auth hook. After each swap, run `python -m py_compile config/jupyterhub_config.py`.
4. **Drop the now-dead inline definitions and unused imports** (`StellarsNativeAuthenticator`, `_NativeSignUpHandler`) only after every consumer is on the module path.
5. **Test gate**: `cd services/jupyterhub/stellars_hub && python -m pytest tests/ -q` must remain 171 passing.
6. **Static-load gate**: `python -c "import ast; ast.parse(open('config/jupyterhub_config.py').read())"` and `python -m py_compile config/jupyterhub_config.py`.
7. **Token-roundtrip sanity**: grep for any remaining mentions of `_query_admin_state`, `_provision_admin_userinfo`, `_admin_post_auth_hook`, `_NativeSignUpHandler`, `StellarsNativeAuthenticator` in the config file - all must be gone after step 4.
8. **Spawn-time path sanity**: this refactor does NOT touch `pre_spawn_hook` / `post_stop_hook` / `post_auth_hook` wiring beyond changing the assigned callable. The hook signatures stay identical.
9. **Revertable**: `CHECKPOINT_BEFORE_GC_3.10.15` tag still rolls back.
10. **Do NOT touch**: the module `admin_bootstrap.py` itself, any tests, any other config logic, any version number.

## What stays the same

- `c.JupyterHub.authenticator_class = BootstrapAdminAuthenticator` (still that name)
- All other `c.NativeAuthenticator.*` traits (inherited by the subclass)
- `_DB_PATH`, `_DB_EMPTY_AT_STARTUP`, `_ADMIN_PRESENT_AT_STARTUP`, `_BOOTSTRAP_WINDOW_OPEN`, `_ADMIN_PROVISIONING_REQUESTED` module-level locals (used elsewhere in the file)
- The `c.Authenticator.post_auth_hook = ...` assignment (only the right-hand side changes)

## Out of scope

- The `_NativeSignUpHandler` re-import line (only used by the inline handler; removed once handler is gone)
- The `StellarsNativeAuthenticator` import (only used as inline-class base; removed once class is gone)
- Anything past `# ── Section 4` not related to admin-bootstrap
