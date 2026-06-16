/* Configure user - a full tabbed screen (Profile / Groups + effective access /
 * Volumes) with one action footer. The username link on the Users list opens
 * this. All writes mocked. */
import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, Switch, Table, Tabs, Tooltip } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { GroupPicker } from '../components/GroupPicker'
import { Icon } from '../components/Icon'
import { Notice } from '../components/Notice'
import { useEffectiveGrants, useUser, useUserVolumes } from '../hooks/queries'
import { mockAction, mockSuccess } from '../services/actions'
import { PLATFORM } from '../services/config'
import type { Volume } from '../services/types'

export default function UserConfig() {
  const { name = '' } = useParams()
  const navigate = useNavigate()
  const { data: user } = useUser(name)
  const { data: volumes = [] } = useUserVolumes(name)
  const { data: grants = [] } = useEffectiveGrants(name)
  const [groups, setGroups] = useState<string[]>([])
  const [tab, setTab] = useState('profile')

  // the platform-configured admin (JUPYTERHUB_ADMIN): always admin + authorised,
  // never removable - those controls are owned by system config, not this screen
  const isBuiltinAdmin = name === PLATFORM.admin

  // React Query resolves after mount, so sync the combo + re-key the Form to
  // re-apply initialValues once the user is loaded (antd captures them at mount).
  useEffect(() => {
    if (user) setGroups(user.groups)
  }, [user])

  const [first = '', last = ''] = (user?.fullName ?? '').split(' ')

  const profile = (
    <Form key={user ? `u-${user.name}` : 'loading'} layout="vertical" initialValues={{ username: name, first, last, email: `${name}@lab.stellars-tech.eu`, admin: user?.admin, authorized: user?.authorized }}>
      {isBuiltinAdmin && (
        <div style={{ marginBottom: 16 }}>
          <Notice type="warning">
            <span><b>Built-in admin account.</b> Admin role and authorisation are set by the platform; this account cannot be de-authorised or removed.</span>
          </Notice>
        </div>
      )}
      <Form.Item label="Username" name="username"><Input disabled /></Form.Item>
      <Form.Item label="First name" name="first"><Input /></Form.Item>
      <Form.Item label="Last name" name="last"><Input /></Form.Item>
      <Form.Item label="Email" name="email"><Input /></Form.Item>
      <Form.Item label="Change password" extra="Admin override - no current password needed">
        <Input.Password placeholder="Leave blank to keep" />
      </Form.Item>
      <Form.Item label="Require password change at next login">
        <Tooltip title="Cleared automatically once the user signs in and sets a new password">
          <Switch />
        </Tooltip>
      </Form.Item>
      {!isBuiltinAdmin && <Form.Item label="Administrator" name="admin" valuePropName="checked"><Switch /></Form.Item>}
      {!isBuiltinAdmin && <Form.Item label="Authorised" name="authorized" valuePropName="checked"><Switch /></Form.Item>}
    </Form>
  )

  const groupsTab = (
    <div>
      <GroupPicker value={groups} onChange={setGroups} />

      <div className="oh-section-title">Effective policies</div>
      <div className="oh-page-sub" style={{ marginBottom: 12 }}>The policy resolved across this user's groups - each grant cites the group that won.</div>
      {grants.map((g) => (
        <div className="oh-grant" key={g.key}>
          <span className="oh-g-ic"><Icon name={g.key as 'gpu'} size={16} /></span>
          <div>
            {g.label}
            <div className="oh-g-from">from {g.from}</div>
          </div>
          <span className="oh-g-val">{g.value}</span>
        </div>
      ))}
    </div>
  )

  const volumesTab = (
    <div>
      <Notice type="info">Volume reset is enabled only when the user's server is stopped.</Notice>
      <Table<Volume>
        rowKey="suffix"
        style={{ marginTop: 12 }}
        pagination={false}
        rowSelection={{ type: 'checkbox' }}
        dataSource={volumes}
        columns={[
          { title: 'Volume', dataIndex: 'name', render: (v) => <span className="oh-mono">{v}</span> },
          { title: 'Mount', dataIndex: 'mount', render: (v) => <span className="oh-mono">{v}</span> },
          { title: 'Description', dataIndex: 'description', render: (v) => <span className="oh-muted">{v}</span> },
          { title: 'Size', dataIndex: 'sizeGB', align: 'right', render: (v) => <span className="oh-num">{v} GB</span> },
        ]}
      />
      <div style={{ marginTop: 12 }}>
        <Button danger onClick={() => mockAction('Reset selected volumes (server must be stopped)')}>Reset selected</Button>
      </div>
    </div>
  )

  const widths: Record<string, number> = { profile: 680, groups: 1000, volumes: 880 }

  return (
    <>
      <PageHeader title={`Configure ${name}`} sub="Profile, group membership and volumes" />
      <Card style={{ maxWidth: widths[tab], transition: 'max-width .18s ease' }}>
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            { key: 'profile', label: 'Profile', children: profile },
            { key: 'groups', label: 'Groups', children: groupsTab },
            { key: 'volumes', label: 'Volumes', children: volumesTab },
          ]}
        />
        <FormFooter
          destructive={isBuiltinAdmin ? undefined : <Button danger icon={<Icon name="close" size={14} />} onClick={() => mockAction(`Remove user ${name}`)}>Remove user</Button>}
          onCancel={() => navigate('/users')}
          onSave={() => mockSuccess(`Saved ${name}`)}
        />
      </Card>
    </>
  )
}
