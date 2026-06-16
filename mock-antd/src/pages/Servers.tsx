/* Servers - the fleet monitor fused with lifecycle actions. Status (lifecycle,
 * drives the actions) and Activity (24h engagement meter) are distinct columns;
 * quota breaches are colour-only; the scope pills keep Offline out of the default
 * view. Every action is mocked. */
import { useMemo, useState } from 'react'
import { ProTable } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { Button, Input, Tag } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { StatusPill } from '../components/StatusPill'
import { ActivityMeter } from '../components/meters'
import { ScopeFilterPills } from '../components/ScopeFilterPills'
import { IconAction } from '../components/IconAction'
import { Icon } from '../components/Icon'
import { useServers } from '../hooks/queries'
import { mockAction } from '../services/actions'
import type { ServerRow, ServerStatus } from '../services/types'

const STATUS_ORDER: Record<ServerStatus, number> = { active: 1, idle: 2, spawning: 3, offline: 4, error: 5 }

const accentTag = { background: 'var(--color-accent-soft)', color: 'var(--color-accent)', borderRadius: 4, marginInlineStart: 6 }

function inScope(r: ServerRow, scope: string): boolean {
  if (scope === 'all') return true
  if (scope === 'active') return r.status === 'active' || r.status === 'spawning'
  if (scope === 'idle') return r.status === 'idle'
  if (scope === 'offline') return r.status === 'offline'
  return true
}

function num(v: number | null) {
  return v == null ? <span className="oh-muted">-</span> : <span className="oh-num">{v}%</span>
}

function rowActions(r: ServerRow) {
  if (r.status === 'spawning') {
    return (
      <div className="oh-row" style={{ justifyContent: 'flex-end' }}>
        <IconAction icon="activity" title="View spawn log" onClick={() => mockAction('Tail live spawn log')} />
        <IconAction icon="stop" title="Cancel spawn" danger filled onClick={() => mockAction(`Cancelled ${r.user}'s spawn`)} />
      </div>
    )
  }
  if (r.status === 'offline') {
    return (
      <div className="oh-row" style={{ justifyContent: 'flex-end' }}>
        <IconAction icon="play" title="Start (you stay here)" onClick={() => mockAction(`Started ${r.user}'s server - you stay here`)} />
        {r.volumesGB != null && (
          <IconAction icon="disk" title="Manage volumes" onClick={() => mockAction(`Manage ${r.user}'s volumes`)} />
        )}
      </div>
    )
  }
  return (
    <div className="oh-row" style={{ justifyContent: 'flex-end' }}>
      <IconAction icon="play" title="Enter session (confirm)" onClick={() => mockAction(`Confirm: enter ${r.user}'s running server?`)} />
      <IconAction icon="restart" title="Restart" onClick={() => mockAction(`Restarted ${r.user}'s server`)} />
      <IconAction icon="stop" title="Stop" danger filled onClick={() => mockAction(`Stopped ${r.user}'s server`)} />
    </div>
  )
}

export default function Servers() {
  const { data = [], isLoading } = useServers()
  const [scope, setScope] = useState('active')
  const [q, setQ] = useState('')

  const counts = useMemo(() => {
    const c = { active: 0, idle: 0, offline: 0 }
    data.forEach((r) => {
      if (r.status === 'active' || r.status === 'spawning') c.active++
      else if (r.status === 'idle') c.idle++
      else if (r.status === 'offline') c.offline++
    })
    return c
  }, [data])

  const filtered = useMemo(
    () => data.filter((r) => inScope(r, scope) && r.user.toLowerCase().includes(q.toLowerCase())),
    [data, scope, q],
  )

  const columns: ProColumns<ServerRow>[] = [
    {
      title: 'User',
      dataIndex: 'user',
      sorter: (a, b) => a.user.localeCompare(b.user),
      render: (_, r) => (
        <span title={`Container jupyterlab-${r.user}`}>
          {r.user}
          {r.admin && <Tag bordered={false} style={accentTag}>admin</Tag>}
        </span>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      sorter: (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status],
      render: (_, r) => <StatusPill status={r.status} label={r.statusLabel} />,
    },
    {
      title: 'Activity',
      dataIndex: 'activity',
      sorter: (a, b) => (a.activity ?? -1) - (b.activity ?? -1),
      render: (_, r) => <ActivityMeter value={r.activity} />,
    },
    { title: 'CPU', dataIndex: 'cpu', align: 'right', sorter: (a, b) => (a.cpu ?? -1) - (b.cpu ?? -1), render: (_, r) => num(r.cpu) },
    {
      title: 'Memory',
      dataIndex: 'mem',
      align: 'right',
      sorter: (a, b) => (a.mem ?? -1) - (b.mem ?? -1),
      render: (_, r) =>
        r.mem == null ? <span className="oh-muted">-</span> : <span className={r.memOver ? 'oh-cell-warn' : 'oh-num'} title={r.memTip}>{r.mem}%</span>,
    },
    {
      title: 'GPU',
      dataIndex: 'gpu',
      align: 'center',
      width: 96,
      render: (_, r) => (r.gpu ? <Tag bordered={false} style={{ background: 'var(--color-accent-soft)', color: 'var(--color-accent)', borderRadius: 4, marginInlineEnd: 0 }}>{r.gpu}</Tag> : <span className="oh-muted">-</span>),
    },
    {
      title: 'Volumes',
      dataIndex: 'volumesGB',
      align: 'right',
      sorter: (a, b) => (a.volumesGB ?? -1) - (b.volumesGB ?? -1),
      render: (_, r) =>
        r.volumesGB == null ? <span className="oh-muted">-</span> : <span className={r.volumesOver ? 'oh-cell-warn' : 'oh-num'} title={r.volumesTip}>{r.volumesGB} GB</span>,
    },
    {
      title: 'System',
      dataIndex: 'systemGB',
      align: 'right',
      sorter: (a, b) => (a.systemGB ?? -1) - (b.systemGB ?? -1),
      render: (_, r) =>
        r.systemGB == null ? <span className="oh-muted">-</span> : <span className={r.systemOver ? 'oh-cell-warn' : 'oh-num'} title={r.systemTip}>+{r.systemGB} GB</span>,
    },
    {
      title: 'Time left',
      dataIndex: 'timeLeftMin',
      align: 'right',
      sorter: (a, b) => (a.timeLeftMin ?? -1) - (b.timeLeftMin ?? -1),
      render: (_, r) =>
        r.timeLeftMin == null ? <span className="oh-muted">-</span> : <span className={r.timeLeftWarn ? 'oh-cell-amber' : 'oh-num'}>{r.timeLeftLabel}</span>,
    },
    { title: 'Actions', align: 'right', render: (_, r) => rowActions(r) },
  ]

  return (
    <>
      <PageHeader title="Servers" sub="Start, stop and restart labs; act on quota breaches and sessions about to be culled" />
      <ProTable<ServerRow>
        rowKey="user"
        columns={columns}
        dataSource={filtered}
        loading={isLoading}
        search={false}
        options={false}
        rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
        pagination={{ pageSize: 8, showSizeChanger: false, showTotal: (t) => `${t} servers in scope` }}
        headerTitle={
          <ScopeFilterPills
            value={scope}
            onChange={setScope}
            scopes={[
              { key: 'active', label: 'Active', count: counts.active, tone: 'ok' },
              { key: 'idle', label: 'Idle', count: counts.idle, tone: 'warn' },
              { key: 'offline', label: 'Offline', count: counts.offline, tone: 'grey' },
              { key: 'all', label: 'All', count: data.length, tone: 'accent' },
            ]}
          />
        }
        toolBarRender={() => [
          <Input
            key="search"
            allowClear
            prefix={<Icon name="search" size={14} />}
            placeholder="Filter by user…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{ width: 200 }}
          />,
          <Button key="reset" onClick={() => mockAction('Reset activity samples')}>Reset samples</Button>,
          <Button key="report" icon={<Icon name="download" size={14} />} onClick={() => mockAction('Downloaded activity report')}>Report</Button>,
          <Button key="refresh" icon={<Icon name="restart" size={14} />} onClick={() => mockAction('Refreshed')}>Refresh</Button>,
        ]}
      />
    </>
  )
}
