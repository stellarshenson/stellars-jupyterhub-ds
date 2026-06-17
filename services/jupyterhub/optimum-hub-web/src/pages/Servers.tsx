/* Servers - the fleet monitor fused with lifecycle actions. Status (lifecycle,
 * drives the actions) and Activity (7-day engagement meter) are distinct columns;
 * quota breaches are colour-only; the scope pills keep Offline out of the default
 * view. Every action is mocked. */
import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ProTable } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { Button, Card, Drawer, Input, Modal, Tag } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { StatusPill } from '../components/StatusPill'
import { ActivityMeter } from '../components/meters'
import { ScopeFilterPills } from '../components/ScopeFilterPills'
import { rowActions } from '../components/ServerRowActions'
import { Icon } from '../components/Icon'
import { Link, useNavigate, type NavigateFunction } from 'react-router-dom'
import { timeAgoShort, exactDate } from '../lib/format'
import { downloadCsv } from '../lib/download'
import { useServers } from '../hooks/queries'
import { invalidate, notify } from '../services/actions'
import { resetActivity, startAllServers, stopAllServers } from '../services/ops'
import { useRole } from '../app/RoleContext'
import { gpuSupported } from '../app/capabilities'
import { useIsMobile } from '../lib/useIsMobile'
import { useServerLifecycle } from '../app/ServerLifecycle'
import type { ServerRow, ServerStatus } from '../services/types'

type Lifecycle = ReturnType<typeof useServerLifecycle>

// spawning sorts just under active (it is becoming active) and is counted in the
// Active scope - consistent bucketing between the sort order and the scope pills
const STATUS_ORDER: Record<ServerStatus, number> = { active: 1, spawning: 2, idle: 3, offline: 4, error: 5 }

// status-only label for the LIST (the widget clubs status + last-activity; the
// list keeps them in separate columns, so the pill shows just the state word)
const statusWord = (s: ServerStatus) => s.charAt(0).toUpperCase() + s.slice(1)

const accentTag = { background: 'var(--color-accent-soft)', color: 'var(--color-accent)', borderRadius: 4, marginInlineStart: 6 }

function inScope(r: ServerRow, scope: string): boolean {
  if (scope === 'all') return true
  if (scope === 'active') return r.status === 'active' || r.status === 'spawning'
  if (scope === 'idle') return r.status === 'idle'
  if (scope === 'offline') return r.status === 'offline'
  return true
}

// row actions (start/enter/restart/stop/manage-volumes) live in a shared module
// so the Home "Active servers" widget renders the IDENTICAL controls; this origin
// tags every nav so the opened sub-screen + breadcrumb return to the Servers list
const SERVERS_ORIGIN = { to: '/servers', label: 'Servers' }

// one labelled metric row in the detail drawer; `detail` is the breakdown line
// (the data that lives in the table cell's tooltip, surfaced inline here)
function Metric({ label, value, detail, over }: { label: string; value: ReactNode; detail?: string; over?: boolean }) {
  return (
    <div style={{ padding: '10px 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
        <span style={{ color: 'var(--color-text-muted)' }}>{label}</span>
        <span className={over ? 'oh-cell-warn' : ''}>{value}</span>
      </div>
      {detail && <div className="oh-muted" style={{ fontSize: 12, marginTop: 3, whiteSpace: 'pre-line' }}>{detail}</div>}
    </div>
  )
}

const dash = <span className="oh-muted">-</span>

// the detailed per-server activity report shown in the drawer - every breakdown
// the table keeps in tooltips, expanded inline
function ServerDetail({ row }: { row: ServerRow }) {
  const running = row.status === 'active' || row.status === 'idle'
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <StatusPill status={row.status} label={row.statusLabel} />
        {row.admin && <Tag bordered={false} style={accentTag}>admin</Tag>}
      </div>
      <Metric label="Activity (7d)" value={<ActivityMeter value={row.activity} hours={row.activityHours} pct={row.activityPct} />} />
      <Metric label="CPU" value={row.cpu == null ? dash : `${row.cpu}%`} detail={row.cpuTip} />
      <Metric label="Memory" value={row.mem == null ? dash : `${row.mem}%`} detail={row.memTip} over={row.memOver} />
      {gpuSupported() && <Metric label="GPU" value={row.gpu ?? <span className="oh-muted">not tracked per-server</span>} />}
      <Metric label="Volumes" value={row.volumesGB == null ? dash : `${row.volumesGB} GB`} detail={row.volumesTip} over={row.volumesOver} />
      <Metric label="System" value={row.systemGB == null ? dash : `+${row.systemGB} GB`} detail={row.systemTip} over={row.systemOver} />
      <Metric label="Time left" value={running ? (row.timeLeftLabel ?? dash) : dash} />
      <Metric label="Last activity" value={row.lastActivityISO ? timeAgoShort(row.lastActivityISO) : dash} detail={row.lastActivityISO ? exactDate(row.lastActivityISO) : undefined} />
    </div>
  )
}

// mobile servers view - a card list mirroring the old JupyterHub admin mobile
// info (user + admin badge, server status, last activity) plus the row actions;
// tapping a card opens the same detail drawer
function MobileServerList({ rows, nav, lf, me, onDetail }: { rows: ServerRow[]; nav: NavigateFunction; lf: Lifecycle; me: string; onDetail: (r: ServerRow) => void }) {
  if (!rows.length) return <div className="oh-muted" style={{ padding: '12px 4px' }}>No servers in scope</div>
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {rows.map((r) => (
        <Card key={r.user} size="small" style={{ cursor: 'pointer' }} onClick={() => onDetail(r)}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {r.user}{r.admin && <Tag bordered={false} style={accentTag}>admin</Tag>}
              </div>
              <div className="oh-muted" style={{ fontSize: 12 }}>{r.lastActivityISO ? timeAgoShort(r.lastActivityISO) : '-'}</div>
            </div>
            <StatusPill status={r.status} label={r.statusLabel} />
          </div>
          <div style={{ marginTop: 10 }} onClick={(e) => e.stopPropagation()}>{rowActions(r, nav, lf, me, SERVERS_ORIGIN)}</div>
        </Card>
      ))}
    </div>
  )
}

export default function Servers() {
  const { data = [], isLoading } = useServers()
  const navigate = useNavigate()
  const lifecycle = useServerLifecycle()
  const { username: me } = useRole()
  const isMobile = useIsMobile()
  const [scope, setScope] = useState('all')
  const [q, setQ] = useState('')
  const [detail, setDetail] = useState<ServerRow | null>(null)

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

  // real client-side CSV of the servers currently in scope - the live fleet
  // activity, not a mock; one row per server with the same numbers the table shows
  const downloadReport = () => {
    const header = ['User', 'Admin', 'Status', 'Activity %', 'CPU %', 'Memory %', 'Volumes GB', 'System GB', 'Time left (min)', 'Last activity']
    const rows = filtered.map((r) => [
      r.user, r.admin ? 'yes' : 'no', r.statusLabel,
      r.activity ?? '', r.cpu ?? '', r.mem ?? '', r.volumesGB ?? '', r.systemGB ?? '',
      r.timeLeftMin ?? '', r.lastActivityISO ?? '',
    ])
    downloadCsv(`activity-report-${scope}.csv`, header, rows)
    notify.success(`Exported activity report (${filtered.length} server${filtered.length === 1 ? '' : 's'})`)
  }

  const columns: ProColumns<ServerRow>[] = [
    {
      title: 'User',
      dataIndex: 'user',
      width: 200,
      sorter: (a, b) => a.user.localeCompare(b.user),
      // username links to the user config (same target as the Users list) and the
      // first/last name shows beneath it - no artificial click-friction
      render: (_, r) => (
        <div className="oh-user-cell">
          <span>
            <Link to={`/users/${r.user}`} style={{ color: 'var(--color-accent)' }} title={`Configure ${r.user}`}>{r.user}</Link>
            {r.admin && <Tag bordered={false} style={accentTag}>admin</Tag>}
          </span>
          {r.name && <span className="oh-name-hint">{r.name}</span>}
        </div>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      width: 104,
      sorter: (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status],
      render: (_, r) => <StatusPill status={r.status} label={statusWord(r.status)} />,
    },
    {
      title: 'Last activity',
      dataIndex: 'lastActivityISO',
      width: 128,
      sorter: (a, b) => (a.lastActivityISO ?? '').localeCompare(b.lastActivityISO ?? ''),
      render: (_, r) =>
        r.lastActivityISO ? <span title={exactDate(r.lastActivityISO)}>{timeAgoShort(r.lastActivityISO)}</span> : <span className="oh-muted">-</span>,
    },
    {
      title: 'Activity',
      dataIndex: 'activity',
      align: 'center',
      sorter: (a, b) => (a.activity ?? -1) - (b.activity ?? -1),
      render: (_, r) => <ActivityMeter value={r.activity} hours={r.activityHours} pct={r.activityPct} />,
    },
    {
      title: 'CPU', dataIndex: 'cpu', align: 'right', sorter: (a, b) => (a.cpu ?? -1) - (b.cpu ?? -1),
      render: (_, r) => (r.cpu == null ? <span className="oh-muted">-</span> : <span className="oh-num" title={r.cpuTip}>{r.cpu}%</span>),
    },
    {
      title: 'Mem',
      dataIndex: 'mem',
      align: 'right',
      sorter: (a, b) => (a.mem ?? -1) - (b.mem ?? -1),
      render: (_, r) =>
        r.mem == null ? <span className="oh-muted">-</span> : <span className={r.memOver ? 'oh-cell-warn' : 'oh-num'} title={r.memTip}>{r.mem}%</span>,
    },
    // GPU column only when the platform has GPU AND some row actually carries a
    // per-server GPU value (live never collects it -> all-null -> column hidden)
    ...(gpuSupported() && data.some((r) => r.gpu) ? [{
      title: 'GPU',
      dataIndex: 'gpu',
      align: 'center' as const,
      width: 96,
      render: (_: unknown, r: ServerRow) => (r.gpu ? <Tag bordered={false} style={{ background: 'var(--color-accent-soft)', color: 'var(--color-accent)', borderRadius: 4, marginInlineEnd: 0 }}>{r.gpu}</Tag> : <span className="oh-muted">-</span>),
    }] as ProColumns<ServerRow>[] : []),
    {
      title: 'Vol',
      dataIndex: 'volumesGB',
      align: 'right',
      sorter: (a, b) => (a.volumesGB ?? -1) - (b.volumesGB ?? -1),
      render: (_, r) =>
        r.volumesGB == null ? <span className="oh-muted">-</span> : <span className={r.volumesOver ? 'oh-cell-warn' : 'oh-num'} title={r.volumesTip}>{r.volumesGB} GB</span>,
    },
    {
      title: 'Sys',
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
      render: (_, r) => {
        if (r.timeLeftMin == null) return <span className="oh-muted">-</span>
        // the standard limit is the server's REAL configured idle-culler TTL (from
        // /activity); if the backend doesn't report it, show the bare time-left
        // rather than assert a limit we don't actually know
        if (r.baseTimeoutMin == null)
          return <span className={r.timeLeftWarn ? 'oh-cell-amber' : 'oh-num'}>{r.timeLeftLabel}</span>
        const baseMin = r.baseTimeoutMin
        const baseH = Math.round((baseMin / 60) * 10) / 10
        const overH = (r.timeLeftMin - baseMin) / 60
        const tip = overH > 0.05
          ? `${Math.round(overH * 10) / 10}h over the ${baseH}h standard limit`
          : `within the ${baseH}h standard limit`
        return <span className={r.timeLeftWarn ? 'oh-cell-amber' : 'oh-num'} title={tip}>{r.timeLeftLabel}</span>
      },
    },
    { title: 'Actions', align: 'right', render: (_, r) => <span onClick={(e) => e.stopPropagation()}>{rowActions(r, navigate, lifecycle, me, SERVERS_ORIGIN)}</span> },
  ]

  const scopes = [
    { key: 'active', label: 'Active', count: counts.active, tone: 'ok' as const },
    { key: 'idle', label: 'Idle', count: counts.idle, tone: 'warn' as const },
    { key: 'offline', label: 'Offline', count: counts.offline, tone: 'grey' as const },
    { key: 'all', label: 'All', count: data.length, tone: 'accent' as const },
  ]
  const offlineUsers = data.filter((r) => r.status === 'offline').map((r) => r.user)
  const runningUsers = data.filter((r) => r.status === 'active' || r.status === 'idle').map((r) => r.user)
  const stopAll = () =>
    Modal.confirm({
      title: 'Stop all running servers?',
      content: `This stops ${runningUsers.length} running lab(s).`,
      okText: 'Stop all',
      okButtonProps: { danger: true },
      onOk: () => stopAllServers(runningUsers),
    })
  const search = (
    <Input key="search" allowClear prefix={<Icon name="search" size={14} />} placeholder="Filter by user…" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: isMobile ? '100%' : 200 }} />
  )

  return (
    <>
      <PageHeader
        title="Servers"
        actions={
          <>
            <Button icon={<Icon name="play" size={14} />} disabled={!offlineUsers.length} onClick={() => startAllServers(offlineUsers)}>Start all</Button>
            <Button danger icon={<Icon name="stop" size={14} filled />} disabled={!runningUsers.length} onClick={stopAll}>Stop all</Button>
          </>
        }
      />
      {isMobile ? (
        <>
          <div style={{ marginBottom: 12 }}><ScopeFilterPills value={scope} onChange={setScope} scopes={scopes} /></div>
          <div style={{ marginBottom: 12 }}>{search}</div>
          <MobileServerList rows={filtered} nav={navigate} lf={lifecycle} me={me} onDetail={setDetail} />
        </>
      ) : (
        <ProTable<ServerRow>
          rowKey="user"
          columns={columns}
          dataSource={filtered}
          loading={isLoading}
          search={false}
          options={false}
          rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
          onRow={(r) => ({ onClick: () => setDetail(r), style: { cursor: 'pointer' } })}
          pagination={{ defaultPageSize: 25, pageSizeOptions: [25, 50, 100], showSizeChanger: { showSearch: false }, showTotal: (t) => `${t} servers in scope` }}
          headerTitle={<ScopeFilterPills value={scope} onChange={setScope} scopes={scopes} />}
          toolBarRender={() => [
            search,
            <Button key="reset" onClick={() => resetActivity()}>Reset samples</Button>,
            <Button key="report" icon={<Icon name="download" size={14} />} disabled={!filtered.length} onClick={downloadReport}>Report</Button>,
            <Button key="refresh" icon={<Icon name="restart" size={14} />} onClick={() => invalidate(['servers'], ['stats'], ['resources'])}>Refresh</Button>,
          ]}
        />
      )}
      <Drawer
        open={!!detail}
        onClose={() => setDetail(null)}
        width={440}
        title={detail ? `${detail.user} - activity report` : ''}
        extra={detail ? <span onClick={(e) => e.stopPropagation()}>{rowActions(detail, navigate, lifecycle, me, SERVERS_ORIGIN)}</span> : null}
      >
        {detail && <ServerDetail row={detail} />}
      </Drawer>
    </>
  )
}
