# Acceptance Criteria - Host Status Provider

The home-screen host-status view is decoupled behind a `HostStatusProvider` associated with the spawner. The provider probes its environment for a fixed minimal set - CPU, memory, GPU - each optional and individually status-tagged; the portal renders whatever is present, including nothing. Design: [design-host-status-provider.md](../design-host-status-provider.md).

## Contract

- [x] **ABC** - `HostStatusProvider` defines `capabilities()` and `get_status()`; lives in a dedicated `host_status` module, not in a handler
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 implemented (`host_status.py`); unit `test_host_status_provider.py`
- [x] **Capabilities** - `capabilities()` returns any subset of `{CPU, MEM, GPU}`; an empty set is valid
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 verified (`test_capabilities_cpu_mem_only_when_gpu_off`, `_includes_gpu_when_enabled`)
- [x] **Status shape** - `get_status()` returns the fixed schema, each top key (`cpu`/`mem`/`gpu`) optional; a key present in the result is also present in `capabilities()`
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 verified (`test_status_keys_are_subset_of_capabilities`)
- [x] **Per-dimension status** - each present dimension carries `ok | degraded | unavailable`; dimensions degrade independently
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 verified (`test_cpu_mem_unaffected_by_gpu_state`, gpu ok/degraded/unavailable tests)
- [x] **Serializable** - the status object is JSON-serializable for the activity response; no provider object leaks to the wire
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 verified (`test_serializable`); handler emits flat fields + `host_capabilities` list, not the provider object

## Spawner association

- [x] **Declared on spawner** - the spawner subclass declares `host_status_provider_class`; the hub reads `c.JupyterHub.spawner_class` and instantiates the provider once at boot
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 implemented (`spawner.py`, `resolve_host_status_provider`); `test_declares_host_status_provider`, `test_resolve_*`
- [x] **Rename** - `TimingDockerSpawner` renamed `DuoptimumDockerSpawner`, timing instrumentation kept; `spawner_class`, package exports and config reference all updated
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done (`timing_spawner.py` -> `spawner.py`; config `spawner_class`; `__init__` exports); live boot log `Using Spawner: ...DuoptimumDockerSpawner`
- [x] **Resolved into context** - the provider instance is stored in `stellars_config`, reachable by the activity handler
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done (`stellars_config['host_status_provider']`); functional `test_activity_reports_host_capabilities`
- [x] **Configured once** - the provider is handed the resolved gpuinfo URL context at construction, not a hardcoded host
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done (constructed with `{gpu_enabled, gpu_list}` boot context; GPU sampling stays via `gpu_cache`, runtime-resolved URL)

## Reference provider (Docker)

- [x] **Logic moved** - `_host_cpu_count`, `_host_total_memory_mb`, the host-aggregate stats merge and the GPU merge move out of `handlers/activity.py` into `DockerHostStatusProvider`, behaviour unchanged
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done; architect adversarial sweep confirmed single-source (no second copy), flat fields byte-identical
- [x] **CPU** - host cores from `/proc/cpuinfo`; used% stays a frontend aggregate over the per-user rows
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done; `test_host_cpu.py` (moved import), `test_status_cpu_mem_ok_with_real_values`
- [x] **MEM** - host total from `/proc/meminfo`; used% stays a frontend aggregate
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done; `test_host_memory.py` (moved import)
- [x] **GPU** - inventory from `gpu_list` (boot), live sample from `gpu_cache`, `connected` from `gpu_sidecar_connected()`
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done; `test_gpu_ok_when_connected_with_sample`; live boot shows 3 GPUs detected
- [x] **GPU capability gated** - GPU absent from `capabilities()` when GPU mode is off at boot (not merely reported unavailable)
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done; gated on `gpu_enabled` (`resolve_gpu_mode` guarantees `gpu_enabled` iff `gpu_list` non-empty); functional `test_activity_reports_host_capabilities` asserts gpu cap == platform GPU flag
- [x] **Handler delegates** - `activity.py` calls `provider.get_status()` for the host aggregate and keeps per-user server rows as-is
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done; functional `test_activity_reports_host_capabilities`; per-user rows untouched

## Frontend

- [x] **Snapshot presence** - `ResourceSnapshot` carries per-dimension capability flags alongside the existing values
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done (`types.ts` `caps: {cpu,mem,gpu}`); tsc clean
- [x] **Adapter mapping** - `getTotalResources` maps `host_capabilities` into `caps`; absent (old backend / error) defaults each shown
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done (`liveSource.ts`; empty array -> all false, undefined -> all true)
- [x] **Presence-gated render** - the Host Status panel renders CPU, memory and GPU rows independently, each only when present
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 verified functional `test_panel_renders_only_capable_rows` (cpu-only -> CPU shown, Memory/GPU dropped)
- [x] **Unchanged when full** - all three dimensions present and ok -> the live admin view is identical to before
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 verified; `test_host_status` + `test_resource_bars` pass unchanged against the rebuilt image
- [x] **Degraded state** - a present-but-degraded dimension shows its error state, not a blank or a zero
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 preserved via existing flags (cpuError/memError from null totals, gpuDisconnected from `gpu_connected`); `test_host_status_bars_have_tooltips` passes

## Edge cases

- [x] **Edge: no provider** - spawner declares no `host_status_provider_class` -> resolver returns None -> empty aggregate -> no panel, no crash
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 verified `test_resolve_none_when_spawner_declares_no_provider`; handler guards `provider.get_status() if provider else {}`
- [x] **Edge: empty capabilities** - provider exposes nothing -> panel hidden entirely, no empty shell
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 verified functional `test_panel_hidden_when_no_capabilities`
- [x] **Edge: GPU-only-absent** - a Docker host with GPU off exposes only CPU/MEM -> no GPU row (covered by the disabled-GPU path)
  - log: 2026-06-22 criterion added (was "GPU-only")
  - log: 2026-06-23 reframed to the reachable Docker case; verified `test_gpu_hidden_when_disabled` + `test_capabilities_cpu_mem_only_when_gpu_off`
- [x] **Edge: proc unreadable** - `/proc` read fails -> cpu/mem `unavailable`, GPU unaffected
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 verified `test_status_cpu_mem_unavailable_on_proc_failure`
- [x] **Edge: sidecar down** - gpuinfo unreachable but GPU is a capability -> gpu `degraded` / `connected=false`, cpu/mem unaffected
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 verified `test_gpu_degraded_when_inventory_but_sidecar_down`, `test_cpu_mem_unaffected_by_gpu_state`

## Verification

- [x] **Unit - provider** - tests for `DockerHostStatusProvider`: capabilities set, full status shape, each-dimension-degraded, GPU-gated-off
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done `test_host_status_provider.py` (12 tests); full unit suite 989 passed
- [x] **Unit - null provider** - a no-capability provider yields an empty status; handler emits no host aggregate
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done `test_resolve_none_when_spawner_declares_no_provider` + handler guard
- [x] **Frontend test** - panel renders a subset and hides on empty
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 done functional `test_panel_renders_only_capable_rows`, `test_panel_hidden_when_no_capabilities`
- [x] **Adversarial review** - architect (seam, separation of concerns, no spawner/provider name drift) + bug-hunt clean on a confirming round
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 architect Mode-2 CLEAN; Mode-1 SHIP after triage (the GPU-gate divergence proven unreachable via `resolve_gpu_mode`); confirm round SHIP; one fix applied (Home loading-state card) + doc drift corrected
- [x] **Live unchanged** - rebuild + redeploy; the admin Home host-status panel is unchanged on the current Docker+GPU host; `/hub/health` 200; functional regime green
  - log: 2026-06-22 criterion added
  - log: 2026-06-23 `make rebuild` (image 660419f4a7e7) + redeploy; hub Healthy, spawner `DuoptimumDockerSpawner`, `/hub/health` 200, konrad lab survived; signup regime 88 passed / 0 failed, 137 acc-crit met / 0 unmet

## Scope boundaries

- [x] **Out: other providers** - HPC / Kubernetes / remote providers are future packages against this contract, not built here
  - log: 2026-06-22 noted
  - log: 2026-06-23 held; only `DockerHostStatusProvider` shipped
- [x] **Out: per-server view** - only the admin Home aggregate panel is fed; contract shaped to allow a per-server surface later
  - log: 2026-06-22 noted
  - log: 2026-06-23 held; per-user server rows stay in the activity handler, untouched
- [x] **Out: GPU plumbing** - de-NVIDIA-ifying the device-request path (`'Driver':'nvidia'`, `NVIDIA_*` env, `runtime='nvidia'`) is a separate follow-up
  - log: 2026-06-22 noted
  - log: 2026-06-23 held; GPU policy/sidecar runtime untouched
