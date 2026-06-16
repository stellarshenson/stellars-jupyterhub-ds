/* Notifications - broadcast to active labs. Send (left, the composer) and past
 * notifications (right, the sent history). Outgoing only. */
import { useState } from 'react'
import { Button, Card, Input, Radio, Select, Switch, Table } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { Icon } from '../components/Icon'
import { Combo } from '../components/Combo'
import { useSentNotifications, useServers } from '../hooks/queries'
import { broadcast } from '../services/ops'
import { timeAgoShort, exactDate } from '../lib/format'
import type { SentNotification } from '../services/types'

// notification type -> status-pill tone (same coloured-pill vocabulary as the rest)
const TYPE_PILL: Record<string, string> = {
  info: 'spawning', success: 'running', warning: 'idle', error: 'error', default: 'stopped', 'in-progress': 'accent',
}

export default function Notifications() {
  const { data: history = [] } = useSentNotifications()
  const { data: servers = [] } = useServers()
  const activeUsers = servers.filter((s) => s.status !== 'offline' && s.status !== 'error').map((s) => s.user)
  const [msg, setMsg] = useState('')
  const [variant, setVariant] = useState('default')
  const [autoClose, setAutoClose] = useState(false)
  const [mode, setMode] = useState<'all' | 'selected'>('all')
  const [recipients, setRecipients] = useState<string[]>([])
  const send = async () => {
    try {
      await broadcast(msg.trim(), variant, autoClose, mode === 'selected' ? recipients : undefined)
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
          <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
            <Switch size="small" checked={autoClose} onChange={setAutoClose} /> <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>Auto-close</span>
          </div>
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 6 }}>Recipients</div>
            <Radio.Group value={mode} onChange={(e) => setMode(e.target.value)}>
              <Radio value="all">All active servers</Radio>
              <Radio value="selected">Selected users</Radio>
            </Radio.Group>
            {mode === 'selected' && (
              <div style={{ marginTop: 8 }}>
                <Combo corpus={activeUsers} value={recipients} onChange={setRecipients} placeholder="Add an active user…" />
              </div>
            )}
          </div>
          <div style={{ marginTop: 16 }}>
            <Button type="primary" icon={<Icon name="megaphone" size={14} />} disabled={!msg.trim() || (mode === 'selected' && recipients.length === 0)} onClick={send}>
              Send broadcast
            </Button>
          </div>
        </Card>

        <Card title="Past notifications" styles={{ body: { padding: 0 } }}>
          <Table<SentNotification>
            rowKey="id"
            pagination={false}
            dataSource={history}
            columns={[
              { title: 'Message', dataIndex: 'message' },
              { title: 'Type', dataIndex: 'type', width: 120, render: (v) => <span className={`oh-pill ${TYPE_PILL[v] ?? 'stopped'}`}>{v}</span> },
              { title: 'Delivered', dataIndex: 'delivered', align: 'right', width: 100, render: (_, n) => <span className="oh-num">{n.delivered}/{n.total}</span> },
              { title: 'Sent', dataIndex: 'sentISO', align: 'right', width: 120, render: (v) => <span className="oh-muted" title={exactDate(v)}>{timeAgoShort(v)}</span> },
            ]}
          />
        </Card>
      </div>
    </>
  )
}
