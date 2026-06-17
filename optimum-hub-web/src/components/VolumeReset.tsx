/* Per-user volume reset: the checkbox table + "Reset selected" action, shared by
 * the dedicated Manage-volumes page and the Configure-user Volumes tab. Reset is
 * gated on the server being stopped (the backend also rejects while running);
 * server state is resolved from the live servers list by username. */
import { useState } from 'react'
import { Button, Table } from 'antd'
import { Notice } from './Notice'
import { useServers, useUserVolumes, useUserVolumeSizes } from '../hooks/queries'
import { resetVolumes } from '../services/ops'
import type { Volume } from '../services/types'

export function VolumeReset({ name }: { name: string }) {
  // Names paint at once (fast /manage-volumes); sizes arrive separately (slow
  // /activity) and merge in, so the panel is never blank waiting on sizes.
  const { data: volumes = [], isPending: namesPending } = useUserVolumes(name)
  const { data: sizes, isPending: sizesPending } = useUserVolumeSizes(name)
  const { data: servers = [] } = useServers()
  const [selected, setSelected] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<string[] | null>(null)

  const row = servers.find((s) => s.user === name)
  const running = !!row && (row.status === 'active' || row.status === 'idle' || row.status === 'spawning')

  const doReset = async () => {
    if (running || !selected.length || busy) return
    setBusy(true)
    const resetNames = volumes.filter((v) => selected.includes(v.suffix)).map((v) => v.name)
    try {
      await resetVolumes(name, selected)
      setDone(resetNames) // report what was reset; offer Close
      setSelected([])
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <div>
        <Notice type="success">
          Reset {done.length} volume{done.length === 1 ? '' : 's'} for <b>{name}</b>. Deleted the contents of <span className="oh-mono">{done.join(', ')}</span>.
        </Notice>
        <div style={{ marginTop: 12 }}>
          <Button onClick={() => setDone(null)}>Close</Button>
        </div>
      </div>
    )
  }

  const rows: Volume[] = volumes.map((v) => ({ ...v, sizeGB: sizes?.[v.suffix] }))

  return (
    <div>
      <Notice type={running ? 'warning' : 'info'}>
        {running ? 'Stop the server before resetting volumes.' : 'Select volumes to reset - this permanently deletes their contents.'}
      </Notice>
      <Table<Volume>
        rowKey="suffix"
        style={{ marginTop: 12 }}
        pagination={false}
        loading={namesPending}
        rowSelection={{ type: 'checkbox', selectedRowKeys: selected, onChange: (keys) => setSelected(keys as string[]), getCheckboxProps: () => ({ disabled: running }) }}
        dataSource={rows}
        columns={[
          { title: 'Volume', dataIndex: 'name', render: (v) => <span className="oh-mono">{v}</span> },
          { title: 'Mount', dataIndex: 'mount', render: (v) => <span className="oh-mono">{v}</span> },
          { title: 'Description', dataIndex: 'description', render: (v) => <span className="oh-muted">{v}</span> },
          { title: 'Size', dataIndex: 'sizeGB', align: 'right', render: (v) => (v != null ? <span className="oh-num">{v} GB</span> : sizesPending ? <span className="oh-muted">updating…</span> : <span className="oh-muted">-</span>) },
        ]}
      />
      <div style={{ marginTop: 12 }}>
        <Button danger loading={busy} disabled={running || !selected.length} onClick={doReset}>{busy ? 'Resetting…' : 'Reset selected'}</Button>
      </div>
    </div>
  )
}
