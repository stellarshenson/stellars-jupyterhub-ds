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
const RECOVERED = 'Hub connection restored'

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

  // desktop uses the header ConnectionStatusPill (its own live region); render nothing here
  if (!isMobile) return null

  const elapsed = down && downSince ? elapsedShort(Date.now() - downSince) : ''
  // ALWAYS-mounted polite role="status" live region so RECOVERY announces too: an
  // unmounted region is silent, so a screen-reader user would hear the outage but never
  // that it cleared (the desktop pill stays mounted and gets this for free). The visible
  // warning panel renders only while down; on recovery the region swaps to an sr-only
  // "restored" line so the change is announced with no visual chrome. polite (not
  // assertive) so a transient blip never interrupts mid-task; the ticking elapsed is
  // aria-hidden so it never re-announces.
  return (
    <div role="status">
      {down ? (
        <div className="doh-hub-warn-panel">
          <span className="doh-hub-warn-diode" aria-hidden="true" />
          <div>
            <div className="doh-hub-warn-title">{TITLE}{elapsed ? <span aria-hidden="true">{` · for ${elapsed}`}</span> : null}</div>
            <div className="doh-hub-warn-body">{BODY}</div>
          </div>
        </div>
      ) : (
        <span className="doh-sr-only">{RECOVERED}</span>
      )}
    </div>
  )
}
