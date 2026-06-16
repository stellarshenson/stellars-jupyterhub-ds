/* Visual-metaphor primitives: the activity meter, the proportional spark bar, the
 * resource bars, and the TTL gadget. Each carries the precise value in a tooltip,
 * never inline (per the design language). */
import type { CSSProperties, ReactNode } from 'react'
import { Button } from 'antd'
import { Icon } from './Icon'
import { fmtMinutes } from '../lib/format'
import { THRESHOLDS } from '../services/config'

// 5-segment engagement meter. Colour follows the score: low red / mid amber / high green.
export function ActivityMeter({ value, title }: { value: number | null; title?: string }) {
  if (value == null) return <span className="oh-muted">-</span>
  const lit = Math.max(0, Math.min(5, Math.round(value / 20)))
  const tone = value < 25 ? 'low' : value < 60 ? 'idle' : ''
  return (
    <span className={`oh-meter ${tone}`} title={title ?? `Activity ${value}% · 24h sampled`}>
      {[0, 1, 2, 3, 4].map((i) => (
        <i key={i} className={i < lit ? 'on' : ''} />
      ))}
    </span>
  )
}

// 5-segment meter stretched to fill a row (resource panels).
export function ActivityMeterFill({ value, title }: { value: number; title?: string }) {
  const lit = Math.max(0, Math.min(5, Math.round(value / 20)))
  const tone = value < 25 ? 'low' : value < 60 ? 'idle' : ''
  return (
    <span className={`oh-meter fill ${tone}`} title={title}>
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
// The index labels make it read unmistakably as N separate GPUs.
export function GpuMeter({ gpus }: { gpus: number[] }) {
  return (
    <span className="oh-gpurows">
      {gpus.map((g, i) => (
        <span className="oh-gpurow" key={i} title={`GPU ${i} - ${g}%`}>
          <small>{i}</small>
          <span className="track">
            <i
              style={{
                width: `${Math.max(3, g)}%`,
                backgroundImage: `repeating-linear-gradient(45deg, ${GPU_STRIPES[i % GPU_STRIPES.length]} 0 3px, transparent 3px 7px)`,
              }}
            />
          </span>
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
  gpus?: number[] // when set, render the segmented GPU meter and label the device count
  meter?: ReactNode // override the bar (e.g. an activity meter)
}

export function ResourceBars({ rows }: { rows: ResourceRow[] }) {
  return (
    <div className="oh-res">
      {rows.map((r) => {
        const hasGpus = r.gpus !== undefined
        const n = r.gpus?.length ?? 0
        const label = hasGpus && n ? `${n} GPU` : r.label
        const bar = r.meter
          ?? (hasGpus
            ? (n ? <GpuMeter gpus={r.gpus!} /> : <span className="oh-res-bar" />)
            : <span className="oh-res-bar"><i style={{ width: `${r.value}%` }} /></span>)
        const val = r.valueLabel
          ?? (r.meter ? '' : hasGpus ? (n ? '' : 'none') : `${r.value}%`)
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

// idle-session timer: progress bar + clock value + Extend. The bar is a fixed
// short length (not full-width) and shifts green -> amber -> red as time drains.
export function TtlGadget({ timeLeftMin, maxMin, onExtend }: { timeLeftMin: number; maxMin: number; onExtend?: () => void }) {
  const pct = maxMin ? Math.min(100, Math.round((timeLeftMin / maxMin) * 100)) : 0
  const warn = THRESHOLDS.timeLeftWarnMin
  const color = timeLeftMin <= warn / 3 ? 'var(--color-danger)' : timeLeftMin <= warn ? 'var(--color-warning)' : 'var(--color-success)'
  return (
    <div className="oh-ttl">
      <Spark
        height={8}
        title="Idle session timer - your server is stopped automatically when this runs out"
        segments={[{ width: pct, color }]}
        style={{ flex: 'none', width: '50%' }}
      />
      <span className="oh-ttl-val">
        <Icon name="clock" size={14} />
        <b>{fmtMinutes(timeLeftMin)}</b>
      </span>
      <Button size="small" onClick={onExtend} title="Add hours before the idle culler stops the lab">
        Extend
      </Button>
    </div>
  )
}
