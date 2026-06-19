/* Export groups - check / uncheck a subset and download it as one JSON bundle. */
import { useEffect, useState } from 'react'
import { Button, Card, Table } from 'antd'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Icon } from '../components/Icon'
import { CappedTags } from '../components/CappedTags'
import { useGroups } from '../hooks/queries'
import { notify } from '../services/actions'
import { downloadJson } from '../lib/download'
import { toPolicies } from '../lib/policyShape'
import type { GroupRow } from '../services/types'

export default function GroupsExport() {
  const navigate = useNavigate()
  const { data = [] } = useGroups()
  const [selected, setSelected] = useState<React.Key[]>([])
  // seed all-selected once the groups load (the initializer runs before data arrives)
  useEffect(() => {
    setSelected((prev) => (prev.length ? prev : data.map((g) => g.name)))
  }, [data])

  // real client-side download: each selected group as {name, description, priority,
  // policies[]} - the flat config folded into named policy sections (group ->
  // policy[] -> members), exactly the shape the Import action reads back.
  const exportSelected = () => {
    const chosen = new Set(selected)
    const groups = data
      .filter((g) => chosen.has(g.name))
      .map((g) => ({ name: g.name, description: g.description ?? '', priority: g.priority, policies: toPolicies(g.config ?? {}) }))
    downloadJson('group-policies.json', { groups })
    notify.success(`Exported ${groups.length} group${groups.length === 1 ? '' : 's'} as JSON`)
  }

  return (
    <>
      <PageHeader title="Export Groups" sub="Pick the groups to include and download them as one JSON bundle" />
      <Card style={{ maxWidth: 880 }}>
        <Table<GroupRow>
          rowKey="name"
          pagination={false}
          rowClassName={(_, i) => (i % 2 ? 'doh-row-alt' : '')}
          rowSelection={{ selectedRowKeys: selected, onChange: setSelected }}
          dataSource={[...data].sort((a, b) => b.priority - a.priority)}
          columns={[
            { title: 'Group', dataIndex: 'name' },
            { title: 'Description', dataIndex: 'description', render: (v) => <span className="doh-muted">{v}</span> },
            { title: 'Policies', dataIndex: 'policies', render: (_, g) => <CappedTags items={g.policies.map((p) => ({ key: p.key, label: p.label, detail: p.detail }))} cap={4} /> },
          ]}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <Button type="primary" icon={<Icon name="download" size={14} />} disabled={!selected.length} onClick={exportSelected}>
            Export {selected.length} groups
          </Button>
          <Button onClick={() => navigate('/groups')}>Cancel</Button>
        </div>
      </Card>
    </>
  )
}
