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

// ── Role definitions (single panel, one row per role) ───────────────────────
interface RoleDef { role: string; description: string; assigned: string; who: string }

const ROLES: RoleDef[] = [
  {
    role: 'Admin',
    description: 'Full read/write/create/remove across the fleet, users, groups and platform settings',
    assigned: "Holds JupyterHub's admin flag - JUPYTERHUB_ADMIN at login, or toggled on the Users screen",
    who: 'Platform operators, maintainers',
  },
  {
    role: 'User',
    description: 'Own server and profile only; reads own launchpad, no fleet/user/group rights',
    assigned: 'Authenticated, authorised account without the admin flag',
    who: 'Data scientists, notebook authors, learners',
  },
]

const roleColumns = [
  { title: 'Role', dataIndex: 'role', width: 90, render: (v: string) => <b>{v}</b> },
  { title: 'Description', dataIndex: 'description' },
  { title: 'How assigned', dataIndex: 'assigned', width: 320 },
  { title: 'Who', dataIndex: 'who', width: 200 },
]

// ── Access matrix (one row per page + action; CRUD rights in the description) ─
interface Cap { area: string; capability: string; desc: string; admin: Level; user: Level }

// Sourced from the router's admin gating (RequireAdmin) and the handlers' self-or-
// admin rules; the description states the read/write/list/create/remove rights,
// the cells state the level each role holds.
const CAPS: Cap[] = [
  // Pages
  { area: 'Pages', capability: 'Home dashboard', desc: 'Admin reads the whole fleet; user reads only their own launchpad', admin: 'full', user: 'full' },
  { area: 'Pages', capability: 'Own profile', desc: 'Read + write own name, email and password', admin: 'full', user: 'self' },
  { area: 'Pages', capability: 'Servers (fleet)', desc: 'List, read and control every user’s server', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Users', desc: 'List, create, read, write and remove any account', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Groups', desc: 'List, create, read, write and remove any group', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Lab Setup', desc: 'Read + write the spawned-lab image and aux config', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Events log', desc: 'Read + clear the platform event stream', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Notifications', desc: 'Compose + broadcast to all running labs', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Settings + reference', desc: 'Read + write hub-wide settings', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Tokens', desc: 'List, create and remove API tokens', admin: 'full', user: 'none' },
  { area: 'Pages', capability: 'Roles (this page)', desc: 'Read-only reference; no writes by any role', admin: 'view', user: 'none' },
  // Server actions
  { area: 'Server', capability: 'Start / stop / restart server', desc: 'Create/remove the lab container; user acts on their own server only', admin: 'full', user: 'self' },
  { area: 'Server', capability: 'Open / enter lab', desc: 'Open a running lab; admin can enter any lab (with a confirm)', admin: 'full', user: 'self' },
  { area: 'Server', capability: 'Extend session (idle TTL)', desc: 'Write a later idle-cull deadline for a running server', admin: 'full', user: 'self' },
  { area: 'Server', capability: 'Manage / reset volumes', desc: 'List + remove a user’s persistent volumes (server stopped)', admin: 'full', user: 'self' },
  { area: 'Server', capability: 'Bulk Start All / Stop All', desc: 'Create/remove every lab in one action', admin: 'full', user: 'none' },
  // User administration
  { area: 'Users', capability: 'Create / remove user', desc: 'Create a new account or delete an existing one', admin: 'full', user: 'none' },
  { area: 'Users', capability: 'Rename user', desc: 'Write a user’s login name; stopped server only; volumes not migrated', admin: 'full', user: 'none' },
  { area: 'Users', capability: 'Authorise / discard signup', desc: 'Approve or remove a pending self-signup', admin: 'full', user: 'none' },
  { area: 'Users', capability: 'Grant / revoke admin', desc: 'Write another account’s admin flag', admin: 'full', user: 'none' },
  { area: 'Users', capability: 'Set another user password', desc: 'Write any user’s password', admin: 'full', user: 'none' },
  { area: 'Users', capability: 'Force password change', desc: 'Flag a user to reset their password at next login', admin: 'full', user: 'none' },
  { area: 'Users', capability: 'Change own password', desc: 'Write own password only', admin: 'full', user: 'self' },
  // Groups + policy
  { area: 'Groups', capability: 'Create / delete / configure groups', desc: 'Create, write and remove access-control groups', admin: 'full', user: 'none' },
  { area: 'Groups', capability: 'Group membership + policy', desc: 'Write a group’s members and spawn policy', admin: 'full', user: 'none' },
  { area: 'Groups', capability: 'Effective access (view own)', desc: 'Read the access a membership grants; user reads own only', admin: 'full', user: 'self' },
  // Platform
  { area: 'Platform', capability: 'Broadcast notifications', desc: 'Send a message to every running lab', admin: 'full', user: 'none' },
  { area: 'Platform', capability: 'Clear events log', desc: 'Remove all recorded events', admin: 'full', user: 'none' },
  { area: 'Platform', capability: 'Reset activity samples', desc: 'Remove the stored activity-monitor history', admin: 'full', user: 'none' },
  { area: 'Platform', capability: 'Edit platform settings', desc: 'Write hub-wide configuration values', admin: 'full', user: 'none' },
]

const columns = [
  { title: 'Capability', dataIndex: 'capability', width: 220, render: (v: string) => <b>{v}</b> },
  { title: 'Description', dataIndex: 'desc', render: (v: string) => <span className="oh-muted">{v}</span> },
  { title: 'Admin', dataIndex: 'admin', width: 110, align: 'center' as const, render: (l: Level) => <AccessPill level={l} /> },
  { title: 'User', dataIndex: 'user', width: 110, align: 'center' as const, render: (l: Level) => <AccessPill level={l} /> },
]

export default function Roles() {
  // group the matrix by area so the table reads section by section
  const areas = Array.from(new Set(CAPS.map((c) => c.area)))
  return (
    <>
      <PageHeader title="Roles" sub="The two platform roles and the access each is granted" />

      <Card title="Role definitions" styles={{ body: { padding: 0 } }} style={{ marginBottom: 16 }}>
        <Table<RoleDef>
          rowKey="role"
          pagination={false}
          rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
          dataSource={ROLES}
          columns={roleColumns}
        />
      </Card>

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
