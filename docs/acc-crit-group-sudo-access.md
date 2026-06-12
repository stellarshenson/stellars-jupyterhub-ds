# Acceptance Criteria - Group Sudo Access Control

A foldable "Sudo Access" group config section that explicitly sets whether members get sudo in their lab. When the section is on, the group configures sudo (enable or disable); `pre_spawn_hook` injects `JUPYTERLAB_SUDO_ENABLE=0|1` into the spawned container, which the image consumes. Resolution is section-gated and priority-wins: among the groups that configure it, the highest-priority group's value applies; if no group configures it, the platform default `JUPYTERHUB_LAB_SUDO_ENABLE_DEFAULT` applies. Hub-side only - the hub injects the env var; enforcing sudo from it is the image's job.

## Platform default

- [x] **Default env** - `JUPYTERHUB_LAB_SUDO_ENABLE_DEFAULT` (compose, `0`/`1`, default `1`) sets the value used when no group configures sudo
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Settings page** - listed in `settings_dictionary.yml` so it appears on the admin Settings page
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Compose default** - `JUPYTERHUB_LAB_SUDO_ENABLE_DEFAULT=1` present in `compose.yml` jupyterhub service environment
  - log: 2026-06-12 implemented (v3.11.5)

## Group config (admin)

- [x] **Section** - foldable "Sudo Access" section in the group modal with a section-active switch `config-sudo-active` (default off), following the `*_active` section pattern
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Value control** - when the section is on, a toggle `config-sudo-enable` chooses enable (1) or disable (0) for members
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Persistence** - `default_config()` carries `sudo_active: False` and `sudo_enable: True`; data persists when the section is folded off and restores when re-enabled (same as other `*_active` sections)
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **No inference** - brand-new feature; legacy rows default to `sudo_active: False` (not configured -> platform default applies), no `infer_active_flags` entry
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **API accept** - `GroupsConfigHandler.put` accepts boolean body keys `sudo_active` and `sudo_enable`
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Badge** - groups table shows `Sudo on` or `Sudo off` when `sudo_active` is set (reflecting the configured value); no badge when the section is off
  - log: 2026-06-12 implemented (v3.11.5)

## Resolution

- [x] **Section-gated** - a group with `sudo_active` false does NOT configure sudo (its `sudo_enable` is ignored); only sections explicitly on are considered
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Priority-wins** - among groups with `sudo_active` on, the highest-priority group's `sudo_enable` wins (groups resolved in descending priority order; first configuring group decides) - not OR, not biggest-wins
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Resolved value** - resolver returns `sudo_enable` as `True`/`False` when configured by some group, or `None` when no group configures it
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Default fallback** - the spawn-time value is the resolved `sudo_enable` when not `None`, else `JUPYTERHUB_LAB_SUDO_ENABLE_DEFAULT` (resolver stays pure; the hook applies the default)
  - log: 2026-06-12 implemented (v3.11.5)

## Spawn injection

- [x] **Always set** - `pre_spawn_hook` always sets `spawner.environment['JUPYTERLAB_SUDO_ENABLE']` to `'1'` or `'0'` (never left unset) so the container gets an explicit value every spawn
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Disable wins when configured** - a higher-priority group setting `sudo_enable=false` yields `JUPYTERLAB_SUDO_ENABLE=0` even if a lower-priority group enables it and even if the platform default is `1`
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Log line** - the existing pre_spawn resolution log line includes the resolved sudo value (configured vs default) for audit
  - log: 2026-06-12 implemented (v3.11.5)

## Edge cases

- [x] **Edge: user in no groups** - no group configures sudo -> platform default applies
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: all configuring groups agree** - any number of groups with the same value resolves to that value
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: configuring groups disagree** - highest-priority configuring group wins regardless of the others
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: section on, value unset in stored row** - defaults to `sudo_enable: True` from `default_config()`
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: higher-priority group section OFF, lower-priority ON** - the lower-priority group (the only one configuring) decides
  - log: 2026-06-12 implemented (v3.11.5)
- [x] **Edge: membership change** - takes effect on the member's next server start (consistent with other group settings)
  - log: 2026-06-12 implemented (v3.11.5)

## Tests

- [x] **Resolver tests** - `TestSudoAccess`: no groups -> None; single configuring group -> its value; section-off group -> None; two configuring groups -> higher priority wins; higher-priority-off + lower-priority-on -> lower-priority value
  - log: 2026-06-12 implemented (v3.11.5)

## Documentation

- [x] **README** - Groups section documents the Sudo Access switch, the value toggle, the priority-wins/default-fallback rule, and the master default env var
  - log: 2026-06-12 implemented (v3.11.5)

## Out of scope

- Enforcing sudo inside the container from the env var - the image owns that; the hub only injects `JUPYTERLAB_SUDO_ENABLE`
- Per-user (non-group) sudo overrides
- Runtime sudo change without a server restart

## API

- `PUT /hub/api/admin/groups/{group}/config` body gains optional booleans `sudo_active`, `sudo_enable`
- Env into container: `JUPYTERLAB_SUDO_ENABLE` (`0`/`1`)
- Platform env: `JUPYTERHUB_LAB_SUDO_ENABLE_DEFAULT` (`0`/`1`, default `1`)
