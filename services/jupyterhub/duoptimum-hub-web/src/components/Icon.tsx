/* Shared icon set - the static mock's line glyphs ported verbatim (Remix-style,
 * 24x24, currentColor stroke), so events / grants / nav / quick-actions render
 * identically to the HTML mock. antd's own icons are used where a stock glyph
 * fits; this set covers the JupyterHub-specific ones.
 *
 * Dual weight (design language): every glyph has a LINE weight (default,
 * wireframe, in-list) and many also a FILLED weight (standalone / primary). A
 * line path with open arcs or interior detail fills WRONG (open bell, buried
 * shield check, cutout box), so the dual-weight glyphs carry a separate solid
 * body in FILLED; simple closed shapes (play / stop / check) just fill the line
 * path. See docs/design-system - section "Two weights, one rule". */
import type { CSSProperties } from 'react'

export type IconKey =
  | 'grid' | 'server' | 'users' | 'group' | 'shield' | 'activity' | 'settings'
  | 'search' | 'sun' | 'moon' | 'monitor' | 'clock' | 'plus' | 'bell' | 'play'
  | 'restart' | 'stop' | 'megaphone' | 'logout' | 'dots' | 'key' | 'user' | 'cpu'
  | 'check' | 'arrowup' | 'arrowdown' | 'chevron' | 'close' | 'grip' | 'disk'
  | 'gpu' | 'memory' | 'download' | 'upload' | 'box' | 'code' | 'warning'

const PATHS: Record<IconKey, string> = {
  grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  server: 'M4 5h16v6H4zM4 13h16v6H4z M8 8h.01M8 16h.01',
  users: 'M16 19v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 19v-2a4 4 0 0 0-3-3.87M16 3.13A4 4 0 0 1 16 11',
  group: 'M17 20v-2a4 4 0 0 0-3-3.87M5 20v-2a4 4 0 0 1 4-4h2a4 4 0 0 1 4 4v2M10 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6M17 11a3 3 0 1 0-2-5.2',
  shield: 'M12 2l8 3v6c0 5-3.5 8-8 11-4.5-3-8-6-8-11V5z M9 12l2 2 4-4',
  activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
  settings: 'M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16M21 21l-4.3-4.3',
  sun: 'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
  moon: 'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z',
  monitor: 'M3 4h18v12H3zM8 20h8M12 16v4',
  clock: 'M12 7v5l3 2M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z',
  plus: 'M12 5v14M5 12h14',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0',
  play: 'M5 3l14 9-14 9z',
  restart: 'M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5',
  stop: 'M6 6h12v12H6z',
  megaphone: 'M3 11l18-5v12L3 14v-3z M11.6 16.8a3 3 0 1 1-5.8-1.6',
  logout: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9',
  dots: 'M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2M19 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2M5 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2',
  key: 'M7 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M11 12h10M17 12v3M21 12v4',
  user: 'M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8',
  cpu: 'M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3M5 5h14v14H5zM9 9h6v6H9z',
  check: 'M20 6L9 17l-5-5',
  arrowup: 'M12 19V5M5 12l7-7 7 7',
  arrowdown: 'M12 5v14M5 12l7 7 7-7',
  chevron: 'M9 18l6-6-6-6',
  close: 'M18 6 6 18M6 6l12 12',
  grip: 'M9 5h.01M9 12h.01M9 19h.01M15 5h.01M15 12h.01M15 19h.01',
  disk: 'M22 12H2M5.45 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.9A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.1z M6 16h.01M10 16h.01',
  gpu: 'M3 6h18v12H3zM8 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M14 10h4M14 14h4',
  memory: 'M3 8h18v8H3zM7 11v2M11 11v2M15 11v2M6 16v2M10 16v2M14 16v2M18 16v2',
  download: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3',
  upload: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12',
  box: 'M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16zM3.27 6.96 12 12.01l8.73-5.05M12 22.08V12',
  code: 'm18 16 4-4-4-4M6 8l-4 4 4 4M14.5 4l-5 16',
  // warning sign - filled triangle with the exclamation punched out via even-odd
  warning: 'M12 2.6a1.7 1.7 0 0 1 1.48.86l8.1 14.02A1.7 1.7 0 0 1 20.1 20H3.9a1.7 1.7 0 0 1-1.48-2.52l8.1-14.02A1.7 1.7 0 0 1 12 2.6zM11 9h2v5h-2V9zm0 7h2v2h-2v-2z',
}

/* Filled-weight variants (design-language dual-weight set). `body` is a solid
 * shape filled with currentColor; optional `detail` is a line drawn over it at a
 * darker same-hue stroke (e.g. the disk's seam + dots). Glyphs absent here fall
 * back to filling their line path - correct for simple closed shapes. */
type FilledSpec = { body: string; detail?: string }
const FILLED: Partial<Record<IconKey, FilledSpec>> = {
  bell: { body: 'M12 2a6 6 0 0 0-6 6c0 7-3 9-3 9h18s-3-2-3-9a6 6 0 0 0-6-6z', detail: 'M10.3 21a2 2 0 0 0 3.4 0' },
  shield: { body: 'M12 2l8 3v6c0 5-3.5 8-8 11-4.5-3-8-6-8-11V5z' },
  box: { body: 'M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z' },
  user: { body: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1z' },
  disk: { body: 'M5.45 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.9A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.1z', detail: 'M22 12H2M6 16h.01M10 16h.01' },
}

export function Icon({
  name,
  size = 16,
  className,
  style,
  filled = false,
}: {
  name: IconKey
  size?: number
  className?: string
  style?: CSSProperties
  filled?: boolean // solid weight instead of line stroke; dual-weight glyphs (FILLED) render a proper solid body, simple closed shapes just fill the line path
}) {
  const spec = filled ? FILLED[name] : undefined
  const common = { className, width: size, height: size, viewBox: '0 0 24 24', style: { flex: 'none', ...style }, 'aria-hidden': true } as const
  // dual-weight filled glyph: solid body + optional darker line detail over it
  if (spec) {
    return (
      <svg {...common} fill="none" stroke="none">
        <path d={spec.body} fill="currentColor" />
        {spec.detail && (
          <path d={spec.detail} fill="none" stroke="color-mix(in srgb, currentColor, black 60%)" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
        )}
      </svg>
    )
  }
  // single-path: line weight, or filled simple closed shape (play/stop/check) with
  // a darker same-hue contour. warning is a self-contained filled sign: even-odd
  // punches its exclamation out as holes, and it carries no contour stroke.
  const isWarning = name === 'warning'
  return (
    <svg
      {...common}
      fill={filled ? 'currentColor' : 'none'}
      stroke={isWarning && filled ? 'none' : filled ? 'color-mix(in srgb, currentColor, black 55%)' : 'currentColor'}
      strokeWidth={filled ? 1 : 1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={PATHS[name]} fillRule={isWarning ? 'evenodd' : undefined} clipRule={isWarning ? 'evenodd' : undefined} />
    </svg>
  )
}
