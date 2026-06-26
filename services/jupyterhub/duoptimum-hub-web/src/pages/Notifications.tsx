/* Notifications - broadcast to active labs. Send (left, the composer) and past
 * notifications (right, the sent history). Outgoing only. */
import { useMemo, useState } from 'react'
import { Button, Card, Checkbox, Input, Radio, Segmented, Select, Table } from 'antd'
import { appModal } from '../services/actions'
import { PageHeader } from '../components/PageHeader'
import { Icon } from '../components/Icon'
import { NotificationPill } from '../components/NotificationPill'
import { useSentNotifications, useServers } from '../hooks/queries'
import { broadcast, clearNotifications } from '../services/ops'
import { timeAgoShort, exactDate } from '../lib/format'
import type { SentNotification } from '../services/types'

// same range control as Events.tsx; Notifications defaults to 24h (Events to 7d)
type Range = '24h' | '7d' | '30d'
const RANGE_MS: Record<Range, number> = { '24h': 864e5, '7d': 6.048e8, '30d': 2.592e9 }

// Scrollable, filterable recipient list: per-user checkboxes plus a select-all
// (scoped to the current filter) so an operator can select all, then unselect a few.
function RecipientPicker({ users, value, onChange }: { users: string[]; value: string[]; onChange: (v: string[]) => void }) {
  const [q, setQ] = useState('')
  if (!users.length) return <div className="doh-muted" style={{ fontSize: 13 }}>No active servers to notify</div>
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
    <div style={{ border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-lg)', padding: 8 }}>
      <Input size="small" allowClear placeholder="Filter users…" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginBottom: 8 }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 6, borderBottom: '1px solid var(--color-border-subtle)' }}>
        <Checkbox checked={allOn} indeterminate={someOn && !allOn} onChange={(e) => toggleAll(e.target.checked)}>
          Select all{q ? ' shown' : ''}
        </Checkbox>
        <span className="doh-muted" style={{ fontSize: 12 }}>{value.length} selected</span>
      </div>
      <div style={{ maxHeight: 200, overflowY: 'auto', marginTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {filtered.length === 0
          ? <span className="doh-muted" style={{ fontSize: 13 }}>No match</span>
          : filtered.map((u) => (
              <Checkbox key={u} checked={selected.has(u)} onChange={(e) => toggle(u, e.target.checked)}>{u}</Checkbox>
            ))}
      </div>
    </div>
  )
}

// preset auto-close durations (value = milliseconds the lab Notification API
// expects); 0 = Never, sent as autoClose:false (no auto-dismiss) and the default.
const AUTO_CLOSE_OPTIONS = [
  { label: 'Never', value: 0 },
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
  const [variant, setVariant] = useState('info')
  const [autoCloseMs, setAutoCloseMs] = useState(0) // default Never (no auto-close), user-changeable
  const [mode, setMode] = useState<'all' | 'selected'>('all')
  const [recipients, setRecipients] = useState<string[]>([])
  const [range, setRange] = useState<Range>('24h')
  const filteredHistory = useMemo(
    () => history.filter((n) => Date.now() - new Date(n.sentISO).getTime() <= RANGE_MS[range]),
    [history, range],
  )
  // clearing the persisted notification history is destructive + irreversible -> confirm first
  const clearHistory = () =>
    appModal.confirm({
      title: 'Clear the notification history?',
      content: 'This permanently deletes every recorded broadcast. This cannot be undone.',
      okText: 'Clear',
      okButtonProps: { danger: true },
      onOk: () => clearNotifications(),
    })
  const send = async () => {
    try {
      await broadcast(msg.trim(), variant, autoCloseMs === 0 ? false : autoCloseMs, mode === 'selected' ? recipients : undefined)
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
              options={['info', 'success', 'warning', 'error', 'in-progress'].map((t) => ({ label: t, value: t }))}
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

        <Card
          title="Past Notifications"
          styles={{ body: { padding: 0 } }}
          extra={
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <Segmented
                size="small"
                value={range}
                onChange={(v) => setRange(v as Range)}
                options={[
                  { label: 'Last 24h', value: '24h' },
                  { label: 'Last 7 days', value: '7d' },
                  { label: 'Last 30 days', value: '30d' },
                ]}
              />
              <Button size="small" danger icon={<Icon name="close" size={14} />} disabled={!history.length} onClick={clearHistory}>Clear</Button>
            </div>
          }
        >
          <Table<SentNotification>
            rowKey="id"
            pagination={false}
            locale={{ emptyText: 'No broadcasts sent yet' }}
            dataSource={filteredHistory}
            columns={[
              { title: 'Message', dataIndex: 'message' },
              { title: 'Type', dataIndex: 'type', width: 120, render: (v) => <NotificationPill type={v} /> },
              { title: 'Delivered', dataIndex: 'delivered', align: 'right', width: 100, render: (_, n) => <span className="doh-num">{n.delivered}/{n.total}</span> },
              { title: 'Sent', dataIndex: 'sentISO', align: 'right', width: 120, render: (v) => <span className="doh-muted" title={exactDate(v)}>{timeAgoShort(v)}</span> },
            ]}
          />
        </Card>
      </div>
    </>
  )
}
