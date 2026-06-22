/* Persist the TanStack Query cache to localStorage so the next portal load paints
 * the last-known data instantly, then revalidates in the background (queries are
 * already stale past staleTime, so each refetches and only what changed updates).
 *
 * Uses the library's own dehydrate/hydrate - no extra dependency. Only successful
 * queries are stored; token data is excluded (secrets must not touch localStorage).
 * The blob is capped by age so it self-heals. */
import { dehydrate, hydrate, type QueryClient } from '@tanstack/react-query'

const KEY = 'doh-query-cache-v1'
const MAX_AGE_MS = 24 * 60 * 60_000 // a day - older blobs are dropped, not shown
const EXCLUDE = ['tokens', 'events'] // never persist: token data (one-time secrets); the events audit feed (must be fresh on load, not painted 30s-stale from cache)

function excluded(queryKey: unknown): boolean {
  return Array.isArray(queryKey) && queryKey.some((k) => EXCLUDE.includes(k as string))
}

/** Load a previously persisted cache into the client (call once, before render). */
export function hydrateQueryCache(qc: QueryClient): void {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return
    const { ts, state } = JSON.parse(raw)
    if (!ts || Date.now() - ts > MAX_AGE_MS) {
      localStorage.removeItem(KEY)
      return
    }
    hydrate(qc, state)
  } catch {
    /* corrupt / unavailable storage - start cold, never crash */
  }
}

/** Subscribe to cache changes and debounce-write them to localStorage. */
export function persistQueryCache(qc: QueryClient): () => void {
  let timer: number | undefined
  const write = () => {
    try {
      const state = dehydrate(qc, {
        shouldDehydrateQuery: (q) => q.state.status === 'success' && !excluded(q.queryKey),
      })
      localStorage.setItem(KEY, JSON.stringify({ ts: Date.now(), state }))
    } catch {
      /* quota or serialisation failure is non-fatal - skip this write */
    }
  }
  return qc.getQueryCache().subscribe(() => {
    clearTimeout(timer)
    timer = window.setTimeout(write, 1000) // coalesce bursts of settles
  })
}
