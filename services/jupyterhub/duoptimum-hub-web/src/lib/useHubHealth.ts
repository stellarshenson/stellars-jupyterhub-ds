/* Polls the hub's /hub/health endpoint and reports the hub unreachable only after
 * a few consecutive failures, so a single blip never flips it. Live mode only -
 * mock has no hub. On recovery it invalidates the query cache so stale data
 * refetches. This is the single source of truth for every hub-offline indicator. */
import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { isMock } from '../services/dataMode'
import { hubUrl } from '../services/hub/client'

const POLL_MS = 15_000 // well under the hub's 1 req/s health rate limit
const TIMEOUT_MS = 8_000 // a probe slower than this counts as a failure
const FAILS_TO_DOWN = 2 // consecutive failures before raising the indicator

export function useHubHealth(): { down: boolean; downSince: number | null } {
  const [down, setDown] = useState(false)
  // timestamp (ms) the hub first went down, null while up - drives the "not
  // responding for XXXX" elapsed readout (the pill / mobile panel tick off it)
  const [downSince, setDownSince] = useState<number | null>(null)
  const downRef = useRef(false)
  const fails = useRef(0)
  const qc = useQueryClient()

  useEffect(() => {
    if (isMock()) return // no hub to probe in mock mode
    let stopped = false
    let timer: ReturnType<typeof setTimeout> | undefined

    // only flips on a real transition; recovery refetches the stale cache
    const apply = (next: boolean) => {
      if (next === downRef.current) return
      downRef.current = next
      setDown(next)
      setDownSince(next ? Date.now() : null)
      if (!next) void qc.invalidateQueries()
    }

    const probe = async () => {
      const ctrl = new AbortController()
      const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS)
      try {
        const res = await fetch(hubUrl('/health'), { signal: ctrl.signal, cache: 'no-store', credentials: 'same-origin' })
        if (stopped) return
        // 401/403 = the hub answered (auth state), NOT the hub being down
        if (res.status === 401 || res.status === 403) { fails.current = 0; apply(false) }
        else if (!res.ok) throw new Error(String(res.status)) // 5xx etc.
        else { fails.current = 0; apply(false) }
      } catch {
        if (stopped) return
        fails.current += 1
        if (fails.current >= FAILS_TO_DOWN) apply(true)
      } finally {
        clearTimeout(t)
        if (!stopped) timer = setTimeout(probe, POLL_MS)
      }
    }

    void probe()
    return () => { stopped = true; clearTimeout(timer) }
  }, [qc])

  return { down, downSince }
}
