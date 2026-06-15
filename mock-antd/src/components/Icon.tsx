/* Shared icon set - the static mock's line glyphs ported verbatim (Remix-style,
 * 24x24, currentColor stroke), so events / grants / nav / quick-actions render
 * identically to the HTML mock. antd's own icons are used where a stock glyph
 * fits; this set covers the JupyterHub-specific ones. */
import type { CSSProperties } from 'react'

export type IconKey =
  | 'grid' | 'server' | 'users' | 'group' | 'shield' | 'activity' | 'settings'
  | 'search' | 'sun' | 'moon' | 'monitor' | 'clock' | 'plus' | 'bell' | 'play'
  | 'restart' | 'stop' | 'megaphone' | 'logout' | 'dots' | 'key' | 'user' | 'cpu'
  | 'check' | 'arrowup' | 'arrowdown' | 'chevron' | 'close' | 'grip' | 'disk'
  | 'gpu' | 'memory' | 'download' | 'upload' | 'box' | 'code'

const PATHS: Record<IconKey, string> = {
  grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  server: 'M4 5h16v6H4zM4 13h16v6H4z M8 8h.01M8 16h.01',
  users: 'M16 19v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 19v-2a4 4 0 0 0-3-3.87M16 3.13A4 4 0 0 1 16 11',
  group: 'M17 20v-2a4 4 0 0 0-3-3.87M5 20v-2a4 4 0 0 1 4-4h2a4 4 0 0 1 4 4v2M10 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6M17 11a3 3 0 1 0-2-5.2',
  shield: 'M12 2l8 3v6c0 5-3.5 8-8 11-4.5-3-8-6-8-11V5z M9 12l2 2 4-4',
  activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
  settings: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z M12 2v3M12 19v3M22 12h-3M5 12H2M19.07 4.93l-2.12 2.12M7.05 16.95l-2.12 2.12M19.07 19.07l-2.12-2.12M7.05 7.05 4.93 4.93',
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
}

export function Icon({
  name,
  size = 16,
  className,
  style,
}: {
  name: IconKey
  size?: number
  className?: string
  style?: CSSProperties
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flex: 'none', ...style }}
      aria-hidden
    >
      <path d={PATHS[name]} />
    </svg>
  )
}
