/* Pure server CPU/MEM cell logic for the Servers page + Home servers widget.
 * Extracted from the live/mock adapters so the calculations and tooltip strings
 * are unit-testable in isolation (see serverMetrics.test.ts) and identical on both
 * surfaces. The counter VALUE is host-relative (CPU = total cores-used %, MEM = GB);
 * the counter COLOUR is quota-relative (% of the server's ASSIGNED limit). */
import { QUOTA_COLOR } from '../config'

const round1 = (n: number) => Math.round(n * 10) / 10
const clampPct = (n: number) => Math.max(0, Math.min(100, Math.round(n)))

/** % of the ASSIGNED cores a server is using (cpu_percent is cores-used x 100, so
 * divide by assigned cores). Capped 0-100 - this is the Server Status hero CPU bar
 * fill (the one bar capped at its assigned cores). */
export const cpuAssignedPct = (cpuPercent: number | null | undefined, cores: number | null | undefined): number =>
  cpuPercent == null ? 0 : clampPct(cores && cores > 0 ? cpuPercent / cores : cpuPercent)

/** CPU usage in the docker/top convention: `cpu_percent` is already cores-used x
 * 100 (100% = one core), so a server saturating 13 cores reads 1300%. Rounded,
 * never clamped, never divided by host cores. null when not sampled. */
export const cpuCounterPct = (cpuPercent: number | null | undefined): number | null =>
  cpuPercent == null ? null : Math.round(cpuPercent)

/** Memory used in GB (absolute), one decimal. null when not sampled. */
export const memCounterGb = (memMb: number | null | undefined): number | null =>
  memMb == null ? null : round1(memMb / 1024)

/** Usage as a % of the ASSIGNED CPU quota: `cpu_percent` is cores-used x 100, so
 * dividing by the assigned cores yields the % of the ceiling. Drives the counter
 * COLOUR, not its value. May exceed 100 (over quota). null when cores unknown. */
export const cpuQuotaPct = (cpuPercent: number | null | undefined, cores: number | null | undefined): number | null =>
  cpuPercent == null || !cores || cores <= 0 ? null : Math.round(cpuPercent / cores)

/** Usage as a % of the ASSIGNED memory limit (`memory_percent` already = usage /
 * cgroup limit). Drives the counter COLOUR. null when not sampled. */
export const memQuotaPct = (memoryPercent: number | null | undefined): number | null =>
  memoryPercent == null ? null : Math.round(memoryPercent)

/** Quota-crossing clause for a usage % of the assigned quota: " (quota reached)" at
 * or over the danger band, " (over warning threshold)" in the warn band, else "". */
export const quotaCrossing = (pct: number | null | undefined): string =>
  pct == null ? '' : pct >= QUOTA_COLOR.dangerPct ? ' (quota reached)' : pct >= QUOTA_COLOR.warnPct ? ' (over warning threshold)' : ''

/** Counter colour by % of the ASSIGNED quota: danger (red) at/over quota, warning
 * (amber) in the warn band, undefined below (the default muted cell colour). Returns
 * a design-token CSS string so it stays matched to the Stop button / warning token. */
export const quotaColor = (pct: number | null | undefined): string | undefined =>
  pct == null ? undefined : pct >= QUOTA_COLOR.dangerPct ? 'var(--color-danger)' : pct >= QUOTA_COLOR.warnPct ? 'var(--color-warning)' : undefined

/** CPU cell tooltip - reveals the full breakdown the host-relative counter hides:
 * cores used, the assigned ceiling, and the % of assigned with the quota-crossing
 * state. Multiline (one fact per line). */
export function cpuTooltip(opts: { cpuPercent: number; cores: number | null | undefined; coresLimited: boolean }): string {
  const { cpuPercent, cores, coresLimited } = opts
  const qp = cpuQuotaPct(cpuPercent, cores)
  return [
    `${round1(cpuPercent / 100)} cores used`,
    cores != null ? `${cores} core${cores === 1 ? '' : 's'} ${coresLimited ? 'assigned' : 'host (no limit)'}` : '',
    qp != null ? `${qp}% of assigned${quotaCrossing(qp)}` : '',
  ].filter(Boolean).join('\n')
}

/** Server Status hero CPU bar tooltip. The bar FILL is the % of assigned (capped);
 * the tooltip reveals cores used, the assigned ceiling, and BOTH the % of assigned
 * compute (the fill) and the % of total host compute. */
export function heroCpuTooltip(opts: { cpuPercent: number; cores: number | null | undefined; coresLimited: boolean; assignedPct: number; hostPct: number | null }): string {
  const { cpuPercent, cores, coresLimited, assignedPct, hostPct } = opts
  return [
    `${round1(cpuPercent / 100)} cores used`,
    cores != null ? `${cores} core${cores === 1 ? '' : 's'} ${coresLimited ? 'assigned' : 'host (no limit)'}` : '',
    `${assignedPct}% of assigned compute`,
    hostPct != null ? `${hostPct}% of host compute` : '',
  ].filter(Boolean).join('\n')
}

/** Host Status aggregate CPU bar tooltip. The bar FILL is the % of total host
 * compute; the tooltip reveals cores used across servers and BOTH the % of host
 * compute (the fill) and the % of total assigned compute. */
export function hostCpuTooltip(opts: { coresUsed: number; hostCores: number; hostPct: number; assignedPct: number | null; servers: string }): string {
  const { coresUsed, hostCores, hostPct, assignedPct, servers } = opts
  return [
    `${round1(coresUsed)} of ${hostCores} core${hostCores === 1 ? '' : 's'} used across ${servers}`,
    `${hostPct}% of host compute`,
    assignedPct != null ? `${assignedPct}% of assigned compute` : '',
  ].filter(Boolean).join('\n')
}

/** Memory cell tooltip - GB used, the assigned ceiling, % of assigned (+ crossing),
 * and % of host RAM. Multiline (one fact per line). */
export function memTooltip(opts: { memMb: number; memTotalMb: number | null | undefined; memLimited: boolean; memoryPercent: number | null | undefined; memHostTotalMb: number }): string {
  const { memMb, memTotalMb, memLimited, memoryPercent, memHostTotalMb } = opts
  const qp = memQuotaPct(memoryPercent)
  const pctHost = memHostTotalMb > 0 ? Math.round((memMb / memHostTotalMb) * 100) : null
  return [
    `${round1(memMb / 1024)} GB used`,
    memTotalMb ? `${round1(memTotalMb / 1024)} GB ${memLimited ? 'assigned' : 'host (no limit)'}` : '',
    qp != null ? `${qp}% of assigned${quotaCrossing(qp)}` : '',
    pctHost != null ? `${pctHost}% of ${round1(memHostTotalMb / 1024)} GB host` : '',
  ].filter(Boolean).join('\n')
}
