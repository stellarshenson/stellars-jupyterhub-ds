/* Global hub-unreachable indicator, driven by the single useHubHealth probe.
 * Reads as a transient WARNING (pill-style diode in warning colour, pulsing with a
 * halo), never a red system error. Desktop: a persistent corner diode plus a
 * dismissable popup (re-armed each time the hub drops again). Mobile: an in-flow
 * warning panel at the top of the content, above the Server Controls. Renders
 * nothing while the hub is reachable. */
import { Modal } from 'antd'
import { useEffect, useState } from 'react'
import { useHubHealth } from '../lib/useHubHealth'
import { useIsMobile } from '../lib/useIsMobile'

const TITLE = 'Hub not responding'
const BODY =
  'The Duoptimum Hub is not responding. Shown data may be stale and actions will fail until the connection is restored - retrying automatically.'

export function HubConnectionIndicator() {
  const { down } = useHubHealth()
  const isMobile = useIsMobile()
  const [dismissed, setDismissed] = useState(false)

  // re-arm the popup whenever the hub recovers and later drops again
  useEffect(() => { if (!down) setDismissed(false) }, [down])

  if (!down) return null

  if (isMobile) {
    return (
      <div className="doh-hub-warn-panel" role="alert" aria-live="assertive">
        <span className="doh-hub-diode-inline" aria-hidden="true" />
        <div>
          <div className="doh-hub-warn-title">{TITLE}</div>
          <div className="doh-hub-warn-body">{BODY}</div>
        </div>
      </div>
    )
  }

  return (
    <>
      <span className="doh-hub-diode" role="status" aria-label={TITLE} title={TITLE} />
      <Modal
        open={!dismissed}
        onOk={() => setDismissed(true)}
        onCancel={() => setDismissed(true)}
        okText="Dismiss"
        cancelButtonProps={{ style: { display: 'none' } }}
        title={<><span className="doh-hub-diode-inline" aria-hidden="true" />{TITLE}</>}
      >
        {BODY}
      </Modal>
    </>
  )
}
