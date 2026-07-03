/* Header connection-status pill - the hub-reachability indicator, driven by the shared
 * useHubHealth probe. Sits in the header chrome beside the stage badge (same height): a
 * calm outlined "Connected" while the hub answers, a warning-filled "Not responding ·
 * XXXX" (elapsed, ticking each second) when it stops. The diode carries a soft pulsing
 * halo - slow when connected (period ANIMATION.statusPulseMs), 3x faster when down (CSS
 * calc /3) to signal urgency. On mobile the text label (.doh-conn-label) is hidden by CSS
 * so the pill collapses to a dot-only chip that fits the phone header; the in-flow panel
 * (HubConnectionIndicator) still carries the full down-state detail there. */
import type { CSSProperties } from 'react'
import { useEffect, useState } from 'react'
import { useHubHealth } from '../lib/useHubHealth'
import { ANIMATION } from '../services/config'
import { elapsedShort } from '../lib/format'
import { hubName } from '../app/capabilities'

// hub name from branding (JUPYTERHUB_BRANDING_HUB_NAME via window.jhdata), not hardcoded
const downTitle = () =>
  `${hubName()} not responding - data may be stale, actions will fail; retrying automatically.`

const pulseVar = { '--doh-status-pulse': `${ANIMATION.statusPulseMs}ms` } as CSSProperties

export function ConnectionStatusPill() {
  const { down, downSince } = useHubHealth()
  const [, setTick] = useState(0)

  // re-render every second while down so the elapsed readout advances
  useEffect(() => {
    if (!down) return
    const id = setInterval(() => setTick((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [down])

  if (!down) {
    return (
      <span className="doh-conn-pill ok" style={pulseVar} role="status" aria-label="Hub connected" title={`Connected to the ${hubName()}`}>
        <span className="doh-conn-dot" aria-hidden="true" />
        <span className="doh-conn-label">Connected</span>
      </span>
    )
  }

  const elapsed = downSince ? elapsedShort(Date.now() - downSince) : ''
  // role="status" is a polite live region; keep its announced text STABLE so a screen
  // reader says "Hub not responding, retrying" once, not the ticking seconds every second.
  // The elapsed readout is visual only - aria-hidden so it never re-announces. The label
  // wrapper is hidden on mobile (dot-only chip); aria-label keeps the accessible name.
  return (
    <span className="doh-conn-pill down" style={pulseVar} role="status" aria-label="Hub not responding, retrying" title={downTitle()}>
      <span className="doh-conn-dot" aria-hidden="true" />
      <span className="doh-conn-label">
        Not responding
        {elapsed ? <span aria-hidden="true">{` · ${elapsed}`}</span> : null}
      </span>
    </span>
  )
}
