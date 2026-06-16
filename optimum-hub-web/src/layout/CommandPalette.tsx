/* Command palette (Cmd/Ctrl+K) - role-scoped go-to-page entries plus the role's
 * quick actions. antd has no Cmd-K, so this is a small custom overlay; arrow keys
 * move the selection, Enter runs it, Esc closes. */
import { Modal, Input } from 'antd'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '../components/Icon'
import type { IconKey } from '../components/Icon'
import { useRole } from '../app/RoleContext'
import { actionsFor, navLeaves } from '../app/nav'
import { mockAction } from '../services/actions'

interface Row {
  group: string
  icon: IconKey
  label: string
  hint?: string
  run: () => void
}

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(0)
  const { role } = useRole()
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const rows = useMemo<Row[]>(() => {
    const nav: Row[] = navLeaves(role).map((n) => ({
      group: 'Go to',
      icon: n.icon,
      label: n.label,
      run: () => navigate(n.path),
    }))
    const acts: Row[] = actionsFor(role).map((a) => ({
      group: a.group,
      icon: a.icon,
      label: a.label,
      hint: a.hint,
      run: a.kind === 'nav' ? () => navigate(a.to) : () => mockAction(a.toast),
    }))
    return [...nav, ...acts]
  }, [role, navigate])

  const filtered = useMemo(
    () => rows.filter((r) => r.label.toLowerCase().includes(q.toLowerCase())),
    [rows, q],
  )

  useEffect(() => {
    if (open) {
      setQ('')
      setSel(0)
      setTimeout(() => inputRef.current?.focus(), 60)
    }
  }, [open])

  useEffect(() => {
    if (sel >= filtered.length) setSel(0)
  }, [filtered.length, sel])

  const run = (i: number) => {
    const r = filtered[i]
    setOpen(false)
    if (r) r.run()
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSel((s) => Math.min(s + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSel((s) => Math.max(s - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      run(sel)
    }
  }

  // group the filtered rows in order of first appearance
  const groups: string[] = []
  filtered.forEach((r) => {
    if (!groups.includes(r.group)) groups.push(r.group)
  })

  let flatIndex = -1

  return (
    <Modal
      open={open}
      onCancel={() => setOpen(false)}
      footer={null}
      closable={false}
      width={620}
      style={{ top: 96 }}
      styles={{ body: { padding: 0 } }}
      destroyOnClose
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)' }}>
        <Icon name="search" size={18} style={{ color: 'var(--color-text-subtle)' }} />
        <Input
          ref={inputRef as never}
          variant="borderless"
          placeholder="Search pages, actions…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={onKeyDown}
          style={{ fontSize: 16, padding: 0 }}
        />
      </div>
      <div style={{ maxHeight: '56vh', overflowY: 'auto', padding: 8 }}>
        {filtered.length === 0 && (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-subtle)' }}>No matches</div>
        )}
        {groups.map((g) => (
          <div key={g}>
            <div className="oh-cmdk-group">{g}</div>
            {filtered
              .filter((r) => r.group === g)
              .map((r) => {
                flatIndex += 1
                const i = flatIndex
                return (
                  <div
                    key={`${g}-${r.label}`}
                    className={`oh-cmdk-item${i === sel ? ' sel' : ''}`}
                    onMouseEnter={() => setSel(i)}
                    onClick={() => run(i)}
                  >
                    <Icon name={r.icon} size={16} />
                    <span style={{ flex: 1 }}>{r.label}</span>
                    {r.hint && <span className="oh-kbd">{r.hint}</span>}
                  </div>
                )
              })}
          </div>
        ))}
      </div>
    </Modal>
  )
}
