/* Per-user volume reset: the checkbox table + "Reset selected" action, shared by
 * the dedicated Manage-volumes page and the Configure-user Volumes tab. Reset is
 * gated on the server being stopped (the backend also rejects while running);
 * server state is resolved from the live servers list by username. */
import { useState } from 'react'
import { Button, Table } from 'antd'
import { Notice } from './Notice'
import { useServers, useUserVolumes } from '../hooks/queries'
import { resetVolumes } from '../services/ops'
import type { Volume } from '../services/types'

export function VolumeReset({ name }: { name: string }) {
  const { data: volumes = [] } = useUserVolumes(name)
  const { data: servers = [] } = useServers()
  const [selected, setSelected] = useState<string[]>([])
  const [busy, setBusy] = useState(false)

  const row = servers.find((s) => s.user === name)
  const running = !!row && (row.status === 'active' || row.status === 'idle' || row.status === 'spawning')

  const doReset = async () => {
    if (running || !selected.length || busy) return
    setBusy(true)
    try {
      await resetVolumes(name, selected)
      setSelected([])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <Notice type={running ? 'warning' : 'info'}>
        {running ? 'Stop the server before resetting volumes.' : 'Select volumes to reset - this permanently deletes their contents.'}
      </Notice>
      <Table<Volume>
        rowKey="suffix"
        style={{ marginTop: 12 }}
        pagination={false}
        rowSelection={{ type: 'checkbox', selectedRowKeys: selected, onChange: (keys) => setSelected(keys as string[]), getCheckboxProps: () => ({ disabled: running }) }}
        dataSource={volumes}
        columns={[
          { title: 'Volume', dataIndex: 'name', render: (v) => <span className="oh-mono">{v}</span> },
          { title: 'Mount', dataIndex: 'mount', render: (v) => <span className="oh-mono">{v}</span> },
          { title: 'Description', dataIndex: 'description', render: (v) => <span className="oh-muted">{v}</span> },
          { title: 'Size', dataIndex: 'sizeGB', align: 'right', render: (v) => (v == null ? <span className="oh-muted">-</span> : <span className="oh-num">{v} GB</span>) },
        ]}
      />
      <div style={{ marginTop: 12 }}>
        <Button danger loading={busy} disabled={running || !selected.length} onClick={doReset}>{busy ? 'Resetting…' : 'Reset selected'}</Button>
      </div>
    </div>
  )
}
