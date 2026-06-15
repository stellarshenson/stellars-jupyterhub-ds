/* Tokens - personal API tokens and authorised OAuth applications. Read-only;
 * request / revoke are mocked. */
import { ProTable } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { Button } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { IconAction } from '../components/IconAction'
import { Icon } from '../components/Icon'
import { useTokens } from '../hooks/queries'
import { mockAction } from '../services/actions'
import { exactDate, timeAgo } from '../lib/format'
import type { TokenRow } from '../services/types'

export default function Tokens() {
  const { data = [], isLoading } = useTokens()
  const tokens = data.filter((t) => t.kind === 'token')
  const apps = data.filter((t) => t.kind === 'oauth')

  const tokenCols: ProColumns<TokenRow>[] = [
    { title: 'Note', dataIndex: 'note', render: (_, t) => <span className="oh-mono">{t.note}</span> },
    { title: 'Scopes', dataIndex: 'scopes', render: (_, t) => <span className="oh-muted">{t.scopes ?? '-'}</span> },
    { title: 'Created', dataIndex: 'createdISO', render: (_, t) => <span title={exactDate(t.createdISO)}>{timeAgo(t.createdISO)}</span> },
    { title: 'Last used', dataIndex: 'lastUsedISO', render: (_, t) => <span title={t.lastUsedISO ? exactDate(t.lastUsedISO) : 'never'}>{timeAgo(t.lastUsedISO)}</span> },
    { title: 'Expires', dataIndex: 'expiresISO', render: (_, t) => (t.expiresISO ? exactDate(t.expiresISO) : <span className="oh-muted">never</span>) },
    { title: 'Actions', align: 'right', width: 80, render: (_, t) => <IconAction icon="close" title="Revoke" danger onClick={() => mockAction(`Revoked token ${t.note}`)} /> },
  ]

  const appCols: ProColumns<TokenRow>[] = [
    { title: 'Application', dataIndex: 'note', render: (_, t) => t.note },
    { title: 'Authorised', dataIndex: 'createdISO', render: (_, t) => <span title={exactDate(t.createdISO)}>{timeAgo(t.createdISO)}</span> },
    { title: 'Last used', dataIndex: 'lastUsedISO', render: (_, t) => <span title={t.lastUsedISO ? exactDate(t.lastUsedISO) : 'never'}>{timeAgo(t.lastUsedISO)}</span> },
    { title: 'Actions', align: 'right', width: 80, render: (_, t) => <IconAction icon="close" title="Revoke access" danger onClick={() => mockAction(`Revoked app ${t.note}`)} /> },
  ]

  return (
    <>
      <PageHeader
        title="Tokens"
        sub="Personal API tokens and the applications authorised against your account"
        actions={<Button type="primary" icon={<Icon name="key" size={14} />} onClick={() => mockAction('Requested a new API token')}>Request token</Button>}
      />
      <ProTable<TokenRow>
        rowKey="id"
        headerTitle="API tokens"
        columns={tokenCols}
        dataSource={tokens}
        loading={isLoading}
        search={false}
        options={false}
        rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
        pagination={false}
        style={{ marginBottom: 16 }}
      />
      <ProTable<TokenRow>
        rowKey="id"
        headerTitle="Authorised applications"
        columns={appCols}
        dataSource={apps}
        search={false}
        options={false}
        rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
        pagination={false}
      />
    </>
  )
}
