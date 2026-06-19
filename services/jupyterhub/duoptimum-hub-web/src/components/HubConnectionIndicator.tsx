/* Global hub-unreachable indicator, driven by the single useHubHealth probe.
 * Desktop: a persistent pulsating warning diode plus a dismissable popup (re-armed
 * each time the hub drops again). Mobile: a fixed top panel, no modal. Renders
 * nothing while the hub is reachable. */
import { Modal } from 'antd'
import { DisconnectOutlined } from '@ant-design/icons'
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
      <div className="doh-hub-offline-bar" role="alert" aria-live="assertive">
        <span className="doh-hub-dot" aria-hidden="true" />
        {TITLE}
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
        title={<><DisconnectOutlined style={{ color: 'var(--color-danger)', marginInlineEnd: 8 }} />{TITLE}</>}
      >
        {BODY}
      </Modal>
    </>
  )
}
