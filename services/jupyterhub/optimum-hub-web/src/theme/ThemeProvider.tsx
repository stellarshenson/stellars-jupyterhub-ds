/* Three-mode theme controller (light / dark / system), persisted in
 * localStorage under "optimum-hub-theme" - mirrors the static mock's app.js.
 * Applies the antd ConfigProvider theme and the CSS variables together, and
 * tracks live OS changes while in system mode. Wraps children in antd's <App>
 * so message/notification have a context. */
import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { App as AntApp, ConfigProvider } from 'antd'
import enUS from 'antd/locale/en_US'
import { buildAntdTheme } from './antdTheme'
import { applyThemeVars } from './cssVars'
import { PALETTES } from './tokens'
import type { ResolvedTheme, ThemeMode } from './tokens'

const STORAGE_KEY = 'optimum-hub-theme'

function systemTheme(): ResolvedTheme {
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function readMode(): ThemeMode {
  try {
    const m = localStorage.getItem(STORAGE_KEY)
    if (m === 'light' || m === 'dark' || m === 'system') return m
    if (m === 'optimum-hub-light') return 'light'
    if (m === 'optimum-hub-dark') return 'dark'
  } catch {
    /* ignore */
  }
  return 'system'
}

function resolve(mode: ThemeMode): ResolvedTheme {
  return mode === 'system' ? systemTheme() : mode
}

interface ThemeCtx {
  mode: ThemeMode
  resolved: ResolvedTheme
  setMode: (m: ThemeMode) => void
}

const Ctx = createContext<ThemeCtx | null>(null)

export function useTheme(): ThemeCtx {
  const c = useContext(Ctx)
  if (!c) throw new Error('useTheme must be used inside ThemeProvider')
  return c
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => readMode())
  const [resolved, setResolved] = useState<ResolvedTheme>(() => resolve(readMode()))

  const setMode = (m: ThemeMode) => {
    setModeState(m)
    try {
      localStorage.setItem(STORAGE_KEY, m)
    } catch {
      /* ignore */
    }
  }

  // resolve + apply whenever the mode changes
  useEffect(() => {
    const r = resolve(mode)
    setResolved(r)
    applyThemeVars(r)
  }, [mode])

  // track OS changes while in system mode
  useEffect(() => {
    if (mode !== 'system' || !window.matchMedia) return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => {
      const r = systemTheme()
      setResolved(r)
      applyThemeVars(r)
    }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [mode])

  const themeConfig = useMemo(() => buildAntdTheme(resolved, PALETTES[resolved]), [resolved])
  const ctx = useMemo<ThemeCtx>(() => ({ mode, resolved, setMode }), [mode, resolved])

  return (
    <Ctx.Provider value={ctx}>
      <ConfigProvider theme={themeConfig} locale={enUS}>
        <AntApp>{children}</AntApp>
      </ConfigProvider>
    </Ctx.Provider>
  )
}
