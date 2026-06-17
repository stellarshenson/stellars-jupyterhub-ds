/* The two-panel server block reused on both Homes: left is status + controls +
 * TTL, right is the lab's resources. Controls are state-aware: a stopped server
 * shows Start (+ Reset volumes for admins); a running one Open lab / Restart / Stop. */
import { Button, Card } from 'antd'
import { useNavigate } from 'react-router-dom'
import { Icon } from './Icon'
import { StatusPill } from './StatusPill'
import { NotificationPill } from './NotificationPill'
import { ActivityMeterFill, ResourceBars, TtlGadget } from './meters'
import { extendSession } from '../services/ops'
import { userServerUrl } from '../services/hub/client'
import { timeAgoShort } from '../lib/format'
import { useRole } from '../app/RoleContext'
import { useServerLifecycle } from '../app/ServerLifecycle'
import type { ServerHero as Hero } from '../services/types'

export function ServerHero({ hero, resourcesTitle }: { hero: Hero; resourcesTitle: string }) {
  const running = hero.status === 'active' || hero.status === 'idle'
  const navigate = useNavigate()
  const { role } = useRole()
  const lifecycle = useServerLifecycle()
  const busy = lifecycle.busyOf(hero.user)
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <h2 style={{ fontSize: 16, margin: 0 }}>Server</h2>
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {running && hero.upgradeAvailable && (
              <NotificationPill type="info" label="Upgrade available" title="A newer lab image is available locally - stop your server and start a new one to upgrade" />
            )}
            <StatusPill status={hero.status} label={hero.statusLabel} />
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 24, flexWrap: 'wrap' }}>
          {running ? (
            <>
              <Button type="primary" icon={<Icon name="play" size={15} filled />} disabled={!!busy} onClick={() => window.location.assign(userServerUrl(hero.user))}>
                Open lab
              </Button>
              <Button icon={<Icon name="restart" size={16} />} loading={busy === 'restart'} disabled={!!busy} onClick={() => lifecycle.restart(hero.user)}>
                Restart
              </Button>
              <Button danger icon={<Icon name="stop" size={14} filled />} loading={busy === 'stop'} disabled={!!busy} onClick={() => lifecycle.stop(hero.user)}>
                Stop
              </Button>
            </>
          ) : (
            <>
              <Button type="primary" icon={<Icon name="play" size={15} filled />} disabled={!!busy} onClick={() => navigate(`/servers/${hero.user}/starting`)}>
                Start server
              </Button>
              {role === 'admin' && (
                <Button icon={<Icon name="disk" size={15} />} disabled={!!busy} onClick={() => navigate(`/servers/${hero.user}/volumes`)}>
                  Manage volumes
                </Button>
              )}
            </>
          )}
        </div>
        {running && (
          <div style={{ marginTop: 20 }}>
            <TtlGadget timeLeftMin={hero.ttl.timeLeftMin} baseMin={hero.ttl.baseMin} maxAddHours={hero.ttl.maxAddHours} uptimeLabel={hero.startedISO ? timeAgoShort(hero.startedISO) : undefined} onExtend={(h) => extendSession(hero.user, h)} />
          </div>
        )}
      </Card>
      <Card>
        <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>{resourcesTitle}</h3>
        <ResourceBars
          rows={[
            { label: 'CPU', value: hero.resources.cpu, tip: hero.resources.cpuTip },
            { label: 'Memory', value: hero.resources.mem, tip: hero.resources.memTip },
            // per-server GPU usage is not tracked - show the row only when there is
            // GPU data to show (utilisation or inventory), never a fabricated 0%
            ...(hero.resources.gpus !== undefined || hero.resources.gpuDevices !== undefined
              ? [{ label: 'GPU', value: hero.resources.gpu, gpus: hero.resources.gpus, gpuDevices: hero.resources.gpuDevices }]
              : []),
            {
              label: 'Activity',
              value: 0,
              valueLabel: '',
              meter: <ActivityMeterFill value={running ? hero.activity : 0} hours={running ? hero.activityHours : null} pct={running ? hero.activityPct : null} />,
            },
          ]}
        />
      </Card>
    </div>
  )
}
