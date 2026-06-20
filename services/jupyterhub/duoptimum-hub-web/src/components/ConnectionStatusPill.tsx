/* Header connection-status pill - the hub-reachability indicator on desktop, driven
 * by the shared useHubHealth probe. Sits in the header chrome beside the stage badge
 * (same height): a calm outlined "Connected" while the hub answers, a warning-filled
 * "Not responding · XXXX" (elapsed, ticking each second) when it stops. The diode
 * carries a soft slowly-pulsing halo (period from ANIMATION.statusPulseMs). Mobile
 * uses the in-flow panel (HubConnectionIndicator) instead, so this renders nothing
 * below the breakpoint; mock has no hub to report on. */
import type { CSSProperties } from 'react'
import { useEffect, useState } from 'react'
import { useHubHealth } from '../lib/useHubHealth'
import { useIsMobile } from '../lib/useIsMobile'
import { isMock } from '../services/dataMode'
import { ANIMATION } from '../services/config'
import { elapsedShort } from '../lib/format'

const DOWN_TITLE =
  'The Duoptimum Hub is not responding. Shown data may be stale and actions will fail until the connection is restored - retrying automatically.'

const pulseVar = { '--doh-status-pulse': `${ANIMATION.statusPulseMs}ms` } as CSSProperties

export function ConnectionStatusPill() {
  const { down, downSince } = useHubHealth()
  const isMobile = useIsMobile()
  const [, setTick] = useState(0)

  // re-render every second while down so the elapsed readout advances
  useEffect(() => {
    if (!down) return
    const id = setInterval(() => setTick((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [down])

  if (isMobile || isMock()) return null

  if (!down) {
    return (
      <span className="doh-conn-pill ok" style={pulseVar} role="status" aria-label="Hub connected" title="Connected to the Duoptimum Hub">
        <span className="doh-conn-dot" aria-hidden="true" />
        Connected
      </span>
    )
  }

  const elapsed = downSince ? elapsedShort(Date.now() - downSince) : ''
  return (
    <span className="doh-conn-pill down" style={pulseVar} role="status" aria-label={`Hub not responding${elapsed ? ` for ${elapsed}` : ''}`} title={DOWN_TITLE}>
      <span className="doh-conn-dot" aria-hidden="true" />
      Not responding{elapsed ? ` · ${elapsed}` : ''}
    </span>
  )
}
