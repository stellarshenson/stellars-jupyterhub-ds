/* Profile - self-service for both roles. Own name / email / password only;
 * username is read-only and the admin-only controls are absent. Name + email
 * persist to the hub profile store; the password change is real. */
import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, Space } from 'antd'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { useRole } from '../app/RoleContext'
import { useUserProfile } from '../hooks/queries'
import { isMock } from '../services/dataMode'
import { mockSuccess } from '../services/actions'
import { changeOwnPassword, saveUserProfile } from '../services/ops'
import { genPassword } from '../lib/password'

export default function Profile() {
  const { username } = useRole()
  const navigate = useNavigate()
  const { data: profile } = useUserProfile(username)
  const [form] = Form.useForm()
  const [pw, setPw] = useState('')
  const [cur, setCur] = useState('')

  // React Query resolves after mount; push the profile into the form imperatively
  useEffect(() => {
    if (profile) form.setFieldsValue({ first: profile.firstName, last: profile.lastName, email: profile.email })
  }, [profile, form])

  const save = async () => {
    if (isMock()) {
      mockSuccess('Profile saved')
      return
    }
    try {
      const v = await form.validateFields()
      await saveUserProfile(username, { firstName: v.first ?? '', lastName: v.last ?? '', email: v.email ?? '' })
      if (pw) {
        await changeOwnPassword(cur, pw)
        setPw('')
        setCur('')
      }
    } catch {
      /* ops surfaced the error */
    }
  }

  return (
    <>
      <PageHeader title="Profile" sub="Edit your own name, email and password" />
      <Card style={{ maxWidth: 640 }}>
        <Form form={form} layout="vertical" initialValues={{ username, first: '', last: '', email: '' }} key={username}>
          <Form.Item label="Username" name="username" extra="Your username cannot be changed">
            <Input disabled />
          </Form.Item>
          <Form.Item label="First name" name="first">
            <Input />
          </Form.Item>
          <Form.Item label="Last name" name="last">
            <Input />
          </Form.Item>
          <Form.Item label="Email" name="email">
            <Input />
          </Form.Item>
          {pw && (
            <Form.Item label="Current password" extra="Required to change your password">
              <Input.Password value={cur} onChange={(e) => setCur(e.target.value)} placeholder="current password" autoComplete="current-password" />
            </Form.Item>
          )}
          <Form.Item label="New password" extra="Leave blank to keep your current password, or generate one">
            <Space.Compact style={{ width: '100%' }}>
              <Input className="doh-mono" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="••••••••" />
              <Button onClick={() => setPw(genPassword())}>Generate</Button>
            </Space.Compact>
          </Form.Item>
        </Form>
        <FormFooter onCancel={() => navigate(-1)} onSave={save} />
      </Card>
    </>
  )
}
