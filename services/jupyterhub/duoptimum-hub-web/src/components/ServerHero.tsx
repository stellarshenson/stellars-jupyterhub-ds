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
import { timeAgoShort, stoppedAgo } from '../lib/format'
import { useRole } from '../app/RoleContext'
import { usePref } from '../app/PrefsContext'
import { useServerLifecycle } from '../app/ServerLifecycle'
import { useUserVolumes } from '../hooks/queries'
import { hasVolumes } from '../lib/volumes'
import type { ServerHero as Hero } from '../services/types'

// the hero only renders on Home, so the sub-screens it opens (Start, Manage
// volumes) and their breadcrumb return to Home
const HERO_ORIGIN = { to: '/home', label: 'Home' }

export function ServerHero({ hero, resourcesTitle }: { hero: Hero; resourcesTitle: string }) {
  const running = hero.status === 'active' || hero.status === 'idle'
  const navigate = useNavigate()
  const { role } = useRole()
  const lifecycle = useServerLifecycle()
  const busy = lifecycle.busyOf(hero.user)
  // becoming-ready window (just started/restarted, lab not yet serving): the Open
  // control reads "Starting" with a spinner and stays disabled until the lab truly
  // answers (DEF-25)
  const opening = running && !lifecycle.isServing(hero.user)
  // CPU display mode for the Server Status bar (label only - the fill is unchanged)
  const cpuMode = usePref('cpuModeServerStatus')
  const cpuLabel = cpuMode === 'cores' && hero.resources.cpuAggregateLabel ? hero.resources.cpuAggregateLabel : `${hero.resources.cpu}%`
  // Manage Volumes is always shown but DISABLED when the user has no persistent volumes
  // (created on first spawn) - a user who never started a server has none to manage (operator)
  const { data: userVolumes = [] } = useUserVolumes(hero.user)
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <h2 style={{ fontSize: 16, margin: 0 }}>My Server Control</h2>
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {/* the "Update available" advisory sits to the LEFT of the status pill (operator) */}
            {running && hero.upgradeAvailable && (
              <NotificationPill type="info" label="Update available" title="A newer lab image is available locally - stop your server and start a new one to update" />
            )}
            <StatusPill status={hero.status} label={hero.statusLabel} />
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 24, flexWrap: 'wrap' }}>
          {running ? (
            <>
              <Button type="primary" icon={<Icon name="play" size={15} filled />} loading={opening} disabled={!!busy || opening} onClick={() => window.location.assign(userServerUrl(hero.user))}>
                {opening ? 'Starting' : 'Open Lab'}
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
              <Button type="primary" icon={<Icon name="play" size={15} filled />} disabled={!!busy} onClick={() => navigate(`/servers/${hero.user}/starting`, { state: { from: HERO_ORIGIN } })}>
                Start Server
              </Button>
              {/* Manage Volumes is admin-only here by design (a non-admin owner resets their
               * own volumes from the dedicated self-service screen); always shown but DISABLED
               * when the user has no volumes to manage */}
              {role === 'admin' && (
                <Button icon={<Icon name="disk" size={15} />} disabled={!!busy || !hasVolumes(userVolumes)} title={hasVolumes(userVolumes) ? undefined : 'No volumes to manage'} onClick={() => navigate(`/servers/${hero.user}/volumes`, { state: { from: HERO_ORIGIN } })}>
                  Manage Volumes
                </Button>
              )}
            </>
          )}
        </div>
        {running ? (
          <div style={{ marginTop: 20 }}>
            <TtlGadget timeLeftMin={hero.ttl.timeLeftMin} baseMin={hero.ttl.baseMin} maxAddHours={hero.ttl.maxAddHours} uptimeLabel={hero.startedISO ? timeAgoShort(hero.startedISO) : undefined} uptimeSince={hero.startedISO ?? undefined} onExtend={(h) => extendSession(hero.user, h)} />
          </div>
        ) : hero.status === 'error' ? (
          // error: the server is in a FAILED state - say so (danger) and prompt a retry,
          // never the milder "stopped Xago" which understates a failure under a red pill
          <div style={{ marginTop: 20, fontSize: 'var(--text-sm)', color: 'var(--color-danger)' }}>
            {hero.statusLabel || 'Server error'} - try starting it again
          </div>
        ) : hero.status !== 'spawning' ? (
          // stopped: no live idle timer - state how long ago it stopped, or that it
          // was never started (no recoverable last-activity time). not a bar.
          <div className="doh-muted" style={{ marginTop: 20, fontSize: 'var(--text-sm)' }}>
            {stoppedAgo(hero.lastActivityISO)}
          </div>
        ) : null}
      </Card>
      <Card>
        <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>{resourcesTitle}</h3>
        <ResourceBars
          rows={[
            { label: 'CPU', value: hero.resources.cpu, valueLabel: cpuLabel, tip: hero.resources.cpuTip },
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
              // Activity is a 7-DAY engagement metric (decays over ~3 days), NOT a
              // live reading - it is meaningful whether or not the server runs right
              // now, exactly like the Servers/Users meters (see liveSource
              // activityFields). A `running ?` gate here was the regression that
              // zeroed the hero meter for an offline-but-active user.
              meter: <ActivityMeterFill value={hero.activity} hours={hero.activityHours} pct={hero.activityPct} />,
            },
          ]}
        />
      </Card>
    </div>
  )
}
