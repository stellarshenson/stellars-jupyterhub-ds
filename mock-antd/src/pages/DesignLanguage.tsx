/* Design language - the full widget gallery, every pill, button, control and
 * token on one page so a theme designer can check the system speaks one language
 * in both light and dark. Unlisted: reachable only by URL (/design-language),
 * not in the nav or the mock switch. */
import { useState } from 'react'
import {
  Alert, Badge, Button, Card, Checkbox, DatePicker, Dropdown, Input, InputNumber,
  Pagination, Progress, Radio, Segmented, Select, Switch, Tabs, Tag, Tooltip,
} from 'antd'
import { GlobalOutlined } from '@ant-design/icons'
import { PageHeader } from '../components/PageHeader'
import { StatusPill } from '../components/StatusPill'
import { ActivityMeter, GpuMeter, ResourceBars, Spark, TtlGadget } from '../components/meters'
import { ScopeFilterPills } from '../components/ScopeFilterPills'
import { CappedTags } from '../components/CappedTags'
import { Notice } from '../components/Notice'
import { IconAction } from '../components/IconAction'
import { Combo } from '../components/Combo'
import { Icon } from '../components/Icon'
import type { IconKey } from '../components/Icon'

const tagStyle = (bg: string, color: string) => ({ background: bg, color, borderRadius: 4 })

const COLORS: Array<{ group: string; vars: Array<[string, string]> }> = [
  { group: 'Accent', vars: [['--color-accent', 'accent'], ['--color-accent-soft', 'accent-soft'], ['--color-accent-ring', 'accent-ring'], ['--color-accent-2', 'accent-2'], ['--color-accent-2-soft', 'accent-2-soft']] },
  { group: 'State', vars: [['--color-success', 'success'], ['--color-success-soft', 'success-soft'], ['--color-warning', 'warning'], ['--color-warning-soft', 'warning-soft'], ['--color-danger', 'danger'], ['--color-danger-soft', 'danger-soft'], ['--color-info', 'info'], ['--color-info-soft', 'info-soft']] },
  { group: 'Surface', vars: [['--color-bg', 'bg'], ['--color-bg-subtle', 'bg-subtle'], ['--color-surface', 'surface'], ['--color-surface-hover', 'surface-hover'], ['--color-surface-active', 'surface-active'], ['--color-surface-raised', 'surface-raised']] },
  { group: 'Border + text', vars: [['--color-border-subtle', 'border-subtle'], ['--color-border', 'border'], ['--color-border-strong', 'border-strong'], ['--color-text', 'text'], ['--color-text-muted', 'text-muted'], ['--color-text-subtle', 'text-subtle']] },
]

const ICONS: IconKey[] = [
  'grid', 'server', 'users', 'group', 'shield', 'activity', 'settings', 'search', 'sun', 'moon',
  'monitor', 'clock', 'plus', 'bell', 'play', 'restart', 'stop', 'megaphone', 'logout', 'dots',
  'key', 'user', 'cpu', 'check', 'arrowup', 'arrowdown', 'chevron', 'close', 'grip', 'disk',
  'gpu', 'memory', 'download', 'upload', 'box', 'code',
]

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: 16, alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
      <div className="oh-muted">{label}</div>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>{children}</div>
    </div>
  )
}

function Swatch({ token, name }: { token: string; name: string }) {
  return (
    <div style={{ width: 116 }}>
      <div style={{ height: 44, borderRadius: 8, background: `var(${token})`, border: '1px solid var(--color-border-subtle)' }} />
      <div style={{ fontSize: 11, marginTop: 4, color: 'var(--color-text-muted)' }}>{name}</div>
    </div>
  )
}

export default function DesignLanguage() {
  const [scope, setScope] = useState('active')
  const [combo, setCombo] = useState<string[]>(['research', 'gpu'])
  const [seg, setSeg] = useState('day')
  const [radio, setRadio] = useState('raw')

  return (
    <>
      <PageHeader title="Design language" sub="Every token, pill, control and widget on one page - check the system in both themes" />
      <div className="oh-note" style={{ marginBottom: 16 }}>
        <span><b>Unlisted:</b> reachable only by URL, not part of the product. Standard antd components carry the surface; the JupyterHub metaphors (pills, meters, bars) are custom and themed by the same tokens.</span>
      </div>

      <Card title="Colour tokens" style={{ marginBottom: 16 }}>
        {COLORS.map((c) => (
          <Row key={c.group} label={c.group}>
            {c.vars.map(([token, name]) => <Swatch key={token} token={token} name={name} />)}
          </Row>
        ))}
      </Card>

      <Card title="Action buttons" style={{ marginBottom: 16 }}>
        <Row label="page (primary/secondary/danger/disabled)">
          <Button type="primary">Save</Button>
          <Button>Cancel</Button>
          <Button danger>Remove user</Button>
          <Button disabled>Save</Button>
        </Row>
        <Row label="primary with icon">
          <Button type="primary" icon={<Icon name="play" size={15} filled />}>Open lab</Button>
          <Button icon={<Icon name="restart" size={16} />}>Restart</Button>
          <Button danger icon={<Icon name="stop" size={14} filled />}>Stop</Button>
        </Row>
        <Row label="list (small)">
          <Button type="primary" size="small">Authorize</Button>
          <Button size="small">Reset samples</Button>
          <Button danger size="small">Discard</Button>
        </Row>
        <Row label="list-icon (incl. filled stop)">
          <IconAction icon="play" title="Enter" />
          <IconAction icon="restart" title="Restart" />
          <IconAction icon="stop" title="Stop" danger filled />
          <IconAction icon="close" title="Remove" danger />
        </Row>
        <Row label="text / link">
          <Button type="text" icon={<GlobalOutlined />} />
          <Button type="link">View all</Button>
        </Row>
      </Card>

      <Card title="Pills, tags and chips" style={{ marginBottom: 16 }}>
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
        <Row label="Capped chips (+N)">
          <CappedTags items={['research', 'data-science', 'gpu', 'nlp', 'vision-lab', 'ml-platform'].map((g) => ({ key: g, label: g }))} cap={3} />
        </Row>
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
      </Card>

      <Card title="Meters, bars and widgets" style={{ marginBottom: 16 }}>
        <Row label="Activity meter (high/mid/low)">
          <ActivityMeter value={96} />
          <ActivityMeter value={45} />
          <ActivityMeter value={12} />
        </Row>
        <Row label="Spark (stacked)">
          <Spark style={{ width: 220 }} segments={[{ width: 30, color: 'var(--color-success)' }, { width: 15, color: 'var(--color-warning)' }, { width: 55, color: 'var(--color-border)' }]} />
        </Row>
        <Row label="Resource bars + GPU meter">
          <div style={{ width: 320 }}>
            <ResourceBars rows={[{ label: 'CPU', value: 41 }, { label: 'Memory', value: 63 }, { label: 'GPU', value: 33, gpus: [62, 41, 18, 9] }]} />
          </div>
        </Row>
        <Row label="GPU meter (1 / 2 / 4 devices)">
          <div style={{ width: 120 }}><GpuMeter gpus={[78]} /></div>
          <div style={{ width: 160 }}><GpuMeter gpus={[82, 40]} /></div>
          <div style={{ width: 220 }}><GpuMeter gpus={[62, 41, 18, 9]} /></div>
        </Row>
        <Row label="TTL gadget (ok / warn / low)">
          <div style={{ width: 340 }}><TtlGadget timeLeftMin={180} maxMin={480} /></div>
          <div style={{ width: 340 }}><TtlGadget timeLeftMin={45} maxMin={480} /></div>
          <div style={{ width: 340 }}><TtlGadget timeLeftMin={12} maxMin={480} /></div>
        </Row>
      </Card>

      <Card title="Effective policy and feed" style={{ marginBottom: 16 }}>
        <Row label="Grant rows">
          <div style={{ width: 420 }}>
            <div className="oh-grant"><span className="oh-g-ic"><Icon name="gpu" size={16} /></span><div>GPU<div className="oh-g-from">from gpu</div></div><span className="oh-g-val">all devices</span></div>
            <div className="oh-grant"><span className="oh-g-ic"><Icon name="memory" size={16} /></span><div>Memory<div className="oh-g-from">from gpu</div></div><span className="oh-g-val">32 GB</span></div>
          </div>
        </Row>
        <Row label="Feed item">
          <div className="oh-feed" style={{ width: 420 }}>
            <div className="oh-feed-item">
              <div className="oh-feed-ic"><Icon name="play" size={15} /></div>
              <div className="oh-feed-body"><div className="t"><b>milan</b> started a server with <b>gpu</b></div><div className="when">2m ago</div></div>
            </div>
          </div>
        </Row>
      </Card>

      <Card title="Notices (custom) and alerts (antd)" style={{ marginBottom: 16 }}>
        <Row label="Notices">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: 460 }}>
            <Notice type="success">Image pulled and verified - ready to spawn</Notice>
            <Notice type="warning">Sharing is not running - link works on this network only</Notice>
            <Notice type="info">Sampling resumes when the server becomes active</Notice>
            <Notice type="error">Could not reach the server - try again</Notice>
          </div>
        </Row>
        <Row label="antd Alert">
          <Alert style={{ width: 460 }} type="info" showIcon message="Read-only mock - actions are simulated" />
        </Row>
      </Card>

      <Card title="Form controls" style={{ marginBottom: 16 }}>
        <Row label="Text / disabled"><Input style={{ width: 240 }} defaultValue="editable" /><Input className="oh-mono" style={{ width: 240 }} defaultValue="locked value" disabled /></Row>
        <Row label="Password / number"><Input.Password style={{ width: 240 }} placeholder="password" /><InputNumber defaultValue={8} /></Row>
        <Row label="Select / date"><Select style={{ width: 200 }} defaultValue="single" options={[{ value: 'single', label: 'single' }, { value: 'pair', label: 'pair' }]} /><DatePicker /></Row>
        <Row label="Radio (button) / segmented">
          <Radio.Group value={radio} optionType="button" buttonStyle="solid" onChange={(e) => setRadio(e.target.value)} options={[{ label: 'Raw', value: 'raw' }, { label: 'Limited', value: 'limited' }]} />
          <Segmented value={seg} onChange={(v) => setSeg(v as string)} options={[{ label: 'Day', value: 'day' }, { label: 'Week', value: 'week' }, { label: 'Month', value: 'month' }]} />
        </Row>
        <Row label="Switch / checkbox"><Switch defaultChecked /><Switch /><Checkbox defaultChecked>Authorise now</Checkbox></Row>
        <Row label="Combo (typeahead)"><div style={{ width: 360 }}><Combo corpus={['research', 'data-science', 'gpu', 'nlp', 'vision-lab', 'staff']} value={combo} onChange={setCombo} /></div></Row>
      </Card>

      <Card title="Navigation and feedback (antd)" style={{ marginBottom: 16 }}>
        <Row label="Dropdown / tooltip">
          <Dropdown menu={{ items: [{ key: 'en', label: 'English' }, { key: 'pl', label: 'Polski' }] }} trigger={['click']}>
            <Button icon={<GlobalOutlined />}>Language</Button>
          </Dropdown>
          <Tooltip title="Tooltip carries the precise value"><Button>Hover me</Button></Tooltip>
        </Row>
        <Row label="Tabs"><div style={{ width: 360 }}><Tabs items={[{ key: 'a', label: 'General' }, { key: 'b', label: 'Policy' }, { key: 'c', label: 'Members' }]} /></div></Row>
        <Row label="Badge / progress">
          <Badge count={5} /><Badge dot><Icon name="bell" size={18} /></Badge>
          <Progress percent={63} style={{ width: 180 }} /><Progress type="circle" percent={41} size={44} />
        </Row>
        <Row label="Pagination"><Pagination simple defaultCurrent={1} total={240} pageSize={10} /></Row>
      </Card>

      <Card title="Conventions" style={{ marginBottom: 16 }}>
        <Row label="Relative time (always short)">
          <span className="oh-muted">now</span>
          <span className="oh-muted">2m</span>
          <span className="oh-muted">5h</span>
          <span className="oh-muted">3d</span>
          <span className="oh-muted">4mo</span>
          <span className="oh-muted">1y</span>
          <span className="oh-page-sub">- one format everywhere; exact timestamp on hover</span>
        </Row>
        <Row label="Alternating rows">
          <span className="oh-page-sub">every table uses zebra striping - mandatory</span>
        </Row>
        <Row label="Panel padding">
          <span className="oh-page-sub">cards use the standard antd body padding; content never sits flush to the edge</span>
        </Row>
        <Row label="State = colour">
          <span className="oh-page-sub">status and type always shown as coloured pills on one shared palette</span>
        </Row>
      </Card>

      <Card title="Icon set">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(96px, 1fr))', gap: 8 }}>
          {ICONS.map((name) => (
            <div key={name} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, padding: '12px 4px', border: '1px solid var(--color-border-subtle)', borderRadius: 8 }}>
              <Icon name={name} size={20} />
              <span style={{ fontSize: 11, color: 'var(--color-text-subtle)' }}>{name}</span>
            </div>
          ))}
        </div>
      </Card>
    </>
  )
}
