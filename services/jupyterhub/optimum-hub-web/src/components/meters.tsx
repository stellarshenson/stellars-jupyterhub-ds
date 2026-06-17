/* Visual-metaphor primitives: the activity meter, the proportional spark bar, the
 * resource bars, and the TTL gadget. Each carries the precise value in a tooltip,
 * never inline (per the design language). */
import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { Button, Popover, Progress, Slider } from 'antd'
import { Icon } from './Icon'
import { fmtMinutes } from '../lib/format'
import { THRESHOLDS, ANIMATION } from '../services/config'
import { gpuSupported } from '../app/capabilities'
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
// the uncapped `pct` (when supplied) so >100% is visible. Colour: low/mid/high.
export function ActivityMeter({ value, hours, pct, title }: { value: number | null; hours?: number | null; pct?: number | null; title?: string }) {
  if (value == null) return <span className="oh-muted">-</span>
  const lit = Math.max(0, Math.min(5, Math.round(value / 20)))
  const tone = value < 25 ? 'low' : value < 60 ? 'idle' : ''
  return (
    <span className={`oh-meter ${tone}`} title={title ?? activityTitle(pct ?? value, hours)}>
      {[0, 1, 2, 3, 4].map((i) => (
        <i key={i} className={i < lit ? 'on' : ''} />
      ))}
    </span>
  )
}

// 5-segment meter stretched to fill a row (resource panels).
export function ActivityMeterFill({ value, hours, pct, title }: { value: number; hours?: number | null; pct?: number | null; title?: string }) {
  const lit = Math.max(0, Math.min(5, Math.round(value / 20)))
  const tone = value < 25 ? 'low' : value < 60 ? 'idle' : ''
  return (
    <span className={`oh-meter fill ${tone}`} title={title ?? activityTitle(pct ?? value, hours)}>
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
    <div className="oh-spark" style={{ height, ...style }} title={title}>
      {segments.map((s, i) => (
        <span key={i} style={{ width: typeof s.width === 'number' ? `${s.width}%` : s.width, background: s.color }} />
      ))}
    </div>
  )
}

// the bar fill is the standard accent on every device; only the diagonal stripe
// tint shifts per device, so one GPU reads just a tad different from the next
const GPU_STRIPES = [
  'rgba(255, 255, 255, .38)',
  'rgba(86, 222, 110, .6)',
  'rgba(184, 132, 255, .62)',
  'rgba(255, 190, 84, .62)',
]

// per-GPU bars: one labelled horizontal bar per device, fill width = its load.
// The index labels make it read unmistakably as N separate GPUs. When device
// metadata is supplied the tooltip names the GPU and quotes its live load.
export function GpuMeter({ gpus, devices }: { gpus: number[]; devices?: GpuDevice[] }) {
  return (
    <span className="oh-gpurows">
      {gpus.map((g, i) => {
        const d = devices?.[i]
        return (
          <span className="oh-gpurow" key={i} title={gpuTip(d, g, i)}>
            <small>{d ? shortGpuName(d.name) : `GPU ${i}`}</small>
            <span className="track">
              <i
                style={{
                  width: `${Math.max(3, g)}%`,
                  backgroundImage: `repeating-linear-gradient(45deg, ${GPU_STRIPES[i % GPU_STRIPES.length]} 0 3px, transparent 3px 7px)`,
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
  gpuDevices?: GpuDevice[] // real inventory - rendered as device chips when utilisation is absent
  meter?: ReactNode // override the bar (e.g. an activity meter)
}

// Resource-bar fill colour: the calm accent up to the 50% mark, then a gradual
// ramp accent -> warning -> danger so a bar only starts "warning" as it fills
// past half. color-mix keeps the shift smooth and reuses the design tokens (no
// hardcoded RGB). Returns undefined at <=50% so the CSS default accent applies.
export function barColor(pct: number): string | undefined {
  if (pct <= 50) return undefined
  if (pct <= 75) {
    const k = Math.round(((pct - 50) / 25) * 100) // 0 -> 100 across 50..75%
    return `color-mix(in srgb, var(--color-warning) ${k}%, var(--color-accent))`
  }
  const k = Math.round(((pct - 75) / 25) * 100) // 0 -> 100 across 75..100%
  return `color-mix(in srgb, var(--color-danger) ${k}%, var(--color-warning))`
}

export function ResourceBars({ rows }: { rows: ResourceRow[] }) {
  // Hide every GPU row when the platform has no GPU (no sidecar / none detected),
  // rather than rendering a "none"/empty GPU bar.
  const visible = gpuSupported() ? rows : rows.filter((r) => r.gpus === undefined && r.gpuDevices === undefined)
  return (
    <div className="oh-res">
      {visible.map((r) => {
        const utils = r.gpus // per-GPU utilisation (when sampled)
        const devices = r.gpuDevices // real inventory (when utilisation is not sampled)
        const isGpuRow = utils !== undefined || devices !== undefined
        const n = utils?.length ?? devices?.length ?? 0
        const invOnly = utils === undefined && devices !== undefined && n > 0
        const memGB = devices ? Math.round(devices.reduce((s, d) => s + (d.memoryMb || 0), 0) / 1024) : 0
        const label = isGpuRow && n ? `${n} GPU${n > 1 ? 's' : ''}` : r.label
        const bar = r.meter
          ?? (isGpuRow
            ? (n
              ? (utils ? <GpuMeter gpus={utils} devices={devices} /> : <GpuInventory devices={devices!} />)
              : <span className="oh-res-bar" title={r.tip} />)
            // the detail tooltip rides BOTH the bar and the value, so hovering the
            // progress bar itself (not only the % readout) shows the breakdown
            : <span className="oh-res-bar" title={r.tip}><i style={{ width: `${r.value}%`, background: barColor(r.value), transition: 'width .4s ease, background .4s ease' }} /></span>)
        const val = r.valueLabel
          ?? (r.meter ? '' : isGpuRow ? (n ? (invOnly && memGB ? `${memGB} GB` : '') : '-') : `${r.value}%`)
        return (
          <div className="oh-res-row" key={r.label}>
            <span className="oh-res-label">{label}</span>
            {bar}
            <span className="oh-res-val" title={r.tip}>{val}</span>
          </div>
        )
      })}
    </div>
  )
}

// idle-session timer: a standard progress bar that reads 100% (blue) when time
// is ample and drains down, shifting blue -> orange -> red as the cull nears; the
// used-up remainder shows as the gray trail. The whole gadget spans the row
// (bar + time + Extend). Extend opens an hours slider whose last tick is "max",
// which tops the session up to the configured ceiling (old-JupyterHub style).
export function TtlGadget({ timeLeftMin, baseMin, maxAddHours = 0, uptimeLabel, onExtend }: { timeLeftMin: number; baseMin: number; maxAddHours?: number; uptimeLabel?: string; onExtend?: (hours: number) => void | Promise<unknown> }) {
  // Measure remaining against the BASE timeout, not the extension ceiling, so a
  // fresh session reads ~100% and drains; an extended session caps at 100%.
  const pct = baseMin ? Math.min(100, Math.round((timeLeftMin / baseMin) * 100)) : 0
  const warn = THRESHOLDS.timeLeftWarnMin
  const color = timeLeftMin <= warn / 3 ? 'var(--color-danger)' : timeLeftMin <= warn ? 'var(--color-warning)' : 'var(--color-accent)'
  const maxH = Math.max(1, Math.round(maxAddHours))
  const [open, setOpen] = useState(false)
  const [hours, setHours] = useState(maxH)
  const atCeiling = maxAddHours <= 0
  // Extend animation: on click the bar fills to 100% immediately (slow CSS fill)
  // while the time text holds its old value. The boost holds - bar pinned full -
  // until the refetched timeLeftMin actually lands (a changed value), with a
  // minimum fill window so the growth is always seen and a safety cap so the boost
  // can never stick if the value never changes. Settling reveals the new time and
  // lets the bar fall to its true %. displayMin freezes the shown time during fill.
  const [boost, setBoost] = useState(false)
  const [displayMin, setDisplayMin] = useState(timeLeftMin)
  const baselineMin = useRef(timeLeftMin) // time-left captured at extend click
  const minFillDone = useRef(false)       // minimum fill window elapsed
  const valueLanded = useRef(false)       // refetch delivered a changed value
  // freeze the shown time during the boost; once it ends, track the live value
  useEffect(() => {
    if (!boost) setDisplayMin(timeLeftMin)
  }, [boost, timeLeftMin])
  // end the boost only when the new value has landed AND the fill has had time to play
  useEffect(() => {
    if (boost && timeLeftMin !== baselineMin.current) {
      valueLanded.current = true
      if (minFillDone.current) setBoost(false)
    }
  }, [boost, timeLeftMin])
  const shownPct = boost ? 100 : pct
  const apply = () => {
    setOpen(false)
    baselineMin.current = timeLeftMin
    minFillDone.current = false
    valueLanded.current = false
    setBoost(true)
    // keep the bar pinned full for at least one fill duration so the growth is seen
    window.setTimeout(() => { minFillDone.current = true; if (valueLanded.current) setBoost(false) }, ANIMATION.ttlExtendMs)
    // safety: never let the boost hang if the refetch never changes the value
    window.setTimeout(() => setBoost(false), ANIMATION.ttlExtendMs + 6000)
    // optimistic fill; if the extend request rejects, drop the boost immediately
    Promise.resolve(onExtend?.(Math.max(1, Math.min(maxH, hours)))).catch(() => setBoost(false))
  }
  // slider marks: first hour and the last tick labelled "max" (tops to ceiling)
  const marks: Record<number, ReactNode> = { 1: '1h', [maxH]: 'max' }
  const atMax = hours >= maxH
  return (
    <div className="oh-ttl">
      <span className={boost ? 'oh-ttl-bar oh-ttl-boost' : 'oh-ttl-bar'} style={{ flex: 1, minWidth: 0, '--oh-ttl-anim': `${ANIMATION.ttlExtendMs}ms` } as CSSProperties} title="Idle session timer - your server is stopped automatically when this runs out">
        <Progress percent={shownPct} showInfo={false} strokeColor={boost ? 'var(--color-accent)' : color} trailColor="var(--color-bg-subtle)" style={{ margin: 0 }} />
      </span>
      <span className="oh-ttl-val">
        <Icon name="clock" size={14} />
        <b>{fmtMinutes(displayMin)}</b>
      </span>
      {uptimeLabel && (
        <span className="oh-muted" title="Server uptime" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
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
              min={1}
              max={maxH}
              step={1}
              value={hours}
              onChange={(v) => setHours(v as number)}
              marks={marks}
              tooltip={{ formatter: (v) => (v != null && v >= maxH ? 'max' : `+${v}h`) }}
            />
            <Button size="small" type="primary" block onClick={apply} style={{ marginTop: 6 }}>
              {atMax ? 'Extend to max' : `Extend +${hours}h`}
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
