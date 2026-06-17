/* Server lifecycle progress popups for restart / stop: each opens a modal with a
 * progress bar tied to the real hub state, and exposes a `busy` map so the server
 * widgets disable conflicting controls while a transition is in flight. On success
 * the popup auto-closes back to the parent screen; failures keep it open with an
 * error + Close.
 *
 * Starting a server is deliberately NOT handled here - it navigates to the
 * dedicated Start-server page (`/servers/:name/starting`), which owns the spawn
 * progress bar and the live container-log tail (see pages/Starting.tsx). */
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { Button, Modal, Progress } from 'antd'
import { getDataSource } from '../services/datasource'
import { invalidate } from '../services/actions'
import { restartServer, stopServer } from '../services/ops'

type Mode = 'restart' | 'stop'
type Phase = 'busy' | 'done' | 'error'

interface Lifecycle {
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

const TITLE: Record<Mode, string> = { restart: 'Restarting server', stop: 'Stopping server' }
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
  const [st, setSt] = useState<ModalState>({ open: false, user: '', mode: 'restart', percent: 0, message: '', phase: 'busy', indeterminate: false })

  const clearBusy = useCallback((user: string) => setBusy((b) => { const n = { ...b }; delete n[user]; return n }), [])
  const refresh = useCallback((user: string) => invalidate(['servers'], ['hero', user], ['resources'], ['stats']), [])
  const close = useCallback(() => setSt((s) => ({ ...s, open: false })), [])

  // Resolve a finished transition: success auto-closes back to the parent screen;
  // failure keeps the popup open with the error so it can be read + dismissed.
  const settle = useCallback(
    (user: string, ok: boolean, doneMsg: string, errMsg: string) => {
      clearBusy(user)
      refresh(user)
      if (!ok) {
        setSt((s) => ({ ...s, indeterminate: false, phase: 'error', message: errMsg }))
        return
      }
      setSt((s) => ({ ...s, indeterminate: false, percent: 100, phase: 'done', message: doneMsg }))
      window.setTimeout(() => close(), 800)
    },
    [clearBusy, refresh, close],
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

  const restart = useCallback(async (user: string) => {
    setBusy((b) => ({ ...b, [user]: 'restart' }))
    setSt({ open: true, user, mode: 'restart', percent: 0, message: 'Restarting container…', phase: 'busy', indeterminate: true })
    try {
      await restartServer(user)
    } catch {
      settle(user, false, '', 'Restart failed'); return
    }
    const ok = await pollUntil(user, isRunning)
    settle(user, ok, 'Running', 'Restart did not complete')
  }, [settle, pollUntil])

  const stop = useCallback(async (user: string) => {
    setBusy((b) => ({ ...b, [user]: 'stop' }))
    setSt({ open: true, user, mode: 'stop', percent: 0, message: 'Stopping server…', phase: 'busy', indeterminate: true })
    try {
      await stopServer(user)
    } catch {
      settle(user, false, '', 'Stop failed'); return
    }
    const ok = await pollUntil(user, (s) => s === 'offline')
    settle(user, ok, 'Stopped', 'Stop did not complete')
  }, [settle, pollUntil])

  const busyOf = useCallback((user: string) => busy[user] ?? null, [busy])

  const stroke = st.phase === 'error' ? 'var(--color-danger)' : st.phase === 'done' ? 'var(--color-success)' : 'var(--color-accent)'

  return (
    <Ctx.Provider value={{ restart, stop, busyOf }}>
      {children}
      <Modal
        open={st.open}
        title={TITLE[st.mode]}
        onCancel={close}
        maskClosable={st.phase === 'error'}
        closable={st.phase === 'error'}
        keyboard={st.phase === 'error'}
        footer={st.phase === 'error' ? [<Button key="close" type="primary" onClick={close}>Close</Button>] : null}
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
