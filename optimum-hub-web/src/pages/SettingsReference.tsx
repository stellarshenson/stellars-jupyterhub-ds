/* Settings reference - every platform env var with its value and description,
 * grouped by category. Sourced from the settings dictionary; searchable. */
import { useMemo, useState } from 'react'
import { Card, Input, Table } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { Icon } from '../components/Icon'
import { useSettingsReference } from '../hooks/queries'
import type { SettingsRefRow } from '../services/types'

export default function SettingsReference() {
  const { data = [] } = useSettingsReference()
  const [q, setQ] = useState('')

  const filtered = useMemo(() => {
    const ql = q.toLowerCase()
    return data
      .map((cat) => ({ ...cat, rows: cat.rows.filter((r) => r.name.toLowerCase().includes(ql) || r.description.toLowerCase().includes(ql)) }))
      .filter((cat) => cat.rows.length > 0)
  }, [data, q])

  const columns = [
    { title: 'Variable', dataIndex: 'name', render: (v: string) => <span className="oh-mono">{v}</span>, width: 360 },
    { title: 'Value', dataIndex: 'value', render: (v: string) => <span className="oh-mono">{v}</span>, width: 280 },
    { title: 'Description', dataIndex: 'description', render: (v: string) => <span className="oh-muted">{v}</span> },
  ]

  return (
    <>
      <PageHeader
        title="Settings reference"
        sub="Every platform environment variable, its value and description"
        actions={<Input allowClear prefix={<Icon name="search" size={14} />} placeholder="Filter variables…" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 240 }} />}
      />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {filtered.map((cat) => (
          <Card key={cat.category} title={cat.category} styles={{ body: { padding: 0 } }}>
            <Table<SettingsRefRow> rowKey="name" pagination={false} dataSource={cat.rows} columns={columns} />
          </Card>
        ))}
      </div>
    </>
  )
}
