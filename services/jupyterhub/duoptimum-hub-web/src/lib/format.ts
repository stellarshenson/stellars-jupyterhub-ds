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
