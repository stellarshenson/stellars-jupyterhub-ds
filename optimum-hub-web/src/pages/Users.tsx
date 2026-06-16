/* Users - a pending-authorisation section on top (shown only when something
 * waits), then the scaled authorised list with state scope pills, inline
 * authorise toggle, and group chips. The username opens Configure user. */
import { useMemo, useState } from 'react'
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
import { setUserAuthorization, discardUser } from '../services/ops'
import { PLATFORM } from '../services/config'
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
        Pending authorisation <span className="oh-muted">· {users.length}</span>
      </div>
      <table className="oh-pending-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Groups</th>
            <th>Signed up</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.name}>
              <td>
                <div className="oh-user-cell">
                  <Link to={`/users/${u.name}`} style={{ color: 'var(--color-accent)' }}>{u.name}</Link>
                  {u.fullName && <span className="oh-name-hint">{u.fullName}</span>}
                </div>
              </td>
              <td><CappedTags items={u.groups.map((g) => ({ key: g, label: g }))} cap={4} /></td>
              <td className="oh-pending-when">{timeAgoShort(u.createdISO)}</td>
              <td className="oh-pending-act">
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
  const [scope, setScope] = useState('authorized')
  const [q, setQ] = useState('')

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
        <div className="oh-user-cell">
          <div>
            <Link to={`/users/${u.name}`} style={{ color: 'var(--color-accent)' }}>
              {u.name}
            </Link>
            {u.admin && <Tag bordered={false} style={accentTag}>admin</Tag>}
          </div>
          {u.fullName && <span className="oh-name-hint">{u.fullName}</span>}
        </div>
      ),
    },
    {
      title: 'Authorised',
      dataIndex: 'authorized',
      width: 110,
      render: (_, u) =>
        u.name === PLATFORM.admin ? (
          <Tooltip title="Built-in admin - authorisation controlled by system config">
            <Switch size="small" checked disabled />
          </Tooltip>
        ) : (
          <Switch size="small" defaultChecked={u.authorized} onChange={(checked) => setUserAuthorization(u.name, checked)} />
        ),
    },
    {
      title: 'Created',
      dataIndex: 'createdISO',
      sorter: (a, b) => a.createdISO.localeCompare(b.createdISO),
      render: (_, u) => <span title={exactDate(u.createdISO)}>{timeAgoShort(u.createdISO)}</span>,
    },
    {
      title: 'Last seen',
      dataIndex: 'lastSeenISO',
      sorter: (a, b) => (a.lastSeenISO ?? '').localeCompare(b.lastSeenISO ?? ''),
      render: (_, u) => <span title={u.lastSeenISO ? exactDate(u.lastSeenISO) : 'never signed in'}>{timeAgoShort(u.lastSeenISO)}</span>,
    },
    {
      title: 'Activity',
      dataIndex: 'activity',
      sorter: (a, b) => a.activity - b.activity,
      render: (_, u) => <ActivityMeter value={u.activity} />,
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
            <Link to="/users/bulk"><Button>Bulk add</Button></Link>
            <Link to="/users/new"><Button type="primary" icon={<Icon name="plus" size={14} />}>Add user</Button></Link>
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
        rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
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
