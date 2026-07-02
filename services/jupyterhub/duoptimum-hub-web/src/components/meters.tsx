/* Visual-metaphor primitives: the activity meter, the proportional spark bar, the
 * resource bars, and the TTL gadget. Each carries the precise value in a tooltip,
 * never inline (per the design language). */
import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { Button, Modal, Popover, Slider } from 'antd'
import { Icon } from './Icon'
import { fmtMinutes } from '../lib/format'
import { useIsMobile } from '../lib/useIsMobile'
import { litBars, meterTone } from '../lib/activityMeter'
import { ANIMATION, BAR_COLOR, GPU_NAME_MAX_WORDS, TTL_COLOR } from '../services/config'
import { gpuSupported } from '../app/capabilities'
import { gpuStripeColor, GPU_STRIPE_COUNT } from '../lib/gpuStripes'
import type { GpuDevice } from '../services/types'

// Multiline tooltip for the engagement meter: the activity % (uncapped - may
// exceed 100% when the user works more than the daily target) plus the real
// average active hours/day behind it. `pct` is the uncapped figure when known,
// else the capped meter value. The 3-day phrasing matches the 72h half-life.
function activityTitle(pct: number | null, hours?: number | null): string {
  const lines: string[] = []
  if (pct != null) lines.push(`${pct}% of the daily activity target`)
  if (hours != null) lines.push(`Active on average ${hours}h/day over the last 3 days`)
  return lines.length ? lines.join('\n') : 'No activity recorded yet'
}

// shared 5-segment meter body. The lit-bar COUNT drives one tone for the whole meter:
// 1 bar pale red, 2-3 orange, 4-5 green. EXACTLY zero activity lights ZERO bars (empty meter) -
// distinct from null, which callers render as a dash. role=img + aria-label expose the value
// off-hover (the lit-bar count alone is not reachable by screen reader / keyboard).
function MeterBody({ value, fill, title }: { value: number; fill?: boolean; title: string }) {
  const lit = litBars(value)
  const tone = meterTone(lit)
  return (
    <span className={`doh-meter${fill ? ' fill' : ''}${tone ? ` ${tone}` : ''}`} role="img" aria-label={title} title={title}>
      {[0, 1, 2, 3, 4].map((i) => (
        <i key={i} className={i < lit ? 'on' : ''} />
      ))}
    </span>
  )
}

// 5-segment engagement meter. Fill follows the capped score; the tooltip + aria-label
// show the uncapped `pct` (when supplied) so >100% is visible. null = a dash.
export function ActivityMeter({ value, hours, pct, title }: { value: number | null; hours?: number | null; pct?: number | null; title?: string }) {
  if (value == null) return <span className="doh-muted">-</span>
  return <MeterBody value={value} title={title ?? activityTitle(pct ?? value, hours)} />
}

// 5-segment meter stretched to fill a row (resource panels).
export function ActivityMeterFill({ value, hours, pct, title }: { value: number; hours?: number | null; pct?: number | null; title?: string }) {
  return <MeterBody value={value} fill title={title ?? activityTitle(pct ?? value, hours)} />
}

export interface SparkSegment {
  width: number | string
  color: string
}

// proportional stacked bar. When a `title` is supplied it is exposed as an accessible
// image; without one (e.g. the metric-card spark, whose breakdown legend carries the
// numbers) it is decorative and hidden from the a11y tree.
export function Spark({ segments, height = 6, title, style }: { segments: SparkSegment[]; height?: number; title?: string; style?: CSSProperties }) {
  return (
    <div className="doh-spark" style={{ height, ...style }} role={title ? 'img' : undefined} aria-label={title} aria-hidden={title ? undefined : true} title={title}>
      {segments.map((s, i) => (
        <span key={i} style={{ width: typeof s.width === 'number' ? `${s.width}%` : s.width, background: s.color }} />
      ))}
    </div>
  )
}

// per-GPU bars: one labelled horizontal bar per device, fill width = its load.
// label = device name capped to GPU_NAME_MAX_WORDS words (vendor+family+model head kept,
// trailing "Laptop GPU" dropped), shown in FULL - the name takes its natural width and the
// bar shrinks to fit, so no required segment is ever ellipsis-trimmed. Every device keeps the
// calm accent base fill (global.css); only the 45-degree stripe overlay carries the device's
// IDENTITY colour from the fixed 10-hue palette (`gpuStripeColor`), bound to the index so a GPU
// keeps its colour as the inventory changes; devices past 10 reuse a colour, label marked with a
// cycle glyph. The per-row % (right-aligned, fixed column) shows when sampled, blank otherwise so
// the bar ENDS stay aligned with the CPU/Mem/Vol bars; the tooltip names the GPU + its live load.
export function GpuMeter({ gpus, devices, sampled = true }: { gpus: number[]; devices?: GpuDevice[]; sampled?: boolean }) {
  return (
    <span className="doh-gpurows">
      {gpus.map((g, i) => {
        const d = devices?.[i]
        const wrapped = i >= GPU_STRIPE_COUNT // identity colours cycle past the 10th device
        const label = `${d ? shortGpuName(d.name) : `GPU ${i}`}${wrapped ? ' ↻' : ''}`
        return (
          <span className="doh-gpurow" key={i} title={gpuTip(d, g, i)}>
            <small>{label}</small>
            <span className="track">
              {/* a 0% GPU reads as EXACTLY empty (the old Math.max(3,g) floor showed a 3% striped
                  sliver that looked like 1-2% load); a positive load keeps the 3% min-visible width
                  so a tiny load is still perceptible. identity at 0% comes from the GPU name. */}
              <i style={{ width: `${g > 0 ? Math.max(3, g) : 0}%`, backgroundImage: `repeating-linear-gradient(45deg, ${gpuStripeColor(i)} 0 3px, transparent 3px 7px)` }} />
            </span>
            <small className="doh-gpurow-val">{sampled ? `${g}%` : ''}</small>
          </span>
        )
      })}
    </span>
  )
}

// real GPU inventory: one accent chip per physical device (index + short name).
// Used when host GPU utilisation is not sampled - shows the true device count
// without claiming a load. Memory total goes in the row value.
// GPU card name: keep the full device name (starts "NVIDIA"), truncated to the
// first N words ("NVIDIA GeForce RTX 4090 Laptop GPU" -> "NVIDIA GeForce RTX
// 4090" at N=4). Shorter names render whole; falls back to the raw name if the
// split yields nothing.
function shortGpuName(name: string, maxWords = GPU_NAME_MAX_WORDS): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  return words.length ? words.slice(0, maxWords).join(' ') : name
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
// with-blue produced. Thresholds in `BAR_COLOR`; stated on /design-system.
function barColor(pct: number): string | undefined {
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
              // striped track) rather than collapsing to inventory chips, and the
              // per-device % readout is suppressed (the row value carries total mem)
              ? <GpuMeter gpus={utils ?? devices!.map((d) => d.utilizationPct ?? 0)} devices={devices} sampled={utils !== undefined || (devices?.some((d) => d.utilizationPct != null) ?? false)} />
              : <span className="doh-res-bar" title={r.tip} />)
            // the detail tooltip rides BOTH the bar and the value, so hovering the
            // progress bar itself (not only the % readout) shows the breakdown. fill
            // width is clamped to 100% (a >100% reading still shows full, not overflow);
            // the value label stays uncapped so the real figure shows
            : <span className="doh-res-bar" title={r.tip}><i style={{ width: `${Math.min(100, r.value)}%`, background: barColor(r.value), transition: 'width .4s ease, background .4s ease' }} /></span>)
        const val = r.valueLabel
          ?? (r.meter ? '' : isGpuRow ? (n ? (invOnly && memGB ? `${memGB} GB` : '') : '-') : `${r.value}%`)
        return (
          <div className="doh-res-row" key={r.label}>
            <span className="doh-res-label">{label}</span>
            {bar}
            {/* GPU rows omit the value column so the per-device striped meter spans to the
              * panel's right edge - each row's own right-aligned % then lines up with the
              * CPU/Mem/Vol % above it (design: every reading right-aligns to one edge) */}
            {!isGpuRow && <span className="doh-res-val" title={r.tip}>{val}</span>}
          </div>
        )
      })}
    </div>
  )
}

// trapezoidal-velocity ease (the TTL "effort" envelope): speed ramps up over the first quarter,
// holds full through the middle, ramps down over the last quarter - so a value tweened with this
// accelerates in, cruises, then decelerates onto its target. returns eased progress 0..1.
// NOTE: a=0.25 (the quarter) MUST match the 25%/75% stops in the doh-ttl-boost-bar/-num/-clock
// keyframes (global.css) - that is what keeps the glow/blur amplitude in lockstep with this velocity.
function rampEase(p: number, a = 0.25): number {
  const norm = 1 - a
  if (p < a) return (p * p) / (2 * a * norm)
  if (p < 1 - a) return (p - a / 2) / norm
  const q = 1 - p
  return 1 - (q * q) / (2 * a * norm)
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
export function TtlGadget({ timeLeftMin, baseMin, maxAddHours = 0, displayCeilingMin, uptimeLabel, uptimeSince, onExtend }: { timeLeftMin: number; baseMin: number; maxAddHours?: number; displayCeilingMin?: number; uptimeLabel?: string; uptimeSince?: string; onExtend?: (hours: number) => void | Promise<unknown> }) {
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
  // extend boost: ONE ramp-up / steady / ramp-down envelope (no pulsing). on extend the bar GROWS
  // and the counter COUNTS from the current remaining up to the new remaining; their speed ramps up
  // to full, holds, then ramps down to settle on the new value (rampEase = trapezoidal velocity).
  // a SINGLE rAF drives bar + counter in lockstep (both need data-driven values JS can supply but
  // CSS can't). riding the same envelope, the fill glow, the clock glow and the counter blur ramp
  // their AMPLITUDE up -> steady -> down via one-shot pure-CSS keyframes (off the compositor). the
  // class is held for the in-flight extend + one envelope, then dropped (bar settles to the new %).
  const [boost, setBoost] = useState(false)
  const [displayMin, setDisplayMin] = useState(timeLeftMin)
  const [displayPct, setDisplayPct] = useState(pct)
  const fromMin = useRef(timeLeftMin), toMin = useRef(timeLeftMin)
  const fromPct = useRef(pct), toPct = useRef(pct)
  const rafRef = useRef<number | null>(null)
  // the value an in-flight extend is landing on; held across the boost-release until the parent's
  // refetch catches up to it (see below). null when no extend is pending.
  const pendingTarget = useRef<number | null>(null)
  // off-boost the readouts track the live prop - EXCEPT right after an extend, while the parent's
  // refetch is still in flight (timeLeftMin still shows the pre-extend remaining). settling on the
  // stale prop there flashes the counter BACKWARD to the old value (most visibly in reduced motion,
  // which releases boost before the refetch lands). so hold the computed target until the prop rises
  // past the pre-extend remaining (refetch landed), then resume tracking the live value.
  useEffect(() => {
    if (boost) return
    if (pendingTarget.current != null && timeLeftMin <= fromMin.current) {
      setDisplayMin(pendingTarget.current); setDisplayPct(toPct.current); return
    }
    pendingTarget.current = null
    setDisplayMin(timeLeftMin); setDisplayPct(pct)
  }, [boost, timeLeftMin, pct])
  // on boost, one rAF tweens the counter integer AND the bar fill from->to over ttlExtendMs with the
  // trapezoidal-velocity envelope (ramp up to full speed, steady, ramp down); they stay in lockstep
  useEffect(() => {
    if (!boost) return
    const m0 = fromMin.current, m1 = toMin.current, p0 = fromPct.current, p1 = toPct.current
    if (m0 === m1 && p0 === p1) return
    // the extend boost is a deliberate, one-shot, user-triggered confirmation, so it counts/tweens
    // REGARDLESS of prefers-reduced-motion (the boost CSS is exempted from the reduced-motion guard
    // too). only the INFINITE expiry pulses stay reduced-motion-gated.
    let start: number | null = null
    const step = (ts: number) => {
      if (start === null) start = ts
      const e = rampEase(Math.min(1, (ts - start) / ANIMATION.ttlExtendMs))
      setDisplayMin(Math.round(m0 + (m1 - m0) * e))
      setDisplayPct(Math.round(p0 + (p1 - p0) * e))
      if (e < 1) rafRef.current = requestAnimationFrame(step)
    }
    rafRef.current = requestAnimationFrame(step)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [boost])
  const apply = () => {
    setOpen(false)
    const add = Math.max(1, Math.min(maxH, hours))
    const targetMin = timeLeftMin + add * 60
    fromMin.current = timeLeftMin; toMin.current = targetMin
    fromPct.current = pct; toPct.current = pctFor(targetMin, targetMin)
    pendingTarget.current = targetMin // hold this across boost-release until the refetch catches up
    setDisplayMin(timeLeftMin); setDisplayPct(pct) // seat the first frame at the current values
    setBoost(true)
    // hold the class for the in-flight extend AND at least one full envelope so the ramp plays out;
    // on success the bar then settles to the new remaining (antd's width transition returns once the
    // class drops), on reject the boost ends immediately. the hold is armed REGARDLESS of reduced
    // motion - the boost is a one-shot user-triggered confirmation that now plays in all cases (an
    // earlier reduce-branch nulled this timer, which - combined with the CSS reduced-motion guard -
    // collapsed the whole boost to ~0s on any machine with OS "reduce motion" on: the real root cause
    // of the operator's "lasts a fraction of a second").
    const minCycle = new Promise<void>((resolve) => window.setTimeout(resolve, ANIMATION.ttlExtendMs))
    Promise.resolve(onExtend?.(add))
      .then(() => minCycle)
      .catch(() => { pendingTarget.current = null }) // extend failed: drop the held target, fall back to the live prop
      .then(() => setBoost(false))
  }
  // slider marks: first hour and the last tick labelled "max" (tops to ceiling)
  const marks: Record<number, ReactNode> = { 1: '1h', [maxH]: 'max' }
  const atMax = hours >= maxH
  // the bar tone (also used by the readout - time number + clock icon): blue normally,
  // warning/danger as the cull nears. an extend boost recolours the whole gadget to the accent
  // hue (fixed) and adds the artifact's motion cues: the fill lifts brightness/saturation on that
  // hue + throws a forward accent box-shadow cropped by the track (boost-bar), the counter number
  // blurs (boost-num), and the clock glyph glows (boost-clock); separately the clock picks up an
  // expiry glow as the timer empties (soft at warn <=warnFrac, bright/fast at end <=dangerFrac).
  // all gated by prefers-reduced-motion.
  const frac = baseMin > 0 ? timeLeftMin / baseMin : 1
  const clockClass = boost
    ? 'doh-ttl-clock-boost'
    : frac <= TTL_COLOR.dangerFrac ? 'doh-ttl-clock-end'
      : frac <= TTL_COLOR.warnFrac ? 'doh-ttl-clock-warn'
        : undefined
  // during a boost the whole gadget recolours to the accent hue (fixed); the glow is brightness/
  // saturation lifted on that hue by the keyframe, never a hue change mid-pulse
  const tone = boost ? 'var(--color-accent)' : color
  // below the mobile breakpoint the Popover (anchored to this small button, which
  // sits at the right edge of the row) overflows the narrow viewport and is
  // cropped - present the identical control as a centered, width-capped Modal that
  // always fits the phone; desktop keeps the click Popover.
  const isMobile = useIsMobile()
  const extendBody = (
    <div style={{ width: isMobile ? '100%' : 240 }}>
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
  )
  // label stays "Extend"; disabled for the in-flight extend so it can't be re-clicked
  // mid-animation. fixed min-width keeps the flex:1 bar from jumping. on mobile the
  // button opens the Modal directly; on desktop the Popover attaches its own click.
  const triggerBtn = (
    <Button
      size="small"
      disabled={atCeiling || boost}
      style={{ minWidth: 96 }}
      title={atCeiling ? 'Already at the maximum session length' : `Add up to ${maxH}h before your lab is stopped for inactivity`}
      onClick={isMobile ? () => setOpen(true) : undefined}
    >
      Extend
    </Button>
  )
  return (
    <div className="doh-ttl" style={{ '--doh-ttl-anim': `${ANIMATION.ttlExtendMs}ms` } as CSSProperties}>
      <span className={boost ? 'doh-ttl-bar doh-ttl-boost' : 'doh-ttl-bar'} style={{ flex: 1, minWidth: 0, color: tone }} title={barTip}>
        {/* custom track+fill (not antd Progress): the track clips the fill and the boost glow so the
         * extend bloom is contained and never bleeds onto the buttons/Extend (DEF-29). width is the
         * rAF-driven displayPct while boosting (CSS transition killed), else the live pct. */}
        <span className="doh-ttl-track">
          <span className="doh-ttl-fill" style={{ width: `${boost ? displayPct : pct}%` }} />
        </span>
      </span>
      <span className={boost ? 'doh-ttl-val doh-ttl-boost' : 'doh-ttl-val'} style={{ color: tone, transition: 'color .4s ease' }}>
        <Icon name="clock" size={14} className={clockClass} />
        {/* the counter is ALWAYS an absolute remaining duration (design "Label" spec, never a
          * "+delta"); on boost it COUNTS from the current remaining up to the new remaining (rAF
          * tween on displayMin) and blurs via the pure-CSS doh-ttl-boost-num keyframe */}
        <b style={{ color: tone }}>{fmtMinutes(displayMin)}</b>
      </span>
      {uptimeLabel && (
        <span className="doh-muted" title={uptimeSince ? `up since\n${new Date(uptimeSince).toLocaleString([], { weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}` : 'Server uptime'} style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
          up {uptimeLabel}
        </span>
      )}
      {isMobile ? (
        <>
          {triggerBtn}
          <Modal
            open={open}
            onCancel={() => setOpen(false)}
            title="Extend session"
            footer={null}
            centered
            width="88%"
            style={{ maxWidth: 360 }}
          >
            {extendBody}
          </Modal>
        </>
      ) : (
        <Popover
          open={open}
          onOpenChange={setOpen}
          trigger="click"
          title="Extend session"
          content={extendBody}
        >
          {triggerBtn}
        </Popover>
      )}
    </div>
  )
}
