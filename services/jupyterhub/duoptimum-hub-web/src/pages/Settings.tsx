/* Settings - the running configuration; mostly a reference, with the admin-
 * overridable controls (signup) rendered as live toggles. The Display Options
 * accordion on top is the per-user options harness (registry-driven). */
import { Card, Collapse, Switch, Tag } from 'antd'
import { Link } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Icon } from '../components/Icon'
import { OptionControl } from '../components/OptionControl'
import { useSettings } from '../hooks/queries'
import { mockAction } from '../services/actions'
import { usePref, useSetPref } from '../app/PrefsContext'
import { SETTINGS_PANELS } from '../services/displayOptions'
import type { DisplayOption } from '../services/displayOptions'
import type { PlatformSetting } from '../services/types'

function value(row: PlatformSetting) {
  if (row.control === 'switch')
    return <Switch size="small" defaultChecked={row.value === 'enabled'} onChange={(v) => mockAction(`${row.key} ${v ? 'enabled' : 'disabled'}`)} />
  if (row.state === 'ok') return <Tag bordered={false} style={{ background: 'var(--color-success-soft)', color: 'var(--color-success)', borderRadius: 4 }}>{row.value}</Tag>
  if (row.state === 'accent') return <Tag bordered={false} style={{ background: 'var(--color-accent-soft)', color: 'var(--color-accent)', borderRadius: 4 }}>{row.value}</Tag>
  if (row.state === 'neutral') return <span className="oh-mono">{row.value}</span>
  return <span className="oh-num">{row.value}</span>
}

// one option row: label (+ help tooltip) and its control, wired to the prefs store
function OptionRow({ option, set }: { option: DisplayOption; set: (key: string, value: import('../services/displayOptions').PrefValue) => void }) {
  const value = usePref(option.key)
  return (
    <tr>
      <td title={option.help} style={{ padding: '10px 16px', color: 'var(--color-text-muted)', borderBottom: '1px solid var(--color-border-subtle)' }}>
        {option.label}
      </td>
      <td style={{ padding: '10px 16px', textAlign: 'right', borderBottom: '1px solid var(--color-border-subtle)' }}>
        <OptionControl option={option} value={value} onChange={(v) => set(option.key, v)} />
      </td>
    </tr>
  )
}

// the registry-driven accordion (each panel = a table of feature -> control)
function OptionsPanels() {
  const set = useSetPref()
  return (
    <Collapse
      style={{ marginBottom: 16 }}
      defaultActiveKey={SETTINGS_PANELS.filter((p) => p.defaultOpen).map((p) => p.key)}
      items={SETTINGS_PANELS.map((panel) => ({
        key: panel.key,
        label: panel.title,
        children: (
          <table className="oh-kv-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <tbody>
              {panel.options.map((option) => (
                <OptionRow key={option.key} option={option} set={set} />
              ))}
            </tbody>
          </table>
        ),
      }))}
    />
  )
}

export default function Settings() {
  const { data = [] } = useSettings()
  return (
    <>
      <PageHeader
        title="Settings"
        sub="Review the running platform configuration"
        actions={
          <Link to="/settings/reference">
            <span className="oh-pill accent" style={{ cursor: 'pointer' }}>
              <Icon name="code" size={14} /> Full Reference
            </span>
          </Link>
        }
      />
      <OptionsPanels />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
        {data.map((group) => (
          <Card key={group.title} styles={{ body: { padding: 0 } }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)', fontWeight: 600 }}>{group.title}</div>
            <table className="oh-kv-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <tbody>
                {group.rows.map((row) => (
                  <tr key={row.key}>
                    <td style={{ padding: '10px 16px', color: 'var(--color-text-muted)', borderBottom: '1px solid var(--color-border-subtle)' }} title={row.tip}>
                      {row.key}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right', borderBottom: '1px solid var(--color-border-subtle)' }}>{value(row)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        ))}
      </div>
    </>
  )
}
