/* Apply the resolved palette as CSS custom properties on <html>, so the bespoke
 * components (status pill, activity meter, spark, resource bars, TTL gadget,
 * notice) read the very same --color-* tokens the antd surface uses. Toggling
 * the theme re-applies these and flips data-theme + color-scheme. */
import { PALETTES, SPACE, RADIUS, TEXT, FONT } from './tokens'
import type { ResolvedTheme } from './tokens'

export function themeVars(mode: ResolvedTheme): Record<string, string> {
  const p = PALETTES[mode]
  return {
    '--color-bg': p.bg,
    '--color-bg-subtle': p.bgSubtle,
    '--color-surface': p.surface,
    '--color-surface-hover': p.surfaceHover,
    '--color-surface-active': p.surfaceActive,
    '--color-surface-raised': p.surfaceRaised,
    '--color-overlay': p.overlay,
    '--color-border-subtle': p.borderSubtle,
    '--color-border': p.border,
    '--color-border-strong': p.borderStrong,
    '--color-text': p.text,
    '--color-text-muted': p.textMuted,
    '--color-text-subtle': p.textSubtle,
    '--color-accent': p.accent,
    '--color-accent-hover': p.accentHover,
    '--color-accent-active': p.accentActive,
    '--color-accent-fg': p.accentFg,
    '--color-accent-soft': p.accentSoft,
    '--color-accent-ring': p.accentRing,
    '--color-accent-2': p.accent2,
    '--color-accent-2-soft': p.accent2Soft,
    '--color-success': p.success,
    '--color-success-fg': p.successFg,
    '--color-success-soft': p.successSoft,
    '--color-warning': p.warning,
    '--color-warning-fg': p.warningFg,
    '--color-warning-soft': p.warningSoft,
    '--color-danger': p.danger,
    '--color-danger-fg': p.dangerFg,
    '--color-danger-soft': p.dangerSoft,
    '--color-info': p.info,
    '--color-info-fg': p.infoFg,
    '--color-info-soft': p.infoSoft,
    '--shadow-sm': p.shadowSm,
    '--shadow-md': p.shadowMd,
    '--shadow-overlay': p.shadowOverlay,
    '--space-1': SPACE[1],
    '--space-2': SPACE[2],
    '--space-3': SPACE[3],
    '--space-4': SPACE[4],
    '--space-5': SPACE[5],
    '--space-6': SPACE[6],
    '--space-8': SPACE[8],
    '--radius-sm': RADIUS.sm,
    '--radius-md': RADIUS.md,
    '--radius-lg': RADIUS.lg,
    '--radius-full': RADIUS.full,
    '--text-xs': TEXT.xs,
    '--text-sm': TEXT.sm,
    '--text-base': TEXT.base,
    '--text-lg': TEXT.lg,
    '--text-xl': TEXT.xl,
    '--text-2xl': TEXT.xxl,
    '--font-sans': FONT.sans,
    '--font-mono': FONT.mono,
  }
}

export function applyThemeVars(mode: ResolvedTheme): void {
  const root = document.documentElement
  const vars = themeVars(mode)
  for (const [k, v] of Object.entries(vars)) root.style.setProperty(k, v)
  root.setAttribute('data-theme', mode === 'dark' ? 'optimum-hub-dark' : 'optimum-hub-light')
  root.style.colorScheme = mode
}
