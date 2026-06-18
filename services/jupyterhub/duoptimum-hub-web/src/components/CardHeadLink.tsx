/* A whole card-head that navigates to the full page: title + chevron, no "View
 * all" text. The dashboard's one "go to section" affordance. */
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Icon } from './Icon'

export function CardHeadLink({ title, to, suffix }: { title: string; to: string; suffix?: ReactNode }) {
  return (
    <Link
      to={to}
      className="oh-head-link"
      style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none', color: 'inherit' }}
    >
      <h3 className="oh-head-title" style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>
        {title}
        {suffix && <span style={{ color: 'var(--color-text-subtle)', fontWeight: 400 }}> {suffix}</span>}
      </h3>
      <span className="oh-head-go" style={{ marginLeft: 'auto' }}>
        <Icon name="chevron" size={18} />
      </span>
    </Link>
  )
}
