/* Lab Container - read-only deployment facts: the image every lab spawns from
 * and the standard per-user volumes mounted into every lab. The image and the
 * volume layout are deployment config (not runtime-editable here); shared and
 * extra volumes are granted per group on the Groups page. */
import { Card, Table, Tooltip } from 'antd'
import { Link } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Notice } from '../components/Notice'
import { useLabContainer } from '../hooks/queries'
import type { LabMount } from '../services/types'

export default function LabContainer() {
  const { data } = useLabContainer()
  const volumes = data?.volumes ?? []
  const systemVolumes = data?.systemVolumes ?? []

  return (
    <>
      <PageHeader title="Lab Setup" sub="The image every lab spawns from, and the volumes mounted into every lab" />
      <Card style={{ marginBottom: 16, maxWidth: 760 }}>
        <div style={{ marginBottom: 8, color: 'var(--color-text-muted)', fontSize: 13 }}>Lab image</div>
        <Tooltip title="Deployment-set; new images apply on the next spawn">
          <span className="doh-mono" style={{ fontSize: 14, cursor: 'help' }}>{data?.image ?? '-'}</span>
        </Tooltip>
      </Card>

      <Card styles={{ body: { padding: 0 } }} style={{ marginBottom: 16 }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)', fontWeight: 600 }}>Standard Volumes</div>
        <Table<LabMount>
          rowKey="name"
          pagination={false}
          locale={{ emptyText: 'No standard volumes configured' }}
          dataSource={volumes}
          rowClassName={(_, i) => (i % 2 ? 'doh-row-alt' : '')}
          columns={[
            { title: 'Name', dataIndex: 'name', render: (v) => <span className="doh-mono">{v}</span> },
            { title: 'Mount Point', dataIndex: 'mount', render: (v) => <span className="doh-mono">{v}</span> },
            { title: 'Description', dataIndex: 'description', render: (v) => <span className="doh-muted">{v}</span> },
          ]}
        />
      </Card>

      {systemVolumes.length > 0 && (
        <Card styles={{ body: { padding: 0 } }} style={{ marginBottom: 16 }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)', fontWeight: 600 }}>System Volumes</div>
          <Table<LabMount>
            rowKey="name"
            pagination={false}
            dataSource={systemVolumes}
            rowClassName={(_, i) => (i % 2 ? 'doh-row-alt' : '')}
            columns={[
              { title: 'Name', dataIndex: 'name', render: (v) => <span className="doh-mono">{v}</span> },
              { title: 'Mount Point', dataIndex: 'mount', render: (v) => <span className="doh-mono">{v}</span> },
              { title: 'Description', dataIndex: 'description', render: (v) => <span className="doh-muted">{v}</span> },
            ]}
          />
        </Card>
      )}

      <div style={{ maxWidth: 760 }}>
        <Notice type="info">System volumes are granted by group policy - the shared volume via a shared-volume grant, the docker-proxy socket via a docker-access grant. Grant shared and extra volumes per group in a <Link to="/groups">group</Link>'s Volume mounts section.</Notice>
      </div>
    </>
  )
}
