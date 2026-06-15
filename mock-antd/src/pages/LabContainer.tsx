/* Lab Container - the spawned image and the custom shared mounts. The three
 * standard volumes (home / workspace / cache) are always present and
 * platform-managed; this table lists only custom mounts. */
import { useState } from 'react'
import { Button, Card, Input, Space, Table } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { IconAction } from '../components/IconAction'
import { Icon } from '../components/Icon'
import { Notice } from '../components/Notice'
import { useLabVolumes } from '../hooks/queries'
import { mockAction } from '../services/actions'
import { PLATFORM } from '../services/config'
import type { Volume } from '../services/types'

export default function LabContainer() {
  const { data: volumes = [] } = useLabVolumes()
  const [image, setImage] = useState(PLATFORM.labImage)
  const [pulled, setPulled] = useState(false)

  return (
    <>
      <PageHeader title="Lab Container" sub="The image every lab spawns from, and the custom shared mounts" />
      <Card style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 8, color: 'var(--color-text-muted)', fontSize: 13 }}>Lab image</div>
        <Space.Compact style={{ width: '100%', maxWidth: 640 }}>
          <Input className="oh-mono" value={image} onChange={(e) => setImage(e.target.value)} />
          <Button type="primary" icon={<Icon name="download" size={14} />} onClick={() => { setPulled(true); mockAction('Pulling and verifying image') }}>
            Set
          </Button>
        </Space.Compact>
        {pulled && <div style={{ marginTop: 12, maxWidth: 640 }}><Notice type="success">Image pulled and verified - ready to spawn.</Notice></div>}
      </Card>

      <Card styles={{ body: { padding: 0 } }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)', display: 'flex', alignItems: 'center' }}>
          <span style={{ fontWeight: 600 }}>Custom mounts</span>
          <Button size="small" style={{ marginLeft: 'auto' }} icon={<Icon name="plus" size={14} />} onClick={() => mockAction('Add a custom mount')}>Add mount</Button>
        </div>
        <Table<Volume>
          rowKey="suffix"
          pagination={false}
          dataSource={volumes}
          columns={[
            { title: 'Name', dataIndex: 'name', render: (v) => <span className="oh-mono">{v}</span> },
            { title: 'Mount point', dataIndex: 'mount', render: (v) => <span className="oh-mono">{v}</span> },
            { title: 'Description', dataIndex: 'description', render: (v) => <span className="oh-muted">{v}</span> },
            { title: '', align: 'right', width: 60, render: (_, v) => <IconAction icon="close" title="Remove mount" danger onClick={() => mockAction(`Remove mount ${v.name}`)} /> },
          ]}
        />
        <div style={{ padding: 16 }}>
          <div className="oh-note">
            <span><b>Note:</b> the standard volumes <span className="oh-mono">home</span>, <span className="oh-mono">workspace</span> and <span className="oh-mono">cache</span> are always present and platform-managed - only custom shared mounts are listed here.</span>
          </div>
        </div>
      </Card>
    </>
  )
}
