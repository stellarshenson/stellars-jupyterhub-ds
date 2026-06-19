/* Notification / semantic pill - the single source of truth that maps a
 * notification level to the shared status-pill tone vocabulary, so a broadcast
 * type, an upgrade badge and any future advisory all read in the same colours:
 *   success     -> running  (green, like an Active server)
 *   warning     -> idle     (amber, like an idle server)
 *   passive      -> stopped  (neutral gray)
 *   info        -> accent   (cyan, like the "All" scope pill)
 *   dangerous   -> error    (red)
 *   in-progress -> spawning (cyan, pulsing - work underway)
 * One mapping, no per-page ad-hoc Tag colours. */

// notification/broadcast `type` -> doh-pill tone class
export const NOTIFICATION_TONE: Record<string, string> = {
  success: 'running',
  warning: 'idle',
  default: 'stopped',
  passive: 'stopped',
  info: 'accent',
  error: 'error',
  dangerous: 'error',
  'in-progress': 'spawning',
}

export function NotificationPill({ type, label, title }: { type: string; label?: string; title?: string }) {
  const tone = NOTIFICATION_TONE[type] ?? 'stopped'
  return (
    <span className={`doh-pill ${tone}`} title={title}>
      {label ?? type}
    </span>
  )
}
