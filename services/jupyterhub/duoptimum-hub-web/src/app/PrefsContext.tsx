/* Per-user display preferences - the client side of the options harness.
 *
 * Single source of truth for the user's Display Options. Loads once per user
 * (live: GET /hub/api/users/{me}/display-preferences; mock: localStorage) and
 * exposes usePref/useSetPref. setPref updates state OPTIMISTICALLY so the change
 * applies immediately - consumers re-render at once, no refetch needed (the data
 * sources already carry every display value) - then writes through (live: PUT;
 * mock: localStorage). Stored values are resolved against PREF_DEFAULTS, so a
 * missing or unknown key falls back to its registry default. */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useRole } from './RoleContext'
import { isMock, dataMode } from '../services/dataMode'
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

const mockKey = (user: string) => `doh-user-prefs-${dataMode()}-${user}`

function readMock(user: string): RawPrefs {
  try {
    const raw = localStorage.getItem(mockKey(user))
    const value = raw ? JSON.parse(raw) : {}
    return value && typeof value === 'object' ? (value as RawPrefs) : {}
  } catch {
    return {}
  }
}

function writeMock(user: string, prefs: RawPrefs) {
  try {
    localStorage.setItem(mockKey(user), JSON.stringify(prefs))
  } catch {
    /* ignore quota / disabled storage */
  }
}

export function PrefsProvider({ children }: { children: ReactNode }) {
  const { username } = useRole()
  const [raw, setRaw] = useState<RawPrefs>({})

  // load once per user (live: hub store; mock: localStorage). A failed live read
  // leaves the defaults in place rather than blocking the app.
  useEffect(() => {
    if (!username) return
    if (isMock()) {
      setRaw(readMock(username))
      return
    }
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
      if (isMock()) {
        writeMock(username, next)
      } else {
        // persist just the changed key (the backend merges); revert-on-error keeps
        // the UI honest if the write fails
        hubSend('PUT', `/users/${encodeURIComponent(username)}/display-preferences`, { prefs: { [key]: value } })
          .catch((e) => {
            notify.error(`Could not save setting: ${(e as Error).message}`)
            setRaw((cur) => ({ ...cur, [key]: prev[key] }))
          })
      }
      return next
    })
  }, [username])

  const ctx = useMemo<PrefsCtx>(() => ({ get, set }), [get, set])
  return <Ctx.Provider value={ctx}>{children}</Ctx.Provider>
}
