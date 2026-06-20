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
import { NotificationPill } from '../components/NotificationPill'
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
      <div className="doh-muted">{label}</div>
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
      <div className="doh-note" style={{ marginBottom: 16 }}>
        <span><b>Unlisted:</b> reachable only by URL, not part of the product. Standard antd components carry the surface; the JupyterHub metaphors (pills, meters, bars) are custom and themed by the same tokens.</span>
      </div>

      <Card title="Colour tokens" style={{ marginBottom: 16 }}>
        {COLORS.map((c) => (
          <Row key={c.group} label={c.group}>
            {c.vars.map(([token, name]) => <Swatch key={token} token={token} name={name} />)}
          </Row>
        ))}
      </Card>

      <Card title="Normal text" style={{ marginBottom: 16 }}>
        <Row label="text colours (reuse the palette vars)">
          <span className="doh-text-neutral">neutral</span>
          <span className="doh-text-link">link</span>
          <span className="doh-text-success">success</span>
          <span className="doh-text-warning">warning</span>
          <span className="doh-text-danger">dangerous</span>
        </Row>
        <div className="doh-note" style={{ marginTop: 4 }}>
          <b>Normal text:</b> neutral (body), link (accent - e.g. a user-profile link), success (green), warning (orange), dangerous (red). One class each (<code>doh-text-*</code>), all from the defined colour vars.
        </div>
      </Card>

      <Card title="Palette (named, dim / normal / bright)" style={{ marginBottom: 16 }}>
        {[
          { v: 'green', label: 'green' },
          { v: 'cyan', label: 'cyan (blue)' },
          { v: 'red', label: 'red' },
          { v: 'orange', label: 'orange' },
          { v: 'gray', label: 'gray' },
        ].map((c) => (
          <Row key={c.v} label={c.label}>
            <Swatch token={`--doh-${c.v}-dim`} name="dim" />
            <Swatch token={`--doh-${c.v}`} name="normal" />
            <Swatch token={`--doh-${c.v}-bright`} name="bright" />
          </Row>
        ))}
        <div className="doh-note" style={{ marginTop: 4 }}>
          <b>Palette:</b> borrowed from the defined tokens (green = success, cyan/blue = accent, red = danger, orange = warning, gray = text-subtle), each <code>--doh-&lt;name&gt;</code> with <code>-dim</code> (toward surface) and <code>-bright</code> (toward text) variants - refer to them by name. Magenta is not in the current tokens.
        </div>
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
        <Row label="action icons - non-list (filled if a fill exists)">
          <IconAction icon="play" title="primary - blue (active / go-to)" tone="primary" filled />
          <IconAction icon="disk" title="secondary - gray (neutral)" tone="secondary" filled />
          <IconAction icon="stop" title="dangerous - red (destructive)" tone="danger" filled />
          <IconAction icon="activity" title="warning - yellow (caution)" tone="warning" />
        </Row>
        <Row label="primary icon sizes (small / medium / large - the sizes the UI uses)">
          {[{ z: 'small', px: 14 }, { z: 'medium', px: 16 }, { z: 'large', px: 18 }].map((s) => (
            <div key={s.z} style={{ textAlign: 'center' }}>
              <Icon name="play" size={s.px} filled style={{ color: 'var(--color-accent)' }} />
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{s.z} {s.px}px</div>
            </div>
          ))}
        </Row>
        <Row label="list icons - wireframe (filled on demand)">
          <IconAction icon="play" title="list-primary - blue" tone="primary" />
          <IconAction icon="restart" title="list-secondary - gray" tone="secondary" />
          <IconAction icon="stop" title="list-dangerous - red" tone="danger" />
          <IconAction icon="activity" title="list-warning - yellow" tone="warning" />
        </Row>
        <div className="doh-note" style={{ marginTop: 4 }}>
          <b>Icons:</b> wireframe by default, filled on demand. Tones - primary (blue, active / go-to), secondary (gray, neutral), dangerous (red, destructive), warning (yellow, caution). List icons stay wireframe and fill only for emphasis (e.g. stop); non-list / button icons use the filled glyph when one is available.
        </div>
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
        <Row label="Notification pills">
          <NotificationPill type="success" label="success" />
          <NotificationPill type="warning" label="warning" />
          <NotificationPill type="info" label="info" />
          <NotificationPill type="default" label="passive" />
          <NotificationPill type="error" label="dangerous" />
          <NotificationPill type="in-progress" label="in-progress" />
        </Row>
        <div className="doh-note" style={{ marginTop: 4 }}>
          <b>Notification tones</b> reuse the status-pill vocabulary so every advisory reads in the same colours: success = Active green, warning = idle amber, info = the "All" scope cyan, passive = neutral gray, dangerous = red, in-progress = pulsing cyan. Broadcast types and the "Update available" badge both draw from this one map (<code>NotificationPill</code>), never an ad-hoc Tag colour.
        </div>
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
        <Row label="Scope states">
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span className="doh-pill doh-scope accent active"><span className="doh-dot" />All 131</span>
            <span className="doh-page-sub">active - lit with accent ring</span>
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span className="doh-pill doh-scope running"><span className="doh-dot" />Active 18</span>
            <span className="doh-page-sub">inactive - dimmed to .6</span>
          </span>
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
        <Row label="TTL gadget - behaviour matrix (full / ample / warn / danger / banked-draining / at-ceiling)">
          <div style={{ width: 320 }}><TtlGadget timeLeftMin={240} baseMin={240} maxAddHours={12} /></div>
          <div style={{ width: 320 }}><TtlGadget timeLeftMin={180} baseMin={240} maxAddHours={12} /></div>
          <div style={{ width: 320 }}><TtlGadget timeLeftMin={45} baseMin={240} maxAddHours={12} /></div>
          <div style={{ width: 320 }}><TtlGadget timeLeftMin={6} baseMin={240} maxAddHours={12} /></div>
          <div style={{ width: 320 }}><TtlGadget timeLeftMin={300} baseMin={240} maxAddHours={6} displayCeilingMin={360} /></div>
          <div style={{ width: 320 }}><TtlGadget timeLeftMin={360} baseMin={240} maxAddHours={0} displayCeilingMin={360} /></div>
        </Row>
        <Row label="TTL glow/blur calibration (static steps - tune colours + amounts)">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18, width: '100%' }}>
            {/* counter BLUR steps - the counter ships blur-only (no glow); shipped default .75px at the peak */}
            <div style={{ display: 'flex', gap: 28, alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <span style={{ width: 92, fontSize: 12, color: 'var(--color-text-muted)' }}>counter blur</span>
              {[0.1, 0.25, 0.5, 0.75, 1].map((px) => (
                <div key={px} style={{ textAlign: 'center' }}>
                  <span className="doh-ttl-val" style={{ minWidth: 'auto', color: 'var(--doh-ttl-blue)', filter: px ? `blur(${px}px)` : 'none' }}>
                    <Icon name="clock" size={14} /><b style={{ color: 'var(--doh-ttl-blue)' }}>9h 58m</b>
                  </span>
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{px}px</div>
                </div>
              ))}
            </div>
            {/* bar GLOW steps - a brightened tint (currentColor mixed toward white) over the fill, by opacity (target 50%) */}
            <div style={{ display: 'flex', gap: 28, alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <span style={{ width: 92, fontSize: 12, color: 'var(--color-text-muted)' }}>bar glow</span>
              {[0, 0.25, 0.5, 0.75, 1].map((op) => (
                <div key={op} style={{ textAlign: 'center' }}>
                  <span className="doh-ttl-bar" style={{ display: 'inline-block', width: 150, position: 'relative', color: 'var(--doh-ttl-blue)' }}>
                    <Progress percent={80} status="normal" showInfo={false} strokeColor="var(--doh-ttl-blue)" trailColor="var(--color-bg-subtle)" style={{ margin: 0 }} />
                    {op > 0 && <span style={{ position: 'absolute', inset: 0, background: 'color-mix(in srgb, currentColor, white 60%)', opacity: op, borderRadius: 'var(--radius-full)', zIndex: 2, pointerEvents: 'none' }} />}
                  </span>
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{Math.round(op * 100)}%</div>
                </div>
              ))}
            </div>
          </div>
        </Row>
        <div className="doh-note" style={{ marginTop: 4 }}>
          <b>Colour thresholds (fixed rule):</b> resource / usage bars (high = bad) - normal accent below 70%, full warning (amber) at &gt;= 70%, full danger (red) at &gt;= 90%. TTL bar (reverse, low time = the end) - blue above 30% of base left, full warning at &lt;= 30%, dim red at &lt;= 10% (a low timer is the normal end state, not an alarm). Warning is ALWAYS the normal warning colour - never dimmed by blending with the accent; only the warn-&gt;danger span blends (warm hues, stays saturated).
          <br /><b>Progress bars:</b> the standard bar (antd Progress) is base-relative; the resource bars are the same family. The <b>alternative striped bars</b> (one per GPU) are for multi-device load - a labelled bar per device rather than a single aggregate. The TTL extend is an hours slider whose last tick "max" tops the session to the ceiling.
          <br /><b>Tooltips, not static text:</b> precise values (exact GB, %, dates, breakdowns) live in a tooltip on hover, never as wasteful static text under the control - the control shows the glanceable shape, the tooltip the precise number.
        </div>
      </Card>

      <Card title="Servers list & resource cues" style={{ marginBottom: 16 }}>
        <Row label="Resource tooltips - the live % beside the assigned ceiling (hover)">
          <div style={{ width: 320 }}>
            <ResourceBars rows={[
              { label: 'CPU', value: 47, tip: '47% used\n32 cores assigned' },
              { label: 'Memory', value: 62, tip: '62% used\n5.0 of 8 GB assigned\n8% of 64 GB host' },
            ]} />
          </div>
        </Row>
        <Row label="Usage bar colour ramp - calm to 50%, then accent -> warning -> danger">
          <div style={{ width: 320 }}>
            <ResourceBars rows={[{ label: '30%', value: 30 }, { label: '60%', value: 60 }, { label: '90%', value: 90 }]} />
          </div>
        </Row>
        <Row label="Activity meter - tooltip shows the real %, may exceed 100% (hover)">
          <ActivityMeter value={96} pct={130} hours={10.4} />
          <ActivityMeter value={60} pct={72} hours={5.8} />
          <ActivityMeter value={12} pct={12} hours={1} />
        </Row>
        <Row label="User cell - name links to the user, first/last beneath (no click-friction)">
          <div className="doh-user-cell">
            <span><span style={{ color: 'var(--color-accent)', cursor: 'pointer' }}>alice</span></span>
            <span className="doh-name-hint">Alice Nowak</span>
          </div>
        </Row>
        <Row label="List columns - status, last-activity and activity are separate; activity centered">
          <StatusPill status="active" label="Active" />
          <span className="doh-muted">2m ago</span>
          <div style={{ width: 90, textAlign: 'center' }}><ActivityMeter value={96} pct={120} hours={9.6} /></div>
        </Row>
        <div className="doh-note" style={{ marginTop: 4 }}>
          <b>Lists keep status, last-activity and activity in separate columns</b> - the single-server widget may club status + last-activity, but a list never does; the activity meter is centered, status/last-activity columns sized to content.
          <br /><b>Admin lifecycle is inline:</b> starting / restarting another user's server spins the control in place (like Stop) and refreshes on completion - it never navigates to a progress screen.
          <br /><b>Resource %:</b> CPU / memory measure against what is ASSIGNED to the user (their cgroup limit) when set, else the host; the tooltip names which, and activity may read above 100% (works more than the daily target).
        </div>
      </Card>

      <Card title="Effective policy and feed" style={{ marginBottom: 16 }}>
        <Row label="Grant rows">
          <div style={{ width: 420 }}>
            <div className="doh-grant"><span className="doh-g-ic"><Icon name="gpu" size={16} /></span><div>GPU<div className="doh-g-from">from gpu</div></div><span className="doh-g-val">all devices</span></div>
            <div className="doh-grant"><span className="doh-g-ic"><Icon name="memory" size={16} /></span><div>Memory<div className="doh-g-from">from gpu</div></div><span className="doh-g-val">32 GB</span></div>
          </div>
        </Row>
        <Row label="Feed item">
          <div className="doh-feed" style={{ width: 420 }}>
            <div className="doh-feed-item">
              <div className="doh-feed-ic"><Icon name="play" size={15} /></div>
              <div className="doh-feed-body"><div className="t"><b>milan</b> started a server with <b>gpu</b></div><div className="when">2m ago</div></div>
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
        <Row label="Text / disabled"><Input style={{ width: 240 }} defaultValue="editable" /><Input className="doh-mono" style={{ width: 240 }} defaultValue="locked value" disabled /></Row>
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
          <span className="doh-muted">now</span>
          <span className="doh-muted">2m</span>
          <span className="doh-muted">5h</span>
          <span className="doh-muted">3d</span>
          <span className="doh-muted">4mo</span>
          <span className="doh-muted">1y</span>
          <span className="doh-page-sub">- one format everywhere; exact timestamp on hover</span>
        </Row>
        <Row label="Alternating rows">
          <span className="doh-page-sub">every table uses zebra striping - mandatory</span>
        </Row>
        <Row label="Panel padding">
          <span className="doh-page-sub">cards use the standard antd body padding; content never sits flush to the edge</span>
        </Row>
        <Row label="State = colour">
          <span className="doh-page-sub">status and type always shown as coloured pills on one shared palette</span>
        </Row>
        <Row label="Label casing (Title Case)">
          <span className="doh-mono">Add User</span>
          <span className="doh-mono">Manage Volumes</span>
          <span className="doh-mono">Clear Events</span>
          <span className="doh-page-sub">- buttons and headers Title-Case every principal word; minor words (a, of, to, on...) stay lowercase unless first; acronyms (API, GPU) and units (7h) kept as-is</span>
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
