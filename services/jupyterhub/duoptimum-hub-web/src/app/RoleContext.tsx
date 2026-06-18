/* Identity + role context. One build serves both admin and plain-user views.
 *
 * - Mock mode: identity is synthetic and the role is flipped by the Home
 *   role-switch (persisted, so a reload keeps the chosen view).
 * - Live mode: identity comes from the hub-rendered shell (`window.jhdata`,
 *   read synchronously so the right shell paints immediately), then groups are
 *   filled in from GET /hub/api/user. The role is derived from the real `admin`
 *   flag and the switch is hidden. Because the hub serves the portal behind
 *   @web.authenticated, an unauthenticated visitor never reaches this code (the
 *   hub 302s to login first); the getCurrentUser redirect is a belt-and-braces
 *   fallback only. */
import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { Role } from '../services/types'
import { isMock } from '../services/dataMode'
import { getCurrentUser, pageUser } from '../services/hub/client'

const KEY = 'duoptimum-hub-role'

interface RoleCtx {
  role: Role
  setRole: (r: Role) => void
  username: string
  groups: string[]
  live: boolean // backed by a real hub session
  ready: boolean // false while the live session is loading
}

const Ctx = createContext<RoleCtx | null>(null)

export function useRole(): RoleCtx {
  const c = useContext(Ctx)
  if (!c) throw new Error('useRole must be used inside RoleProvider')
  return c
}

function readStoredRole(): Role {
  try {
    const r = localStorage.getItem(KEY)
    if (r === 'user' || r === 'admin') return r
  } catch {
    /* ignore */
  }
  return 'admin'
}

export function RoleProvider({ children }: { children: ReactNode }) {
  const live = !isMock()
  // Live: the hub embeds the signed-in identity in the page shell, so we know
  // name + admin before any fetch and never flash the wrong shell.
  const seeded = live ? pageUser() : null
  const [role, setRoleState] = useState<Role>(() => (seeded ? (seeded.admin ? 'admin' : 'user') : readStoredRole()))
  const [username, setUsername] = useState<string>(() =>
    seeded ? seeded.name : readStoredRole() === 'admin' ? 'admin' : 'alice',
  )
  const [groups, setGroups] = useState<string[]>([])
  const [ready, setReady] = useState<boolean>(!live || !!seeded)

  // Live mode: fill in groups (and reconcile name/role) from the real session.
  useEffect(() => {
    if (!live) return
    let cancelled = false
    getCurrentUser()
      .then((u) => {
        if (cancelled) return
        setUsername(u.name)
        setGroups(u.groups ?? [])
        setRoleState(u.admin ? 'admin' : 'user')
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
  }, [live])

  const setRole = (r: Role) => {
    if (live) return // role is owned by the session in live mode
    setRoleState(r)
    setUsername(r === 'admin' ? 'admin' : 'alice')
    try {
      localStorage.setItem(KEY, r)
    } catch {
      /* ignore */
    }
  }

  const ctx = useMemo<RoleCtx>(() => ({ role, setRole, username, groups, live, ready }), [role, username, groups, live, ready])

  if (live && !ready) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', color: 'var(--color-text-muted)', font: '14px system-ui' }}>
        Connecting to the hub…
      </div>
    )
  }

  return <Ctx.Provider value={ctx}>{children}</Ctx.Provider>
}
