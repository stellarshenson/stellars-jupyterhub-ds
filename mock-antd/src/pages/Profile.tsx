/* Profile - self-service for both roles. Own name / email / password only;
 * username is read-only and the admin-only controls are absent. */
import { useState } from 'react'
import { Button, Card, Form, Input, Space } from 'antd'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { useRole } from '../app/RoleContext'
import { mockSuccess } from '../services/actions'
import { genPassword } from '../lib/password'

export default function Profile() {
  const { role } = useRole()
  const navigate = useNavigate()
  const [pw, setPw] = useState('')
  const me = role === 'admin'
    ? { username: 'admin', first: 'Platform', last: 'Admin', email: 'admin@lab.stellars-tech.eu' }
    : { username: 'alice', first: 'Alice', last: 'Nowak', email: 'alice@lab.stellars-tech.eu' }

  return (
    <>
      <PageHeader title="Profile" sub="Edit your own name, email and password" />
      <Card style={{ maxWidth: 640 }}>
        <Form layout="vertical" initialValues={me}>
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
          <Form.Item label="New password" extra="Leave blank to keep your current password, or generate one">
            <Space.Compact style={{ width: '100%' }}>
              <Input className="oh-mono" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="••••••••" />
              <Button onClick={() => setPw(genPassword())}>Generate</Button>
            </Space.Compact>
          </Form.Item>
        </Form>
        <FormFooter onCancel={() => navigate(-1)} onSave={() => mockSuccess('Profile saved')} />
      </Card>
    </>
  )
}
