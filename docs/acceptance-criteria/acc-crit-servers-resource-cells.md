# Acceptance Criteria - Servers resource cells

The Servers table enriches every resource cell with a full breakdown and its quota so an admin reads usage-vs-limit at a glance. Data comes from the `/api/activity` payload (per-user `memory_mb`/`memory_total_mb`, `volume_breakdown`, `container_size_rw_mb`/`container_size_rootfs_mb`, `last_activity`) plus the aggregate quotas (`memory_max_usage_mb`, `volume_max_total_size_mb`, `container_max_extra_space_mb`). Absent values render as the muted dash, never a fabricated zero.

- [x] **Mem column label** - the Memory column header reads "Mem"
  - log: 2026-06-17 implemented (Servers.tsx column title)
- [x] **Mem tooltip breakdown** - tooltip shows used vs configured per-user limit vs total host RAM (e.g. "19.2 GB used / 32 GB limit / 64 GB host")
  - log: 2026-06-17 implemented in liveSource.getServers memTip (code+typecheck verified; runtime render pending deploy)
- [x] **Mem over-quota** - cell flags (warn colour) when used exceeds the configured per-user limit; tooltip states it is over
  - log: 2026-06-17 implemented (memOver + " (over limit)" clause)
- [ ] **CPU assigned cores** - CPU cell/tooltip also shows how many cores are assigned to the user (per-user limit), not only % of host
  - log: 2026-06-17 NOT done - assigned cores not in current activity payload, must be exposed backend-side first (task #179)
- [x] **Volumes tooltip breakdown** - tooltip lists per-volume sizes (home / workspace / cache) and the total; shows the quota when the total is exceeded
  - log: 2026-06-17 implemented in liveSource.getServers volTip from volume_breakdown (code+typecheck; runtime pending deploy)
- [x] **Volumes over-quota** - cell flags (warn colour) when total exceeds the volume quota; tooltip states the quota
  - log: 2026-06-17 implemented (volumesOver + "quota exceeded" clause)
- [x] **System size breakdown** - tooltip shows base image size, writable layer size, and the quota (e.g. "base 3.1 GB + writable 1.4 GB / 10 GB quota")
  - log: 2026-06-17 implemented (base = rootfs - rw) in sysTip (code+typecheck; runtime pending deploy)
- [x] **System over-quota** - cell flags (warn colour) when writable layer exceeds the extra-space quota; tooltip states the quota
  - log: 2026-06-17 implemented (systemOver + " (over)" clause)
- [x] **Last activity column** - a "Last activity" column sits immediately after Status, showing time-ago of the last activity, shortened per design language ("2m", "3h", "2d")
  - log: 2026-06-17 implemented (Servers.tsx column + lastActivityISO + timeAgoShort; mock populated)
- [x] **GPU column gating** - the GPU column is shown only when the platform has GPU (window.jhdata.gpu_enabled), hidden entirely otherwise
  - log: 2026-06-17 implemented under task #173 (gpuSupported() spread; runtime pending deploy)
- [x] **Edge: server stopped** - resource cells (cpu/mem/system/last-activity) read the muted dash when the server is not running; volumes still show last-known size
  - log: 2026-06-17 verified by code: cpu/mem/system gated on running/non-null -> dash; volumesGB from last-known; lastActivityISO null when not running -> dash
- [x] **Edge: data not yet sampled** - before the first stats/volume sample lands, cells show the muted dash (or last-known for volumes), never a 0
  - log: 2026-06-17 verified by code: null-guards render muted dash; volumes seed from persisted last-known
- [x] **Edge: no quota configured** - when a quota env is 0/unset, the cell never flags over-quota and the tooltip omits the quota clause
  - log: 2026-06-17 verified by code: every over/quota clause guarded on max > 0
- [x] **Edge: no last activity** - users with no recorded activity show the muted dash in the Last activity column
  - log: 2026-06-17 verified by code: timeAgoShort on null/undefined -> muted dash render

## Data sources (existing /api/activity per-user fields)

- `memory_mb`, `memory_percent`, `memory_total_mb` - mem used / % host / host total
- `volume_size_mb`, `volume_breakdown` (suffix -> MB) - volumes total + per-mount
- `container_size_rw_mb`, `container_size_rootfs_mb` - writable layer + full rootfs (base = rootfs - rw)
- `last_activity` (ISO) - last activity timestamp
- aggregate quotas: `memory_max_usage_mb`, `volume_max_total_size_mb`, `container_max_extra_space_mb`
- MISSING: per-user assigned CPU cores (needs to be added to the payload for the CPU-cores criterion)
