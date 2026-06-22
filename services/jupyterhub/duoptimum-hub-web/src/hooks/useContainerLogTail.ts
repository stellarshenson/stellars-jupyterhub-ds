import { useEffect, useState } from 'react'
import { hubGet } from '../services/hub/client'

/* Polls the bounded container-log tail while `active`, newest line last - the log
 * half of the Start-server page. Stops on active=false / unmount (no leaked
 * timer). A 404 (container not created yet) or transient error keeps the last
 * tail, so the page can show a "waiting for container" placeholder until lines
 * arrive. */
export function useContainerLogTail(user: string, active: boolean, tail = 15): string[] {
  const [lines, setLines] = useState<string[]>([])

  useEffect(() => {
    if (!active) return

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
