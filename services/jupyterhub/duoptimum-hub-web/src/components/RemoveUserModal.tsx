/* Remove-user confirmation. A checkbox opts into ALSO deleting the user's volumes
 * (home/workspace/cache). When ticked the removal runs behind a spinner popup with
 * rotating docker-flavour text (the volumes are real Docker volumes - it takes a
 * moment) and ends on a done report; when unticked it is a plain quick delete that
 * keeps the volumes. Ordering matters: volumes are removed BEFORE the user, because
 * the manage-volumes endpoint resolves the user (404 once the account is gone). Both
 * the volume delete and the user delete need the server stopped, so the volume
 * checkbox is disabled while it runs. */
import { useEffect, useState } from 'react'
import { Button, Checkbox, Modal, Spin } from 'antd'
import { Notice } from './Notice'
import { Icon } from './Icon'
import { useUserVolumes } from '../hooks/queries'
import { deleteUser, resetVolumes } from '../services/ops'

// docker-flavour steps cycled while the volumes are torn down (same spirit as the
// old stop-server spinner) - they are cosmetic, the real work runs underneath
const DOCKER_STEPS = [
  'Unmounting volumes…',
  'Removing volume data…',
  'Pruning anonymous volumes…',
  'Reclaiming disk space…',
  'Clearing the user record…',
  'Sweeping up dangling layers…',
  'Finalising…',
]

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

type Phase = 'confirm' | 'working' | 'done' | 'error'

export function RemoveUserModal({
  name, open, serverRunning, onClose, onRemoved,
}: {
  name: string
  open: boolean
  serverRunning: boolean
  onClose: () => void
  onRemoved: () => void
}) {
  const { data: volumes = [] } = useUserVolumes(name)
  const suffixes = volumes.map((v) => v.suffix)
  const [withVolumes, setWithVolumes] = useState(false)
  const [phase, setPhase] = useState<Phase>('confirm')
  const [step, setStep] = useState(0)
  const [removed, setRemoved] = useState<string[]>([])
  const [error, setError] = useState('')

  // fresh state every time the modal (re)opens
  useEffect(() => {
    if (open) { setWithVolumes(false); setPhase('confirm'); setStep(0); setRemoved([]); setError('') }
  }, [open])

  // cycle the flavour text while tearing volumes down
  useEffect(() => {
    if (phase !== 'working') return
    const t = setInterval(() => setStep((i) => (i + 1) % DOCKER_STEPS.length), 900)
    return () => clearInterval(t)
  }, [phase])

  const removeOnly = async () => {
    try {
      await deleteUser(name)
      onClose()
      onRemoved()
    } catch { /* ops surfaced the error toast - leave the confirm open to retry */ }
  }

  const removeWithVolumes = async () => {
    setPhase('working')
    try {
      // volumes first (the user must still exist for the manage-volumes endpoint),
      // then the account; keep the spinner up long enough to read
      await Promise.all([
        (async () => { await resetVolumes(name, suffixes); await deleteUser(name) })(),
        delay(1400),
      ])
      setRemoved(suffixes)
      setPhase('done')
    } catch (e) {
      setError((e as Error).message || 'removal failed')
      setPhase('error')
    }
  }

  const onRemove = () => (withVolumes && suffixes.length ? removeWithVolumes() : removeOnly())

  const center: React.CSSProperties = { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, padding: '20px 0' }

  let body: React.ReactNode
  let footer: React.ReactNode
  if (phase === 'working') {
    body = (
      <div style={center}>
        <Spin size="large" />
        <div style={{ fontWeight: 500 }}>{DOCKER_STEPS[step]}</div>
        <small className="doh-muted">Removing {name} and {suffixes.length} volume{suffixes.length === 1 ? '' : 's'}…</small>
      </div>
    )
    footer = null
  } else if (phase === 'done') {
    body = (
      <div style={center}>
        <span style={{ color: 'var(--color-success)' }}><Icon name="check" size={32} /></span>
        <div style={{ fontWeight: 500 }}>{name} removed</div>
        {removed.length > 0 && <small className="doh-muted">Deleted {removed.length} volume{removed.length === 1 ? '' : 's'}: {removed.join(', ')}</small>}
      </div>
    )
    footer = <Button type="primary" onClick={() => { onClose(); onRemoved() }}>Close</Button>
  } else if (phase === 'error') {
    body = <Notice type="error"><span>Removal failed: {error}</span></Notice>
    footer = (
      <>
        <Button onClick={() => setPhase('confirm')}>Back</Button>
        <Button danger onClick={onClose}>Close</Button>
      </>
    )
  } else {
    body = (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Notice type="warning">
          <span>Removing <b>{name}</b> deletes the account, its group memberships and authorisation. This cannot be undone.</span>
        </Notice>
        {suffixes.length ? (
          <div>
            <Checkbox checked={withVolumes} disabled={serverRunning} onChange={(e) => setWithVolumes(e.target.checked)}>
              Also delete this user's volumes ({suffixes.join(', ')}) - permanent
            </Checkbox>
            {serverRunning && <div style={{ marginTop: 6 }}><small className="doh-muted">Stop the server to also remove its volumes.</small></div>}
          </div>
        ) : (
          <Notice type="info"><span>No active volumes for this user.</span></Notice>
        )}
      </div>
    )
    footer = (
      <>
        <Button onClick={onClose}>Cancel</Button>
        <Button danger onClick={onRemove}>Remove User</Button>
      </>
    )
  }

  return (
    <Modal
      open={open}
      title={`Remove ${name}`}
      onCancel={phase === 'working' ? undefined : onClose}
      closable={phase !== 'working'}
      maskClosable={false}
      keyboard={phase !== 'working'}
      footer={footer}
      destroyOnHidden
    >
      {body}
    </Modal>
  )
}
