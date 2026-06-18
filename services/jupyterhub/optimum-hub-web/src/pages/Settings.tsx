/* Settings - the running configuration; mostly a reference, with the admin-
 * overridable controls (signup) rendered as live toggles. */
import { Card, Switch, Tag } from 'antd'
import { Link } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Icon } from '../components/Icon'
import { useSettings } from '../hooks/queries'
import { mockAction } from '../services/actions'
import type { PlatformSetting } from '../services/types'

function value(row: PlatformSetting) {
  if (row.control === 'switch')
    return <Switch size="small" defaultChecked={row.value === 'enabled'} onChange={(v) => mockAction(`${row.key} ${v ? 'enabled' : 'disabled'}`)} />
  if (row.state === 'ok') return <Tag bordered={false} style={{ background: 'var(--color-success-soft)', color: 'var(--color-success)', borderRadius: 4 }}>{row.value}</Tag>
  if (row.state === 'accent') return <Tag bordered={false} style={{ background: 'var(--color-accent-soft)', color: 'var(--color-accent)', borderRadius: 4 }}>{row.value}</Tag>
  if (row.state === 'neutral') return <span className="oh-mono">{row.value}</span>
  return <span className="oh-num">{row.value}</span>
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
