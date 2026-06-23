/* Dedicated Start-server page: a centered branded card with a spawn progress bar
 * and a live tail of the freshly-started container's logs. Composition only - the
 * spawn lifecycle and the log feed are each owned by a focused hook; this page
 * renders them and applies the redirect-on-ready policy (own server -> into the
 * lab; admin starting another -> back to Servers). Failure keeps the page with an
 * error and a Back action. */
import { useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button, Progress } from 'antd'
import { useRole } from '../app/RoleContext'
import { useSpawnProgress } from '../hooks/useSpawnProgress'
import { useContainerLogTail } from '../hooks/useContainerLogTail'
import { userServerUrl, portalAssetBase } from '../services/hub/client'
import { waitForLabReady } from '../services/hub/labReady'

export default function Starting() {
  const { name = '' } = useParams()
  const navigate = useNavigate()
  const { username } = useRole()
  const isOwn = name === username
  const { percent, message, phase } = useSpawnProgress(name)
  const logs = useContainerLogTail(name, phase === 'spawning')
  const logRef = useRef<HTMLDivElement>(null)

  // keep the terminal pinned to the newest line as it streams
  useEffect(() => {
    const el = logRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [logs])

  // on ready: own server -> into the lab; admin starting someone else's -> back to
  // the Servers fleet view (never auto-enter another user's lab)
  useEffect(() => {
    if (phase !== 'ready') return
    // admin-other -> straight back to the fleet view
    if (!isOwn) {
      const t = window.setTimeout(() => navigate('/servers'), 600)
      return () => window.clearTimeout(t)
    }
    // own server: the hub 'ready' flag flips ~1s before the lab actually serves
    // HTTP, so redirecting on it lands on the hub's stock spawn-pending page
    // (DEF-1). Wait for the lab to genuinely answer via the shared readiness gate
    // and enter only then; it enters anyway after the gate's deadline.
    let aborted = false
    void waitForLabReady(name, { aborted: () => aborted }).then(() => {
      if (!aborted) window.location.assign(userServerUrl(name))
    })
    return () => { aborted = true }
  }, [phase, isOwn, name, navigate])

  const failed = phase === 'failed'
  const ready = phase === 'ready'
  const color = failed ? 'var(--color-danger)' : ready ? 'var(--color-success)' : 'var(--color-accent)'
  const heading = failed ? 'Could not start' : ready ? 'Ready' : 'Starting'

  return (
    <div className="doh-starting">
      <div className="doh-starting-card">
        <img className="doh-starting-mark" src={`${portalAssetBase()}brand/jl-logo.svg`} alt="" />
        <h1 className="doh-starting-title">{heading} {name}'s lab</h1>
        <p className="doh-starting-status">{message}</p>
        <Progress
          percent={failed ? 100 : percent}
          showInfo={false}
          status={failed ? 'exception' : phase === 'spawning' ? 'active' : undefined}
          strokeColor={color}
        />
        <div className="doh-termlog" ref={logRef} aria-label="container log">
          {logs.length === 0
            ? <span className="doh-termlog-wait">waiting for container…</span>
            : logs.map((l, i) => <div key={i} className="doh-termlog-line">{l}</div>)}
        </div>
        {failed && (
          <Button type="primary" block onClick={() => navigate(isOwn ? '/home' : '/servers')} style={{ marginTop: 14 }}>
            Back to {isOwn ? 'home' : 'servers'}
          </Button>
        )}
      </div>
    </div>
  )
}
