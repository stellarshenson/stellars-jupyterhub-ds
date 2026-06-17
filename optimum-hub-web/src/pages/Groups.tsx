/* Groups - priority-ordered (higher wins on conflict), each row a link to its
 * policy config. Policy tags are type-only with the valued detail in a tooltip;
 * reorder by the up/down arrows; import / export a JSON of many groups. */
import { useEffect, useMemo, useRef, useState } from 'react'
import { DragSortTable } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { Button, Input, InputNumber, Popover, Space, Tooltip } from 'antd'
import { Link } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { CappedTags } from '../components/CappedTags'
import { IconAction } from '../components/IconAction'
import { Icon } from '../components/Icon'
import { useGroups } from '../hooks/queries'
import { notify } from '../services/actions'
import { deleteGroup, importGroups, reorderGroups } from '../services/ops'
import { fromPolicies } from '../lib/policyShape'
import type { GroupRow } from '../services/types'

// Editable rank cell: shows the row position and, on click, a small popover to
// type an arbitrary position; the value is clamped to [1, total] on apply.
function PositionCell({ rank, total, disabled, onSet }: { rank: number; total: number; disabled?: boolean; onSet: (pos: number) => void }) {
  const [open, setOpen] = useState(false)
  const [val, setVal] = useState<number | null>(rank)
  useEffect(() => setVal(rank), [rank])
  const apply = () => {
    const p = Math.max(1, Math.min(total, Math.round(val ?? rank)))
    setOpen(false)
    if (p !== rank) onSet(p)
  }
  if (disabled) return <span className="oh-num" title="Clear the filter to reorder">{rank}</span>
  return (
    <Popover
      open={open}
      onOpenChange={setOpen}
      trigger="click"
      title="Move to position"
      content={
        <Space.Compact>
          <InputNumber min={1} max={total} value={val} onChange={(v) => setVal(v == null ? null : Number(v))} onPressEnter={apply} size="small" style={{ width: 72 }} autoFocus />
          <Button size="small" type="primary" onClick={apply}>Apply</Button>
        </Space.Compact>
      }
    >
      <span className="oh-num" style={{ cursor: 'pointer' }} title="Priority rank - top wins on conflict; click to set position, or drag to reorder">{rank}</span>
    </Popover>
  )
}

export default function Groups() {
  const { data = [], isLoading } = useGroups()
  const [q, setQ] = useState('')
  const [rows, setRows] = useState<GroupRow[]>([])

  useEffect(() => {
    // Higher priority wins on conflict (server resolves priority-descending), so
    // the highest-priority group sits at the top - matching the reorder below,
    // which assigns the top row the highest number.
    setRows([...data].sort((a, b) => b.priority - a.priority))
  }, [data])

  const filtered = useMemo(() => rows.filter((g) => g.name.toLowerCase().includes(q.toLowerCase())), [rows, q])

  // Import a {groups:[{name, description, priority, policies[]}]} bundle (or a bare
  // array). policies[] is unfolded back to the flat config the hub stores; a legacy
  // flat `config` is still accepted so older exports round-trip. Parse client-side;
  // importGroups does the real create + PUT-config writes and owns its own toast.
  const fileRef = useRef<HTMLInputElement>(null)
  const onImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = '' // let the same file be re-picked later
    if (!file) return
    let groups
    try {
      const parsed = JSON.parse(await file.text())
      const list = Array.isArray(parsed) ? parsed : parsed?.groups
      if (!Array.isArray(list)) throw new Error('expected a { groups: [...] } bundle')
      groups = list
        .filter((g) => g && typeof g.name === 'string' && g.name.trim())
        .map((g) => ({
          name: g.name.trim(),
          description: g.description ?? '',
          priority: g.priority,
          config: Array.isArray(g.policies) ? fromPolicies(g.policies) : (g.config ?? {}),
        }))
      if (!groups.length) throw new Error('no valid group entries')
    } catch (err) {
      notify.error(`Import failed: ${(err as Error).message}`)
      return
    }
    importGroups(groups).catch(() => {}) // importGroups already toasted the failure
  }

  // Persist a new full ordering: top row gets the highest contiguous priority.
  // The backend re-normalises on the next fetch, so optimistic + persisted agree.
  const applyOrder = (order: GroupRow[]) => {
    setRows(order)
    reorderGroups(order.map((g, i) => ({ name: g.name, priority: order.length - i })))
  }
  const move = (from: number, to: number) => {
    if (from < 0 || to < 0 || to >= rows.length || from === to) return
    const next = [...rows]
    const [item] = next.splice(from, 1)
    next.splice(to, 0, item)
    applyOrder(next)
  }
  const setPosition = (name: string, pos: number) => {
    const from = rows.findIndex((r) => r.name === name)
    move(from, Math.max(0, Math.min(rows.length - 1, pos - 1)))
  }

  const columns: ProColumns<GroupRow>[] = [
    {
      title: '#',
      dataIndex: 'priority',
      width: 56,
      // Row rank, not the stored priority value: the backend normalises stored
      // priority to this contiguous rank on every fetch (top = highest). Click
      // to type a position; drag to reorder. Disabled while a filter is active.
      render: (_, g, i) => <PositionCell rank={i + 1} total={rows.length} disabled={!!q} onSet={(p) => setPosition(g.name, p)} />,
    },
    {
      title: 'Group',
      dataIndex: 'name',
      width: 180,
      ellipsis: true,
      render: (_, g) => (
        <Link to={`/groups/${g.name}`} style={{ color: 'var(--color-accent)' }} title="Open policy config">
          {g.name}
        </Link>
      ),
    },
    { title: 'Description', dataIndex: 'description', render: (_, g) => <span className="oh-muted">{g.description}</span> },
    {
      title: 'Members',
      dataIndex: 'members',
      align: 'right',
      sorter: (a, b) => a.members - b.members,
      render: (_, g) => {
        const names = g.memberNames ?? []
        const shown = names.slice(0, 10)
        const extra = names.length - shown.length
        const tip = names.length
          ? <span style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>{shown.join(', ')}{extra > 0 ? `, +${extra} more` : ''}</span>
          : 'No members'
        return (
          <Tooltip title={tip} styles={{ root: { maxWidth: 320 } }}>
            <Link to={`/groups/${g.name}`} className="oh-num">{g.members}</Link>
          </Tooltip>
        )
      },
    },
    {
      title: 'Policies',
      dataIndex: 'policies',
      render: (_, g) => <CappedTags items={g.policies.map((p) => ({ key: p.key, label: p.label, detail: p.detail }))} cap={4} />,
    },
    {
      title: 'Actions',
      align: 'right',
      width: 140,
      render: (_, g) => {
        const i = rows.findIndex((r) => r.name === g.name)
        return (
          <div className="oh-row" style={{ justifyContent: 'flex-end' }}>
            <IconAction icon="arrowup" title="Move up" disabled={!!q || i <= 0} onClick={() => move(i, i - 1)} />
            <IconAction icon="arrowdown" title="Move down" disabled={!!q || i < 0 || i >= rows.length - 1} onClick={() => move(i, i + 1)} />
            <IconAction icon="close" title="Delete group" tone="danger" onClick={() => deleteGroup(g.name)} />
          </div>
        )
      },
    },
  ]

  return (
    <>
      <PageHeader
        title="Groups"
        sub="Membership grants policy - priority decides who wins on conflict"
        actions={
          <>
            <input ref={fileRef} type="file" accept=".json,application/json" style={{ display: 'none' }} onChange={onImportFile} />
            <Button onClick={() => fileRef.current?.click()}>Import</Button>
            <Link to="/groups/export"><Button icon={<Icon name="download" size={14} />}>Export</Button></Link>
            <Link to="/groups/new"><Button type="primary" icon={<Icon name="plus" size={14} />}>Add group</Button></Link>
          </>
        }
      />
      <DragSortTable<GroupRow>
        rowKey="name"
        columns={columns}
        dataSource={filtered}
        loading={isLoading}
        search={false}
        options={false}
        dragSortKey="priority"
        onDragSortEnd={(_b, _a, newData) => {
          if (!q) setRows(newData)
          reorderGroups(newData.map((g, i) => ({ name: g.name, priority: newData.length - i })))
        }}
        rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
        pagination={{ pageSize: 12, showSizeChanger: false }}
        headerTitle={`${data.length} groups by priority`}
        toolBarRender={() => [
          <Input
            key="search"
            allowClear
            prefix={<Icon name="search" size={14} />}
            placeholder="Filter by name…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{ width: 200 }}
          />,
        ]}
      />
    </>
  )
}
