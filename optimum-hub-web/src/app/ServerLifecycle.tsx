/* Server lifecycle progress popups. start / restart / stop each open a modal with
 * a progress bar tied to the real hub state, and expose a `busy` map so the server
 * widgets disable conflicting controls while a transition is in flight.
 *
 * - start: streams the hub's spawn-progress (SSE; `_xsrf` goes in the query string
 *   because EventSource cannot set headers), falling back to a status poll if the
 *   stream ends without a ready event.
 * - restart / stop: no spawn stream exists (container.restart / server delete), so
 *   they poll the server status until it settles. */
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react'
import { Button, Modal, Progress } from 'antd'
import { getDataSource } from '../services/datasource'
import { isMock } from '../services/dataMode'
import { invalidate } from '../services/actions'
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
        if (p >= 100) { window.clearInterval(t); setSt((s) => ({ ...s, phase: 'done' })); clearBusy(user); refresh(user) }
      }, 320)
      return
    }

    // EventSource can't set headers; pass the xsrf token as a query param.
    const token = xsrfToken()
    const url = hubUrl(`/api/users/${encodeURIComponent(user)}/server/progress${token ? `?_xsrf=${encodeURIComponent(token)}` : ''}`)
    const es = new EventSource(url, { withCredentials: true })
    esRef.current = es
    let settled = false
    es.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data) as { progress?: number; message?: string; ready?: boolean; failed?: boolean }
        setSt((s) => ({ ...s, percent: typeof d.progress === 'number' ? d.progress : s.percent, message: d.message ?? s.message }))
        if (d.ready) { settled = true; es.close(); setSt((s) => ({ ...s, percent: 100, phase: 'done', message: 'Ready' })); clearBusy(user); refresh(user) }
        else if (d.failed) { settled = true; es.close(); setSt((s) => ({ ...s, phase: 'error', message: d.message ?? 'Spawn failed' })); clearBusy(user); refresh(user) }
      } catch { /* ignore a malformed frame */ }
    }
    es.onerror = () => {
      es.close()
      if (settled) return
      // stream closed without a ready event - confirm via a status poll
      pollUntil(user, isRunning).then((ok) => {
        setSt((s) => ({ ...s, percent: ok ? 100 : s.percent, phase: ok ? 'done' : 'error', message: ok ? 'Ready' : 'Could not confirm spawn' }))
        clearBusy(user); refresh(user)
      })
    }
  }, [clearBusy, refresh, pollUntil])

  const restart = useCallback(async (user: string) => {
    setBusy((b) => ({ ...b, [user]: 'restart' }))
    setSt({ open: true, user, mode: 'restart', percent: 0, message: 'Restarting container…', phase: 'busy', indeterminate: true })
    try {
      await restartServer(user)
    } catch {
      setSt((s) => ({ ...s, indeterminate: false, phase: 'error', message: 'Restart failed' })); clearBusy(user); return
    }
    const ok = await pollUntil(user, isRunning)
    setSt((s) => ({ ...s, indeterminate: false, percent: 100, phase: ok ? 'done' : 'error', message: ok ? 'Running' : 'Restart did not complete' }))
    clearBusy(user); refresh(user)
  }, [clearBusy, refresh, pollUntil])

  const stop = useCallback(async (user: string) => {
    setBusy((b) => ({ ...b, [user]: 'stop' }))
    setSt({ open: true, user, mode: 'stop', percent: 0, message: 'Stopping server…', phase: 'busy', indeterminate: true })
    try {
      await stopServer(user)
    } catch {
      setSt((s) => ({ ...s, indeterminate: false, phase: 'error', message: 'Stop failed' })); clearBusy(user); return
    }
    const ok = await pollUntil(user, (s) => s === 'offline')
    setSt((s) => ({ ...s, indeterminate: false, percent: 100, phase: ok ? 'done' : 'error', message: ok ? 'Stopped' : 'Stop did not complete' }))
    clearBusy(user); refresh(user)
  }, [clearBusy, refresh, pollUntil])

  const busyOf = useCallback((user: string) => busy[user] ?? null, [busy])

  const stroke = st.phase === 'error' ? 'var(--color-danger)' : st.phase === 'done' ? 'var(--color-success)' : 'var(--color-accent)'
  const showLab = st.phase === 'done' && st.mode !== 'stop'

  return (
    <Ctx.Provider value={{ start, restart, stop, busyOf }}>
      {children}
      <Modal
        open={st.open}
        title={TITLE[st.mode]}
        onCancel={close}
        maskClosable={st.phase !== 'busy'}
        closable={st.phase !== 'busy'}
        keyboard={st.phase !== 'busy'}
        footer={
          st.phase === 'busy'
            ? null
            : showLab
              ? [
                  <Button key="close" onClick={close}>Close</Button>,
                  <Button key="lab" type="primary" onClick={() => { close(); window.location.assign(userServerUrl(st.user)) }}>Open lab</Button>,
                ]
              : [<Button key="close" type="primary" onClick={close}>Close</Button>]
        }
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
