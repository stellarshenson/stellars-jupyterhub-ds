/* Mock-only disclaimer. The live hub portal pulls real data AND its actions
 * really mutate the hub (ops.run() issues the hub call in live mode), so there is
 * nothing to disclaim there - showing "every action is simulated" on the live
 * portal is false and dangerous. Only the fixture-backed mock demo gets a banner. */
import { Alert } from 'antd'
import { isMock } from '../services/dataMode'

export function ReadonlyBanner() {
  if (!isMock()) return null
  return (
    <Alert
      type="info"
      showIcon
      closable
      style={{ marginBottom: 16 }}
      message="Read-only mock - data is fixture-backed (no hub); every action is simulated."
    />
  )
}
