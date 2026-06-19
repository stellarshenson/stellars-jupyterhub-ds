/* Group membership widget: the current-groups chip input plus a browse-and-add
 * list (filter + each group's policies + an explicit Add). Shared by Configure
 * user, New user and Bulk add so the add-a-group experience is identical. */
import { useMemo, useState } from 'react'
import { Button, Input, Table } from 'antd'
import { Combo } from './Combo'
import { CappedTags } from './CappedTags'
import { Icon } from './Icon'
import { useGroupCorpus, useGroups } from '../hooks/queries'
import type { GroupRow } from '../services/types'

export function GroupPicker({ value, onChange, label = 'Groups' }: { value: string[]; onChange: (v: string[]) => void; label?: string }) {
  const { data: corpus = [] } = useGroupCorpus()
  const { data: allGroups = [] } = useGroups()
  const [q, setQ] = useState('')

  const addable = useMemo(() => {
    const s = q.toLowerCase()
    return allGroups.filter(
      (g) => !value.includes(g.name) && (g.name.toLowerCase().includes(s) || (g.description ?? '').toLowerCase().includes(s)),
    )
  }, [allGroups, value, q])

  const add = (g: GroupRow) => {
    if (!value.includes(g.name)) onChange([...value, g.name])
  }

  return (
    <div>
      {label && <div style={{ marginBottom: 8, color: 'var(--color-text-muted)', fontSize: 13 }}>{label}</div>}
      <Combo corpus={corpus} value={value} onChange={onChange} placeholder="Add a group by name…" />

      <div className="doh-section-title">Add a Group</div>
      <div className="doh-page-sub" style={{ marginBottom: 12 }}>Browse the catalogue - each group's policies are shown; membership grants them.</div>
      <Input
        allowClear
        prefix={<Icon name="search" size={14} />}
        placeholder="Filter groups…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        style={{ maxWidth: 280, marginBottom: 12 }}
      />
      <Table<GroupRow>
        rowKey="name"
        size="small"
        pagination={false}
        scroll={{ y: 260 }}
        dataSource={addable}
        locale={{ emptyText: 'No group matches that filter' }}
        columns={[
          { title: 'Group', dataIndex: 'name', width: 160, render: (v) => <b>{v}</b> },
          { title: 'Description', dataIndex: 'description', render: (v) => <span className="doh-muted">{v}</span> },
          {
            title: 'Policies',
            dataIndex: 'policies',
            render: (_, g) =>
              g.policies.length ? (
                <CappedTags items={g.policies.map((p) => ({ key: p.key, label: p.label, detail: p.detail }))} cap={4} />
              ) : (
                <span className="doh-muted">No policies</span>
              ),
          },
          {
            title: 'Add',
            align: 'right',
            width: 90,
            render: (_, g) => (
              <Button size="small" icon={<Icon name="plus" size={13} />} onClick={() => add(g)}>
                Add
              </Button>
            ),
          },
        ]}
      />
    </div>
  )
}
