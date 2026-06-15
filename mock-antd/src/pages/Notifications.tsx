/* Notifications - broadcast to active labs. Send (left, the composer) and past
 * notifications (right, the sent history). Outgoing only. */
import { useState } from 'react'
import { Button, Card, Input, Radio, Select, Switch, Table } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { Icon } from '../components/Icon'
import { useSentNotifications } from '../hooks/queries'
import { mockSuccess } from '../services/actions'
import { timeAgo, exactDate } from '../lib/format'
import type { SentNotification } from '../services/types'

const TYPE_COLORS: Record<string, string> = {
  info: 'var(--color-info)', success: 'var(--color-success)', warning: 'var(--color-warning)',
  error: 'var(--color-danger)', default: 'var(--color-text-muted)', 'in-progress': 'var(--color-accent)',
}

export default function Notifications() {
  const { data: history = [] } = useSentNotifications()
  const [msg, setMsg] = useState('')

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
              defaultValue="default"
              style={{ width: 160 }}
              options={['default', 'info', 'success', 'warning', 'error', 'in-progress'].map((t) => ({ label: t, value: t }))}
            />
          </div>
          <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
            <Switch size="small" /> <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>Auto-close</span>
          </div>
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 6 }}>Recipients</div>
            <Radio.Group defaultValue="all">
              <Radio value="all">All active servers</Radio>
              <Radio value="selected">Selected users</Radio>
            </Radio.Group>
          </div>
          <div style={{ marginTop: 16 }}>
            <Button type="primary" icon={<Icon name="megaphone" size={14} />} disabled={!msg.trim()} onClick={() => { mockSuccess('Broadcast sent to 18 active servers'); setMsg('') }}>
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
              { title: 'Type', dataIndex: 'type', width: 110, render: (v) => <span style={{ color: TYPE_COLORS[v] }}>{v}</span> },
              { title: 'Delivered', dataIndex: 'delivered', align: 'right', width: 100, render: (_, n) => <span className="oh-num">{n.delivered}/{n.total}</span> },
              { title: 'Sent', dataIndex: 'sentISO', align: 'right', width: 120, render: (v) => <span className="oh-muted" title={exactDate(v)}>{timeAgo(v)}</span> },
            ]}
          />
        </Card>
      </div>
    </>
  )
}
