/* Home - role-aware. Admin sees the fleet dashboard (own server hero, Servers /
 * Users metrics, total resources, pending callout, active-servers preview, quick
 * actions, recent events). A plain user sees the launchpad (their server hero,
 * their groups, effective access). */
import { Card } from 'antd'
import { Link } from 'react-router-dom'
import { ProTable } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { PageHeader } from '../components/PageHeader'
import { ServerHero } from '../components/ServerHero'
import { MetricCard } from '../components/MetricCard'
import { ResourceBars, ActivityMeter } from '../components/meters'
import { StatusPill } from '../components/StatusPill'
import { CardHeadLink } from '../components/CardHeadLink'
import { CappedTags } from '../components/CappedTags'
import { IconAction } from '../components/IconAction'
import { Icon } from '../components/Icon'
import { useRole } from '../app/RoleContext'
import { useEffectiveGrants, useEvents, useServerHero, useServers, useStats, useTotalResources, useUser } from '../hooks/queries'
import { restartServer, startServer, stopServer } from '../services/ops'
import type { ServerRow, ServerStatus } from '../services/types'

const STATUS_ORDER: Record<ServerStatus, number> = { active: 1, idle: 2, spawning: 3, offline: 4, error: 5 }

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
        <span className="oh-pill accent" style={{ cursor: 'pointer' }}>Review</span>
      </Link>
    </div>
  )
}

function ActiveServersPreview() {
  const { data = [] } = useServers()
  const top = [...data].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]).slice(0, 10)
  const columns: ProColumns<ServerRow>[] = [
    { title: 'User', dataIndex: 'user', render: (_, r) => <span>{r.user}</span> },
    { title: 'Status', render: (_, r) => <StatusPill status={r.status} label={r.statusLabel} /> },
    { title: 'Activity', render: (_, r) => <ActivityMeter value={r.activity} /> },
    { title: 'CPU', align: 'right', render: (_, r) => (r.cpu == null ? <span className="oh-muted">-</span> : <span className="oh-num">{r.cpu}%</span>) },
    { title: 'Mem', align: 'right', render: (_, r) => (r.mem == null ? <span className="oh-muted">-</span> : <span className={r.memOver ? 'oh-cell-warn' : 'oh-num'} title={r.memTip}>{r.mem}%</span>) },
    {
      title: 'Time left',
      align: 'right',
      render: (_, r) => (r.timeLeftMin == null ? <span className="oh-muted">-</span> : <span className={r.timeLeftWarn ? 'oh-cell-amber' : 'oh-num'}>{r.timeLeftLabel}</span>),
    },
    {
      title: '',
      align: 'right',
      render: (_, r) => (
        <div className="oh-row" style={{ justifyContent: 'flex-end' }}>
          {r.status === 'offline' || r.status === 'error' ? (
            <IconAction icon="play" title="Start" onClick={() => startServer(r.user)} />
          ) : (
            <>
              <IconAction icon="restart" title="Restart" onClick={() => restartServer(r.user)} />
              <IconAction icon="stop" title="Stop" danger filled onClick={() => stopServer(r.user)} />
            </>
          )}
        </div>
      ),
    },
  ]
  return (
    <Card>
      <CardHeadLink title="Active servers" to="/servers" suffix="· top 10 by status" />
      <ProTable<ServerRow>
        rowKey="user"
        columns={columns}
        dataSource={top}
        search={false}
        options={false}
        ghost
        style={{ marginTop: 12 }}
        pagination={false}
      />
    </Card>
  )
}

function QuickActions() {
  const items: Array<{ to: string; icon: 'user' | 'group' | 'megaphone' | 'settings'; label: string; sub: string }> = [
    { to: '/users/new', icon: 'user', label: 'Add user', sub: 'create + authorise' },
    { to: '/groups/new', icon: 'group', label: 'Create group', sub: 'grant policies' },
    { to: '/notifications', icon: 'megaphone', label: 'Broadcast', sub: 'notify lab users' },
    { to: '/settings', icon: 'settings', label: 'Settings', sub: 'platform config' },
  ]
  return (
    <Card>
      <h3 style={{ marginBottom: 12 }}>Quick actions</h3>
      <div className="oh-qa">
        {items.map((it) => (
          <Link key={it.to} to={it.to} className="oh-qa-btn">
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
        <CardHeadLink title="Recent events" to="/events" />
      </div>
      <div className="oh-feed" style={{ padding: '0 16px' }}>
        {data.slice(0, 5).map((e) => (
          <div className="oh-feed-item" key={e.id}>
            <div className="oh-feed-ic">
              <Icon name={e.icon as 'play'} size={15} />
            </div>
            <div className="oh-feed-body">
              <div className="t" dangerouslySetInnerHTML={{ __html: e.text }} />
              <div className="when">{timeAgoShort(e.whenISO)}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

function timeAgoShort(iso: string): string {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const h = Math.round(mins / 60)
  if (h < 24) return `${h} hour${h > 1 ? 's' : ''} ago`
  return `${Math.round(h / 24)} day${h >= 48 ? 's' : ''} ago`
}

function AdminHome() {
  const { username } = useRole()
  const { data: stats } = useStats()
  const { data: hero } = useServerHero(username)
  const { data: total } = useTotalResources()
  const s = stats?.servers
  const u = stats?.users

  return (
    <>
      <PageHeader title="Home" sub="Platform at a glance - what is running and what needs attention" />
      {hero && <ServerHero hero={hero} resourcesTitle="Server resources" />}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        {s && (
          <MetricCard
            icon="server"
            label="Servers"
            value={s.total.toLocaleString()}
            to="/servers"
            segments={[
              { width: (s.running / s.total) * 100, color: 'var(--color-success)' },
              { width: (s.idle / s.total) * 100, color: 'var(--color-warning)' },
              { width: (s.offline / s.total) * 100, color: 'var(--color-border)' },
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
              { width: (u.pending / u.total) * 100, color: 'var(--color-accent-2)' },
              { width: (u.active / u.total) * 100, color: 'var(--color-success)' },
              { width: (u.new / u.total) * 100, color: 'var(--color-accent)' },
              { width: (u.inactive / u.total) * 100, color: 'var(--color-text-subtle)' },
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
          <h3 style={{ margin: '0 0 12px' }}>Total resources</h3>
          {total && (
            <ResourceBars
              rows={[
                { label: 'CPU', value: total.cpu },
                { label: 'Memory', value: total.mem },
                { label: 'GPU', value: total.gpu, gpus: total.gpus, gpuDevices: total.gpuDevices },
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
      {hero && <ServerHero hero={hero} resourcesTitle="Server resources" />}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Card>
          <h3 style={{ margin: '0 0 12px' }}>Your groups</h3>
          <CappedTags items={(me?.groups ?? []).map((g) => ({ key: g, label: g }))} cap={8} />
        </Card>
        <Card>
          <h3 style={{ margin: '0 0 12px' }}>What your groups grant</h3>
          {grants.map((g) => (
            <div className="oh-grant" key={g.key}>
              <span className="oh-g-ic"><Icon name={g.key as 'gpu'} size={16} /></span>
              <div>
                {g.label}
                <div className="oh-g-from">from {g.from}</div>
              </div>
              <span className="oh-g-val">{g.value}</span>
            </div>
          ))}
        </Card>
      </div>
    </>
  )
}

export default function Home() {
  const { role } = useRole()
  return role === 'admin' ? <AdminHome /> : <UserHome />
}
