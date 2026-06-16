/* Server lifecycle progress popups. start / restart / stop each open a modal with
 * a progress bar tied to the real hub state, and expose a `busy` map so the server
 * widgets disable conflicting controls while a transition is in flight.
 *
 * On completion the popup resolves itself (no manual click):
 *   - start your OWN server -> immediately move into the new lab
 *   - start someone else's server (admin) -> return to the parent screen
 *   - restart / stop -> return to the parent screen once it settles
 * Failures keep the popup open with an error + Close.
 *
 * start streams the hub's spawn-progress (SSE; `_xsrf` in the query string because
 * EventSource cannot set headers), falling back to a status poll if the stream
 * ends without a ready event. restart / stop poll the status until it settles. */
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react'
import { Button, Modal, Progress } from 'antd'
import { getDataSource } from '../services/datasource'
import { isMock } from '../services/dataMode'
import { invalidate } from '../services/actions'
import { useRole } from './RoleContext'
import { restartServer, startServer, stopServer } from '../services/ops'
import { hubUrl, userServerUrl, xsrfToken } from '../services/hub/client'

type Mode = 'start' | 'restart' | 'stop'
type Phase = 'busy' | 'done' | 'error'

interface Lifecycle {
  start: (user: string) => void
  restart: (user: string) => void
  stop: (user: string) => void
  busyOf: (user: string) => Mode | null
}

const Ctx = createContext<Lifecycle | null>(null)

export function useServerLifecycle(): Lifecycle {
  const c = useContext(Ctx)
  if (!c) throw new Error('useServerLifecycle must be used within ServerLifecycleProvider')
  return c
}

const TITLE: Record<Mode, string> = { start: 'Starting server', restart: 'Restarting server', stop: 'Stopping server' }
const isRunning = (s: string) => s === 'active' || s === 'idle' || s === 'spawning'

interface ModalState {
  open: boolean
  user: string
  mode: Mode
  percent: number
  message: string
  phase: Phase
  indeterminate: boolean
}

export function ServerLifecycleProvider({ children }: { children: ReactNode }) {
  const { username } = useRole()
  const [busy, setBusy] = useState<Record<string, Mode>>({})
  const [st, setSt] = useState<ModalState>({ open: false, user: '', mode: 'start', percent: 0, message: '', phase: 'busy', indeterminate: false })
  const esRef = useRef<EventSource | null>(null)

  const clearBusy = useCallback((user: string) => setBusy((b) => { const n = { ...b }; delete n[user]; return n }), [])
  const refresh = useCallback((user: string) => invalidate(['servers'], ['hero', user], ['resources'], ['stats']), [])

  const close = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
    setSt((s) => ({ ...s, open: false }))
  }, [])

  // Resolve a finished transition. Success: start-your-own moves into the new lab;
  // everything else returns to the parent screen (auto-close). Failure: keep the
  // popup open with the error so it can be read + dismissed.
  const settle = useCallback(
    (user: string, mode: Mode, ok: boolean, doneMsg: string, errMsg: string) => {
      clearBusy(user)
      refresh(user)
      if (!ok) {
        setSt((s) => ({ ...s, indeterminate: false, phase: 'error', message: errMsg }))
        return
      }
      setSt((s) => ({ ...s, indeterminate: false, percent: 100, phase: 'done', message: doneMsg }))
      if (mode === 'start' && user === username && !isMock()) {
        // immediately move to the freshly started server
        window.setTimeout(() => window.location.assign(userServerUrl(user)), 400)
      } else {
        // return to the parent screen
        window.setTimeout(() => close(), 800)
      }
    },
    [username, clearBusy, refresh, close],
  )

  // Poll server status until `pred` holds or ~90s elapse. Returns whether it held.
  const pollUntil = useCallback(async (user: string, pred: (status: string) => boolean) => {
    const deadline = Date.now() + 90_000
    while (Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 1500))
      try {
        const servers = await getDataSource().getServers()
        const row = servers.find((s) => s.user === user)
        if (pred(row?.status ?? 'offline')) return true
      } catch { /* transient - keep polling */ }
    }
    return false
  }, [])

  const start = useCallback((user: string) => {
    setBusy((b) => ({ ...b, [user]: 'start' }))
    setSt({ open: true, user, mode: 'start', percent: 5, message: 'Requesting spawn…', phase: 'busy', indeterminate: false })
    startServer(user).catch(() => {})

    if (isMock()) {
      let p = 5
      const t = window.setInterval(() => {
        p = Math.min(100, p + 19)
        setSt((s) => (s.open && s.mode === 'start' ? { ...s, percent: p, message: p < 100 ? 'Spawning…' : 'Ready' } : s))
        if (p >= 100) { window.clearInterval(t); settle(user, 'start', true, 'Ready', '') }
      }, 320)
      return
    }

    // EventSource can't set headers; pass the xsrf token as a query param.
    const token = xsrfToken()
    const url = hubUrl(`/api/users/${encodeURIComponent(user)}/server/progress${token ? `?_xsrf=${encodeURIComponent(token)}` : ''}`)
    const es = new EventSource(url, { withCredentials: true })
    esRef.current = es
    let resolved = false
    es.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data) as { progress?: number; message?: string; ready?: boolean; failed?: boolean }
        setSt((s) => ({ ...s, percent: typeof d.progress === 'number' ? d.progress : s.percent, message: d.message ?? s.message }))
        if (d.ready) { resolved = true; es.close(); settle(user, 'start', true, 'Ready', '') }
        else if (d.failed) { resolved = true; es.close(); settle(user, 'start', false, '', d.message ?? 'Spawn failed') }
      } catch { /* ignore a malformed frame */ }
    }
    es.onerror = () => {
      es.close()
      if (resolved) return
      // stream closed without a ready event - confirm via a status poll
      pollUntil(user, isRunning).then((ok) => settle(user, 'start', ok, 'Ready', 'Could not confirm spawn'))
    }
  }, [settle, pollUntil])

  const restart = useCallback(async (user: string) => {
    setBusy((b) => ({ ...b, [user]: 'restart' }))
    setSt({ open: true, user, mode: 'restart', percent: 0, message: 'Restarting container…', phase: 'busy', indeterminate: true })
    try {
      await restartServer(user)
    } catch {
      settle(user, 'restart', false, '', 'Restart failed'); return
    }
    const ok = await pollUntil(user, isRunning)
    settle(user, 'restart', ok, 'Running', 'Restart did not complete')
  }, [settle, pollUntil])

  const stop = useCallback(async (user: string) => {
    setBusy((b) => ({ ...b, [user]: 'stop' }))
    setSt({ open: true, user, mode: 'stop', percent: 0, message: 'Stopping server…', phase: 'busy', indeterminate: true })
    try {
      await stopServer(user)
    } catch {
      settle(user, 'stop', false, '', 'Stop failed'); return
    }
    const ok = await pollUntil(user, (s) => s === 'offline')
    settle(user, 'stop', ok, 'Stopped', 'Stop did not complete')
  }, [settle, pollUntil])

  const busyOf = useCallback((user: string) => busy[user] ?? null, [busy])

  const stroke = st.phase === 'error' ? 'var(--color-danger)' : st.phase === 'done' ? 'var(--color-success)' : 'var(--color-accent)'

  return (
    <Ctx.Provider value={{ start, restart, stop, busyOf }}>
      {children}
      <Modal
        open={st.open}
        title={TITLE[st.mode]}
        onCancel={close}
        maskClosable={st.phase === 'error'}
        closable={st.phase === 'error'}
        keyboard={st.phase === 'error'}
        footer={st.phase === 'busy' ? null : [<Button key="close" type="primary" onClick={close}>Close</Button>]}
      >
        <p style={{ marginBottom: 12 }}>{st.message}</p>
        <Progress
          percent={st.indeterminate && st.phase === 'busy' ? 100 : st.percent}
          showInfo={!st.indeterminate || st.phase !== 'busy'}
          status={st.phase === 'error' ? 'exception' : st.indeterminate && st.phase === 'busy' ? 'active' : undefined}
          strokeColor={stroke}
        />
      </Modal>
    </Ctx.Provider>
  )
}
