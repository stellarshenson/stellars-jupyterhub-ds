/* Home - role-aware. Admin sees the fleet dashboard (own server hero, Servers /
 * Users metrics, total resources, pending callout, active-servers preview, quick
 * actions, recent events). A plain user sees the launchpad (their server hero,
 * their groups, effective access). */
import { useEffect } from 'react'
import { Card, Tag, Tooltip } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import { ProTable } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { PageHeader } from '../components/PageHeader'
import { ServerHero } from '../components/ServerHero'
import { MetricCard } from '../components/MetricCard'
import { ResourceBars, ActivityMeter } from '../components/meters'
import { StatusPill } from '../components/StatusPill'
import { CardHeadLink } from '../components/CardHeadLink'
import { CappedTags } from '../components/CappedTags'
import { rowActions } from '../components/ServerRowActions'
import { Icon } from '../components/Icon'
import { useRole } from '../app/RoleContext'
import { usePref } from '../app/PrefsContext'
import { useIsMobile } from '../lib/useIsMobile'
import MobileHome from './MobileHome'
import { timeAgoShort } from '../lib/format'
import { useEffectiveGrants, useEvents, useServerHero, useServers, useStats, useTotalResources, useUser } from '../hooks/queries'
import { invalidate } from '../services/actions'
import { useServerLifecycle } from '../app/ServerLifecycle'
import type { ServerRow, ServerStatus } from '../services/types'
import { quotaColor } from '../services/hub/serverMetrics'
import { SERVERS_COL_HELP } from '../services/config'

const STATUS_ORDER: Record<ServerStatus, number> = { active: 1, idle: 2, spawning: 3, offline: 4, error: 5 }
const accentTag = { background: 'var(--color-accent-soft)', color: 'var(--color-accent)', borderRadius: 4, marginInlineStart: 6 }

// the Home widget lists OTHER users' servers too, so its row actions tag Home as
// the origin -> the Start / Manage-volumes sub-screens + breadcrumb return here
const HOME_ORIGIN = { to: '/home', label: 'Home' }

function PendingCallout({ count }: { count: number }) {
  if (count === 0) return null
  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', borderRadius: 10, marginTop: 16,
        background: 'var(--color-accent-2-soft)', border: '1px solid color-mix(in srgb, var(--color-accent-2) 30%, transparent)', fontSize: 13,
      }}
    >
      <Icon name="user" size={18} style={{ color: 'var(--color-accent-2)' }} />
      <div>
        <b>{count} users awaiting approval</b> - review and authorise
      </div>
      <Link to="/users" style={{ marginLeft: 'auto' }}>
        <span className="doh-pill accent" style={{ cursor: 'pointer' }}>Review</span>
      </Link>
    </div>
  )
}

function ActiveServersPreview() {
  const { data = [] } = useServers()
  const navigate = useNavigate()
  const { username: me } = useRole()
  const lifecycle = useServerLifecycle()
  const listCpuMode = usePref('cpuModeServersList') // 'cores' shows docker/top %, 'normalized' shows % of assigned
  const top = [...data].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]).slice(0, 10)
  // minimal info on the home preview - the detailed CPU/mem/vol/sys breakdowns
  // live in the Servers screen drawer now
  const columns: ProColumns<ServerRow>[] = [
    {
      title: 'User',
      dataIndex: 'user',
      width: 170,
      // username links to the user config + first/last name beneath, matching the
      // Servers list and Users screen
      render: (_, r) => (
        <div className="doh-user-cell">
          <span>
            <Link to={`/users/${r.user}`} state={{ from: HOME_ORIGIN }} style={{ color: 'var(--color-accent)' }} title={`Configure ${r.user}`}>{r.user}</Link>
            {r.admin && <Tag bordered={false} style={accentTag}>admin</Tag>}
          </span>
          {r.name && <span className="doh-name-hint">{r.name}</span>}
        </div>
      ),
    },
    { title: 'Status', width: 92, render: (_, r) => <StatusPill status={r.status} label={r.statusLabel} /> },
    { title: 'Activity', render: (_, r) => <ActivityMeter value={r.activity} hours={r.activityHours} pct={r.activityPct} /> },
    {
      title: <Tooltip title={SERVERS_COL_HELP.cpu}><span>CPU</span></Tooltip>,
      align: 'right',
      render: (_, r) => (r.cpu == null ? <span className="doh-muted">-</span> : <span className="doh-num" title={r.cpuTip} style={{ color: quotaColor(r.cpuQuotaPct) }}>{listCpuMode === 'cores' ? r.cpu : (r.cpuAssignedPct ?? r.cpu)}%</span>),
    },
    {
      title: <Tooltip title={SERVERS_COL_HELP.mem}><span>Mem</span></Tooltip>,
      align: 'right',
      render: (_, r) => (r.mem == null ? <span className="doh-muted">-</span> : <span className="doh-num" title={r.memTip} style={{ color: quotaColor(r.memQuotaPct) }}>{r.mem} GB</span>),
    },
    {
      title: 'Time Left',
      align: 'right',
      render: (_, r) => (r.timeLeftMin == null ? <span className="doh-muted">-</span> : <span className={r.timeLeftWarn ? 'doh-cell-amber' : 'doh-num'}>{r.timeLeftLabel}</span>),
    },
    {
      title: '',
      align: 'right',
      // identical controls + behaviour to the Servers list (shared rowActions),
      // tagged with Home as the origin so sub-screens return here
      render: (_, r) => rowActions(r, navigate, lifecycle, me, HOME_ORIGIN),
    },
  ]
  return (
    <Card>
      <CardHeadLink title="Active Servers" to="/servers" suffix="· top 10 by status" />
      <ProTable<ServerRow>
        rowKey="user"
        columns={columns}
        dataSource={top}
        search={false}
        options={false}
        ghost
        style={{ marginTop: 12 }}
        pagination={false}
        rowClassName={(_, i) => (i % 2 ? 'doh-row-alt' : '')}
      />
    </Card>
  )
}

function QuickActions() {
  const items: Array<{ to: string; icon: 'user' | 'group' | 'megaphone' | 'settings'; label: string; sub: string }> = [
    { to: '/users/new', icon: 'user', label: 'Add User', sub: 'create + authorise' },
    { to: '/groups/new', icon: 'group', label: 'Create Group', sub: 'grant policies' },
    { to: '/notifications', icon: 'megaphone', label: 'Broadcast', sub: 'notify lab users' },
    { to: '/settings', icon: 'settings', label: 'Settings', sub: 'platform config' },
  ]
  return (
    <Card>
      <h3 style={{ marginBottom: 12 }}>Quick Actions</h3>
      <div className="doh-qa">
        {items.map((it) => (
          <Link key={it.to} to={it.to} className="doh-qa-btn">
            <Icon name={it.icon} size={18} />
            <span>
              {it.label}
              <small>{it.sub}</small>
            </span>
          </Link>
        ))}
      </div>
    </Card>
  )
}

function RecentEvents() {
  const { data = [] } = useEvents()
  return (
    <Card style={{ flex: 1 }} styles={{ body: { padding: 0 } }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)' }}>
        <CardHeadLink title="Recent Events" to="/events" />
      </div>
      <div className="doh-feed" style={{ padding: '0 16px' }}>
        {data.slice(0, 5).map((e) => (
          <div className="doh-feed-item" key={e.id}>
            <div className="doh-feed-ic">
              <Icon name={e.icon as 'play'} size={15} />
            </div>
            <div className="doh-feed-body">
              <div className="t" dangerouslySetInnerHTML={{ __html: e.text }} />
              <div className="when">{timeAgoShort(e.whenISO)}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

// proportional segment width, guarded so an empty platform (total 0) yields 0, not NaN%
function segPct(n: number, total: number): number {
  return total > 0 ? (n / total) * 100 : 0
}

function AdminHome() {
  const { username } = useRole()
  const { data: stats } = useStats()
  const { data: hero } = useServerHero(username)
  const { data: total } = useTotalResources()
  const hostCpuMode = usePref('cpuModeHostStatus') // 'cores' = summed cores-used label; bar fill unchanged
  const s = stats?.servers
  const u = stats?.users

  return (
    <>
      <PageHeader title="Home" sub="Platform at a glance - what is running and what needs attention" />
      {hero && <ServerHero hero={hero} resourcesTitle="Server Status" />}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        {s && (
          <MetricCard
            icon="server"
            label="Servers"
            value={s.total.toLocaleString()}
            to="/servers"
            segments={[
              { width: segPct(s.running, s.total), color: 'var(--color-success)' },
              { width: segPct(s.idle, s.total), color: 'var(--color-warning)' },
              { width: segPct(s.offline, s.total), color: 'var(--color-border)' },
            ]}
            breakdown={
              <>
                <span style={{ color: 'var(--color-success)' }} title="Running with recent activity"><b>{s.running}</b> running</span>
                <span style={{ color: 'var(--color-warning)' }} title="Running but idle"><b>{s.idle}</b> idle</span>
                <span title="Stopped"><b>{s.offline.toLocaleString()}</b> offline</span>
              </>
            }
          />
        )}
        {u && (
          <MetricCard
            icon="users"
            label="Users"
            value={u.total.toLocaleString()}
            to="/users"
            segments={[
              { width: segPct(u.pending, u.total), color: 'var(--color-accent-2)' },
              { width: segPct(u.active, u.total), color: 'var(--color-success)' },
              { width: segPct(u.new, u.total), color: 'var(--color-accent)' },
              { width: segPct(u.inactive, u.total), color: 'var(--color-text-subtle)' },
            ]}
            breakdown={
              <>
                <span style={{ color: 'var(--color-accent-2)' }} title="Signed up, awaiting authorisation"><b>{u.pending}</b> pending</span>
                <span style={{ color: 'var(--color-success)' }} title="Activity above 0%"><b>{u.active.toLocaleString()}</b> active</span>
                <span style={{ color: 'var(--color-accent)' }} title="Authorised but never signed in"><b>{u.new}</b> new</span>
                <span title="Activity at 0%"><b>{u.inactive}</b> inactive</span>
              </>
            }
          />
        )}
        <Card style={{ gridColumn: 'span 2' }}>
          <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>Host Status</h3>
          {total && (
            <ResourceBars
              rows={[
                { label: 'CPU', value: total.cpu, valueLabel: hostCpuMode === 'cores' && total.cpuAggregateLabel ? total.cpuAggregateLabel : `${total.cpu}%`, tip: total.cpuTip, error: total.cpuError },
                { label: 'Memory', value: total.mem, tip: total.memTip, error: total.memError },
                // GPU row only when there is real GPU data (matches ServerHero); a bare
                // GPU row must not leak when GPU is off or the sidecar is down
                ...(total.gpus !== undefined || total.gpuDevices !== undefined
                  ? [{ label: 'GPU', value: total.gpu, gpus: total.gpus, gpuDevices: total.gpuDevices }]
                  : []),
              ]}
            />
          )}
        </Card>
      </div>

      <PendingCallout count={u?.pending ?? 0} />

      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 16, marginTop: 24 }}>
        <ActiveServersPreview />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <QuickActions />
          <RecentEvents />
        </div>
      </div>
    </>
  )
}

function UserHome() {
  const { username } = useRole()
  const { data: hero } = useServerHero(username)
  const { data: me } = useUser(username)
  const { data: grants = [] } = useEffectiveGrants(username)

  return (
    <>
      <PageHeader title="Home" sub="Your lab - launch it, watch it, manage it" />
      {hero && <ServerHero hero={hero} resourcesTitle="Server Status" />}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Card>
          <h3 style={{ margin: '0 0 12px' }}>Your Groups</h3>
          <CappedTags items={(me?.groups ?? []).map((g) => ({ key: g, label: g }))} cap={8} />
        </Card>
        <Card>
          <h3 style={{ margin: '0 0 12px' }}>What your groups grant</h3>
          {grants.map((g) => (
            <div className="doh-grant" key={g.key}>
              <span className="doh-g-ic"><Icon name={g.key as 'gpu'} size={16} /></span>
              <div>
                {g.label}
                <div className="doh-g-from">from {g.from}</div>
              </div>
              <span className="doh-g-val">{g.value}</span>
            </div>
          ))}
        </Card>
      </div>
    </>
  )
}

export default function Home() {
  const { role, username } = useRole()
  const isMobile = useIsMobile()
  // Returning to the dashboard (e.g. after starting the lab from the start page,
  // which navigates out into the lab) can paint a stale "offline" status from the
  // hydrated cache. Force a refetch of the server-status queries on mount so the
  // server control, servers widget and servers list redraw current immediately.
  useEffect(() => {
    invalidate(['hero', username], ['servers'], ['stats'], ['resources'], ['session', username])
  }, [username])
  // Below the mobile breakpoint, drop to the minimal phone surface (status +
  // Start/Stop/Extend; admins also get a read-only servers widget + links).
  if (isMobile) return <MobileHome />
  return role === 'admin' ? <AdminHome /> : <UserHome />
}
