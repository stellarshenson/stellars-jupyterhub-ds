import { useEffect, useState } from 'react'
import { hubGet } from '../services/hub/client'
import { isMock } from '../services/dataMode'

const MOCK_TAIL = [
  '[I 2026-06-17 11:53:01.204 SingleUserNotebookApp] Starting jupyterlab-konrad',
  '[I 2026-06-17 11:53:01.640 SingleUserNotebookApp] Mounting /home/lab/workspace',
  '[I 2026-06-17 11:53:02.118 SingleUserNotebookApp] Extension jupyterlab loaded',
  '[I 2026-06-17 11:53:02.553 SingleUserNotebookApp] Extension jupyterlab_notifications_extension loaded',
  '[I 2026-06-17 11:53:03.001 SingleUserNotebookApp] Serving notebooks from /home/lab/workspace',
  '[I 2026-06-17 11:53:03.402 SingleUserNotebookApp] Jupyter Server is running at:',
  '[I 2026-06-17 11:53:03.404 SingleUserNotebookApp] http://jupyterlab-konrad:8888/user/konrad/',
  '[I 2026-06-17 11:53:03.808 SingleUserNotebookApp] Kernel started',
  '[I 2026-06-17 11:53:04.210 SingleUserNotebookApp] Ready',
]

/* Polls the bounded container-log tail while `active`, newest line last - the log
 * half of the Start-server page. Stops on active=false / unmount (no leaked
 * timer). A 404 (container not created yet) or transient error keeps the last
 * tail, so the page can show a "waiting for container" placeholder until lines
 * arrive. Mock mode returns a canned sample so the design pages demo the feed. */
export function useContainerLogTail(user: string, active: boolean, tail = 15): string[] {
  const [lines, setLines] = useState<string[]>([])

  useEffect(() => {
    if (!active) return
    if (isMock()) { setLines(MOCK_TAIL.slice(-tail)); return }

    let alive = true
    const tick = async () => {
      try {
        const r = await hubGet<{ lines: string[] }>(`/users/${encodeURIComponent(user)}/server/logs?tail=${tail}`)
        if (alive) setLines(r.lines ?? [])
      } catch { /* 404 before the container exists, or transient - keep the last tail */ }
    }
    void tick()
    const id = window.setInterval(tick, 1500)
    return () => { alive = false; window.clearInterval(id) }
  }, [user, active, tail])

  return lines
}
