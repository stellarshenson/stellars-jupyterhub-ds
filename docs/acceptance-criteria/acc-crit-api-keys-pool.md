# Acceptance Criteria - API Keys Pool Group Config

## Overview

A new group configuration type that distributes a finite pool of API credentials to user containers so that no two running containers ever hold the same credential. It joins the existing group config family (env variables, GPU, Docker, compute, memory) and is resolved, applied, and logged through the same machinery in `duoptimum_hub_services`.

The pool is exclusive by design: each running container is assigned at most one credential per pool, the credential returns to the pool when the container stops, and the in-use set is rebuilt by inspecting the actual running containers rather than trusting lifecycle events alone.

## Definitions

- **Pool**: an ordered set of credentials defined on a single group config, with a fixed mode and fixed target environment variable names
- **Credential**: one pool entry, either a key-id/key-secret pair or a single API key, depending on pool mode
- **Slot**: a stable identifier for a credential within its pool, independent of list position, used to record and reconcile assignments
- **Assignment**: the binding of one slot to one running container for that container's lifetime
- **In-use set**: the set of slots currently held by running containers, derived by reconciliation
- **Mode**: `pair` (key-id + key-secret) or `single` (api key) - mutually exclusive per pool

## Configuration (admin)

- **AC-1** Given a group config editor, when an admin enables the API keys pool, then they select exactly one mode: `pair` or `single` (mutually exclusive)
- **AC-2** Given `pair` mode, when configuring target variables, then the admin specifies an environment variable name for the key id and an environment variable name for the key secret
- **AC-3** Given `single` mode, when configuring the target variable, then the admin specifies one environment variable name for the api key
- **AC-4** Given an enabled pool, when the admin adds credentials, then the list accepts an unlimited number of entries, each entry matching the pool mode (id+secret for `pair`, single value for `single`)
- **AC-5** Given a stored pool, when the admin reorders or edits the credential list, then each existing credential keeps its stable slot identity so in-flight assignments remain valid
- **AC-6** Given the group config persistence layer, when a pool is saved, then credential secrets are stored in the same protected store as other group config (`groups_config.sqlite`). The groups page and its API are admin-only and return credentials in full (the admin manages them, so they are shown unmasked in the editor); obfuscation applies only to the logs (AC-26/AC-28)

## Validation

- **AC-7** Given an enabled pool, when no mode is selected or both target-variable sets are empty, then validation fails with a clear message and the config is not saved
- **AC-8** Given `pair` mode, when either the key-id variable name or the key-secret variable name is missing, then validation fails
- **AC-9** Given `single` mode, when the api-key variable name is missing, then validation fails
- **AC-10** Given any target variable name, when it collides with a reserved name or reserved prefix (the same `reserved_env_var_names` / `reserved_env_var_prefixes` used elsewhere), then validation fails
- **AC-11** Given `pair` mode, when an entry is missing either the id or the secret, then validation fails (no half-credentials in the pool)

## Assignment at spawn

- **AC-12** Given a user in a group with an enabled pool, when their container spawns, then the pool assigns one free slot to that container and injects the credential into the configured environment variables (`pair` -> two variables; `single` -> one variable)
- **AC-13** Given an assignment, when the credential is injected, then no other running container in the same pool holds the same slot (exclusivity invariant)
- **AC-14** Given the assignment, when it is made, then it is recorded durably on the container itself in a stable, version-independent form (so it survives a hub restart and can be reconciled), in addition to any hub-side bookkeeping
- **AC-15** Given a user already holding a slot from a still-running container, when a duplicate spawn or reconciliation occurs, then the existing assignment is reused rather than allocating a second slot

## Release at stop

- **AC-16** Given a running container with an assignment, when the container stops cleanly, then its slot returns to the pool and becomes available for the next spawn
- **AC-17** Given a returned slot, when it re-enters the pool, then a subsequent spawn may receive it; assignments are per container lifetime and not sticky to a user across stop/start

## Resilience and reconciliation

The pool must never rely on stop events alone. Containers can be stopped while the hub is down (missed event), or were started by a previous or different hub version. The authoritative in-use set is therefore always derived from the running containers.

- **AC-18** Given the hub starts, when the startup reconciliation runs, then it enumerates running user containers, reads each container's recorded assignment, and rebuilds the in-use set from that observation - not from stale hub state
- **AC-19** Given a slot recorded as in-use but with no corresponding running container, when reconciliation runs, then that slot is returned to the pool
- **AC-20** Given a periodic reconciliation pass, when it runs at a fixed interval, then it re-derives the in-use set from running containers and converges the pool to match reality (self-healing against missed events)
- **AC-21** Given a container started by an older hub version with no recognizable assignment marker, when reconciliation runs, then it is treated as holding no pool slot - the pool does not crash, double-free, or guess; its already-injected environment is left untouched
- **AC-22** Given the assignment marker scheme, when the hub version changes, then the scheme is stable and backward-compatible so future reconciliation keeps working across upgrades

## Exhaustion

- **AC-23** Given a pool with all slots assigned, when another group member's container spawns, then the configured environment variables are still set but empty, and the container starts normally
- **AC-24** Given pool exhaustion at spawn, when the empty assignment is made, then a warning is logged stating the pool is exhausted, naming the pool and the user
- **AC-25** Given an exhausted pool, when a slot is later released and reconciliation runs, then it becomes available for the next spawn (no permanent starvation)

## Logging

- **AC-26** Given a credential assignment, when it succeeds, then an event is logged to the JupyterHub log naming the user and pool, showing only the last 4 characters of the id and/or secret and/or api key - never the full value
- **AC-27** Given pool exhaustion, when a container is assigned empty variables, then a warning-level event is logged
- **AC-28** Given any logging path, when an assignment or exhaustion is recorded, then full credential values never appear in logs or in container labels (log lines carry last-4 only; labels carry slot identity, not the secret). Full values are exposed only through the admin-only groups API/editor (AC-6)

## Multiple groups

- **AC-29** Given a user in several groups each defining a pool, when their container spawns, then each pool independently assigns one slot and injects its own configured variables
- **AC-30** Given two groups that set the same environment variable name (whether via a pool target variable or a plain group env var), when both would inject, then the group higher in the ordered group list wins and the shadowed value is not applied - this is the purpose of ordering groups by importance
- **AC-31** Given the resolved precedence in AC-30, when a higher-priority group's value shadows a lower one, then the shadowing is observable in the logs so an admin can see which group supplied the effective value

## Out of scope

- Credential rotation, expiry, or revocation against the upstream provider - the pool distributes static credentials supplied by the admin
- Validating that a credential is live or accepted by its target service
- Per-credential usage metering or quota beyond the one-container-one-slot exclusivity invariant
