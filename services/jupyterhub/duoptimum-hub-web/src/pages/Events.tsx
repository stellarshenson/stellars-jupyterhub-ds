/* Events - the audit timeline behind the Overview feed. Scaled list: type scope
 * pills, search, pager. */
import { useMemo, useState } from 'react'
import { ProTable } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { Button, Input, Segmented } from 'antd'
import { appModal } from '../services/actions'
import { PageHeader } from '../components/PageHeader'
import { ScopeFilterPills, TONE_CLASS } from '../components/ScopeFilterPills'
import { Icon } from '../components/Icon'
import { clearEvents } from '../services/ops'
import { useEvents } from '../hooks/queries'
import { timeAgoShort, exactDate } from '../lib/format'
import { useResponsiveColumns } from '../lib/useResponsiveColumns'
import { EVENT_TONE, glyphFilled } from '../lib/eventVisual'
import type { EventRow } from '../services/types'

type Range = '24h' | '7d' | '30d'
const RANGE_MS: Record<Range, number> = { '24h': 864e5, '7d': 6.048e8, '30d': 2.592e9 }

export default function Events() {
  const { data = [], isLoading } = useEvents()
  const [scope, setScope] = useState('all')
  const [q, setQ] = useState('')
  const [range, setRange] = useState<Range>('7d')

  // everything inside the current time range + search, before the type scope -
  // the type pill counts read off this so they track the time filter
  const rangeFiltered = useMemo(
    () => data.filter((e) => e.text.toLowerCase().includes(q.toLowerCase()) && Date.now() - new Date(e.whenISO).getTime() <= RANGE_MS[range]),
    [data, q, range],
  )

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    rangeFiltered.forEach((e) => (c[e.type] = (c[e.type] ?? 0) + 1))
    return c
  }, [rangeFiltered])

  const filtered = useMemo(() => rangeFiltered.filter((e) => scope === 'all' || e.type === scope), [rangeFiltered, scope])

  // clearing the persisted audit log is destructive + irreversible -> confirm first
  const clearLog = () =>
    appModal.confirm({
      title: 'Clear the event log?',
      content: 'This permanently deletes every recorded event. This cannot be undone.',
      okText: 'Clear Events',
      okButtonProps: { danger: true },
      onOk: () => clearEvents(),
    })

  const columns: ProColumns<EventRow>[] = useResponsiveColumns([
    {
      title: 'Event',
      dataIndex: 'text',
      render: (_, e) => (
        <div className="doh-row">
          <span className={`doh-feed-ic ${EVENT_TONE[e.type]}`}>
            <Icon name={e.icon as 'play'} size={15} filled={glyphFilled(e.icon)} />
          </span>
          <span dangerouslySetInnerHTML={{ __html: e.text }} />
        </div>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      width: 120,
      render: (_, e) => <span className={`doh-pill ${TONE_CLASS[EVENT_TONE[e.type]]}`}>{e.type}</span>,
    },
    {
      title: 'When',
      dataIndex: 'whenISO',
      responsive: ['xl'], // time metadata: drops first on tablet (<1200)
      width: 160,
      align: 'right',
      sorter: (a, b) => b.whenISO.localeCompare(a.whenISO),
      render: (_, e) => <span title={exactDate(e.whenISO)} className="doh-muted">{timeAgoShort(e.whenISO)}</span>,
    },
  ])

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
        rowClassName={(_, i) => (i % 2 ? 'doh-row-alt' : '')}
        pagination={{ pageSize: 12, showSizeChanger: false }}
        headerTitle={
          <ScopeFilterPills
            value={scope}
            onChange={setScope}
            scopes={[
              { key: 'all', label: 'All', count: rangeFiltered.length, tone: 'accent' },
              { key: 'server', label: 'Server', count: counts.server, tone: 'ok' },
              { key: 'user', label: 'User', count: counts.user, tone: 'accent' },
              { key: 'group', label: 'Group', count: counts.group, tone: 'accent' },
              { key: 'policy', label: 'Policy', count: counts.policy, tone: 'accent' },
              { key: 'broadcast', label: 'Broadcast', count: counts.broadcast, tone: 'accent' },
              { key: 'cull', label: 'Culled', count: counts.cull, tone: 'danger' },
              { key: 'volume', label: 'Volume', count: counts.volume, tone: 'warn' },
              { key: 'error', label: 'Failed', count: counts.error, tone: 'danger' },
            ]}
          />
        }
        toolBarRender={() => [
          <Segmented
            key="range"
            value={range}
            onChange={(v) => setRange(v as Range)}
            options={[
              { label: 'Last 24h', value: '24h' },
              { label: 'Last 7 days', value: '7d' },
              { label: 'Last 30 days', value: '30d' },
            ]}
          />,
          <Input
            key="search"
            allowClear
            prefix={<Icon name="search" size={14} />}
            placeholder="Filter events…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{ width: 220 }}
          />,
          <Button key="clear" danger icon={<Icon name="close" size={14} />} disabled={!data.length} onClick={clearLog}>Clear</Button>,
        ]}
      />
    </>
  )
}
