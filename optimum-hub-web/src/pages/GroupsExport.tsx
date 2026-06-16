/* Export groups - check / uncheck a subset and download it as one JSON bundle. */
import { useState } from 'react'
import { Button, Card, Table } from 'antd'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Icon } from '../components/Icon'
import { CappedTags } from '../components/CappedTags'
import { useGroups } from '../hooks/queries'
import { mockAction } from '../services/actions'
import type { GroupRow } from '../services/types'

export default function GroupsExport() {
  const navigate = useNavigate()
  const { data = [] } = useGroups()
  const [selected, setSelected] = useState<React.Key[]>(data.map((g) => g.name))

  return (
    <>
      <PageHeader title="Export groups" sub="Pick the groups to include and download them as one JSON bundle" />
      <Card style={{ maxWidth: 880 }}>
        <Table<GroupRow>
          rowKey="name"
          pagination={false}
          rowSelection={{ selectedRowKeys: selected, onChange: setSelected }}
          dataSource={[...data].sort((a, b) => a.priority - b.priority)}
          columns={[
            { title: 'Group', dataIndex: 'name' },
            { title: 'Description', dataIndex: 'description', render: (v) => <span className="oh-muted">{v}</span> },
            { title: 'Policies', dataIndex: 'policies', render: (_, g) => <CappedTags items={g.policies.map((p) => ({ key: p.key, label: p.label, detail: p.detail }))} cap={4} /> },
          ]}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <Button type="primary" icon={<Icon name="download" size={14} />} onClick={() => mockAction(`Exported ${selected.length} groups as JSON`)}>
            Export {selected.length} groups
          </Button>
          <Button onClick={() => navigate('/groups')}>Cancel</Button>
        </div>
      </Card>
    </>
  )
}
