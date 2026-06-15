/* Role context - one build serves both admin and plain-user views (the static
 * mock used two URLs). The mock-only role switch on Home flips this; it persists
 * so a reload keeps the chosen view. */
import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { Role } from '../services/types'

const KEY = 'optimum-hub-role'

interface RoleCtx {
  role: Role
  setRole: (r: Role) => void
}

const Ctx = createContext<RoleCtx | null>(null)

export function useRole(): RoleCtx {
  const c = useContext(Ctx)
  if (!c) throw new Error('useRole must be used inside RoleProvider')
  return c
}

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>(() => {
    try {
      const r = localStorage.getItem(KEY)
      if (r === 'user' || r === 'admin') return r
    } catch {
      /* ignore */
    }
    return 'admin'
  })
  const setRole = (r: Role) => {
    setRoleState(r)
    try {
      localStorage.setItem(KEY, r)
    } catch {
      /* ignore */
    }
  }
  const ctx = useMemo<RoleCtx>(() => ({ role, setRole }), [role])
  return <Ctx.Provider value={ctx}>{children}</Ctx.Provider>
}
