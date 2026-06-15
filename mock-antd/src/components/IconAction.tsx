/* Icon-only row action (the `list-icon` button). Text-button square with a
 * tooltip; danger turns it red on hover. The single affordance for per-row
 * lifecycle actions. */
import { Button, Tooltip } from 'antd'
import { Icon } from './Icon'
import type { IconKey } from './Icon'

export function IconAction({
  icon,
  title,
  onClick,
  danger,
  disabled,
}: {
  icon: IconKey
  title: string
  onClick?: () => void
  danger?: boolean
  disabled?: boolean
}) {
  return (
    <Tooltip title={title}>
      <Button
        type="text"
        size="small"
        danger={danger}
        disabled={disabled}
        onClick={onClick}
        icon={<Icon name={icon} size={16} />}
        aria-label={title}
      />
    </Tooltip>
  )
}
