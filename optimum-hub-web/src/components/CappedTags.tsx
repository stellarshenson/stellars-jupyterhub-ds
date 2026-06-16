/* A tag row capped at N, the rest collapsing behind a +N popover. Used for the
 * Users list group chips and the Groups list policy tags (both accent-soft). */
import { Popover, Tag, Tooltip } from 'antd'

export interface TagItem {
  key: string
  label: string
  detail?: string
}

const base = { borderRadius: 4, margin: 0 }

function one(t: TagItem, accent: boolean) {
  const style = accent ? { ...base, background: 'var(--color-accent-soft)', color: 'var(--color-accent)' } : base
  const tag = (
    <Tag key={t.key} bordered={false} style={style}>
      {t.label}
    </Tag>
  )
  return t.detail ? (
    <Tooltip key={t.key} title={t.detail}>
      {tag}
    </Tooltip>
  ) : (
    tag
  )
}

export function CappedTags({ items, cap = 3, accent = true }: { items: TagItem[]; cap?: number; accent?: boolean }) {
  if (items.length === 0) return <span className="oh-muted">-</span>
  const shown = items.slice(0, cap)
  const rest = items.slice(cap)
  return (
    <span style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
      {shown.map((t) => one(t, accent))}
      {rest.length > 0 && (
        <Popover
          content={<div style={{ maxWidth: 260, display: 'flex', gap: 6, flexWrap: 'wrap' }}>{rest.map((t) => one(t, accent))}</div>}
        >
          <Tag style={{ ...base, cursor: 'pointer' }}>+{rest.length}</Tag>
        </Popover>
      )}
    </span>
  )
}
