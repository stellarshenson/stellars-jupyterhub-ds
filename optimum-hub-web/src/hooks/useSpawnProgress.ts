import { useEffect, useRef, useState } from 'react'
import { startServer } from '../services/ops'
import { hubUrl, xsrfToken } from '../services/hub/client'
import { isMock } from '../services/dataMode'
import { getDataSource } from '../services/datasource'

export type SpawnPhase = 'spawning' | 'ready' | 'failed'
export interface SpawnProgress {
  percent: number
  message: string
  phase: SpawnPhase
}

const isRunning = (s: string) => s === 'active' || s === 'idle' || s === 'spawning'

/* Drives a single server spawn and reports live progress - the data half of the
 * Start-server page (the page owns presentation + the redirect-on-ready policy).
 *
 * The page is deep-linkable and an admin can land on another user's RUNNING lab,
 * so it never blindly POSTs: it confirms current status first - already up (active
 * /idle) jumps straight to "ready"; mid-spawn follows progress WITHOUT re-POSTing;
 * only a truly offline server is spawned (once). It then follows the hub
 * spawn-progress SSE (`_xsrf` in the query string because EventSource cannot set
 * headers), falling back to a bounded status poll if the stream drops before a
 * terminal event. Mock mode animates a canned ramp. All timers + the EventSource
 * are torn down on unmount - nothing leaks. */
export function useSpawnProgress(user: string): SpawnProgress {
  const [state, setState] = useState<SpawnProgress>({ percent: 5, message: 'Requesting spawn…', phase: 'spawning' })
  const posted = useRef(false)

  useEffect(() => {
    let cancelled = false
    let es: EventSource | null = null
    const timers: number[] = []

    if (isMock()) {
      let p = 5
      const t = window.setInterval(() => {
        p = Math.min(100, p + 12)
        setState({ percent: p, message: p < 100 ? 'Spawning…' : 'Ready', phase: p < 100 ? 'spawning' : 'ready' })
        if (p >= 100) window.clearInterval(t)
      }, 360)
      timers.push(t)
      return () => { cancelled = true; timers.forEach(window.clearInterval) }
    }

    // Follow the hub spawn-progress SSE; creep the bar toward ~90% (the hub emits
    // only a couple of events for a fast/cached spawn, which otherwise reads as
    // "sit at 10% then snap to 100%"). Real SSE values jump it ahead (never
    // backwards); a dropped stream confirms readiness via a bounded poll.
    const beginStream = () => {
      const token = xsrfToken()
      const url = hubUrl(`/api/users/${encodeURIComponent(user)}/server/progress${token ? `?_xsrf=${encodeURIComponent(token)}` : ''}`)
      es = new EventSource(url, { withCredentials: true })
      let resolved = false

      const creep = window.setInterval(() => {
        setState((s) => (s.phase === 'spawning' && s.percent < 90 ? { ...s, percent: s.percent + 2 } : s))
      }, 450)
      timers.push(creep)

      es.onmessage = (ev) => {
        try {
          const d = JSON.parse(ev.data) as { progress?: number; message?: string; ready?: boolean; failed?: boolean }
          setState((s) => ({
            percent: typeof d.progress === 'number' ? d.progress : s.percent,
            message: d.message ?? s.message,
            phase: d.ready ? 'ready' : d.failed ? 'failed' : 'spawning',
          }))
          if (d.ready || d.failed) { resolved = true; es?.close() }
        } catch { /* ignore a malformed frame */ }
      }

      es.onerror = () => {
        es?.close()
        if (resolved || cancelled) return
        // Stream dropped without a terminal event - confirm via a bounded status poll.
        const deadline = Date.now() + 90_000
        const poll = window.setInterval(async () => {
          try {
            const servers = await getDataSource().getServers()
            const row = servers.find((s) => s.user === user)
            if (row && isRunning(row.status)) {
              window.clearInterval(poll)
              if (!cancelled) setState((s) => ({ ...s, percent: 100, phase: 'ready' }))
            } else if (Date.now() > deadline) {
              window.clearInterval(poll)
              if (!cancelled) setState((s) => ({ ...s, phase: 'failed', message: 'Could not confirm spawn' }))
            }
          } catch {
            if (Date.now() > deadline) {
              window.clearInterval(poll)
              if (!cancelled) setState((s) => ({ ...s, phase: 'failed', message: 'Could not confirm spawn' }))
            }
          }
        }, 1500)
        timers.push(poll)
      }
    }

    ;(async () => {
      // Confirm the server is actually offline before spawning - a deep-link or an
      // admin landing on a running lab must not POST a spurious spawn at a live
      // session.
      try {
        const servers = await getDataSource().getServers()
        if (cancelled) return
        const status = servers.find((s) => s.user === user)?.status
        if (status === 'active' || status === 'idle') {
          setState({ percent: 100, message: 'Already running', phase: 'ready' })
          return
        }
        if (cancelled) return
        // truly offline -> spawn once; already-spawning -> just follow progress
        if (status !== 'spawning' && !posted.current) {
          posted.current = true
          startServer(user).catch(() => {}) // progress is observed via SSE
        }
      } catch {
        // status unknown - attempt the spawn once and follow progress
        if (cancelled) return
        if (!posted.current) {
          posted.current = true
          startServer(user).catch(() => {})
        }
      }
      if (!cancelled) beginStream()
    })()

    return () => { cancelled = true; es?.close(); timers.forEach(window.clearInterval) }
  }, [user])

  return state
}
