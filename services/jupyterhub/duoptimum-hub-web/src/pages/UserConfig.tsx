/* Configure user - a full tabbed screen (Profile / Groups + effective access /
 * Volumes) with one action footer. The username link on the Users list opens
 * this. All writes mocked. */
import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, Modal, Space, Switch, Tabs } from 'antd'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { GroupPicker } from '../components/GroupPicker'
import { Icon } from '../components/Icon'
import { Notice } from '../components/Notice'
import { VolumeReset } from '../components/VolumeReset'
import { RemoveUserModal } from '../components/RemoveUserModal'
import { useRole } from '../app/RoleContext'
import { useEffectiveGrants, useServerHero, useUser, useUserProfile } from '../hooks/queries'
import { mockSuccess } from '../services/actions'
import { isMock } from '../services/dataMode'
import { addMember, setUserAuthorization, removeMember, renameUser, saveUserProfile, setAdmin, setForcePasswordChange, setUserPassword } from '../services/ops'
import { PLATFORM } from '../services/config'
import { adminUser, isAdminUser } from '../app/capabilities'
import { genPassword } from '../lib/password'

export default function UserConfig() {
  // /users/:name carries the target; /profile has no param -> fall back to the
  // logged-in user so Profile reuses this exact screen, scoped to self
  const { name: paramName } = useParams()
  const { username, role } = useRole()
  const name = paramName || username
  const navigate = useNavigate()
  // Save / Cancel / Remove return to where this was opened from (Home or Servers
  // widget, per the nav-origin state); the Users list is the canonical fallback
  // (deep link, or opened from Users itself - same pattern as Manage volumes).
  const { state } = useLocation()
  const backTo = (state as { from?: { to: string } } | null)?.from?.to ?? '/users'
  const { data: user } = useUser(name)
  const { data: userProfile } = useUserProfile(name)
  const { data: grants = [] } = useEffectiveGrants(name)
  // server status for the rename gate (rename only while the lab is stopped)
  const { data: hero } = useServerHero(name)
  const [form] = Form.useForm()
  const [groups, setGroups] = useState<string[]>([])
  const [tab, setTab] = useState('profile')
  const [removeOpen, setRemoveOpen] = useState(false)
  const [pw, setPw] = useState('')
  const [renameTo, setRenameTo] = useState(name)
  // keep the rename field in sync when the target changes (incl. after a rename
  // navigates to /users/{newName})
  useEffect(() => { setRenameTo(name) }, [name])

  // the platform-configured admin (JUPYTERHUB_ADMIN_USERNAME, from the live shell; mock
  // falls back to the fixture): always admin + authorised, never removable.
  const isBuiltinAdmin = name === (adminUser() || PLATFORM.admin)
  // rename is admin-only, never for the built-in admin, and only while the user's
  // server is stopped (offline) - renaming a running container would orphan it
  const canRename = role === 'admin' && !isBuiltinAdmin
  const serverStopped = hero?.status === 'offline'
  const serverRunning = hero?.status === 'active' || hero?.status === 'idle' || hero?.status === 'spawning'
  // effective admin includes the hook-promoted admin whose persistent row is False
  const userIsAdmin = isAdminUser(name, !!user?.admin)
  // dependent controls react to the LIVE admin toggle, not the saved state, so
  // flipping Administrator updates them at once (before undefined: saved value)
  const watchedAdmin = Form.useWatch('admin', form)
  const liveAdmin = watchedAdmin ?? userIsAdmin

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
    if (userProfile) form.setFieldsValue({ first: userProfile.firstName, last: userProfile.lastName, email: userProfile.email, forcePw: !!userProfile.mustChangePassword })
  }, [userProfile, form])

  const save = async () => {
    try {
      const v = await form.validateFields()
      // validate in both modes; the mock demo should gate on the same rules, not
      // "save" invalid data
      if (isMock()) {
        mockSuccess(`Saved ${name}`)
        navigate(backTo)
        return
      }
      await saveUserProfile(name, { firstName: v.first ?? '', lastName: v.last ?? '', email: v.email ?? '' })
      const effAdmin = isAdminUser(name, !!user?.admin)
      if (!isBuiltinAdmin && user && !!v.admin !== effAdmin) await setAdmin(name, !!v.admin)
      // admins are always authorised -> the switch is hidden for them; only persist for non-admins
      if (!isBuiltinAdmin && !effAdmin && user && !!v.authorized !== user.authorized) await setUserAuthorization(name, !!v.authorized)
      if (pw) await setUserPassword(name, pw)
      // applied AFTER any password set so the gate sticks (a password change clears it)
      if (!isBuiltinAdmin && user && !!v.forcePw !== !!userProfile?.mustChangePassword) await setForcePasswordChange(name, !!v.forcePw)
      const before = new Set(user?.groups ?? [])
      const after = new Set(groups)
      for (const g of groups) if (!before.has(g)) await addMember(g, name)
      for (const g of user?.groups ?? []) if (!after.has(g)) await removeMember(g, name)
      setPw('')
      // ops surfaced per-write success toasts; return to the list on success
      navigate(backTo)
    } catch {
      /* ops surfaced the error - stay on the form */
    }
  }

  // Rename: confirm first (it is collateral-heavy), then go to the renamed
  // profile. The confirm spells out that the account moves but volumes do NOT.
  const doRename = () => {
    const target = renameTo.trim()
    Modal.confirm({
      title: `Rename ${name} to ${target}?`,
      okText: 'Rename',
      okButtonProps: { danger: true },
      content:
        'The account, group memberships, authorisation and password move to the new name - '
        + 'the user signs in with the new name from now on. Their existing volumes '
        + '(home, workspace, cache) stay attached to the OLD name and are NOT migrated; '
        + 'move them across separately.',
      onOk: async () => {
        await renameUser(name, target)
        if (!isMock()) navigate(`/users/${encodeURIComponent(target)}`, { state })
      },
    })
  }

  const profile = (
    <Form form={form} key={name} layout="vertical" initialValues={{ username: name, first: '', last: '', email: '', admin: false, authorized: false, forcePw: false }}>
      {isBuiltinAdmin && (
        <div style={{ marginBottom: 16 }}>
          <Notice type="warning">
            <span><b>Built-in admin account.</b> Admin role and authorisation are set by the platform; this account cannot be de-authorised or removed.</span>
          </Notice>
        </div>
      )}
      {/* Username + attached Rename action (design-language input-with-action
          pattern, like Change password / Generate). Admin-only, and only while the
          server is stopped; the field itself stays read-only otherwise. */}
      <Form.Item label="Username" extra={canRename ? "Renaming detaches the user's volumes - migrate them separately" : undefined}>
        <Space.Compact style={{ width: '100%' }}>
          <Input value={renameTo} onChange={(e) => setRenameTo(e.target.value)} disabled={!canRename || !serverStopped} />
          <Button
            onClick={doRename}
            disabled={!canRename || !serverStopped || !renameTo.trim() || renameTo.trim() === name}
            title={
              !canRename
                ? (isBuiltinAdmin ? 'The built-in admin account cannot be renamed' : 'Only admins can rename users')
                : !serverStopped
                  ? "Stop the user's server before renaming"
                  : 'Rename this user'
            }
          >
            Rename
          </Button>
        </Space.Compact>
      </Form.Item>
      <Form.Item label="First name" name="first"><Input /></Form.Item>
      <Form.Item label="Last name" name="last"><Input /></Form.Item>
      <Form.Item label="Email" name="email"><Input /></Form.Item>
      <Form.Item label="Change password" extra="Leave blank to keep, or generate one">
        <Space.Compact style={{ width: '100%' }}>
          <Input className="doh-mono" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="Leave blank to keep" />
          <Button onClick={() => setPw(genPassword())}>Generate</Button>
        </Space.Compact>
      </Form.Item>
      {!isBuiltinAdmin && <Form.Item label="Administrator" name="admin" valuePropName="checked"><Switch /></Form.Item>}
      {/* admins are always authorised -> the switch yields to a note the moment admin is toggled on */}
      {!isBuiltinAdmin && (liveAdmin
        ? <div style={{ marginBottom: 16 }}><Notice type="info">Administrators are authorised automatically.</Notice></div>
        : <Form.Item label="Authorised" name="authorized" valuePropName="checked"><Switch /></Form.Item>)}
      {/* admins can always spawn -> the force-password gate is meaningless for
          them; the control hides the moment admin is toggled on (like Authorised) */}
      {!isBuiltinAdmin && !liveAdmin && (
        <Form.Item label="Force password change on next login" name="forcePw" valuePropName="checked">
          {/* native hover tooltip on the control itself (antd Switch forwards
              `title` to its button) - not a Form.Item `tooltip` (?) icon */}
          <Switch title="The user cannot start their server until they set a new password" />
        </Form.Item>
      )}
    </Form>
  )

  const groupsTab = (
    <div>
      <GroupPicker value={groups} onChange={setGroups} />

      <div className="doh-section-title">Effective Policies</div>
      <div className="doh-page-sub" style={{ marginBottom: 12 }}>The policy resolved across this user's groups - each grant cites the group that won.</div>
      {grants.map((g) => (
        <div className="doh-grant" key={g.key}>
          <span className="doh-g-ic"><Icon name={g.key as 'gpu'} size={16} /></span>
          <div>
            {g.label}
            <div className="doh-g-from">from {g.from}</div>
          </div>
          <span className="doh-g-val">{g.value}</span>
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
          destructive={isBuiltinAdmin ? undefined : <Button danger icon={<Icon name="close" size={14} />} onClick={() => setRemoveOpen(true)}>Remove User</Button>}
          onCancel={() => navigate(backTo)}
          onSave={save}
        />
      </Card>
      <RemoveUserModal
        name={name}
        open={removeOpen}
        serverRunning={serverRunning}
        onClose={() => setRemoveOpen(false)}
        onRemoved={() => navigate(backTo)}
      />
    </>
  )
}
