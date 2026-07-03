# Acceptance Criteria - Per-User Environment Variables

An Environment tab on the user profile lets a user (or an admin editing that user) set name/value/description env vars that are injected into their lab container on spawn, guarded by the same reserved-name blacklist the group policy editor enforces, consolidated into a protected-env dictionary. Storage is a dedicated per-user SQLite store with replace semantics; the spawn hook injects them before group policies so admin/policy env always wins.

## Contents

- [Storage](#storage)
- [API](#api)
- [Access control](#access-control)
- [Blacklist / protection](#blacklist--protection)
- [Spawn injection](#spawn-injection)
- [Frontend](#frontend)
- [Edge cases](#edge-cases)

## Storage

- [x] **Store** - `UserEnvVarsManager` persists a JSON list of `{name, value, description}` per username in `/data/user_env_vars.sqlite` (env override `STELLARS_USER_ENV_VARS_DB_PATH`)
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Replace semantics** - `set_env_vars` overwrites the whole set; a var absent from the new set is removed (not merged)
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Caps** - reject over `MAX_ENV_COUNT` (100) entries or an over `MAX_ENV_BYTES` (16 KB) serialized blob
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Rename sync** - a user rename moves their env-vars row (SQLAlchemy `User.name` listener in `events.py`)
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Delete sync** - deleting a user deletes their env-vars row (delete listener in `events.py`)
  - log: 2026-07-03 implemented (v4.0.18)

## API

- `GET /api/users/{name}/env-vars` -> `{env_vars: [{name, value, description}], reserved_names: [...], reserved_prefixes: [...]}`
- `PUT /api/users/{name}/env-vars` body `{env_vars: [{name, value, description}]}` -> `{env_vars: [...]}` (the stored, cleaned set); `400 {code, message, rejected}` on a reserved/invalid/duplicate name or over-cap payload; `403` when not self and not admin

## Access control

- [x] **Self edits own** - a non-admin user may GET/PUT their own env vars
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Admin edits another user** - an admin may GET/PUT any user's env vars
  - log: 2026-07-03 implemented (v4.0.18); functional-covered
- [x] **Other forbidden** - a non-admin PUT/GET for another user returns 403
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Anonymous forbidden** - no authenticated user returns 403
  - log: 2026-07-03 implemented (v4.0.18)

## Blacklist / protection

- [x] **Dictionary** - protected names + prefixes load from `conf/protected_env_dictionary.yml` (baked to `/srv/jupyterhub/`), unioned with the globally-injected `c.DockerSpawner.environment` keys to build `RESERVED_ENV_VAR_NAMES`/`PREFIXES`
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Policy-owned names protected** - GPU (`NVIDIA_VISIBLE_DEVICES`, `CUDA_VISIBLE_DEVICES`, `ENABLE_GPU_SUPPORT`, `ENABLE_GPUSTAT`), docker (`DOCKER_HOST`), sudo (`JUPYTERLAB_SUDO_ENABLE`) are in the dictionary
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Image privilege levers protected** - docker-stacks root-time env vars (`GRANT_SUDO`, `NB_UID`, `NB_GID`, `NB_USER`, `NB_GROUP`, `NB_UMASK`, `CHOWN_HOME*`, `CHOWN_EXTRA*`) are reserved so a user cannot self-escalate past the sudo policy
  - log: 2026-07-03 added after adversarial review (v4.0.18)
- [x] **Prefixes protected** - `JUPYTERHUB_`, `JPY_`, `MEM_`, `CPU_` reject on save
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Reserved rejected on save** - a PUT containing a reserved name returns `400 code=reserved_env_var_names` with the offending names in `rejected`; nothing is persisted
  - log: 2026-07-03 implemented (v4.0.18); functional-covered
- [x] **Invalid name rejected** - a name not matching `[A-Za-z_][A-Za-z0-9_]*` returns `400 code=invalid_env_var_names`
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Duplicate rejected** - two entries with the same name return `400 code=duplicate_env_var_names`
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Same blacklist as policies** - the per-user validator and the group-policy validator both use `policy.base.is_reserved_env_var` against the same reserved sets
  - log: 2026-07-03 implemented (v4.0.18)

## Spawn injection

- [x] **Inject on spawn** - a user's saved env vars appear in the spawned container's environment (`Config.Env`)
  - log: 2026-07-03 implemented (v4.0.18); functional-covered
- [x] **Precedence** - user env is injected before `apply_policies`, so a group/GPU/sudo/docker policy env of the same name overrides it; the global base env is unaffected
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Reserved stripped defensively** - `get_injectable` filters reserved names again at spawn even if one was persisted before the reserved set changed
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Description not injected** - the description field is stored and shown but never passed as an env var
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Fail-open** - an env-store error at spawn logs a warning and continues (never blocks a spawn)
  - log: 2026-07-03 implemented (v4.0.18)

## Frontend

- [x] **Admin tab** - `UserConfig` shows an Environment tab (admin, and `/users/:name`)
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **User tab** - self-service `Profile` is tabbed (Profile + Environment) so a plain user edits their own
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Shared editor** - the group-policy env table is extracted to `EnvVarEditor` and reused by the profile tab (name/value/description + Add/remove)
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Live validation** - the editor flags a reserved/invalid/duplicate name (error status + tooltip) using the reserved lists from the GET; Save is blocked while any row is in error
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Combined save** - the profile Save persists name/email, env vars and (if set) password in one action
  - log: 2026-07-03 implemented (v4.0.18)

## Edge cases

- [x] **Edge: blank-name rows** - rows with an empty/whitespace name are dropped silently on save, never an error
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Edge: value coercion** - a null value stores as `""`; a non-string value stores as its string form
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Edge: corrupt blob** - a corrupt/non-list stored blob reads as an empty set (never raises, never breaks a spawn); a subsequent save overwrites it
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Edge: missing dictionary file** - the loader falls back to built-in defaults (warn) rather than an empty blacklist; a malformed dictionary file raises (fail loud)
  - log: 2026-07-03 implemented (v4.0.18)
- [x] **Edge: empty set** - GET for a user with no saved vars returns `env_vars: []`; a PUT of `[]` clears the set
  - log: 2026-07-03 implemented (v4.0.18)
