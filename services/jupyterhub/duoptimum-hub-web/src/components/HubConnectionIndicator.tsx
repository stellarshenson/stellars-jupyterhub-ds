/* Mobile hub-unreachable panel - the in-flow warning shown at the top of the content
 * below the breakpoint (desktop uses the header ConnectionStatusPill instead). Pale
 * warning surface so it never washes out the text, a soft slowly-pulsing diode and the
 * elapsed "for XXXX". Driven by the shared useHubHealth probe; renders nothing while
 * the hub is reachable or on desktop. */
import { useEffect, useState } from 'react'
import { useHubHealth } from '../lib/useHubHealth'
import { useIsMobile } from '../lib/useIsMobile'
import { elapsedShort } from '../lib/format'

const TITLE = 'Hub not responding'
const BODY =
  'The Duoptimum Hub is not responding. Shown data may be stale and actions will fail until the connection is restored - retrying automatically.'

export function HubConnectionIndicator() {
  const { down, downSince } = useHubHealth()
  const isMobile = useIsMobile()
  const [, setTick] = useState(0)

  // tick each second while down so the elapsed readout advances
  useEffect(() => {
    if (!down) return
    const id = setInterval(() => setTick((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [down])

  if (!isMobile || !down) return null

  const elapsed = downSince ? elapsedShort(Date.now() - downSince) : ''
  // polite role="status" (NOT assertive/alert): a transient blip should not interrupt a
  // screen-reader user mid-task - matches the desktop pill's urgency. Title text stays
  // stable; the ticking elapsed is visual only (aria-hidden) so it never re-announces.
  return (
    <div className="doh-hub-warn-panel" role="status">
      <span className="doh-hub-warn-diode" aria-hidden="true" />
      <div>
        <div className="doh-hub-warn-title">{TITLE}{elapsed ? <span aria-hidden="true">{` · for ${elapsed}`}</span> : null}</div>
        <div className="doh-hub-warn-body">{BODY}</div>
      </div>
    </div>
  )
}
