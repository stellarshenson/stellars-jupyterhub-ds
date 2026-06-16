/* Groups - priority-ordered (higher wins on conflict), each row a link to its
 * policy config. Policy tags are type-only with the valued detail in a tooltip;
 * reorder by the up/down arrows; import / export a JSON of many groups. */
import { useEffect, useMemo, useState } from 'react'
import { DragSortTable } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { Button, Input } from 'antd'
import { Link } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { CappedTags } from '../components/CappedTags'
import { IconAction } from '../components/IconAction'
import { Icon } from '../components/Icon'
import { useGroups } from '../hooks/queries'
import { mockAction } from '../services/actions'
import type { GroupRow } from '../services/types'

export default function Groups() {
  const { data = [], isLoading } = useGroups()
  const [q, setQ] = useState('')
  const [rows, setRows] = useState<GroupRow[]>([])

  useEffect(() => {
    setRows([...data].sort((a, b) => a.priority - b.priority))
  }, [data])

  const filtered = useMemo(() => rows.filter((g) => g.name.toLowerCase().includes(q.toLowerCase())), [rows, q])

  const columns: ProColumns<GroupRow>[] = [
    {
      title: '#',
      dataIndex: 'priority',
      width: 72,
      render: (_, g) => <span className="oh-num" title="Drag to reorder - lower number wins on conflict">{g.priority}</span>,
    },
    {
      title: 'Group',
      dataIndex: 'name',
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
      render: (_, g) => (
        <Link to={`/groups/${g.name}`} className="oh-num" title="View members">
          {g.members}
        </Link>
      ),
    },
    {
      title: 'Policies',
      dataIndex: 'policies',
      render: (_, g) => <CappedTags items={g.policies.map((p) => ({ key: p.key, label: p.label, detail: p.detail }))} cap={4} />,
    },
    {
      title: 'Actions',
      align: 'right',
      width: 80,
      render: (_, g) => <IconAction icon="close" title="Delete group" danger onClick={() => mockAction(`Delete group ${g.name} - removes all members`)} />,
    },
  ]

  return (
    <>
      <PageHeader
        title="Groups"
        sub="Membership grants policy - priority decides who wins on conflict"
        actions={
          <>
            <Button onClick={() => mockAction('Import groups from JSON')}>Import</Button>
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
        onDragSortEnd={(_b, _a, newData) => { if (!q) setRows(newData); mockAction('Reordered groups by priority') }}
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
