/* Standard page header - title, optional sub-line, optional right-aligned actions
 * (the `.page-head` of the static mock). */
import type { ReactNode } from 'react'

export function PageHeader({ title, sub, actions }: { title: string; sub?: ReactNode; actions?: ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 24 }}>
      <div style={{ minWidth: 0 }}>
        <h1 style={{ fontSize: 26, fontWeight: 600, margin: 0, color: 'var(--color-text)' }}>{title}</h1>
        {sub && <div className="oh-page-sub" style={{ marginTop: 2 }}>{sub}</div>}
      </div>
      {actions && (
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>{actions}</div>
      )}
    </div>
  )
}
