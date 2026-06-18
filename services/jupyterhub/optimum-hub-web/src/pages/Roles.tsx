/* Roles reference - the two IMPLICIT platform roles (admin, user) and the access
 * each is granted across every page and action. Roles are not assigned by name:
 * the platform derives them from the JupyterHub admin flag (admin) vs a regular
 * authenticated account (user). Static curated reference (no backend). */
import { Card, Table } from 'antd'
import { PageHeader } from '../components/PageHeader'

type Level = 'full' | 'self' | 'view' | 'none'

// access tones: green = full manage, amber = own only, blue = read-only, red = denied
const LEVEL: Record<Level, { label: string; color: string }> = {
  full: { label: 'Full', color: 'var(--color-success)' },
  self: { label: 'Self only', color: 'var(--color-warning)' },
  view: { label: 'View', color: 'var(--color-accent)' },
  none: { label: 'Denied', color: 'var(--color-danger)' },
}

function AccessPill({ level }: { level: Level }) {
  const t = LEVEL[level]
  return (
    <span
      className="oh-pill"
      style={{
        color: t.color,
        background: `color-mix(in srgb, ${t.color} 14%, transparent)`,
        border: `1px solid color-mix(in srgb, ${t.color} 30%, transparent)`,
      }}
    >
      {t.label}
    </span>
  )
}

interface Cap { area: string; capability: string; admin: Level; user: Level; note?: string }

// Sourced from the router's admin gating (RequireAdmin) and the handlers' self-or-
// admin rules; cells say what each role may do, not merely see.
const CAPS: Cap[] = [
  // Pages
  { area: 'Pages', capability: 'Home dashboard', admin: 'full', user: 'full', note: 'admin sees the fleet; user sees their own launchpad' },
  { area: 'Pages', capability: 'Own profile', admin: 'full', user: 'self', note: 'name, email, own password' },
  { area: 'Pages', capability: 'Servers (fleet)', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Users', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Groups', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Lab Setup', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Events log', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Notifications', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Settings + reference', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Tokens', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Roles (this page)', admin: 'view', user: 'none' },
  // Server actions
  { area: 'Server', capability: 'Start / stop / restart server', admin: 'full', user: 'self', note: 'user acts on their own server only' },
  { area: 'Server', capability: 'Open / enter lab', admin: 'full', user: 'self', note: 'admin can enter any lab (with a confirm)' },
  { area: 'Server', capability: 'Extend session (idle TTL)', admin: 'full', user: 'self' },
  { area: 'Server', capability: 'Manage / reset volumes', admin: 'full', user: 'self' },
  { area: 'Server', capability: 'Bulk Start All / Stop All', admin: 'full', user: 'none' },
  // User administration
  { area: 'Users', capability: 'Create / remove user', admin: 'full', user: 'none' },
  { area: 'Users', capability: 'Rename user', admin: 'full', user: 'none', note: 'stopped server only; see Roles note on collateral' },
  { area: 'Users', capability: 'Authorise / discard signup', admin: 'full', user: 'none' },
  { area: 'Users', capability: 'Grant / revoke admin', admin: 'full', user: 'none' },
  { area: 'Users', capability: 'Set another user password', admin: 'full', user: 'none' },
  { area: 'Users', capability: 'Force password change', admin: 'full', user: 'none' },
  { area: 'Users', capability: 'Change own password', admin: 'full', user: 'self' },
  // Groups + policy
  { area: 'Groups', capability: 'Create / delete / configure groups', admin: 'full', user: 'none' },
  { area: 'Groups', capability: 'Group membership + policy', admin: 'full', user: 'none' },
  { area: 'Groups', capability: 'Effective access (view own)', admin: 'full', user: 'self' },
  // Platform
  { area: 'Platform', capability: 'Broadcast notifications', admin: 'full', user: 'none' },
  { area: 'Platform', capability: 'Clear events log', admin: 'full', user: 'none' },
  { area: 'Platform', capability: 'Reset activity samples', admin: 'full', user: 'none' },
  { area: 'Platform', capability: 'Edit platform settings', admin: 'full', user: 'none' },
]

const columns = [
  {
    title: 'Capability',
    dataIndex: 'capability',
    render: (v: string, r: Cap) => (
      <div>
        <div>{v}</div>
        {r.note && <div className="oh-muted" style={{ fontSize: 12 }}>{r.note}</div>}
      </div>
    ),
  },
  { title: 'Admin', dataIndex: 'admin', width: 120, align: 'center' as const, render: (l: Level) => <AccessPill level={l} /> },
  { title: 'User', dataIndex: 'user', width: 120, align: 'center' as const, render: (l: Level) => <AccessPill level={l} /> },
]

export default function Roles() {
  // group the matrix by area so the table reads section by section
  const areas = Array.from(new Set(CAPS.map((c) => c.area)))
  return (
    <>
      <PageHeader title="Roles" sub="The two platform roles and the access each is granted" />

      <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
        <Card title="Admin" style={{ flex: 1, minWidth: 280 }}>
          <p>Holds JupyterHub's <span className="oh-mono">admin</span> flag - granted to the
            configured <span className="oh-mono">JUPYTERHUB_ADMIN</span> at login, or toggled on the
            Users screen. Sees the full Administration nav and manages the whole fleet: every user,
            group, server and platform setting.</p>
        </Card>
        <Card title="User" style={{ flex: 1, minWidth: 280 }}>
          <p>Any authenticated, authorised account without the admin flag. Operates only their own
            server and profile - start/stop their lab, manage their own volumes, change their own
            password. No fleet, user or group administration.</p>
        </Card>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {areas.map((area) => (
          <Card key={area} title={area} styles={{ body: { padding: 0 } }}>
            <Table<Cap>
              rowKey="capability"
              pagination={false}
              rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
              dataSource={CAPS.filter((c) => c.area === area)}
              columns={columns}
            />
          </Card>
        ))}
      </div>
    </>
  )
}
