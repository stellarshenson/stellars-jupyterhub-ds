import { hubGet } from './client'

/* Shared lab-readiness gate. The hub `running` flag flips ~1s before the lab
 * actually serves HTTP, so anything that enters a lab must first wait for it to
 * genuinely answer (DEF-1 cold start, DEF-25 the Open controls). Polls the
 * hub-side always-200 `lab-ready` probe (the hub checks the lab socket
 * server-side, so the browser console stays clean) until the lab answers or a
 * deadline passes - then the caller proceeds (the server IS running; the gate
 * only avoids the early-race spawn-pending / 503 page). Pure of React; the single
 * implementation used by both the Starting page and the server-lifecycle gate. */

const LAB_READY_POLL_MS = 1_000
const LAB_READY_DEADLINE_MS = 60_000

/** Resolve true once the lab answers, false on the deadline or on abort. The
 *  caller proceeds in both the ready and deadline cases (deadline = give up
 *  gating, the server is up); abort means navigate-away, so it must NOT proceed -
 *  re-check `aborted()` after the call. */
export async function waitForLabReady(
  name: string,
  opts: { aborted?: () => boolean; pollMs?: number; deadlineMs?: number } = {},
): Promise<boolean> {
  const aborted = opts.aborted ?? (() => false)
  const pollMs = opts.pollMs ?? LAB_READY_POLL_MS
  const deadline = Date.now() + (opts.deadlineMs ?? LAB_READY_DEADLINE_MS)
  for (;;) {
    if (aborted()) return false
    let ready = false
    try {
      ready = (await hubGet<{ ready: boolean }>(`/users/${encodeURIComponent(name)}/lab-ready`)).ready
    } catch {
      /* transient (network blip / lab not yet listening) - keep polling */
    }
    if (aborted()) return false
    if (ready) return true
    if (Date.now() > deadline) return false
    await new Promise((r) => setTimeout(r, pollMs))
  }
}
