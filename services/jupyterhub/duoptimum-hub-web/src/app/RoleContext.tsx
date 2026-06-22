/* Identity + role context. One build serves both admin and plain-user views.
 *
 * Identity comes from the hub-rendered shell (`window.jhdata`, read synchronously
 * so the right shell paints immediately), then groups are filled in from
 * GET /hub/api/user. The role is derived from the real `admin` flag. Because the
 * hub serves the portal behind @web.authenticated, an unauthenticated visitor
 * never reaches this code (the hub 302s to login first); the getCurrentUser
 * redirect is a belt-and-braces fallback only. */
import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { Role } from '../services/types'
import { getCurrentUser, pageUser } from '../services/hub/client'

interface RoleCtx {
  role: Role
  username: string
  groups: string[]
  ready: boolean // false while the session is loading
}

const Ctx = createContext<RoleCtx | null>(null)

export function useRole(): RoleCtx {
  const c = useContext(Ctx)
  if (!c) throw new Error('useRole must be used inside RoleProvider')
  return c
}

export function RoleProvider({ children }: { children: ReactNode }) {
  // The hub embeds the signed-in identity in the page shell, so we know
  // name + admin before any fetch and never flash the wrong shell.
  const seeded = pageUser()
  const [role, setRole] = useState<Role>(() => (seeded && seeded.admin ? 'admin' : 'user'))
  const [username, setUsername] = useState<string>(() => (seeded ? seeded.name : ''))
  const [groups, setGroups] = useState<string[]>([])
  const [ready, setReady] = useState<boolean>(!!seeded)

  // Fill in groups (and reconcile name/role) from the real session.
  useEffect(() => {
    let cancelled = false
    getCurrentUser()
      .then((u) => {
        if (cancelled) return
        setUsername(u.name)
        setGroups(u.groups ?? [])
        setRole(u.admin ? 'admin' : 'user')
        setReady(true)
      })
      .catch(() => {
        // getCurrentUser redirects on 401/403; any other failure still unblocks
        // the shell (using the page-seeded identity) so an error surface renders.
        if (!cancelled) setReady(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const ctx = useMemo<RoleCtx>(() => ({ role, username, groups, ready }), [role, username, groups, ready])

  if (!ready) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', color: 'var(--color-text-muted)', font: '14px system-ui' }}>
        Connecting to the hub…
      </div>
    )
  }

  return <Ctx.Provider value={ctx}>{children}</Ctx.Provider>
}
