# Acceptance Criteria - Servers host-relative resources

On the Servers widget (Home) and the Servers page table the per-server CPU/MEM cell is a numeric COUNTER (no progress bar): CPU shows the server's % of the HOST and MEM shows the absolute GB used, so the CPU counters across active servers sum to ~100% of host and the MEM counters sum to the host total. The counter's COLOUR encodes the server's usage as a % of its own ASSIGNED quota. The Server Status hero widget is unchanged and remains the only surface showing % of assigned (with its bars). Tooltips reveal the full breakdown so nothing is lost by the host-relative view.

## Supersedes

- replaces, for the Servers widget + Servers page only, the per-server "bar = usage/assignment" rule in [[acc-crit-resource-bars]] (CPU "Bar is usage/assignment", Memory "Bar is usage/limit") - the Servers list cells are counters, not bars; that usage/assignment BAR is retained for the Server Status hero
- replaces the Servers-page cell display + tooltip rules in [[acc-crit-servers-resource-cells]] (Mem tooltip breakdown, Mem over-quota, CPU assigned cores) with the host-relative counter + quota-colour + full-breakdown-tooltip rules below

## CPU counter - % of host

- [ ] **CPU counter = % of host** - the per-server CPU cell shows a numeric counter `cpu_percent / host_cpu_count * 100` clamped 0-100 (no bar), so all active servers' CPU counters sum to ~100% of host
  - log: 2026-06-18 criterion added (operator "CPU and MEM need to show % of total (host) ... all servers CPU % add up to 100%"); 2026-06-18 corrected "bar" -> "counter" (operator "there is no bar; counter")
- [ ] **Host CPU count denominator** - the % uses a real host CPU-core count from `/api/activity`, not the per-container `online_cpus` nor a max-of-assigned approximation
  - log: 2026-06-18 criterion added; backend must expose host CPU count first (blocking task)

## MEM counter - absolute GB

- [ ] **MEM counter = absolute GB** - the per-server MEM cell shows the actual GB used (e.g. "19.2 GB"), never a % and no bar; the MEM counters across active servers sum to the host total GB used
  - log: 2026-06-18 criterion added (operator "in Mem we don't show % but the actual GB used"); 2026-06-18 corrected "bar" -> "counter"
- [ ] **Host RAM in tooltip, not on the cell** - the host total (`memory_host_total_mb`) and the % of host appear in the tooltip; the cell itself stays a raw GB figure
  - log: 2026-06-18 criterion added

## Counter colour - % of assigned (quota)

- [ ] **Colour encodes quota usage, not the displayed value** - both the CPU and MEM counter COLOUR is driven by the server's usage as a % of its ASSIGNED quota, independent of the host-relative value the counter shows
  - log: 2026-06-18 criterion added (the key non-obvious design point: counter value = host share, counter colour = quota usage)
- [ ] **Reached quota -> danger** - at >= 100% of the assigned quota the counter colours danger (`--color-danger`, the Stop-button red)
  - log: 2026-06-18 criterion added (operator "if someone reached quota - we show in dangerous colour")
- [ ] **>= 75% and < quota -> warning** - between 75% and 100% of assigned the counter colours warning
  - log: 2026-06-18 criterion added (operator ">=75% of quota and still < quota - warning colour")
- [ ] **< 75% -> normal** - below 75% of assigned the counter keeps the normal text colour
  - log: 2026-06-18 criterion added
- [ ] **CPU quota source** - the CPU quota % uses `cpu_percent / cpu_cores` (the assigned-core ceiling already on `/api/activity`)
  - log: 2026-06-18 criterion added
- [ ] **MEM quota source** - the MEM quota % uses `memory_percent` (usage / assigned limit already on `/api/activity`)
  - log: 2026-06-18 criterion added

## Tooltips reveal all

- [ ] **CPU tooltip full breakdown** - the CPU tooltip lists usage in cores, the assigned ceiling, the % of assigned used, and the quota-crossing state
  - log: 2026-06-18 criterion added (operator "tooltip reveals all, incl crossing the quota info")
- [ ] **MEM tooltip full breakdown** - the MEM tooltip lists GB used, the assigned ceiling, the % of assigned used, the % of host total, and the quota-crossing state
  - log: 2026-06-18 criterion added
- [ ] **Quota-crossing line** - when usage is >= 75% the tooltip states "over warning threshold"; when >= 100% it states the quota is reached/exceeded
  - log: 2026-06-18 criterion added
- [ ] **Multiline** - tooltips are `\n`-joined (one fact per line), consistent with the existing servers tooltips
  - log: 2026-06-18 criterion added

## Server Status hero unchanged

- [ ] **Hero keeps bars at % of assigned** - the Server Status hero widget keeps its CPU/MEM bars showing usage as a % of the server's ASSIGNED quota (`cpuBarPct` / `memory_percent`); it is the ONLY surface showing % of assigned and must not switch to host-relative counters
  - log: 2026-06-18 criterion added (operator "the only place where we see the % of assigned - is the Server Status widget")

## Edge cases

- [ ] **Edge: unlimited quota** - when a server has no CPU/MEM limit the assigned ceiling is the host, so % of assigned coincides with % of host; the colour then ramps against that single value and the tooltip says "no limit"
  - log: 2026-06-18 criterion added
- [ ] **Edge: no quota configured** - when the platform quota env is 0/unset the colour never reaches warning/danger from that quota and the tooltip omits the quota clause
  - log: 2026-06-18 criterion added
- [ ] **Edge: server stopped** - the CPU/MEM counters read the muted dash when the server is not running (no host-relative figure invented)
  - log: 2026-06-18 criterion added
- [ ] **Edge: host total unknown** - when the host CPU count or host RAM total is unavailable the affected counter renders an explicit unknown/error state, never a fabricated value (see the no-fallback memory rule in [[acc-crit-resource-bars]])
  - log: 2026-06-18 criterion added
- [ ] **Edge: data not yet sampled** - before the first stats sample lands the counters show the muted dash, never a 0
  - log: 2026-06-18 criterion added

## Data sources (/api/activity per-user fields)

- `cpu_percent`, `cpu_cores`, `cpu_cores_limited` - usage (cores x 100), assigned cores, whether limited
- `memory_mb`, `memory_percent`, `memory_total_mb`, `memory_limited` - GB used, % of assigned, assigned ceiling, whether limited
- `memory_host_total_mb` - host RAM total (for the MEM tooltip's % of host)
- NEEDED: host CPU-core count (CPU counter denominator) - to be added to the payload
