/* Per-row server lifecycle actions, shared by the Servers list and the Home
 * "Active servers" widget so both behave IDENTICALLY (background start for own +
 * other, enter, restart, stop, manage volumes, spawning cancel). `from` (optional)
 * tags the navigation origin so the sub-screen it opens (Manage volumes) and its
 * breadcrumb return to where the action was invoked, not a hardcoded parent. */
import { Modal, Spin } from 'antd'
import type { NavigateFunction } from 'react-router-dom'
import { IconAction } from './IconAction'
import { userServerUrl } from '../services/hub/client'
import type { useServerLifecycle } from '../app/ServerLifecycle'
import type { ServerRow } from '../services/types'

type Lifecycle = ReturnType<typeof useServerLifecycle>
export interface NavOrigin {
  to: string
  label: string
}

// entering another user's running lab confirms first (you act inside their env);
// your own opens straight through.
export function enterSession(user: string, me: string) {
  if (user === me) {
    window.location.assign(userServerUrl(user))
    return
  }
  Modal.confirm({
    title: `Open ${user}'s server?`,
    content: `You are about to enter another user's lab. Everything you do happens inside ${user}'s environment.`,
    okText: `Open ${user}'s server`,
    cancelText: 'Cancel',
    onOk: () => window.location.assign(userServerUrl(user)),
  })
}

export function rowActions(r: ServerRow, navigate: NavigateFunction, lf: Lifecycle, me: string, from?: NavOrigin) {
  const mode = lf.busyOf(r.user) // 'start' | 'restart' | 'stop' | null
  const busy = !!mode
  // tag the navigation origin so the opened sub-screen + breadcrumb return here
  const nav = (to: string) => navigate(to, from ? { state: { from } } : undefined)
  if (r.status === 'spawning') {
    // a rotating spinner says "starting" (not the old ekg/activity glyph); Cancel
    // stops the in-flight spawn.
    return (
      <div className="doh-row doh-actions" style={{ justifyContent: 'flex-end', alignItems: 'center', gap: 6 }}>
        <Spin size="small" />
        <IconAction icon="stop" title="Cancel spawn" tone="danger" filled busy={mode === 'stop'} disabled={busy} onClick={() => lf.stop(r.user)} />
      </div>
    )
  }
  if (r.status === 'offline') {
    // start runs inline in the BACKGROUND here (spinner on the play button, no
    // navigation), monitored + refreshed like restart/stop - for OWN and other
    // servers alike. The foreground Start page (progress + log) is reached only
    // from the home ServerHero, never from this shared list/widget row.
    return (
      <div className="doh-row doh-actions" style={{ justifyContent: 'flex-end' }}>
        <IconAction icon="play" title={r.user === me ? 'Start server' : `Start ${r.user}'s server`} busy={mode === 'start'} disabled={busy} onClick={() => lf.start(r.user)} />
        <IconAction icon="disk" title="Manage volumes" disabled={busy} onClick={() => nav(`/servers/${r.user}/volumes`)} />
      </div>
    )
  }
  return (
    <div className="doh-row doh-actions" style={{ justifyContent: 'flex-end' }}>
      <IconAction icon="play" title={r.user === me ? 'Enter session' : `Open ${r.user}'s session`} tone="primary" disabled={busy} onClick={() => enterSession(r.user, me)} />
      <IconAction icon="restart" title="Restart" busy={mode === 'restart'} disabled={busy} onClick={() => lf.restart(r.user)} />
      <IconAction icon="stop" title="Stop" tone="danger" filled busy={mode === 'stop'} disabled={busy} onClick={() => lf.stop(r.user)} />
    </div>
  )
}
