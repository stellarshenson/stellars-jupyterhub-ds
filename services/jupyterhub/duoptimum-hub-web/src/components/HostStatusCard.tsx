/* Host Status card - aggregate host CPU / Memory / GPU bars. Rows gated on the
 * provider's declared capabilities (total.caps); absent caps default to shown,
 * GPU also needs real data (matches ServerHero). Renders the titled card while
 * loading (total not in yet); returns null once loaded with an empty capability
 * set. Shared by the desktop admin dashboard and the mobile admin surface. */
import type { CSSProperties } from 'react'
import { Card } from 'antd'
import { ResourceBars } from './meters'
import { usePref } from '../app/PrefsContext'
import { useTotalResources } from '../hooks/queries'

export function HostStatusCard({ style }: { style?: CSSProperties }) {
  const { data: total } = useTotalResources()
  const hostCpuMode = usePref('cpuModeHostStatus') // 'cores' = summed cores-used label; bar fill unchanged
  const hostRows = total
    ? [
        ...(total.caps?.cpu !== false
          ? [{ label: 'CPU', value: total.cpu, valueLabel: hostCpuMode === 'cores' && total.cpuAggregateLabel ? total.cpuAggregateLabel : `${total.cpu}%`, tip: total.cpuTip, error: total.cpuError }]
          : []),
        ...(total.caps?.mem !== false
          ? [{ label: 'Memory', value: total.mem, tip: total.memTip, error: total.memError }]
          : []),
        ...(total.caps?.gpu !== false && (total.gpus !== undefined || total.gpuDevices !== undefined)
          ? [{ label: 'GPU', value: total.gpu, gpus: total.gpus, gpuDevices: total.gpuDevices }]
          : []),
      ]
    : []
  if (total && hostRows.length === 0) return null
  return (
    <Card style={style}>
      <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>Host Status</h3>
      {total && <ResourceBars rows={hostRows} />}
    </Card>
  )
}
