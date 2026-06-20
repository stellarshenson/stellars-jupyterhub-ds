/* Small formatting helpers shared across pages. */
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

export function timeAgo(iso?: string): string {
  if (!iso) return 'never'
  return dayjs(iso).fromNow()
}

// compact relative time ("2m", "5h", "3d", "4mo", "1y") - the short form used
// consistently across lists (Servers, Users)
export function timeAgoShort(iso?: string): string {
  if (!iso) return 'never'
  const now = dayjs()
  const then = dayjs(iso)
  const mins = now.diff(then, 'minute')
  if (mins < 1) return 'now'
  if (mins < 60) return `${mins}m`
  const hours = now.diff(then, 'hour')
  if (hours < 24) return `${hours}h`
  const days = now.diff(then, 'day')
  if (days < 30) return `${days}d`
  const months = now.diff(then, 'month')
  if (months < 12) return `${months}mo`
  return `${now.diff(then, 'year')}y`
}

// compact elapsed duration from a millisecond span ("5s", "2m", "1h 3m") - used
// by the connection indicator's "not responding for XXXX" readout, which ticks
// each second from the moment the hub went down (seconds granularity, unlike the
// minute-floored timeAgoShort)
export function elapsedShort(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  return `${h}h ${m % 60}m`
}

// "stopped <when> ago" phrasing for the offline TTL slot. Sub-minute reads
// "a moment ago" (never the ungrammatical "now ago"); null = "never started".
export function stoppedAgo(iso?: string | null): string {
  if (!iso) return 'never started'
  const short = timeAgoShort(iso)
  return short === 'now' ? 'stopped a moment ago' : `stopped ${short} ago`
}

export function exactDate(iso?: string): string {
  if (!iso) return '-'
  return dayjs(iso).format('YYYY-MM-DD HH:mm')
}

export function fmtMinutes(min: number): string {
  if (min >= 60) {
    const h = Math.floor(min / 60)
    const m = min % 60
    return `${h}h ${m}m`  // always show minutes (e.g. "4h 0m"), never bare "4h"
  }
  return `${min}m`
}
