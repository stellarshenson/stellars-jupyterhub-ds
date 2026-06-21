/* Single shared probe of the hub's /hub/health endpoint. ONE poll loop and ONE
 * down/downSince state for the whole app, exposed via useSyncExternalStore - so the
 * desktop pill and the mobile panel read the same source instead of each running their
 * own probe (which drifted up to a poll apart). The hub is reported unreachable only
 * after a few consecutive failures, so a single blip never flips it. Live mode only -
 * mock has no hub. On recovery it invalidates the query cache so stale data refetches. */
import { useSyncExternalStore } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { isMock } from '../services/dataMode'
import { hubUrl } from '../services/hub/client'

const POLL_MS = 15_000 // well under the hub's 1 req/s health rate limit
const TIMEOUT_MS = 8_000 // a probe slower than this counts as a failure
const FAILS_TO_DOWN = 2 // consecutive failures before raising the indicator

type Health = { down: boolean; downSince: number | null }

// module-level shared store: one state object (stable identity until it changes, so
// useSyncExternalStore never loops), one set of subscribers, one probe loop.
let state: Health = { down: false, downSince: null }
const listeners = new Set<() => void>()
let probeStarted = false
let fails = 0
let timer: ReturnType<typeof setTimeout> | undefined
// the React Query client, captured from the first mounted hook - single app, one client,
// so the probe can invalidate stale queries on recovery without per-consumer wiring
let qc: { invalidateQueries: () => void } | null = null

function emit() {
  for (const l of listeners) l()
}

// only flips on a real transition; recovery refetches the stale cache. downSince is the
// timestamp (ms) the hub first went down (null while up) - drives the "for XXXX" readout.
function apply(next: boolean) {
  if (next === state.down) return
  state = { down: next, downSince: next ? Date.now() : null }
  if (!next) qc?.invalidateQueries()
  emit()
}

async function probe() {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(hubUrl('/health'), { signal: ctrl.signal, cache: 'no-store', credentials: 'same-origin' })
    // 401/403 = the hub answered (auth state), NOT the hub being down
    if (res.status === 401 || res.status === 403) { fails = 0; apply(false) }
    else if (!res.ok) throw new Error(String(res.status)) // 5xx etc.
    else { fails = 0; apply(false) }
  } catch {
    fails += 1
    if (fails >= FAILS_TO_DOWN) apply(true)
  } finally {
    clearTimeout(t)
    timer = setTimeout(probe, POLL_MS)
  }
}

// started once, by the first subscriber; runs for the app lifetime (both consumers stay
// mounted). Guarded so N consumers never start N probes.
function subscribe(cb: () => void) {
  listeners.add(cb)
  if (!probeStarted && !isMock()) {
    probeStarted = true
    void probe()
  }
  return () => {
    listeners.delete(cb)
  }
}

function getSnapshot(): Health {
  return state
}

export function useHubHealth(): Health {
  // capture the query client for the shared probe's recovery invalidation (idempotent;
  // same client every render in this single-app context)
  qc = useQueryClient()
  return useSyncExternalStore(subscribe, getSnapshot)
}

// test seam: reset the module singleton between unit tests
export function __resetHubHealth() {
  if (timer) clearTimeout(timer)
  state = { down: false, downSince: null }
  listeners.clear()
  probeStarted = false
  fails = 0
  qc = null
}
