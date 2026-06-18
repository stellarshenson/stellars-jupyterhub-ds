/* Icon-only row action (the `list-icon` button). Text-button square with a
 * tooltip. Tone follows the icon design language:
 *   primary   - blue  (var(--color-accent))  - the active / go-to affordance
 *   secondary - gray  (antd text default)    - neutral, the default
 *   danger    - red   (antd danger)          - destructive / stop
 *   warning   - yellow(var(--color-warning)) - caution
 * The single affordance for per-row lifecycle actions. */
import { Button, Spin, Tooltip } from 'antd'
import { Icon } from './Icon'
import type { IconKey } from './Icon'

export type IconTone = 'primary' | 'secondary' | 'danger' | 'warning'

export function IconAction({
  icon,
  title,
  onClick,
  tone = 'secondary',
  disabled,
  filled,
  busy,
}: {
  icon: IconKey
  title: string
  onClick?: () => void
  tone?: IconTone
  disabled?: boolean
  filled?: boolean // solid glyph - used for stop (a stroked square reads as a stray box)
  busy?: boolean // show an inline spinner in place of the icon while this action is in flight
}) {
  const color = disabled
    ? undefined
    : tone === 'primary'
      ? 'var(--color-accent)'
      : tone === 'warning'
        ? 'var(--color-warning)'
        : undefined // secondary -> antd default; danger -> antd danger handles red
  return (
    <Tooltip title={title}>
      <Button
        type="text"
        size="small"
        danger={tone === 'danger'}
        disabled={disabled || busy}
        onClick={onClick}
        icon={busy ? <Spin size="small" /> : <Icon name={icon} size={filled ? 14 : 16} filled={filled} />}
        style={color ? { color } : undefined}
        aria-label={title}
      />
    </Tooltip>
  )
}
