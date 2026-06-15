/* Events - the audit timeline behind the Overview feed. Scaled list: type scope
 * pills, search, pager. */
import { useMemo, useState } from 'react'
import { ProTable } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { Input } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { ScopeFilterPills } from '../components/ScopeFilterPills'
import { Icon } from '../components/Icon'
import { useEvents } from '../hooks/queries'
import { timeAgo, exactDate } from '../lib/format'
import type { EventRow, EventType } from '../services/types'

const TYPE_TONE: Record<EventType, 'ok' | 'warn' | 'grey' | 'accent' | 'danger'> = {
  server: 'ok',
  user: 'accent',
  group: 'accent',
  policy: 'warn',
  broadcast: 'accent',
  cull: 'danger',
}

export default function Events() {
  const { data = [], isLoading } = useEvents()
  const [scope, setScope] = useState('all')
  const [q, setQ] = useState('')

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    data.forEach((e) => (c[e.type] = (c[e.type] ?? 0) + 1))
    return c
  }, [data])

  const filtered = useMemo(
    () => data.filter((e) => (scope === 'all' || e.type === scope) && e.text.toLowerCase().includes(q.toLowerCase())),
    [data, scope, q],
  )

  const columns: ProColumns<EventRow>[] = [
    {
      title: 'Event',
      dataIndex: 'text',
      render: (_, e) => (
        <div className="oh-row">
          <span className="oh-feed-ic">
            <Icon name={e.icon as 'play'} size={15} />
          </span>
          <span dangerouslySetInnerHTML={{ __html: e.text }} />
        </div>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      width: 120,
      render: (_, e) => <span className={`oh-pill ${TYPE_TONE[e.type] === 'danger' ? 'error' : TYPE_TONE[e.type] === 'warn' ? 'idle' : 'accent'}`}>{e.type}</span>,
    },
    {
      title: 'When',
      dataIndex: 'whenISO',
      width: 160,
      align: 'right',
      sorter: (a, b) => b.whenISO.localeCompare(a.whenISO),
      render: (_, e) => <span title={exactDate(e.whenISO)} className="oh-muted">{timeAgo(e.whenISO)}</span>,
    },
  ]

  return (
    <>
      <PageHeader title="Events" sub="An audit timeline of platform actions - who did what, and when" />
      <ProTable<EventRow>
        rowKey="id"
        columns={columns}
        dataSource={filtered}
        loading={isLoading}
        search={false}
        options={false}
        rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
        pagination={{ pageSize: 12, showSizeChanger: false }}
        headerTitle={
          <ScopeFilterPills
            value={scope}
            onChange={setScope}
            scopes={[
              { key: 'all', label: 'All', count: data.length, tone: 'accent' },
              { key: 'server', label: 'Server', count: counts.server, tone: 'ok' },
              { key: 'user', label: 'User', count: counts.user, tone: 'accent' },
              { key: 'policy', label: 'Policy', count: counts.policy, tone: 'warn' },
              { key: 'cull', label: 'Culled', count: counts.cull, tone: 'danger' },
            ]}
          />
        }
        toolBarRender={() => [
          <Input
            key="search"
            allowClear
            prefix={<Icon name="search" size={14} />}
            placeholder="Filter events…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{ width: 220 }}
          />,
        ]}
      />
    </>
  )
}
