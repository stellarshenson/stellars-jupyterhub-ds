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
 * Fires the spawn POST once, then follows the hub spawn-progress SSE (`_xsrf` in
 * the query string because EventSource cannot set headers). If the stream drops
 * before a terminal event it confirms readiness with a bounded status poll.
 * Mock mode animates a canned ramp so the design pages demo the flow. All timers
 * and the EventSource are torn down on unmount - nothing leaks. */
export function useSpawnProgress(user: string): SpawnProgress {
  const [state, setState] = useState<SpawnProgress>({ percent: 5, message: 'Requesting spawn…', phase: 'spawning' })
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return // strict-mode / re-render guard: spawn exactly once
    started.current = true
    const timers: number[] = []

    if (isMock()) {
      let p = 5
      const t = window.setInterval(() => {
        p = Math.min(100, p + 12)
        setState({ percent: p, message: p < 100 ? 'Spawning…' : 'Ready', phase: p < 100 ? 'spawning' : 'ready' })
        if (p >= 100) window.clearInterval(t)
      }, 360)
      timers.push(t)
      return () => timers.forEach(window.clearInterval)
    }

    startServer(user).catch(() => {}) // progress is observed via SSE; ignore the POST resolution
    const token = xsrfToken()
    const url = hubUrl(`/api/users/${encodeURIComponent(user)}/server/progress${token ? `?_xsrf=${encodeURIComponent(token)}` : ''}`)
    const es = new EventSource(url, { withCredentials: true })
    let resolved = false

    // Smooth creep so the bar always advances toward ~90% while spawning. The
    // hub emits only a couple of progress events for a fast/cached spawn (one
    // early value, then ready=100), which otherwise reads as "sit at 10% then
    // snap to 100%". Real SSE progress jumps it ahead (we never go backwards);
    // ready sets 100.
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
        if (d.ready || d.failed) { resolved = true; es.close() }
      } catch { /* ignore a malformed frame */ }
    }

    es.onerror = () => {
      es.close()
      if (resolved) return
      // Stream dropped without a terminal event - confirm via a bounded status poll.
      const deadline = Date.now() + 90_000
      const poll = window.setInterval(async () => {
        try {
          const servers = await getDataSource().getServers()
          const row = servers.find((s) => s.user === user)
          if (row && isRunning(row.status)) {
            window.clearInterval(poll)
            setState((s) => ({ ...s, percent: 100, phase: 'ready' }))
          } else if (Date.now() > deadline) {
            window.clearInterval(poll)
            setState((s) => ({ ...s, phase: 'failed', message: 'Could not confirm spawn' }))
          }
        } catch {
          if (Date.now() > deadline) {
            window.clearInterval(poll)
            setState((s) => ({ ...s, phase: 'failed', message: 'Could not confirm spawn' }))
          }
        }
      }, 1500)
      timers.push(poll)
    }

    return () => { es.close(); timers.forEach(window.clearInterval) }
  }, [user])

  return state
}
