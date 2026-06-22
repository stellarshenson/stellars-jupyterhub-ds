/* Per-user display preferences - the client side of the options harness.
 *
 * Single source of truth for the user's Display Options. Loads once per user
 * (GET /hub/api/users/{me}/display-preferences) and exposes usePref/useSetPref.
 * setPref updates state OPTIMISTICALLY so the change applies immediately -
 * consumers re-render at once, no refetch needed (the data sources already carry
 * every display value) - then writes through (PUT). Stored values are resolved
 * against PREF_DEFAULTS, so a missing or unknown key falls back to its registry
 * default. */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useRole } from './RoleContext'
import { hubGet, hubSend } from '../services/hub/client'
import { notify } from '../services/actions'
import { PREF_DEFAULTS } from '../services/displayOptions'
import type { PrefValue, RawPrefs } from '../services/displayOptions'

interface PrefsCtx {
  get: (key: string) => PrefValue
  set: (key: string, value: PrefValue) => void
}

const Ctx = createContext<PrefsCtx | null>(null)

export function usePref(key: string): PrefValue {
  const c = useContext(Ctx)
  if (!c) throw new Error('usePref must be used inside PrefsProvider')
  return c.get(key)
}

export function useSetPref(): (key: string, value: PrefValue) => void {
  const c = useContext(Ctx)
  if (!c) throw new Error('useSetPref must be used inside PrefsProvider')
  return c.set
}

export function PrefsProvider({ children }: { children: ReactNode }) {
  const { username } = useRole()
  const [raw, setRaw] = useState<RawPrefs>({})

  // load once per user from the hub store. A failed read leaves the defaults in
  // place rather than blocking the app.
  useEffect(() => {
    if (!username) return
    let cancelled = false
    hubGet<{ prefs?: RawPrefs }>(`/users/${encodeURIComponent(username)}/display-preferences`)
      .then((r) => { if (!cancelled) setRaw(r.prefs ?? {}) })
      .catch(() => { /* defaults apply */ })
    return () => { cancelled = true }
  }, [username])

  // `??` (not `in`) so a stored `false`/`0` is kept but a missing/undefined key
  // (incl. a reverted one) falls back to the registry default
  const get = useCallback((key: string): PrefValue => raw[key] ?? PREF_DEFAULTS[key], [raw])

  const set = useCallback((key: string, value: PrefValue) => {
    setRaw((prev) => {
      const next = { ...prev, [key]: value }
      // persist just the changed key (the backend merges); revert-on-error keeps
      // the UI honest if the write fails
      hubSend('PUT', `/users/${encodeURIComponent(username)}/display-preferences`, { prefs: { [key]: value } })
        .catch((e) => {
          notify.error(`Could not save setting: ${(e as Error).message}`)
          setRaw((cur) => ({ ...cur, [key]: prev[key] }))
        })
      return next
    })
  }, [username])

  const ctx = useMemo<PrefsCtx>(() => ({ get, set }), [get, set])
  return <Ctx.Provider value={ctx}>{children}</Ctx.Provider>
}
