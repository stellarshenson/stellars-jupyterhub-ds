/* Dashboard metric card - value + proportional spark + coloured breakdown. The
 * whole card links to its full page (chevron, top-right). */
import type { ReactNode } from 'react'
import { Card } from 'antd'
import { Link } from 'react-router-dom'
import { Icon } from './Icon'
import type { IconKey } from './Icon'
import { Spark } from './meters'
import type { SparkSegment } from './meters'

export function MetricCard({
  icon,
  label,
  value,
  to,
  segments,
  breakdown,
}: {
  icon: IconKey
  label: string
  value: ReactNode
  to: string
  segments: SparkSegment[]
  breakdown: ReactNode
}) {
  return (
    <Link to={to} style={{ display: 'block', height: '100%' }}>
      <Card hoverable styles={{ body: { padding: 16 } }} style={{ height: '100%' }}>
        <div className="doh-m-top">
          <span className="doh-m-ic">
            <Icon name={icon} size={18} />
          </span>
          <span>{label}</span>
          <span style={{ marginLeft: 'auto', color: 'var(--color-text-subtle)', display: 'inline-flex' }}>
            <Icon name="chevron" size={16} />
          </span>
        </div>
        <div className="doh-m-val">{value}</div>
        <Spark segments={segments} />
        <div className="doh-m-break">{breakdown}</div>
      </Card>
    </Link>
  )
}
