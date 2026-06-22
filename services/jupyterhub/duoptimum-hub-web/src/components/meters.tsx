/* Visual-metaphor primitives: the activity meter, the proportional spark bar, the
 * resource bars, and the TTL gadget. Each carries the precise value in a tooltip,
 * never inline (per the design language). */
import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { Button, Popover, Progress, Slider } from 'antd'
import { Icon } from './Icon'
import { fmtMinutes } from '../lib/format'
import { ANIMATION, BAR_COLOR, TTL_COLOR } from '../services/config'
import { gpuSupported } from '../app/capabilities'
import { useTheme } from '../theme/ThemeProvider'
import { PALETTES } from '../theme/tokens'
import { gpuStripeColor } from '../lib/gpuStripes'
import type { GpuDevice } from '../services/types'

// Multiline tooltip for the engagement meter: the activity % (uncapped - may
// exceed 100% when the user works more than the daily target) plus the real
// average active hours/day behind it. `pct` is the uncapped figure when known,
// else the capped meter value. The 3-day phrasing matches the 72h half-life.
export function activityTitle(pct: number | null, hours?: number | null): string {
  const lines: string[] = []
  if (pct != null) lines.push(`${pct}% of the daily activity target`)
  if (hours != null) lines.push(`Active on average ${hours}h/day over the last 3 days`)
  return lines.length ? lines.join('\n') : 'No activity recorded yet'
}

// 5-segment engagement meter. Fill follows the capped score; the tooltip shows
// the uncapped `pct` (when supplied) so >100% is visible. The whole meter takes
// one tone by lit-bar count: 1 bar pale red, 2-3 orange, 4-5 green.
export function ActivityMeter({ value, hours, pct, title }: { value: number | null; hours?: number | null; pct?: number | null; title?: string }) {
  if (value == null) return <span className="doh-muted">-</span>
  const lit = Math.max(0, Math.min(5, Math.round(value / 20)))
  const tone = lit <= 1 ? 'low' : lit <= 3 ? 'idle' : ''
  return (
    <span className={`doh-meter ${tone}`} title={title ?? activityTitle(pct ?? value, hours)}>
      {[0, 1, 2, 3, 4].map((i) => (
        <i key={i} className={i < lit ? 'on' : ''} />
      ))}
    </span>
  )
}

// 5-segment meter stretched to fill a row (resource panels).
export function ActivityMeterFill({ value, hours, pct, title }: { value: number; hours?: number | null; pct?: number | null; title?: string }) {
  const lit = Math.max(0, Math.min(5, Math.round(value / 20)))
  const tone = lit <= 1 ? 'low' : lit <= 3 ? 'idle' : ''
  return (
    <span className={`doh-meter fill ${tone}`} title={title ?? activityTitle(pct ?? value, hours)}>
      {[0, 1, 2, 3, 4].map((i) => (
        <i key={i} className={i < lit ? 'on' : ''} />
      ))}
    </span>
  )
}

export interface SparkSegment {
  width: number | string
  color: string
}

export function Spark({ segments, height = 6, title, style }: { segments: SparkSegment[]; height?: number; title?: string; style?: CSSProperties }) {
  return (
    <div className="doh-spark" style={{ height, ...style }} title={title}>
      {segments.map((s, i) => (
        <span key={i} style={{ width: typeof s.width === 'number' ? `${s.width}%` : s.width, background: s.color }} />
      ))}
    </div>
  )
}

// per-GPU bars: one labelled horizontal bar per device, fill width = its load.
// The index labels make it read unmistakably as N separate GPUs. When device
// metadata is supplied the tooltip names the GPU and quotes its live load.
// The bar fill is the standard accent on every device; only the diagonal stripe
// tint shifts per device. Each stripe colour is computed (`gpuStripeColor`) to
// CONTRAST with the theme accent (the fill), with the hue rotated per device so
// the GPUs read distinct while every stripe stays inside the contrast budget.
export function GpuMeter({ gpus, devices }: { gpus: number[]; devices?: GpuDevice[] }) {
  const { resolved } = useTheme()
  const accent = PALETTES[resolved].accent // the bar-fill base the stripes contrast against
  return (
    <span className="doh-gpurows">
      {gpus.map((g, i) => {
        const d = devices?.[i]
        return (
          <span className="doh-gpurow" key={i} title={gpuTip(d, g, i)}>
            <small>{d ? shortGpuName(d.name) : `GPU ${i}`}</small>
            <span className="track">
              <i
                style={{
                  width: `${Math.max(3, g)}%`,
                  backgroundImage: `repeating-linear-gradient(45deg, ${gpuStripeColor(accent, i, gpus.length)} 0 3px, transparent 3px 7px)`,
                }}
              />
            </span>
          </span>
        )
      })}
    </span>
  )
}

// real GPU inventory: one accent chip per physical device (index + short name).
// Used when host GPU utilisation is not sampled - shows the true device count
// without claiming a load. Memory total goes in the row value.
// mini GPU name: drop vendor/brand boilerplate, keep the distinguishing model
// ("NVIDIA GeForce RTX 5090" -> "5090", "NVIDIA RTX 5000 Ada Generation" ->
// "5000 Ada"). Falls back to the raw name if stripping leaves nothing.
function shortGpuName(name: string): string {
  const s = name
    .replace(/\b(NVIDIA|GeForce|RTX|GTX|Tesla|Quadro|Generation|Laptop GPU)\b/gi, '')
    .replace(/\s+/g, ' ')
    .trim()
  return s || name
}

// multiline GPU tooltip as a plain newline-joined string for the native `title`
// attribute - the SAME standard browser tooltip the CPU/memory/volume/system
// cells use, so every resource tooltip reads identically (no bespoke antd popup).
// Full name, UUID, memory, live utilisation, temperature, power; only lines with
// data show; falls back to a bare index + load when no device metadata exists.
function gpuTip(d: GpuDevice | undefined, utilPct?: number, idx?: number): string {
  if (!d) return `GPU ${idx ?? '?'}${utilPct != null ? ` - ${utilPct}%` : ''}`
  const gb = (mb?: number) => (mb ? (mb / 1024).toFixed(mb >= 10240 ? 0 : 1) : null)
  const total = gb(d.memoryMb)
  const used = gb(d.memoryUsedMb)
  const util = utilPct ?? d.utilizationPct
  const lines: string[] = [d.name]
  if (d.uuid) lines.push(`UUID ${d.uuid}`)
  if (total) lines.push(`Memory ${used ? `${used} / ` : ''}${total} GB`)
  if (util != null) lines.push(`Utilisation ${util}%`)
  if (d.temperatureC != null) lines.push(`Temp ${d.temperatureC}°C`)
  if (d.powerW != null) lines.push(`Power ${Math.round(d.powerW)} W`)
  return lines.join('\n')
}

export function GpuInventory({ devices }: { devices: GpuDevice[] }) {
  return (
    <span style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {devices.map((d) => (
        <span
          key={d.index}
          title={gpuTip(d)}
          style={{
            display: 'inline-flex', alignItems: 'baseline', gap: 5, padding: '1px 8px', borderRadius: 6,
            fontSize: 12, lineHeight: 1.5, background: 'var(--color-accent-soft)', color: 'var(--color-accent)',
          }}
        >
          <small style={{ opacity: 0.65 }}>{d.index}</small>
          {shortGpuName(d.name)}
        </span>
      ))}
    </span>
  )
}

export interface ResourceRow {
  label: string
  value: number
  valueLabel?: string
  tip?: string
  gpus?: number[] // per-GPU utilisation % - segmented meter; takes precedence over gpuDevices
  gpuDevices?: GpuDevice[] // real inventory - drives the striped per-GPU bars (zero fill when utilisation is absent)
  gpuDisconnected?: boolean // gpuinfo sidecar down - drop this GPU row entirely (no stale inventory / no health)
  meter?: ReactNode // override the bar (e.g. an activity meter)
  error?: boolean // readout unavailable - show an explicit "unavailable", never a fabricated bar
}

// Resource-bar fill colour rule (fixed bands, no accent muddying): normal accent
// below `warnPct`, full (normal) warning at/above `warnPct`, full danger at/above
// `dangerPct`. Only the warn..danger span blends - and that's warm warning -> red
// (adjacent hues) so it stays saturated, never the dim brown that warning-mixed-
// with-blue produced. Thresholds in `BAR_COLOR`; stated on /design-language.
export function barColor(pct: number): string | undefined {
  const { warnPct, dangerPct } = BAR_COLOR
  if (pct < warnPct) return undefined // calm: CSS default accent, no tint
  if (pct >= dangerPct) return 'var(--color-danger)' // full danger
  const k = Math.round(((pct - warnPct) / (dangerPct - warnPct)) * 100) // full warning at warnPct -> red toward dangerPct
  return `color-mix(in srgb, var(--color-danger) ${k}%, var(--color-warning))`
}

export function ResourceBars({ rows }: { rows: ResourceRow[] }) {
  // Hide every GPU row when the platform has no GPU (no sidecar / none detected),
  // rather than rendering a "none"/empty GPU bar. Also drop any GPU row flagged
  // gpuDisconnected - the gpuinfo sidecar is down, so the inventory may be stale and
  // there is no live health; show NO GPU info rather than devices we know nothing about.
  const visible = (gpuSupported() ? rows : rows.filter((r) => r.gpus === undefined && r.gpuDevices === undefined))
    .filter((r) => !r.gpuDisconnected)
  return (
    <div className="doh-res">
      {visible.map((r) => {
        // readout unavailable: never fabricate a bar - show an explicit "unavailable"
        // (operator: better to say "I don't know" than guess a denominator)
        if (r.error) {
          return (
            <div className="doh-res-row" key={r.label}>
              <span className="doh-res-label">{r.label}</span>
              <span className="doh-res-bar" title={r.tip || 'Reading unavailable'} />
              <span className="doh-res-val doh-muted" title={r.tip || 'Reading unavailable'}>unavailable</span>
            </div>
          )
        }
        const utils = r.gpus // per-GPU utilisation (when sampled)
        const devices = r.gpuDevices // real inventory (names; fills the bars when utilisation is absent)
        const isGpuRow = utils !== undefined || devices !== undefined
        const n = utils?.length ?? devices?.length ?? 0
        const invOnly = utils === undefined && devices !== undefined && n > 0
        const memGB = devices ? Math.round(devices.reduce((s, d) => s + (d.memoryMb || 0), 0) / 1024) : 0
        const label = isGpuRow && n ? `${n} GPU${n > 1 ? 's' : ''}` : r.label
        const bar = r.meter
          ?? (isGpuRow
            ? (n
              // always the labelled striped per-GPU bars when devices exist; when
              // utilisation is not sampled the bars render at zero fill (empty
              // striped track) rather than collapsing to inventory chips
              ? <GpuMeter gpus={utils ?? devices!.map((d) => d.utilizationPct ?? 0)} devices={devices} />
              : <span className="doh-res-bar" title={r.tip} />)
            // the detail tooltip rides BOTH the bar and the value, so hovering the
            // progress bar itself (not only the % readout) shows the breakdown
            : <span className="doh-res-bar" title={r.tip}><i style={{ width: `${r.value}%`, background: barColor(r.value), transition: 'width .4s ease, background .4s ease' }} /></span>)
        const val = r.valueLabel
          ?? (r.meter ? '' : isGpuRow ? (n ? (invOnly && memGB ? `${memGB} GB` : '') : '-') : `${r.value}%`)
        return (
          <div className="doh-res-row" key={r.label}>
            <span className="doh-res-label">{label}</span>
            {bar}
            <span className="doh-res-val" title={r.tip}>{val}</span>
          </div>
        )
      })}
    </div>
  )
}

// CSS `ease` timing function (cubic-bezier(.25,.1,.25,1)) as a JS easing, so a
// JS-driven number tween moves in lockstep with a CSS width transition that uses
// `ease`. Compact Newton-Raphson solve for t given progress x, then sample y.
function EASE(x: number): number {
  const p1x = 0.25, p1y = 0.1, p2x = 0.25, p2y = 1
  const cx = 3 * p1x, bx = 3 * (p2x - p1x) - cx, ax = 1 - cx - bx
  const cy = 3 * p1y, by = 3 * (p2y - p1y) - cy, ay = 1 - cy - by
  const sx = (t: number) => ((ax * t + bx) * t + cx) * t
  const sy = (t: number) => ((ay * t + by) * t + cy) * t
  const dx = (t: number) => (3 * ax * t + 2 * bx) * t + cx
  let t = x
  for (let i = 0; i < 5; i++) {
    const d = dx(t)
    if (Math.abs(d) < 1e-6) break
    t -= (sx(t) - x) / d
  }
  return sy(t)
}

// TTL colour by fraction of base left (reverse of the resource bars; fixed bands).
// Blue (info) above warnFrac; full (normal) warning at/below warnFrac; dim red
// (--doh-ttl-red, not the bright alarm danger - a low timer is the normal end
// state) at/below dangerFrac. Only the warn..danger span blends, warm warning ->
// dim red. Thresholds in config.ts (visual only).
function ttlTone(frac: number): string {
  const { warnFrac, dangerFrac } = TTL_COLOR
  if (frac >= warnFrac) return 'var(--doh-ttl-blue)'
  if (frac <= dangerFrac) return 'var(--doh-ttl-red)'
  const k = Math.round(((warnFrac - frac) / (warnFrac - dangerFrac)) * 100) // full warning at warnFrac -> dim red toward dangerFrac
  return `color-mix(in srgb, var(--doh-ttl-red) ${k}%, var(--color-warning))`
}

// idle-session timer: a standard progress bar that reads 100% (blue) when time
// is ample and drains down, shifting blue -> orange -> red as the cull nears; the
// used-up remainder shows as the gray trail. The whole gadget spans the row
// (bar + time + Extend). Extend opens an hours slider whose last tick is "max",
// which tops the session up to the configured ceiling (old-JupyterHub style).
export function TtlGadget({ timeLeftMin, baseMin, maxAddHours = 0, displayCeilingMin, uptimeLabel, onExtend }: { timeLeftMin: number; baseMin: number; maxAddHours?: number; displayCeilingMin?: number; uptimeLabel?: string; onExtend?: (hours: number) => void | Promise<unknown> }) {
  // bar 100% ref. below base: base (fresh ~full, drains in last base window). banked
  // above base: high-water mark = remaining last extended TO (displayCeilingMin), so
  // just-extended reads 100% and drains vs THAT mark, not the far 72h ceiling (old bug:
  // 35h of 72h = ~50%). below base: ignore mark, use base. ceilMin arg = boost's new
  // mark. SSOT: idle_culler.calc_progress_pct_extended.
  const pctFor = (min: number, ceilMin?: number) => {
    const c = ceilMin ?? displayCeilingMin
    const ceil = c && c > baseMin ? c : 0
    if (min > baseMin && ceil > 0) return Math.min(100, Math.round((min / ceil) * 100))
    return baseMin ? Math.max(0, Math.min(100, Math.round((min / baseMin) * 100))) : 0
  }
  const pct = pctFor(timeLeftMin)
  // colour vs % of base left (not bar scale): blue, blending amber then red as it empties
  const color = ttlTone(baseMin > 0 ? timeLeftMin / baseMin : 1)
  // native 2-line tooltip: fill %, banked hours over base (if extended), wall-clock cull ETA
  const overH = Math.floor((timeLeftMin - baseMin) / 60)
  const cullAt = new Date(Date.now() + timeLeftMin * 60000)
  const cullLabel = cullAt.toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' })
  const barTip = `Idle timer - ${pct}% left${overH > 0 ? ` · +${overH}h over standard TTL` : ''}\nAuto-stops ~${cullLabel} if left idle`
  const maxH = Math.max(1, Math.round(maxAddHours))
  const [open, setOpen] = useState(false)
  // slider default = stable +4h (clamped to available), NOT max - max shrinks as time
  // banks, so defaulting to it gave a jumpy "+48h ... +11h" offer
  const RECOMMENDED_ADD_H = 4
  const [hours, setHours] = useState(Math.min(RECOMMENDED_ADD_H, maxH))
  const atCeiling = maxAddHours <= 0
  // extend boost: bar fill (displayPct) grows by rAF from the current fill to the target
  // vs the NEW high-water mark, in lockstep with the count-up text. holds until refetch
  // lands a changed value (min-fill window so growth is seen, safety cap so it can't
  // stick). backend stores the same mark, so the landed % == the target: seamless grow,
  // never a momentary 100% then drop. displayMin freezes shown time during fill.
  const [boost, setBoost] = useState(false)
  const [displayMin, setDisplayMin] = useState(timeLeftMin)
  const [displayPct, setDisplayPct] = useState(0) // bar fill driven by rAF during a boost
  const baselineMin = useRef(timeLeftMin) // time-left captured at extend click
  const boostTargetMin = useRef(timeLeftMin) // post-extend time-left captured at click
  const baselinePct = useRef(0)  // bar fill % at extend click - grow FROM here
  const boostTargetPct = useRef(0) // post-extend fill % - grow TO here (vs the new mark)
  const rafRef = useRef<number | null>(null) // count-up animation frame (bar + counter)
  const minFillDone = useRef(false)       // minimum fill window elapsed
  const valueLanded = useRef(false)       // refetch delivered a changed value
  // while NOT boosting, the shown time tracks the live value; once the boost ends
  // it lands here (the invariant ceiling makes the landed value equal the target)
  useEffect(() => {
    if (!boost) setDisplayMin(timeLeftMin)
  }, [boost, timeLeftMin])
  // during the boost, count the shown time UP from the captured baseline to the
  // post-extend target over the SAME duration and easing as the bar fill, so the
  // number climbs in lockstep with the bar (CSS `ease` = cubic-bezier(.25,.1,.25,1))
  useEffect(() => {
    if (!boost) return
    const fromMin = baselineMin.current
    const toMin = boostTargetMin.current
    const fromPct = baselinePct.current
    const toPct = boostTargetPct.current
    if (toMin === fromMin && toPct === fromPct) return
    let startTs: number | null = null
    const step = (ts: number) => {
      if (startTs === null) startTs = ts
      const p = Math.min(1, (ts - startTs) / ANIMATION.ttlExtendMs)
      const e = EASE(p)
      setDisplayMin(Math.round(fromMin + (toMin - fromMin) * e))
      // bar grows FROM the current fill TO the target, frame by frame, in lockstep
      // with the counter - never a flip straight to 100% (DEF-15)
      setDisplayPct(Math.round(fromPct + (toPct - fromPct) * e))
      if (p < 1) rafRef.current = requestAnimationFrame(step)
    }
    rafRef.current = requestAnimationFrame(step)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [boost])
  // end the boost only when the new value has landed AND the fill has had time to play
  useEffect(() => {
    if (boost && timeLeftMin !== baselineMin.current) {
      valueLanded.current = true
      if (minFillDone.current) setBoost(false)
    }
  }, [boost, timeLeftMin])
  const shownPct = boost ? displayPct : pct
  // the bar's tone, shared by the readout: the time number + clock icon take the
  // SAME colour the bar shows at this moment (accent normally, warning/danger as
  // the cull nears, accent during an extend boost) so the gadget reads as one cue
  const barTone = boost ? 'var(--color-accent)' : color
  const apply = () => {
    setOpen(false)
    const add = Math.max(1, Math.min(maxH, hours))
    // optimistic post-extend remaining = new high-water mark; bar measured vs it
    // (banked extend -> 100%, sub-base extend -> fills toward base). grows, no flash.
    const targetMin = timeLeftMin + add * 60
    baselineMin.current = timeLeftMin
    boostTargetMin.current = targetMin // counter count-up target, in lockstep with the bar
    baselinePct.current = pct          // bar grows FROM the current fill...
    boostTargetPct.current = pctFor(targetMin, targetMin) // ...UP TO the target vs the new mark
    setDisplayPct(pct)                 // seat the first boost frame at the current fill (no flip)
    minFillDone.current = false
    valueLanded.current = false
    setBoost(true)
    // keep the bar at the target for at least one fill duration so the growth is seen
    window.setTimeout(() => { minFillDone.current = true; if (valueLanded.current) setBoost(false) }, ANIMATION.ttlExtendMs)
    // safety: never let the boost hang if the refetch never changes the value
    window.setTimeout(() => setBoost(false), ANIMATION.ttlExtendMs + 6000)
    // optimistic fill; if the extend request rejects, drop the boost immediately
    Promise.resolve(onExtend?.(add)).catch(() => setBoost(false))
  }
  // slider marks: first hour and the last tick labelled "max" (tops to ceiling)
  const marks: Record<number, ReactNode> = { 1: '1h', [maxH]: 'max' }
  const atMax = hours >= maxH
  return (
    <div className="doh-ttl" style={{ '--doh-ttl-glow': `${ANIMATION.ttlGlowMs}ms` } as CSSProperties}>
      <span className={boost ? 'doh-ttl-bar doh-ttl-boost' : 'doh-ttl-bar'} style={{ flex: 1, minWidth: 0, color: barTone }} title={barTip}>
        {/* status="normal" pins the status: antd otherwise auto-switches to "success"
         * at percent>=100 (progress.js), toggling .ant-progress-status-success exactly
         * at max - which re-animates/restyles the fill (the flicker + slightly-wider
         * look at max vs almost-max). Pinned, the bar renders identically at 99 and 100. */}
        <Progress percent={shownPct} status="normal" showInfo={false} strokeColor={barTone} trailColor="var(--color-bg-subtle)" style={{ margin: 0 }} />
      </span>
      <span className={boost ? 'doh-ttl-val doh-ttl-boost' : 'doh-ttl-val'} style={{ color: barTone, transition: 'color .4s ease, filter var(--doh-ttl-glow, 250ms) ease' }}>
        <Icon name="clock" size={14} />
        <b style={{ color: barTone }}>{fmtMinutes(displayMin)}</b>
      </span>
      {uptimeLabel && (
        <span className="doh-muted" title="Server uptime" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
          up {uptimeLabel}
        </span>
      )}
      <Popover
        open={open}
        onOpenChange={setOpen}
        trigger="click"
        title="Extend session"
        content={
          <div style={{ width: 240 }}>
            <Slider
              className="doh-ttl-slider"
              min={1}
              max={maxH}
              step={1}
              value={hours}
              onChange={(v) => setHours(v as number)}
              marks={marks}
              tooltip={{ formatter: (v) => (v != null && v >= maxH ? 'max' : `+${v}h`) }}
            />
            <Button size="small" type="primary" block onClick={apply} style={{ marginTop: 6 }}>
              {atMax ? 'Extend to Max' : `Extend +${hours}h`}
            </Button>
          </div>
        }
      >
        <Button size="small" disabled={atCeiling} title={atCeiling ? 'Already at the maximum session length' : `Add up to ${maxH}h before your lab is stopped for inactivity`}>
          Extend
        </Button>
      </Popover>
    </div>
  )
}
