/* Duoptimum Hub design tokens - the single source of truth for both themes.
 *
 * Theme = JupyterLab "Stellars Sublime" surfaces + Stellars-Tech cyan accent,
 * transcribed verbatim from mock/assets/tokens.css. This one module feeds BOTH
 * the antd ConfigProvider theme object (theme/antdTheme.ts) and the injected CSS
 * variables the bespoke components consume (theme/cssVars.ts) - so the antd
 * surface and the hand-built meters/pills/bars never drift apart. */

export type ThemeMode = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

export interface Palette {
  bg: string
  bgSubtle: string
  surface: string
  surfaceHover: string
  surfaceActive: string
  surfaceRaised: string
  overlay: string
  borderSubtle: string
  border: string
  borderStrong: string
  text: string
  textMuted: string
  textSubtle: string
  accent: string
  accentHover: string
  accentActive: string
  accentFg: string
  accentSoft: string
  accentRing: string
  accent2: string
  accent2Soft: string
  success: string
  successFg: string
  successSoft: string
  warning: string
  warningFg: string
  warningSoft: string
  danger: string
  dangerFg: string
  dangerSoft: string
  info: string
  infoFg: string
  infoSoft: string
  shadowSm: string
  shadowMd: string
  shadowOverlay: string
}

export const DARK: Palette = {
  bg: '#252b32',
  bgSubtle: '#2a313a',
  surface: '#303841',
  surfaceHover: '#374049',
  surfaceActive: '#404b54',
  surfaceRaised: '#343d47',
  overlay: 'rgba(15, 18, 22, .66)',
  borderSubtle: '#363f49',
  border: '#404b54',
  borderStrong: '#4d5a65',
  text: '#c3c3c3',
  textMuted: '#a5a5a5',
  textSubtle: '#7d8791',
  accent: '#21a8e4',
  accentHover: '#46bcf0',
  accentActive: '#0e93cf',
  accentFg: '#ffffff',
  accentSoft: 'rgba(0, 150, 209, .14)',
  accentRing: 'rgba(0, 150, 209, .45)',
  accent2: '#da8230',
  accent2Soft: 'rgba(218, 130, 48, .16)',
  success: '#3fb950',
  successFg: '#0b1410',
  successSoft: 'rgba(63,185,80,.15)',
  warning: '#da8230',
  warningFg: '#1a1209',
  warningSoft: 'rgba(218,130,48,.16)',
  danger: '#f1746c',
  dangerFg: '#1a0c0b',
  dangerSoft: 'rgba(241,116,108,.15)',
  info: '#0096d1',
  infoFg: '#06141a',
  infoSoft: 'rgba(0,150,209,.15)',
  shadowSm: '0 1px 2px rgba(0,0,0,.35)',
  shadowMd: '0 6px 18px rgba(0,0,0,.4)',
  shadowOverlay: '0 16px 48px rgba(0,0,0,.5)',
}

export const LIGHT: Palette = {
  bg: '#f5f7fa',
  bgSubtle: '#eef1f5',
  surface: '#ffffff',
  surfaceHover: '#f1f4f7',
  surfaceActive: '#e6ebf0',
  surfaceRaised: '#ffffff',
  overlay: 'rgba(26, 35, 41, .38)',
  borderSubtle: '#e7ecf1',
  border: '#d4dde3',
  borderStrong: '#b7c4cc',
  text: '#1a3540',
  textMuted: '#46606c',
  textSubtle: '#6c828d',
  accent: '#06709c',
  accentHover: '#0a82b8',
  accentActive: '#05607f',
  accentFg: '#ffffff',
  accentSoft: 'rgba(10, 130, 184, .10)',
  accentRing: 'rgba(10, 130, 184, .35)',
  accent2: '#b5641b',
  accent2Soft: 'rgba(181, 100, 27, .12)',
  success: '#1a7f37',
  successFg: '#ffffff',
  successSoft: 'rgba(26,127,55,.12)',
  warning: '#9a6700',
  warningFg: '#ffffff',
  warningSoft: 'rgba(154,103,0,.12)',
  danger: '#d94851',
  dangerFg: '#ffffff',
  dangerSoft: 'rgba(217,72,81,.10)',
  info: '#0a82b8',
  infoFg: '#ffffff',
  infoSoft: 'rgba(10,130,184,.12)',
  shadowSm: '0 1px 2px rgba(16,40,56,.08)',
  shadowMd: '0 6px 18px rgba(16,40,56,.10)',
  shadowOverlay: '0 16px 48px rgba(16,40,56,.18)',
}

export const PALETTES: Record<ResolvedTheme, Palette> = { light: LIGHT, dark: DARK }

export const SPACE = { 1: '4px', 2: '8px', 3: '12px', 4: '16px', 5: '24px', 6: '32px', 8: '48px' }
export const RADIUS = { sm: '4px', md: '6px', lg: '10px', full: '9999px' }
export const TEXT = { xs: '12px', sm: '13px', base: '14px', lg: '16px', xl: '20px', xxl: '26px' }
export const FONT = {
  sans: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
  mono: 'ui-monospace, "JetBrains Mono", "SFMono-Regular", Menlo, monospace',
}

export const SIDEBAR_W = 248
export const TOPBAR_H = 56
