/* Visual-metaphor primitives: the activity meter, the proportional spark bar, the
 * resource bars, and the TTL gadget. Each carries the precise value in a tooltip,
 * never inline (per the design language). */
import type { CSSProperties, ReactNode } from 'react'
import { Button } from 'antd'
import { Icon } from './Icon'
import { fmtMinutes } from '../lib/format'

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

export interface ResourceRow {
  label: string
  value: number
  valueLabel?: string
  tip?: string
  meter?: ReactNode // override the bar (e.g. an activity meter)
}

export function ResourceBars({ rows }: { rows: ResourceRow[] }) {
  return (
    <div className="oh-res">
      {rows.map((r) => (
        <div className="oh-res-row" key={r.label}>
          <span className="oh-res-label">{r.label}</span>
          {r.meter ?? (
            <span className="oh-res-bar">
              <i style={{ width: `${r.value}%` }} />
            </span>
          )}
          <span className="oh-res-val" title={r.tip}>
            {r.valueLabel ?? (r.meter ? '' : `${r.value}%`)}
          </span>
        </div>
      ))}
    </div>
  )
}

// idle-session timer: progress bar + clock value + Extend
export function TtlGadget({ timeLeftMin, maxMin, onExtend }: { timeLeftMin: number; maxMin: number; onExtend?: () => void }) {
  const pct = maxMin ? Math.min(100, Math.round((timeLeftMin / maxMin) * 100)) : 0
  return (
    <div className="oh-ttl">
      <Spark
        height={8}
        title="Idle session timer - your server is stopped automatically when this runs out"
        segments={[{ width: pct, color: 'var(--color-success)' }]}
        style={{ flex: 1 }}
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
