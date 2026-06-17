/* Server restart / stop lifecycle. Runs the transition in the background and
 * exposes a `busy` map so the controls show an INLINE spinner (no modal popup):
 * the op fires (its `run()` toasts + invalidates), then a background monitor polls
 * the real hub status until the transition completes and refreshes the affected
 * views immediately. A failed POST is surfaced by the op's own error toast.
 *
 * Starting a server is handled by the dedicated Start-server page
 * (`/servers/:name/starting`), which owns the spawn progress + log tail. */
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { getDataSource } from '../services/datasource'
import { invalidate } from '../services/actions'
import { restartServer, stopServer } from '../services/ops'

type Mode = 'restart' | 'stop'

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

const isRunning = (s: string) => s === 'active' || s === 'idle' || s === 'spawning'

export function ServerLifecycleProvider({ children }: { children: ReactNode }) {
  const [busy, setBusy] = useState<Record<string, Mode>>({})

  const clearBusy = useCallback((user: string) => setBusy((b) => { const n = { ...b }; delete n[user]; return n }), [])
  const refresh = useCallback((user: string) => invalidate(['servers'], ['hero', user], ['resources'], ['stats']), [])

  // Poll the real server status until `pred` holds or ~90s elapse - the background
  // monitor that reports completion so we can refresh immediately.
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

  const runOp = useCallback(
    async (user: string, mode: Mode, op: (u: string) => Promise<unknown>, pred: (s: string) => boolean) => {
      setBusy((b) => ({ ...b, [user]: mode }))
      try {
        await op(user) // run() toasts success/error + invalidates the server keys
      } catch {
        clearBusy(user) // the op already toasted the failure
        return
      }
      await pollUntil(user, pred) // monitor until the transition lands
      clearBusy(user)
      refresh(user) // immediate refresh on completion
    },
    [clearBusy, refresh, pollUntil],
  )

  const restart = useCallback((user: string) => { void runOp(user, 'restart', restartServer, isRunning) }, [runOp])
  const stop = useCallback((user: string) => { void runOp(user, 'stop', stopServer, (s) => s === 'offline') }, [runOp])
  const busyOf = useCallback((user: string) => busy[user] ?? null, [busy])

  return <Ctx.Provider value={{ restart, stop, busyOf }}>{children}</Ctx.Provider>
}
