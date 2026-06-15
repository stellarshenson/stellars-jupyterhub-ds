/* Users - a pending-authorisation section on top (shown only when something
 * waits), then the scaled authorised list with state scope pills, inline
 * authorise toggle, and group chips. The username opens Configure user. */
import { useMemo, useState } from 'react'
import { ProTable } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { Button, Card, Input, Switch, Tag } from 'antd'
import { Link } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { ScopeFilterPills } from '../components/ScopeFilterPills'
import { ActivityMeter } from '../components/meters'
import { CappedTags } from '../components/CappedTags'
import { Icon } from '../components/Icon'
import { useUsers } from '../hooks/queries'
import { mockAction } from '../services/actions'
import { exactDate, timeAgo } from '../lib/format'
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
    <Card style={{ marginBottom: 16 }} styles={{ body: { padding: 0 } }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)', fontWeight: 600 }}>
        Pending authorisation <span className="oh-muted">· {users.length}</span>
      </div>
      {users.map((u) => (
        <div key={u.name} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <Icon name="user" size={16} />
          <div style={{ minWidth: 0 }}>
            {u.name}
            {u.fullName && <span className="oh-name-hint">{u.fullName}</span>}
          </div>
          <div style={{ marginLeft: 'auto', color: 'var(--color-text-subtle)', fontSize: 12 }}>signed up {timeAgo(u.createdISO)}</div>
          <Button type="primary" size="small" onClick={() => mockAction(`Authorized ${u.name}`)}>Authorize</Button>
          <Button danger size="small" onClick={() => mockAction(`Discarded ${u.name}`)}>Discard</Button>
        </div>
      ))}
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
        <div>
          <Link to={`/users/${u.name}`} style={{ color: 'var(--color-accent)' }}>
            {u.name}
          </Link>
          {u.admin && <Tag bordered={false} style={accentTag}>admin</Tag>}
          {u.fullName && <span className="oh-name-hint">{u.fullName}</span>}
        </div>
      ),
    },
    {
      title: 'Authorised',
      dataIndex: 'authorized',
      width: 110,
      render: (_, u) => (
        <Switch size="small" defaultChecked={u.authorized} onChange={(v) => mockAction(`${v ? 'Authorized' : 'De-authorized'} ${u.name}`)} />
      ),
    },
    {
      title: 'Created',
      dataIndex: 'createdISO',
      sorter: (a, b) => a.createdISO.localeCompare(b.createdISO),
      render: (_, u) => <span title={exactDate(u.createdISO)}>{timeAgo(u.createdISO)}</span>,
    },
    {
      title: 'Last seen',
      dataIndex: 'lastSeenISO',
      sorter: (a, b) => (a.lastSeenISO ?? '').localeCompare(b.lastSeenISO ?? ''),
      render: (_, u) => <span title={u.lastSeenISO ? exactDate(u.lastSeenISO) : 'never signed in'}>{timeAgo(u.lastSeenISO)}</span>,
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
      render: (_, u) => <CappedTags items={u.groups.map((g) => ({ key: g, label: g }))} cap={3} />,
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
