# Acceptance Criteria - Unified Group Policy Model

One policy-type registry is the single source for every group permission (default, set-rule, validate, cross-group resolve), and at spawn a user's groups collapse into one effective policy object the hook reads. The legacy resolver and per-field validator are deleted, gated on a frozen golden snapshot proving the new engine reproduces them (v3.11.6 -> 3.12.0).

## Registry + engine

- [x] **Single source** - `POLICY_TYPES` is the only place each type's default, coerce, validate, and resolve live
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **default_config from registry** - `default_config()` is assembled from each type's `default`, no hand-listed field bag
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **resolve_policies drop-in** - same signature and output key set as the deleted `resolve_group_config`; the three hook call sites switch with no behaviour change
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Registry-driven save** - `GroupsConfigHandler.put` coercion and validation loop over `POLICY_TYPES`; no per-field if-chain remains
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **ctx carries non-config inputs** - `gpu_available`, reserved env names/prefixes flow via a context object, not globals
  - log: 2026-06-13 criterion added; done (v3.12.0)

## Per-type set-rule + resolve-rule

- [x] **env_vars** - reserved names stripped to `skipped_env_vars`; priority-first-wins on name; inactive section contributes nothing
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **gpu** - OR-grant; all-GPUs wins else device-id union; hardware-gated; grant with neither all nor ids falls back to all
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **docker** - OR-grant access/limited/privileged; max quota across granting groups; raw supersedes limited (clears limited + its flags)
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **mem** - biggest-enabled-GB wins; swap policy follows the winning cap; disabled group does not un-cap
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **cpu** - biggest-enabled-cores wins; disabled group does not un-cap
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **sudo** - section-gated priority-wins; `None` when unconfigured (hook applies platform default)
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **downloads** - section-gated priority-wins; `None` when unconfigured (hook applies platform default)
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **api_keys** - priority-ordered pool list; reserved target names rejected at save
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **volume_mounts** - union keyed by mountpoint; priority-wins on conflict; protected-mountpoint blacklist re-checked at resolve
  - log: 2026-06-13 criterion added; done (v3.12.0)

## Drivers (lifecycle controllers)

- [x] **Controllers own lifecycle** - api-keys (`PoolManager`) and docker-limited (proxy `register_user`) controllers own slot handout/rotation/masking and quota/ownership; wired in `hooks.py`/`config`, behaviour unchanged
  - log: 2026-06-13 criterion added; done (v3.12.0)
  - log: 2026-06-13 GC: registry `DriverRef` indirection removed as unconsumed (user "trim to what's used"); controllers stay wired directly, registry is data-only
- [x] **api_keys restart persistence** - in-use set is label-derived; a lab surviving a hub restart keeps its slot; the startup reconcile rebuilds in-use before any new spawn assigns
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **api_keys label at create** - the slot label is stamped on the container via `extra_create_kwargs` at create (the one gap that would reintroduce collisions)
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: collision after restart** - two labs running, hub restarts, a third spawn must not re-hand-out either surviving slot
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: exhausted pool** - more containers than credentials sets the target vars empty and logs a warning, never reuses a live slot
  - log: 2026-06-13 criterion added; done (v3.12.0)

## Migration + no-regression

- [x] **Golden frozen** - `tests/golden/policy_resolution.json` captures the old resolver outputs across the scenario matrix
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Golden green** - new engine output deep-equals the frozen golden for every scenario
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Old path deleted** - `resolve_group_config` and per-field `GroupConfigValidator` methods removed; no shim, no fallback; importers updated
  - log: 2026-06-13 criterion added; done (v3.12.0)

## Bundle round-trip (import/export foundation)

- [x] **Bundle shape** - a group serializes to `{group_name, description, priority, policies}`
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Round-trip** - export then import a bundle through the registry coerce path deep-equals the source config
  - log: 2026-06-13 criterion added; done (v3.12.0)

## UI

- [x] **Name opens config** - clicking the group name opens its configuration modal (edit icon dropped)
  - log: 2026-06-13 implemented (group name is a clickable config link, cog button removed)
- [x] **Hover tooltip** - hovering the group name lists the group's active policies, rendered from the server-provided `policy_summary` detail lines (no policy-display logic in the browser)
  - log: 2026-06-13 criterion added; done (v3.12.0)
  - log: 2026-06-13 GC removed the unconsumed `ui.summarize`; then redesigned per operator - `summarize` restored as a consumed display facet on each `PolicyType`, served by `GroupsDataHandler` as `policy_summary`, client renders verbatim
- [x] **Single-source badges + tooltip** - each `PolicyType.summarize(config)` returns `{badge, detail}`; `summarize_config` feeds `GroupsDataHandler.policy_summary`; the group table badges and tooltip both render it, so neither drifts from the registry
  - log: 2026-06-13 criterion added; done (v3.12.0)

## Edge cases

- [x] **Edge: zero matched groups** - resolve returns all defaults / `None` for section-gated types
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: section off with stale data** - an inactive section contributes nothing while its stored data persists
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: legacy row missing active flags** - `infer_active_flags` still applies; legacy groups keep working
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: conflicting priorities** - higher-priority group wins for priority-type keys; ties keep the higher-priority (earlier) group
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Edge: reserved env-var name** - rejected at save with the stable `reserved_env_var_names` JSON error
  - log: 2026-06-13 criterion added; done (v3.12.0)

## Gate

- [x] **Tests green** - `uv run pytest` passes including golden, per-type, driver, restart, round-trip
  - log: 2026-06-13 criterion added; done (v3.12.0)
- [x] **Version bumped** - root `pyproject.toml` 3.11.6 -> 3.12.0
  - log: 2026-06-13 criterion added; done (v3.12.0)

## API

Admin-only group config endpoints; the PUT body is coerced and validated through the registry.

- `GET /api/admin/groups` -> `{groups: [{name, description, priority, member_count, members, config, policy_summary}], shared_volume}`, priority-descending; `policy_summary` = `[{key, badge, detail}]` per active policy (registry-sourced display facet)
- `GET /api/admin/groups/{name}/config` -> `{group_name, description, priority, config}`
- `PUT /api/admin/groups/{name}/config` body = partial policy dict (any registry keys) -> saved `{group_name, description, priority, config}`
  - 403 non-admin
  - 400 `{error: 'reserved_env_var_names', message, rejected: [...]}` - env_vars or api-keys target name reserved (structured)
  - 400 `{error: '<code>', message}` coherence failure, first wins: `invalid_gpu_selection`, `invalid_docker_selection`, `invalid_cpu_limit`, `invalid_mem_limit`, `invalid_api_keys_pool`, `invalid_volume_mounts`
  - 400 bare message - malformed shape (`env_vars`/`gpu_device_ids`/`volume_mounts` not a list, `api_keys_pool` not an object)
- Bundle (import/export foundation) = `{group_name, description, priority, policies}` where `policies` is the config dict; import re-coerces each slice through the registry
