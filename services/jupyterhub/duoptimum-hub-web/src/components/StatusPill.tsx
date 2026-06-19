/* Lifecycle status pill - coloured dot + soft background. The one place server
 * state turns into colour (running green / idle amber / offline grey / spawning
 * cyan / error red). */
import type { ServerStatus } from '../services/types'

const PILL_CLASS: Record<ServerStatus, string> = {
  active: 'running',
  idle: 'idle',
  spawning: 'spawning',
  offline: 'stopped',
  error: 'error',
}

export function StatusPill({ status, label, title }: { status: ServerStatus; label: string; title?: string }) {
  return (
    <span className={`doh-pill ${PILL_CLASS[status]}`} title={title ?? label}>
      <span className="doh-dot" />
      {label}
    </span>
  )
}
