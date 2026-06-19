/* Users - a pending-authorisation section on top (shown only when something
 * waits), then the scaled authorised list with state scope pills, inline
 * authorise toggle, and group chips. The username opens Configure user. */
import { useEffect, useMemo, useState } from 'react'
import { ProTable } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { Button, Card, Input, Switch, Tag, Tooltip } from 'antd'
import { Link } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { ScopeFilterPills } from '../components/ScopeFilterPills'
import { ActivityMeter } from '../components/meters'
import { CappedTags } from '../components/CappedTags'
import { Icon } from '../components/Icon'
import { useUsers } from '../hooks/queries'
import { invalidate } from '../services/actions'
import { setUserAuthorization, discardUser } from '../services/ops'
import { isAdminUser } from '../app/capabilities'
import { exactDate, timeAgoShort } from '../lib/format'
import type { UserRow } from '../services/types'

const accentTag = { background: 'var(--color-accent-soft)', color: 'var(--color-accent)', borderRadius: 4, marginInlineStart: 6 }

function inScope(u: UserRow, scope: string): boolean {
  if (scope === 'all') return true
  if (scope === 'authorized') return u.authorized
  if (scope === 'inactive') return u.authorized && u.activity === 0
  if (scope === 'unauthorized') return !u.authorized
  return true
}

function PendingSection({ users }: { users: UserRow[] }) {
  if (users.length === 0) return null
  return (
    <Card style={{ marginBottom: 16, borderColor: 'var(--color-warning)' }} styles={{ body: { padding: 0 } }}>
      <div style={{ padding: '12px 24px', borderBottom: '1px solid var(--color-warning-soft)', fontWeight: 600 }}>
        Pending Authorisation <span className="doh-muted">· {users.length}</span>
      </div>
      <table className="doh-pending-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Groups</th>
            <th>Signed Up</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.name}>
              <td>
                <div className="doh-user-cell">
                  <Link to={`/users/${u.name}`} style={{ color: 'var(--color-accent)' }}>{u.name}</Link>
                  {u.fullName && <span className="doh-name-hint">{u.fullName}</span>}
                </div>
              </td>
              <td><CappedTags items={u.groups.map((g) => ({ key: g, label: g }))} cap={4} /></td>
              <td className="doh-pending-when">{timeAgoShort(u.createdISO)}</td>
              <td className="doh-pending-act">
                <Button type="primary" size="small" onClick={() => setUserAuthorization(u.name, true)}>Authorize</Button>
                <Button danger size="small" onClick={() => discardUser(u.name)}>Discard</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

export default function Users() {
  const { data = [], isLoading } = useUsers()
  const [scope, setScope] = useState('all')
  const [q, setQ] = useState('')
  // Returning to the list after a profile save can paint a stale full name from
  // the hydrated cache (staleTime 30s trusts the persisted value). Force a refetch
  // of the user list on mount so a just-saved first/last name shows immediately.
  useEffect(() => {
    invalidate(['users'])
  }, [])

  const pending = useMemo(() => data.filter((u) => u.pending), [data])
  const main = useMemo(() => data.filter((u) => !u.pending), [data])

  const counts = useMemo(() => {
    return {
      authorized: main.filter((u) => u.authorized).length,
      inactive: main.filter((u) => u.authorized && u.activity === 0).length,
      unauthorized: main.filter((u) => !u.authorized).length,
    }
  }, [main])

  const filtered = useMemo(
    () => main.filter((u) => inScope(u, scope) && u.name.toLowerCase().includes(q.toLowerCase())),
    [main, scope, q],
  )

  const columns: ProColumns<UserRow>[] = [
    {
      title: 'User',
      dataIndex: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (_, u) => (
        <div className="doh-user-cell">
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Link to={`/users/${u.name}`} style={{ color: 'var(--color-accent)' }}>
              {u.name}
            </Link>
            {u.admin && <Tag bordered={false} style={accentTag}>admin</Tag>}
          </div>
          {u.fullName && <span className="doh-name-hint">{u.fullName}</span>}
        </div>
      ),
    },
    {
      title: 'Authorised',
      dataIndex: 'authorized',
      width: 110,
      // admins are always authorised -> no switch for them (just a muted state);
      // others get a controlled switch (checked, not defaultChecked, so it can't
      // desync from the data after a refetch)
      render: (_, u) =>
        isAdminUser(u.name, !!u.admin) ? (
          <Tooltip title="Admins are always authorised">
            <span className="doh-muted">authorised</span>
          </Tooltip>
        ) : (
          <Switch size="small" checked={u.authorized} onChange={(checked) => setUserAuthorization(u.name, checked)} />
        ),
    },
    {
      title: 'Created',
      dataIndex: 'createdISO',
      sorter: (a, b) => a.createdISO.localeCompare(b.createdISO),
      render: (_, u) => <span title={exactDate(u.createdISO)}>{timeAgoShort(u.createdISO)}</span>,
    },
    {
      title: 'Last Seen',
      dataIndex: 'lastSeenISO',
      sorter: (a, b) => (a.lastSeenISO ?? '').localeCompare(b.lastSeenISO ?? ''),
      render: (_, u) =>
        u.lastSeenISO ? <span title={exactDate(u.lastSeenISO)}>{timeAgoShort(u.lastSeenISO)}</span> : <span className="doh-muted" title="never signed in">-</span>,
    },
    {
      title: 'Activity',
      dataIndex: 'activity',
      sorter: (a, b) => a.activity - b.activity,
      render: (_, u) => <ActivityMeter value={u.activity} hours={u.activityHours} pct={u.activityPct} />,
    },
    {
      title: 'Groups',
      dataIndex: 'groups',
      render: (_, u) => <CappedTags items={u.groups.map((g) => ({ key: g, label: g }))} cap={5} />,
    },
  ]

  return (
    <>
      <PageHeader
        title="Users"
        sub="Authorise, configure and watch every account"
        actions={
          <>
            <Link to="/users/bulk"><Button>Bulk Add</Button></Link>
            <Link to="/users/new"><Button type="primary" icon={<Icon name="plus" size={14} />}>Add User</Button></Link>
          </>
        }
      />
      <PendingSection users={pending} />
      <ProTable<UserRow>
        rowKey="name"
        columns={columns}
        dataSource={filtered}
        loading={isLoading}
        search={false}
        options={false}
        rowClassName={(_, i) => (i % 2 ? 'doh-row-alt' : '')}
        pagination={{ pageSize: 10, showSizeChanger: false, showTotal: (t) => `${t} users in scope` }}
        headerTitle={
          <ScopeFilterPills
            value={scope}
            onChange={setScope}
            scopes={[
              { key: 'authorized', label: 'Authorised', count: counts.authorized, tone: 'ok' },
              { key: 'inactive', label: 'Inactive', count: counts.inactive, tone: 'warn' },
              { key: 'unauthorized', label: 'Unauthorised', count: counts.unauthorized, tone: 'danger' },
              { key: 'all', label: 'All', count: main.length, tone: 'accent' },
            ]}
          />
        }
        toolBarRender={() => [
          <Input
            key="search"
            allowClear
            prefix={<Icon name="search" size={14} />}
            placeholder="Filter by username…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{ width: 200 }}
          />,
        ]}
      />
    </>
  )
}
