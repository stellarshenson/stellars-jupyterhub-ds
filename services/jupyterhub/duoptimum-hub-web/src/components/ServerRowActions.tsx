/* Per-row server lifecycle actions, shared by the Servers list and the Home
 * "Active servers" widget so both behave IDENTICALLY (background start for own +
 * other, enter, restart, stop, manage volumes, spawning cancel). `from` (optional)
 * tags the navigation origin so the sub-screen it opens (Manage volumes) and its
 * breadcrumb return to where the action was invoked, not a hardcoded parent. */
import { Spin } from 'antd'
import type { NavigateFunction } from 'react-router-dom'
import { IconAction } from './IconAction'
import { userServerUrl } from '../services/hub/client'
import { appModal } from '../services/actions'
import { useUserVolumes } from '../hooks/queries'
import { hasVolumes } from '../lib/volumes'
import type { useServerLifecycle } from '../app/ServerLifecycle'
import type { ServerRow } from '../services/types'

// the Manage-volumes affordance is ALWAYS present but DISABLED when the user has no volumes
// (a brand-new or just-reset user has none) - own per-row volume query; the icon keeps its place
// with an explanatory tooltip rather than vanishing, so the action row is predictable.
function ManageVolumesAction({ user, busy, onOpen }: { user: string; busy: boolean; onOpen: () => void }) {
  const { data: volumes } = useUserVolumes(user)
  const none = !hasVolumes(volumes)
  return <IconAction icon="disk" title={none ? 'No volumes to manage' : 'Manage volumes'} disabled={busy || none} onClick={onOpen} />
}

type Lifecycle = ReturnType<typeof useServerLifecycle>
export interface NavOrigin {
  to: string
  label: string
}

// entering another user's running lab confirms first (you act inside their env);
// your own opens straight through.
function enterSession(user: string, me: string) {
  if (user === me) {
    window.location.assign(userServerUrl(user))
    return
  }
  appModal.confirm({
    title: `Open ${user}'s server?`,
    content: `You are about to enter another user's lab. Everything you do happens inside ${user}'s environment. JupyterHub will ask you to authorize the access.`,
    okText: 'Open',
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
        <ManageVolumesAction user={r.user} busy={busy} onOpen={() => nav(`/servers/${r.user}/volumes`)} />
      </div>
    )
  }
  // becoming-ready window (just started/restarted, lab not yet serving): the enter
  // action shows a spinner and stays disabled until the lab truly answers (DEF-25)
  const opening = !lf.isServing(r.user)
  return (
    <div className="doh-row doh-actions" style={{ justifyContent: 'flex-end' }}>
      <IconAction icon="play" title={opening ? 'Opening…' : r.user === me ? 'Enter session' : `Open ${r.user}'s session`} tone="primary" busy={opening} disabled={busy || opening} onClick={() => enterSession(r.user, me)} />
      <IconAction icon="restart" title="Restart" busy={mode === 'restart'} disabled={busy} onClick={() => lf.restart(r.user)} />
      <IconAction icon="stop" title="Stop" tone="danger" filled busy={mode === 'stop'} disabled={busy} onClick={() => lf.stop(r.user)} />
    </div>
  )
}
