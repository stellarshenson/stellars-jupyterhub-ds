/* Notifications - broadcast to active labs. Send (left, the composer) and past
 * notifications (right, the sent history). Outgoing only. */
import { useState } from 'react'
import { Button, Card, Checkbox, Input, Radio, Segmented, Select, Table } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { Icon } from '../components/Icon'
import { NotificationPill } from '../components/NotificationPill'
import { useSentNotifications, useServers } from '../hooks/queries'
import { broadcast } from '../services/ops'
import { timeAgoShort, exactDate } from '../lib/format'
import type { SentNotification } from '../services/types'

// Scrollable, filterable recipient list: per-user checkboxes plus a select-all
// (scoped to the current filter) so an operator can select all, then unselect a few.
function RecipientPicker({ users, value, onChange }: { users: string[]; value: string[]; onChange: (v: string[]) => void }) {
  const [q, setQ] = useState('')
  if (!users.length) return <div className="oh-muted" style={{ fontSize: 13 }}>No active servers to notify</div>
  const filtered = users.filter((u) => u.toLowerCase().includes(q.toLowerCase()))
  const selected = new Set(value)
  const allOn = filtered.length > 0 && filtered.every((u) => selected.has(u))
  const someOn = filtered.some((u) => selected.has(u))
  const toggle = (u: string, on: boolean) => {
    const next = new Set(value)
    if (on) next.add(u)
    else next.delete(u)
    onChange([...next])
  }
  const toggleAll = (on: boolean) => {
    const next = new Set(value)
    filtered.forEach((u) => {
      if (on) next.add(u)
      else next.delete(u)
    })
    onChange([...next])
  }
  return (
    <div style={{ border: '1px solid var(--color-border-subtle)', borderRadius: 8, padding: 8 }}>
      <Input size="small" allowClear placeholder="Filter users…" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginBottom: 8 }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 6, borderBottom: '1px solid var(--color-border-subtle)' }}>
        <Checkbox checked={allOn} indeterminate={someOn && !allOn} onChange={(e) => toggleAll(e.target.checked)}>
          Select all{q ? ' shown' : ''}
        </Checkbox>
        <span className="oh-muted" style={{ fontSize: 12 }}>{value.length} selected</span>
      </div>
      <div style={{ maxHeight: 200, overflowY: 'auto', marginTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {filtered.length === 0
          ? <span className="oh-muted" style={{ fontSize: 13 }}>No match</span>
          : filtered.map((u) => (
              <Checkbox key={u} checked={selected.has(u)} onChange={(e) => toggle(u, e.target.checked)}>{u}</Checkbox>
            ))}
      </div>
    </div>
  )
}

// preset auto-close durations (value = milliseconds, what the lab Notification API
// expects); 30s is the default. The user picks one before sending.
const AUTO_CLOSE_OPTIONS = [
  { label: '30s', value: 30000 },
  { label: '1min', value: 60000 },
  { label: '10min', value: 600000 },
  { label: '30min', value: 1800000 },
  { label: '1h', value: 3600000 },
]

export default function Notifications() {
  const { data: history = [] } = useSentNotifications()
  const { data: servers = [] } = useServers()
  // only READY servers can receive a broadcast (a spawning lab has no extension
  // to ingest it yet -> selecting it would guarantee a delivery failure)
  const activeUsers = servers.filter((s) => s.status === 'active' || s.status === 'idle').map((s) => s.user)
  const [msg, setMsg] = useState('')
  const [variant, setVariant] = useState('default')
  const [autoCloseMs, setAutoCloseMs] = useState(30000) // default 30s, user-changeable
  const [mode, setMode] = useState<'all' | 'selected'>('all')
  const [recipients, setRecipients] = useState<string[]>([])
  const send = async () => {
    try {
      await broadcast(msg.trim(), variant, autoCloseMs, mode === 'selected' ? recipients : undefined)
      setMsg('')
    } catch {
      /* ops surfaced the error */
    }
  }

  return (
    <>
      <PageHeader title="Notifications" sub="Broadcast a message to every active lab - outgoing only" />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: 16, alignItems: 'start' }}>
        <Card title="Send">
          <div style={{ marginBottom: 8, color: 'var(--color-text-muted)', fontSize: 13 }}>Message</div>
          <Input.TextArea rows={3} maxLength={140} showCount value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Keep it short - 140 characters" />
          <div style={{ marginTop: 12, display: 'flex', gap: 12, alignItems: 'center' }}>
            <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>Type</span>
            <Select
              value={variant}
              onChange={setVariant}
              style={{ width: 160 }}
              options={['default', 'info', 'success', 'warning', 'error', 'in-progress'].map((t) => ({ label: t, value: t }))}
            />
          </div>
          <div style={{ marginTop: 12, display: 'flex', gap: 12, alignItems: 'center' }}>
            <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>Auto-close</span>
            <Segmented
              size="small"
              value={autoCloseMs}
              onChange={(v) => setAutoCloseMs(v as number)}
              options={AUTO_CLOSE_OPTIONS}
            />
          </div>
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 6 }}>Recipients</div>
            <Radio.Group value={mode} onChange={(e) => setMode(e.target.value)}>
              <Radio value="all">All active servers</Radio>
              <Radio value="selected">Selected users</Radio>
            </Radio.Group>
            {mode === 'selected' && (
              <div style={{ marginTop: 8 }}>
                <RecipientPicker users={activeUsers} value={recipients} onChange={setRecipients} />
              </div>
            )}
          </div>
          <div style={{ marginTop: 16 }}>
            <Button type="primary" icon={<Icon name="megaphone" size={14} />} disabled={!msg.trim() || (mode === 'selected' && recipients.length === 0)} onClick={send}>
              Send Broadcast
            </Button>
          </div>
        </Card>

        <Card title="Past Notifications" styles={{ body: { padding: 0 } }}>
          <Table<SentNotification>
            rowKey="id"
            pagination={false}
            locale={{ emptyText: 'No broadcasts sent yet' }}
            dataSource={history}
            columns={[
              { title: 'Message', dataIndex: 'message' },
              { title: 'Type', dataIndex: 'type', width: 120, render: (v) => <NotificationPill type={v} /> },
              { title: 'Delivered', dataIndex: 'delivered', align: 'right', width: 100, render: (_, n) => <span className="oh-num">{n.delivered}/{n.total}</span> },
              { title: 'Sent', dataIndex: 'sentISO', align: 'right', width: 120, render: (v) => <span className="oh-muted" title={exactDate(v)}>{timeAgoShort(v)}</span> },
            ]}
          />
        </Card>
      </div>
    </>
  )
}
