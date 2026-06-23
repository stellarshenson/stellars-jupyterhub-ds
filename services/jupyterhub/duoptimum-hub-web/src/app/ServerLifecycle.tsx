/* Server start / restart / stop lifecycle. Runs the transition in the background
 * and exposes a `busy` map so the controls show an INLINE spinner (no modal, no
 * navigation): the op fires (its `run()` toasts + invalidates), then a background
 * monitor polls the real hub status until the transition completes and refreshes
 * the affected views immediately. A failed POST is surfaced by the op's error toast.
 *
 * `start` is for starting ANOTHER user's server inline (admin action) - a user
 * starting their OWN server still goes through the dedicated Start-server page
 * (`/servers/:name/starting`), which owns the spawn progress + log tail. */
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react'
import { getDataSource } from '../services/datasource'
import { invalidate } from '../services/actions'
import { restartServer, startServer, stopServer } from '../services/ops'
import { waitForLabReady } from '../services/hub/labReady'

type Mode = 'start' | 'restart' | 'stop'

interface Lifecycle {
  start: (user: string) => void
  restart: (user: string) => void
  stop: (user: string) => void
  busyOf: (user: string) => Mode | null
  // false while a just-started/restarted server is running but the lab is not yet
  // serving HTTP (the becoming-ready window) - the Open controls gate on this so
  // they never enter a lab that lands on the spawn-pending/503 page (DEF-25).
  // Optimistic: true by default (a server running since page load is assumed up);
  // only a start/restart this session opens the gate.
  isServing: (user: string) => boolean
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
  // becoming-ready: user is running but the lab is not yet confirmed serving after
  // a start/restart this session. Absent = serving (optimistic) - see isServing.
  const [pending, setPending] = useState<Record<string, boolean>>({})
  // per-user generation: each start/restart bumps it; a settle only closes the gate
  // it opened (its gen is still current), so a stale settle from an EARLIER op cannot
  // clear the gate a NEWER op opened - which would prematurely activate Open while the
  // newer op's lab is still booting (the exact DEF-25 503, reachable by a restart
  // during the becoming-ready window).
  const gen = useRef<Record<string, number>>({})

  const clearBusy = useCallback((user: string) => setBusy((b) => { const n = { ...b }; delete n[user]; return n }), [])
  const clearPending = useCallback((user: string) => setPending((p) => { if (!(user in p)) return p; const n = { ...p }; delete n[user]; return n }), [])
  // open the becoming-ready gate, returning this op's generation
  const openGate = useCallback((user: string) => { const g = (gen.current[user] ?? 0) + 1; gen.current[user] = g; setPending((p) => ({ ...p, [user]: true })); return g }, [])
  // close the gate only if no newer op has opened it since (generation still current)
  const closeGate = useCallback((user: string, g: number) => { if (gen.current[user] === g) clearPending(user) }, [clearPending])
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
    async (user: string, mode: Mode, op: (u: string) => Promise<unknown>, pred: (s: string) => boolean,
           g?: number) => {
      setBusy((b) => ({ ...b, [user]: mode }))
      try {
        await op(user) // run() toasts success/error + invalidates the server keys
      } catch {
        clearBusy(user) // the op already toasted the failure
        if (g !== undefined) closeGate(user, g) // never strand the gate on a failed op
        return
      }
      const ok = await pollUntil(user, pred) // monitor until the transition lands
      clearBusy(user)
      refresh(user) // immediate refresh on completion
      if (g === undefined) return
      // reached running -> wait for the lab to truly serve before Open activates;
      // if it never reached running, drop the gate. closeGate is in `finally` so the
      // gate is ALWAYS released even if waitForLabReady ever throws (never strand
      // Open disabled); gen-guarded, so a newer start/restart still owns the gate.
      try {
        if (ok) await waitForLabReady(user)
      } finally {
        closeGate(user, g)
      }
    },
    [clearBusy, closeGate, refresh, pollUntil],
  )

  // start waits until the server is truly up (active/idle), not merely spawning,
  // so the inline spinner spans the whole spawn; the fast poll catches the flip.
  // start/restart open the becoming-ready gate; the lab-ready settle closes it.
  const start = useCallback((user: string) => { const g = openGate(user); void runOp(user, 'start', startServer, (s) => s === 'active' || s === 'idle', g) }, [runOp, openGate])
  const restart = useCallback((user: string) => { const g = openGate(user); void runOp(user, 'restart', restartServer, isRunning, g) }, [runOp, openGate])
  const stop = useCallback((user: string) => { clearPending(user); void runOp(user, 'stop', stopServer, (s) => s === 'offline') }, [runOp, clearPending])
  const busyOf = useCallback((user: string) => busy[user] ?? null, [busy])
  const isServing = useCallback((user: string) => !pending[user], [pending])

  return <Ctx.Provider value={{ start, restart, stop, busyOf, isServing }}>{children}</Ctx.Provider>
}
