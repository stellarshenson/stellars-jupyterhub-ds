/* Visual-metaphor primitives: the activity meter, the proportional spark bar, the
 * resource bars, and the TTL gadget. Each carries the precise value in a tooltip,
 * never inline (per the design language). */
import { useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { Button, Popover, Progress, Slider } from 'antd'
import { Icon } from './Icon'
import { fmtMinutes } from '../lib/format'
import { THRESHOLDS } from '../services/config'
import { gpuSupported } from '../app/capabilities'
import type { GpuDevice } from '../services/types'

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
// The index labels make it read unmistakably as N separate GPUs. When device
// metadata is supplied the tooltip names the GPU and quotes its live load.
export function GpuMeter({ gpus, devices }: { gpus: number[]; devices?: GpuDevice[] }) {
  return (
    <span className="oh-gpurows">
      {gpus.map((g, i) => {
        const d = devices?.[i]
        const tip = d ? `GPU ${d.index} ${shortGpuName(d.name)} - ${g}%` : `GPU ${i} - ${g}%`
        return (
          <span className="oh-gpurow" key={i} title={tip}>
            <small>{d?.index ?? i}</small>
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
function shortGpuName(name: string): string {
  return name.replace(/^NVIDIA\s+/i, '')
}

export function GpuInventory({ devices }: { devices: GpuDevice[] }) {
  return (
    <span style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {devices.map((d) => (
        <span
          key={d.index}
          title={`GPU ${d.index} - ${d.name}${d.memoryMb ? ` · ${Math.round(d.memoryMb / 1024)} GB` : ''}`}
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
              : <span className="oh-res-bar" />)
            : <span className="oh-res-bar"><i style={{ width: `${r.value}%` }} /></span>)
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
export function TtlGadget({ timeLeftMin, baseMin, maxAddHours = 0, onExtend }: { timeLeftMin: number; baseMin: number; maxAddHours?: number; onExtend?: (hours: number) => void }) {
  // Measure remaining against the BASE timeout, not the extension ceiling, so a
  // fresh session reads ~100% and drains; an extended session caps at 100%.
  const pct = baseMin ? Math.min(100, Math.round((timeLeftMin / baseMin) * 100)) : 0
  const warn = THRESHOLDS.timeLeftWarnMin
  const color = timeLeftMin <= warn / 3 ? 'var(--color-danger)' : timeLeftMin <= warn ? 'var(--color-warning)' : 'var(--color-accent)'
  const maxH = Math.max(1, Math.round(maxAddHours))
  const [open, setOpen] = useState(false)
  const [hours, setHours] = useState(maxH)
  const atCeiling = maxAddHours <= 0
  const apply = () => {
    setOpen(false)
    onExtend?.(Math.max(1, Math.min(maxH, hours)))
  }
  // slider marks: first hour and the last tick labelled "max" (tops to ceiling)
  const marks: Record<number, ReactNode> = { 1: '1h', [maxH]: 'max' }
  const atMax = hours >= maxH
  return (
    <div className="oh-ttl">
      <span style={{ flex: 1, minWidth: 0 }} title="Idle session timer - your server is stopped automatically when this runs out">
        <Progress percent={pct} showInfo={false} strokeColor={color} trailColor="var(--color-bg-subtle)" style={{ margin: 0 }} />
      </span>
      <span className="oh-ttl-val">
        <Icon name="clock" size={14} />
        <b>{fmtMinutes(timeLeftMin)}</b>
      </span>
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
        <Button size="small" disabled={atCeiling} title={atCeiling ? 'Already at the maximum session length' : `Add up to ${maxH}h before the idle culler stops the lab`}>
          Extend
        </Button>
      </Popover>
    </div>
  )
}
