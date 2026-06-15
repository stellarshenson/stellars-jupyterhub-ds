/* In-UI confirmation/status line - a subtle bar with a coloured left edge and a
 * sized leading glyph. Shown under the action that produced it. */
import type { ReactNode } from 'react'
import { Icon } from './Icon'
import type { IconKey } from './Icon'

type NoticeType = 'success' | 'warning' | 'info' | 'error'

const ICON: Record<NoticeType, IconKey> = { success: 'check', warning: 'shield', info: 'activity', error: 'close' }
const COLOR: Record<NoticeType, string> = {
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  info: 'var(--color-info)',
  error: 'var(--color-danger)',
}

export function Notice({ type, children }: { type: NoticeType; children: ReactNode }) {
  return (
    <div className={`oh-notice ${type}`}>
      <Icon name={ICON[type]} size={15} style={{ color: COLOR[type] }} />
      <span>{children}</span>
    </div>
  )
}
