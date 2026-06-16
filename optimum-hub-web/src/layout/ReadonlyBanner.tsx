/* States the contract plainly: this portal reads real data but every action is
 * simulated. Dismissible; shown once at the top of the content. */
import { Alert } from 'antd'
import { dataMode } from '../services/dataMode'

export function ReadonlyBanner() {
  const mode = dataMode()
  return (
    <Alert
      type="info"
      showIcon
      closable
      style={{ marginBottom: 16 }}
      message={
        mode === 'live'
          ? 'Read-only mock - data is pulled live from the hub; every action is simulated.'
          : 'Read-only mock - data is fixture-backed (no hub); every action is simulated.'
      }
    />
  )
}
