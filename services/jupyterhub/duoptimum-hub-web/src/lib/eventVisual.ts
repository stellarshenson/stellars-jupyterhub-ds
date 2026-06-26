/* Activity-feed visual mapping (design system "Activity feed"): a row's circle
 * bg-tint AND the icon colour come from the SAME category tone token - a mismatched
 * pair reads as a bug. The GLYPH comes from the event itself (the hub sends a per-event
 * icon for specific actions, e.g. server stop / extend; else the type default), and a
 * closed-shape glyph (play / stop) renders FILLED for a terminal/standalone event while
 * open glyphs stay stroked. Single source for the feed circle (Home + Events), the Events
 * type pill, and the scope-filter chips so a category's colour never drifts between them. */
import type { EventType } from '../services/types'

export type FeedTone = 'ok' | 'warn' | 'danger' | 'accent'

// category -> tone: started=success, approaching-limit/storage=warning, failed/ended=danger,
// config/identity/policy/announcement=accent (the design-system category palette)
export const EVENT_TONE: Record<EventType, FeedTone> = {
  server: 'ok', // started / lifecycle
  user: 'accent', // identity / config
  group: 'accent', // config
  policy: 'accent', // config / policy change
  broadcast: 'accent', // announcement
  cull: 'danger', // session ended (idle cull)
  volume: 'warn', // storage / approaching-limit
  error: 'danger', // failed
}

// closed-shape glyphs that read right when FILLED (terminal/standalone events: started=play,
// stopped/ended=stop); open glyphs (x, clock, restart, megaphone...) stay stroked, per the
// design-system "never fill an open polyline" rule. keyed by GLYPH not type, so one server
// event shows a filled play on start and a filled stop on stop.
const FILLED_GLYPHS = new Set<string>(['play', 'stop'])
export const glyphFilled = (icon: string): boolean => FILLED_GLYPHS.has(icon)
