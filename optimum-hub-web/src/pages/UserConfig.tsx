/* Configure user - a full tabbed screen (Profile / Groups + effective access /
 * Volumes) with one action footer. The username link on the Users list opens
 * this. All writes mocked. */
import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, Space, Switch, Tabs } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { GroupPicker } from '../components/GroupPicker'
import { Icon } from '../components/Icon'
import { Notice } from '../components/Notice'
import { VolumeReset } from '../components/VolumeReset'
import { useEffectiveGrants, useUser, useUserProfile } from '../hooks/queries'
import { mockSuccess } from '../services/actions'
import { isMock } from '../services/dataMode'
import { addMember, setUserAuthorization, deleteUser, removeMember, saveUserProfile, setAdmin, setUserPassword } from '../services/ops'
import { PLATFORM } from '../services/config'
import { adminUser, isAdminUser } from '../app/capabilities'
import { genPassword } from '../lib/password'

export default function UserConfig() {
  const { name = '' } = useParams()
  const navigate = useNavigate()
  const { data: user } = useUser(name)
  const { data: userProfile } = useUserProfile(name)
  const { data: grants = [] } = useEffectiveGrants(name)
  const [form] = Form.useForm()
  const [groups, setGroups] = useState<string[]>([])
  const [tab, setTab] = useState('profile')
  const [pw, setPw] = useState('')

  // the platform-configured admin (JUPYTERHUB_ADMIN, from the live shell; mock
  // falls back to the fixture): always admin + authorised, never removable.
  const isBuiltinAdmin = name === (adminUser() || PLATFORM.admin)
  // effective admin includes the hook-promoted admin whose persistent row is False
  const userIsAdmin = isAdminUser(name, !!user?.admin)

  // React Query resolves after mount; the Form is keyed on the stable `name` (no
  // remount), so push each async source into it imperatively as it arrives.
  useEffect(() => {
    if (user) {
      setGroups(user.groups)
      const eff = isAdminUser(name, !!user.admin)
      form.setFieldsValue({ admin: eff, authorized: user.authorized || eff })
    }
  }, [user, form, name])
  useEffect(() => {
    if (userProfile) form.setFieldsValue({ first: userProfile.firstName, last: userProfile.lastName, email: userProfile.email })
  }, [userProfile, form])

  const save = async () => {
    try {
      const v = await form.validateFields()
      // validate in both modes; the mock demo should gate on the same rules, not
      // "save" invalid data
      if (isMock()) {
        mockSuccess(`Saved ${name}`)
        navigate('/users')
        return
      }
      await saveUserProfile(name, { firstName: v.first ?? '', lastName: v.last ?? '', email: v.email ?? '' })
      const effAdmin = isAdminUser(name, !!user?.admin)
      if (!isBuiltinAdmin && user && !!v.admin !== effAdmin) await setAdmin(name, !!v.admin)
      // admins are always authorised -> the switch is hidden for them; only persist for non-admins
      if (!isBuiltinAdmin && !effAdmin && user && !!v.authorized !== user.authorized) await setUserAuthorization(name, !!v.authorized)
      if (pw) await setUserPassword(name, pw)
      const before = new Set(user?.groups ?? [])
      const after = new Set(groups)
      for (const g of groups) if (!before.has(g)) await addMember(g, name)
      for (const g of user?.groups ?? []) if (!after.has(g)) await removeMember(g, name)
      setPw('')
      // ops surfaced per-write success toasts; return to the list on success
      navigate('/users')
    } catch {
      /* ops surfaced the error - stay on the form */
    }
  }

  const remove = async () => {
    await deleteUser(name)
    if (!isMock()) navigate('/users')
  }

  const profile = (
    <Form form={form} key={name} layout="vertical" initialValues={{ username: name, first: '', last: '', email: '', admin: false, authorized: false }}>
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
      <Form.Item label="Change password" extra="Leave blank to keep, or generate one">
        <Space.Compact style={{ width: '100%' }}>
          <Input className="oh-mono" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="Leave blank to keep" />
          <Button onClick={() => setPw(genPassword())}>Generate</Button>
        </Space.Compact>
      </Form.Item>
      {!isBuiltinAdmin && <Form.Item label="Administrator" name="admin" valuePropName="checked"><Switch /></Form.Item>}
      {/* admins are always authorised -> hide the switch for the built-in and any effective admin */}
      {!isBuiltinAdmin && !userIsAdmin && <Form.Item label="Authorised" name="authorized" valuePropName="checked"><Switch /></Form.Item>}
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

  const volumesTab = <VolumeReset name={name} />

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
          destructive={isBuiltinAdmin ? undefined : <Button danger icon={<Icon name="close" size={14} />} onClick={remove}>Remove user</Button>}
          onCancel={() => navigate('/users')}
          onSave={save}
        />
      </Card>
    </>
  )
}
