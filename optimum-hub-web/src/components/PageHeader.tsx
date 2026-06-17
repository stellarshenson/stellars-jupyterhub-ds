/* Page header. The big title + sub-line were removed - the breadcrumb already
 * names the page, so they only cost ~50px of vertical space. Only the optional
 * right-aligned actions remain (so pages that put a primary action here keep it).
 * `title`/`sub` are accepted but ignored, so no call site needs touching. */
import type { ReactNode } from 'react'

export function PageHeader({ actions }: { title?: string; sub?: ReactNode; actions?: ReactNode }) {
  if (!actions) return null
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
      {actions}
    </div>
  )
}
