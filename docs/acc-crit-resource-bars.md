# Acceptance Criteria - resource bars (limits + tooltips)

The CPU/Memory/GPU progress bars on the Server status card, the Servers table, and the Home "Total resources" widget. Each bar must read 0-100% against the right reference (a quota-limited user's bar measures against THEIR ceiling, not the host) and every bar must carry a hover tooltip with the precise breakdown. Backend `docker_utils.get_container_stats`; frontend `liveSource` (`getServerHero`/`getServers`/`getTotalResources`) + `components/meters.tsx` (`ResourceBars`).

## CPU bar reference

- [x] **Quota detected two ways** - `get_container_stats` reads BOTH `HostConfig.NanoCpus` (DockerSpawner `cpu_limit`) and `HostConfig.CpuQuota`/`CpuPeriod` (the cpu-quota-* cgroup groups); either yields `cpu_cores` + `cpu_cores_limited=True`
  - log: 2026-06-17 FIXED - was NanoCpus-only, so a quota-group user (konrad: CpuQuota=3200000 -> 32 cores) reported `cpu_cores=64` host, `limited=False`
- [x] **CpuPeriod default** - a quota set without an explicit period uses the kernel cfs default 100000 (so 3200000/100000 = 32)
  - log: 2026-06-17 implemented (`cpu_period = hostcfg.get('CpuPeriod') or 100000`)
- [x] **No limit -> host cores** - absent any limit, `cpu_cores` = `online_cpus`, `cpu_cores_limited=False`
  - log: 2026-06-17 retained
- [x] **Bar is usage/assignment** - the CPU bar value = `cpu_percent / cpu_cores` clamped 0-100 (`cpuBarPct`), parallel to the memory bar's usage/limit; docker's `cpu_percent` is cores-used x 100, so a multi-core container previously overflowed past 100%
  - log: 2026-06-17 implemented (`liveSource.cpuBarPct`, applied in getServers + getServerHero)
- [x] **CPU tooltip names the ceiling** - `cpuTip` = "N cores assigned" (limited) or "N cores host (no limit)"
  - log: 2026-06-17 present; now reads "32 cores assigned" for konrad

## Memory bar reference

- [x] **Bar is usage/limit** - `memory_percent` = usage / container memory limit; a 256 GiB-limited user reads against 256 GiB, not host RAM
  - log: 2026-06-17 verified live (konrad memory_total_mb=262144 reflected) - was already correct
- [x] **memory_limited flag** - the service exposes whether the bar's denominator is an explicit per-user limit or the host fallback, parallel to `cpu_cores_limited`; from `HostConfig.Memory > 0`
  - log: 2026-06-17 added so the tooltip can name "assigned" vs "host (no limit)" - previously the hero tooltip said "of host RAM" unconditionally (the reported bug)
- [x] **Memory tooltip names the ceiling honestly** - "N GB used of M GB assigned" when `memory_limited`, else "of M GB host (no limit)"; Servers also annotates "(over warning threshold)" on a `memory_max_usage_mb` breach
  - log: 2026-06-17 FIXED - hero was "X GB of host RAM" regardless; both paths now flag-driven (`getServers`, `getServerHero`)

## Granular assigned-resource service design

- [x] **Pure, tested helpers** - `derive_cpu_assignment(hostcfg, online_cpus)` and `derive_memory_assignment(hostcfg, stats_limit_bytes)` in `docker_utils` are pure functions, unit-tested independently of Docker (8 cases), so the assignment logic is granular and verifiable, not inlined in the socket call
  - log: 2026-06-17 operator "make sure the service that calculates it is properly designed and granular" - extracted both; `tests/test_docker_resource_assignment.py`, 600 backend pass
- [x] **Edge: nano-cpus wins over quota; zero mem limit = unlimited** - explicit `NanoCpus` takes precedence over a cfs quota; `HostConfig.Memory == 0` reads as host fallback, not a 0-byte ceiling
  - log: 2026-06-17 covered by `test_cpu_nano_cpus_wins_over_quota`, `test_memory_zero_limit_is_unlimited`
- [x] **Exposed on /activity** - per-user `memory_limited` added (default `False`, set from the stats passthrough in `handlers/activity.py`)
  - log: 2026-06-17

## Colour ramp (mem + cpu, both Total and the widget)

- [x] **Calm to 50%** - the CPU/memory fill keeps the default accent up to and including 50% (`meters.barColor` returns undefined)
  - log: 2026-06-17 operator "only past 50% mark start slowly changing colours"
- [x] **Gradual ramp past 50%** - 50-75% blends accent -> warning, 75-100% blends warning -> danger via `color-mix` (smooth, design-token based, no hardcoded RGB)
  - log: 2026-06-17 `meters.barColor`
- [x] **Smooth recolour** - the fill transitions width + background ~0.4s so a value change eases rather than jumps
  - log: 2026-06-17 inline transition on the bar fill
- [x] **CPU/memory only** - the ramp rides the standard fill bar; GPU rows (striped meter / inventory chips) and the activity meter keep their own colours
  - log: 2026-06-17 applied only on the `<i style=width>` branch in `ResourceBars`
- [x] **Both surfaces** - one helper in `meters.tsx`, used by the server widget and Total resources alike
  - log: 2026-06-17

## Tooltips on every bar

- [x] **Bar + value carry the tip** - `ResourceBars` puts `title={r.tip}` on BOTH the `.oh-res-bar` span and the value readout, so hovering the bar itself (not only the %) shows the breakdown
  - log: 2026-06-17 verified (meters.tsx)
- [x] **Total resources tips populated** - the Home "Total resources" rows pass `tip` for CPU (`cpuTip`) and Memory (`memTip`); previously they passed none so the bars had no tooltip
  - log: 2026-06-17 FIXED - added `cpuTip` to `getTotalResources`, passed `total.cpuTip`/`total.memTip` in Home.tsx
- [x] **Total CPU is host-relative** - the aggregate CPU bar = total cores-used / host cores (largest assigned-core count among active servers), not a clamped sum that always pegged ~100%
  - log: 2026-06-17 implemented; tip reads "~N of H cores in use across M servers"
- [x] **GPU tooltips native** - per-GPU bars/chips carry the standard browser `title` (name/UUID/memory/util/temp/power), not a bespoke antd popup
  - log: 2026-06-17 verified (gpuTip returns a \n-joined string)
- [x] **Multiline tooltips** - the Servers memory/volume/system tooltips are `\n`-joined (one fact per line) like the GPU tooltip, not a single long " / "-joined string; the desktop table's native `title` breaks on `\n` and the mobile drawer's inline `detail` uses `white-space: pre-line`
  - log: 2026-06-17 operator (repeat) "tooltips weirdly long, must be multiline broken nicely" - memTip/volTip/sysTip switched to `[...].filter(Boolean).join('\n')`; Metric detail div got `pre-line`

## Edge cases

- [x] **Edge: just-started container** - empty `precpu_stats` -> get_container_stats try/except returns None -> bars show "-" rather than 500
  - log: 2026-06-17 verified (whole body guarded)
- [x] **Edge: no active servers (totals)** - `getTotalResources` returns cpu/mem 0 with the real GPU inventory still surfaced
  - log: 2026-06-17 verified
- [ ] **Runtime: konrad CPU bar reads against 32 cores** - on the live hub the CPU bar + tooltip reflect his 32-core quota, not 64 host
  - log: 2026-06-17 backend confirmed live (`cpu_cores=32` after fix pending rebuild); on-screen confirm pends operator rebuild
- [x] **Edge: GPU absent** - `gpuSupported()` false (live `window.jhdata.gpu_enabled` false) -> GPU rows hidden entirely, not a "-" row
  - log: 2026-06-17 default tightened to false in live mode (was `?? true`)
