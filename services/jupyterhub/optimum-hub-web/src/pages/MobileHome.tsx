/* Mobile home - below the breakpoint the portal drops to a JupyterHub-style
 * minimal surface: the server card carries the SAME lifecycle actions as the
 * desktop hero (Open lab / Restart / Stop, or Start / Manage volumes) plus the
 * TTL extend. Admins additionally get a read-only active-servers widget and
 * links to the Servers and Users screens. */
import { Button, Card, Tag } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import { StatusPill } from '../components/StatusPill'
import { NotificationPill } from '../components/NotificationPill'
import { TtlGadget } from '../components/meters'
import { Icon } from '../components/Icon'
import { timeAgoShort } from '../lib/format'
import { useRole } from '../app/RoleContext'
import { useServerLifecycle } from '../app/ServerLifecycle'
import { useServerHero, useServers } from '../hooks/queries'
import { extendSession } from '../services/ops'
import { userServerUrl } from '../services/hub/client'

const adminTag = { background: 'var(--color-accent-soft)', color: 'var(--color-accent)', borderRadius: 4, marginInlineStart: 6 }

// status + the SAME action set as the desktop hero (full-width, touch-friendly),
// plus the TTL extend when running
function MyServerCard() {
  const { role, username } = useRole()
  const { data: hero } = useServerHero(username)
  const lifecycle = useServerLifecycle()
  const navigate = useNavigate()
  if (!hero) return null
  const running = hero.status === 'active' || hero.status === 'idle'
  const busy = !!lifecycle.busyOf(hero.user)
  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <h2 style={{ fontSize: 16, margin: 0 }}>Server status</h2>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {running && hero.upgradeAvailable && (
            <NotificationPill type="info" label="Upgrade available" title="A newer lab image is available locally - restart to upgrade" />
          )}
          <StatusPill status={hero.status} label={hero.statusLabel} />
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 20 }}>
        {running ? (
          <>
            <Button type="primary" block size="large" icon={<Icon name="play" size={15} filled />} disabled={busy} onClick={() => window.location.assign(userServerUrl(hero.user))}>Open lab</Button>
            <Button block size="large" icon={<Icon name="restart" size={16} />} disabled={busy} onClick={() => lifecycle.restart(hero.user)}>Restart</Button>
            <Button danger block size="large" icon={<Icon name="stop" size={14} filled />} disabled={busy} onClick={() => lifecycle.stop(hero.user)}>Stop</Button>
          </>
        ) : (
          <>
            <Button type="primary" block size="large" icon={<Icon name="play" size={15} filled />} disabled={busy} onClick={() => navigate(`/servers/${hero.user}/starting`)}>Start server</Button>
            {role === 'admin' && <Button block size="large" icon={<Icon name="disk" size={15} />} disabled={busy} onClick={() => navigate(`/servers/${hero.user}/volumes`)}>Manage volumes</Button>}
          </>
        )}
      </div>
      {running && (
        <div style={{ marginTop: 16 }}>
          <TtlGadget timeLeftMin={hero.ttl.timeLeftMin} baseMin={hero.ttl.baseMin} maxAddHours={hero.ttl.maxAddHours} uptimeLabel={hero.startedISO ? timeAgoShort(hero.startedISO) : undefined} onExtend={(h) => extendSession(hero.user, h)} />
        </div>
      )}
    </Card>
  )
}

// admin-only, read-only glance of running servers - same info as the old
// JupyterHub admin: user (+ admin badge), server status, last activity
function MobileServersWidget() {
  const { data: servers = [] } = useServers()
  const active = servers.filter((s) => s.status !== 'offline')
  return (
    <Card style={{ marginTop: 16 }}>
      <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>Active servers</h3>
      {active.length === 0 ? (
        <span className="oh-muted">No active servers</span>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {active.map((s) => (
            <div key={s.user} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {s.user}{s.admin && <Tag bordered={false} style={adminTag}>admin</Tag>}
                </div>
                <div className="oh-muted" style={{ fontSize: 12 }}>{s.lastActivityISO ? `active ${timeAgoShort(s.lastActivityISO)}` : '-'}</div>
              </div>
              <StatusPill status={s.status} label={s.statusLabel} />
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

export default function MobileHome() {
  const { role } = useRole()
  return (
    <div style={{ maxWidth: 520, margin: '0 auto' }}>
      <MyServerCard />
      {role === 'admin' && (
        <>
          <MobileServersWidget />
          <div style={{ marginTop: 16 }}>
            {/* mobile exposes only the Servers screen, not Users */}
            <Link to="/servers">
              <Button block icon={<Icon name="server" size={15} />}>Servers</Button>
            </Link>
          </div>
        </>
      )}
    </div>
  )
}
