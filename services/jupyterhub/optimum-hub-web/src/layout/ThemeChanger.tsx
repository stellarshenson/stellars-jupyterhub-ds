/* Segmented light / dark / system control - mirrors the static mock, sits in the
 * sider foot. */
import { Tooltip } from 'antd'
import { Icon } from '../components/Icon'
import type { IconKey } from '../components/Icon'
import { useTheme } from '../theme/ThemeProvider'
import type { ThemeMode } from '../theme/tokens'

const MODES: Array<{ mode: ThemeMode; icon: IconKey; title: string }> = [
  { mode: 'light', icon: 'sun', title: 'Light' },
  { mode: 'dark', icon: 'moon', title: 'Dark' },
  { mode: 'system', icon: 'monitor', title: 'System' },
]

export function ThemeChanger() {
  const { mode, setMode } = useTheme()
  return (
    <div className="oh-theme-changer">
      {MODES.map((m) => (
        <Tooltip key={m.mode} title={m.title}>
          <button className={mode === m.mode ? 'on' : ''} onClick={() => setMode(m.mode)} aria-label={m.title}>
            <Icon name={m.icon} size={15} />
          </button>
        </Tooltip>
      ))}
    </div>
  )
}
