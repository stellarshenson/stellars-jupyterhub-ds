/* Profile - self-service for both roles. Own name / email / password only;
 * username is read-only and the admin-only controls are absent. Name + email are
 * display-only (the hub stores neither); the password change is real. */
import { useState } from 'react'
import { Button, Card, Form, Input, Space } from 'antd'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { useRole } from '../app/RoleContext'
import { isMock } from '../services/dataMode'
import { mockSuccess, notify } from '../services/actions'
import { changeOwnPassword } from '../services/ops'
import { genPassword } from '../lib/password'

export default function Profile() {
  const { role, username, live } = useRole()
  const navigate = useNavigate()
  const [pw, setPw] = useState('')
  const [cur, setCur] = useState('')
  const me = live
    ? { username, first: '', last: '', email: '' }
    : role === 'admin'
      ? { username: 'admin', first: 'Platform', last: 'Admin', email: 'admin@lab.stellars-tech.eu' }
      : { username: 'alice', first: 'Alice', last: 'Nowak', email: 'alice@lab.stellars-tech.eu' }

  const save = async () => {
    if (isMock()) {
      mockSuccess('Profile saved')
      return
    }
    if (!pw) {
      notify.info('Name and email are display-only; nothing to save')
      return
    }
    try {
      await changeOwnPassword(cur, pw)
      setPw('')
      setCur('')
    } catch {
      /* ops surfaced the error */
    }
  }

  return (
    <>
      <PageHeader title="Profile" sub="Edit your own name, email and password" />
      <Card style={{ maxWidth: 640 }}>
        <Form layout="vertical" initialValues={me} key={me.username}>
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
              <Input className="oh-mono" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="••••••••" />
              <Button onClick={() => setPw(genPassword())}>Generate</Button>
            </Space.Compact>
          </Form.Item>
        </Form>
        <FormFooter onCancel={() => navigate(-1)} onSave={save} />
      </Card>
    </>
  )
}
