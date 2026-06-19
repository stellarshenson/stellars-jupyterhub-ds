/* The one action footer every config / create screen uses: destructive on the
 * left, Cancel / Save on the right. */
import type { ReactNode } from 'react'
import { Button } from 'antd'

export function FormFooter({
  onCancel,
  onSave,
  saveLabel = 'Save',
  destructive,
}: {
  onCancel: () => void
  onSave: () => void
  saveLabel?: string
  destructive?: ReactNode
}) {
  return (
    <div className="doh-form-foot">
      <div>{destructive}</div>
      <div className="right">
        <Button onClick={onCancel}>Cancel</Button>
        <Button type="primary" onClick={onSave}>
          {saveLabel}
        </Button>
      </div>
    </div>
  )
}
