/* Per-user volume reset: the checkbox table + "Reset selected" action, shared by
 * the dedicated Manage-volumes page and the Configure-user Volumes tab. Reset is
 * gated on the server being stopped (the backend also rejects while running);
 * server state is resolved from the live servers list by username. After a reset
 * the screen STAYS put - the removed rows are marked "removed" in red and become
 * non-selectable, rather than switching to a separate confirmation view. */
import { useState } from 'react'
import { Button, Table } from 'antd'
import { Notice } from './Notice'
import { FormFooter } from './FormFooter'
import { useServers, useUserVolumes, useUserVolumeSizes } from '../hooks/queries'
import { resetVolumes } from '../services/ops'
import type { Volume } from '../services/types'

// onClose lets the parent decide where Close goes - the dedicated Manage-volumes
// PAGE returns to its parent screen, the Configure-user tab just dismisses.
export function VolumeReset({ name, onClose }: { name: string; onClose?: () => void }) {
  // Names paint at once (fast /manage-volumes); sizes arrive separately (slow
  // /activity) and merge in, so the panel is never blank waiting on sizes.
  const { data: volumes = [], isPending: namesPending } = useUserVolumes(name)
  const { data: sizes, isPending: sizesPending } = useUserVolumeSizes(name)
  const { data: servers = [] } = useServers()
  const [selected, setSelected] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  // suffixes already removed this session - marked "removed" in place (same
  // screen), never re-selectable; no separate done view.
  const [removed, setRemoved] = useState<string[]>([])

  const row = servers.find((s) => s.user === name)
  const running = !!row && (row.status === 'active' || row.status === 'idle' || row.status === 'spawning')

  const doReset = async () => {
    if (running || !selected.length || busy) return
    setBusy(true)
    try {
      await resetVolumes(name, selected)
      setRemoved((prev) => [...prev, ...selected]) // mark in place; stay on screen
      setSelected([])
    } finally {
      setBusy(false)
    }
  }

  const rows: Volume[] = volumes.map((v) => ({ ...v, sizeGB: sizes?.[v.suffix] }))
  const resetBtn = (
    <Button danger loading={busy} disabled={running || !selected.length} onClick={doReset}>{busy ? 'Resetting…' : 'Reset Selected'}</Button>
  )

  return (
    <div>
      <Notice type="warning">
        {running
          ? 'Stop the server before resetting volumes.'
          : 'Removing volumes is irreversible - the selected volumes and all their contents are permanently deleted.'}
      </Notice>
      <Table<Volume>
        rowKey="suffix"
        style={{ marginTop: 12 }}
        pagination={false}
        loading={namesPending}
        rowSelection={{ type: 'checkbox', selectedRowKeys: selected, onChange: (keys) => setSelected(keys as string[]), getCheckboxProps: (record) => ({ disabled: running || removed.includes(record.suffix) }) }}
        dataSource={rows}
        columns={[
          { title: 'Volume', dataIndex: 'name', render: (v) => <span className="doh-mono">{v}</span> },
          { title: 'Mount', dataIndex: 'mount', render: (v) => <span className="doh-mono">{v}</span> },
          { title: 'Description', dataIndex: 'description', render: (v) => <span className="doh-muted">{v}</span> },
          {
            title: 'Size',
            dataIndex: 'sizeGB',
            align: 'right',
            // a removed volume reads "removed" in dangerous (red) text in place;
            // otherwise the size (or the slow-sizes placeholder)
            render: (v, record) =>
              removed.includes(record.suffix)
                ? <span className="doh-text-danger">removed</span>
                : v != null ? <span className="doh-num">{v} GB</span> : sizesPending ? <span className="doh-muted">updating…</span> : <span className="doh-muted">-</span>,
          },
        ]}
      />
      {onClose ? (
        // page mode (dedicated Manage-volumes screen): standard config footer -
        // Reset (destructive, left), Cancel + Done (right) both return to origin
        <FormFooter destructive={resetBtn} onCancel={onClose} onSave={onClose} saveLabel="Done" />
      ) : (
        // tab mode (Configure-user Volumes tab): just the reset action; the
        // Configure-user screen owns the Cancel / Save footer
        <div style={{ marginTop: 12 }}>{resetBtn}</div>
      )}
    </div>
  )
}
