/* Design system - the control vocabulary shown live, in both themes. Mock-only
 * reference (reached from the Home mock-switch), not part of the product. */
import { useState } from 'react'
import { Button, Card, Input, Select, Switch, Tag } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { StatusPill } from '../components/StatusPill'
import { ActivityMeter, ResourceBars, Spark } from '../components/meters'
import { ScopeFilterPills } from '../components/ScopeFilterPills'
import { CappedTags } from '../components/CappedTags'
import { Notice } from '../components/Notice'
import { IconAction } from '../components/IconAction'
import { Combo } from '../components/Combo'

const tagStyle = (bg: string, color: string) => ({ background: bg, color, borderRadius: 4 })

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: 16, alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
      <div className="oh-muted">{label}</div>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>{children}</div>
    </div>
  )
}

export default function DesignSystem() {
  const [scope, setScope] = useState('active')
  const [combo, setCombo] = useState<string[]>(['research', 'gpu'])

  return (
    <>
      <PageHeader title="Design system" sub="The control vocabulary - one language across every screen" />
      <div className="oh-note" style={{ marginBottom: 16 }}>
        <span><b>Note:</b> mock-only reference, not part of the design. Standard antd components carry the surface; the JupyterHub-specific metaphors (pills, meters, bars) are custom and themed by the same tokens.</span>
      </div>

      <Card title="Action buttons" style={{ marginBottom: 16 }}>
        <Row label="page (primary/secondary/danger/disabled)">
          <Button type="primary">Save</Button>
          <Button>Cancel</Button>
          <Button danger>Remove user</Button>
          <Button disabled>Save</Button>
        </Row>
        <Row label="list (small)">
          <Button type="primary" size="small">Authorize</Button>
          <Button size="small">Reset samples</Button>
          <Button danger size="small">Discard</Button>
        </Row>
        <Row label="list-icon">
          <IconAction icon="play" title="Enter" />
          <IconAction icon="restart" title="Restart" />
          <IconAction icon="stop" title="Stop" danger />
          <IconAction icon="close" title="Remove" danger />
        </Row>
      </Card>

      <Card title="Labels" style={{ marginBottom: 16 }}>
        <Row label="Status pills">
          <StatusPill status="active" label="active" />
          <StatusPill status="idle" label="idle" />
          <StatusPill status="spawning" label="spawning" />
          <StatusPill status="offline" label="offline" />
          <StatusPill status="error" label="error" />
        </Row>
        <Row label="Tags">
          <Tag bordered={false} style={tagStyle('var(--color-accent-soft)', 'var(--color-accent)')}>accent</Tag>
          <Tag bordered={false} style={tagStyle('var(--color-success-soft)', 'var(--color-success)')}>ok</Tag>
          <Tag bordered={false} style={tagStyle('var(--color-warning-soft)', 'var(--color-warning)')}>warn</Tag>
          <Tag bordered={false} style={tagStyle('var(--color-danger-soft)', 'var(--color-danger)')}>danger</Tag>
        </Row>
        <Row label="Capped chips">
          <CappedTags items={['research', 'data-science', 'gpu', 'nlp', 'vision-lab'].map((g) => ({ key: g, label: g }))} cap={3} />
        </Row>
      </Card>

      <Card title="Meters and bars" style={{ marginBottom: 16 }}>
        <Row label="Activity meter">
          <ActivityMeter value={96} />
          <ActivityMeter value={45} />
          <ActivityMeter value={12} />
        </Row>
        <Row label="Spark">
          <Spark style={{ width: 200 }} segments={[{ width: 30, color: 'var(--color-success)' }, { width: 15, color: 'var(--color-warning)' }, { width: 55, color: 'var(--color-border)' }]} />
        </Row>
        <Row label="Resource bars">
          <div style={{ width: 280 }}>
            <ResourceBars rows={[{ label: 'CPU', value: 41 }, { label: 'Memory', value: 63 }, { label: 'GPU', value: 33 }]} />
          </div>
        </Row>
      </Card>

      <Card title="List filters and notices" style={{ marginBottom: 16 }}>
        <Row label="Scope pills">
          <ScopeFilterPills
            value={scope}
            onChange={setScope}
            scopes={[
              { key: 'active', label: 'Active', count: 18, tone: 'ok' },
              { key: 'idle', label: 'Idle', count: 4, tone: 'warn' },
              { key: 'offline', label: 'Offline', count: 109, tone: 'grey' },
              { key: 'all', label: 'All', count: 131, tone: 'accent' },
            ]}
          />
        </Row>
        <Row label="Notices">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: 420 }}>
            <Notice type="success">Image pulled and verified - ready to spawn</Notice>
            <Notice type="warning">Sharing is not running - link works on this network only</Notice>
            <Notice type="info">Sampling resumes when the server becomes active</Notice>
            <Notice type="error">Could not reach the server - try again</Notice>
          </div>
        </Row>
      </Card>

      <Card title="Inputs">
        <Row label="Text input"><Input style={{ width: 280 }} defaultValue="editable" /></Row>
        <Row label="Disabled input"><Input className="oh-mono" style={{ width: 280 }} defaultValue="locked value" disabled /></Row>
        <Row label="Select"><Select style={{ width: 280 }} defaultValue="single" options={[{ value: 'single', label: 'single' }, { value: 'pair', label: 'pair' }]} /></Row>
        <Row label="Switch"><Switch defaultChecked /> <Switch /></Row>
        <Row label="Combo (typeahead)"><div style={{ width: 360 }}><Combo corpus={['research', 'data-science', 'gpu', 'nlp', 'vision-lab', 'staff']} value={combo} onChange={setCombo} /></div></Row>
      </Card>
    </>
  )
}
