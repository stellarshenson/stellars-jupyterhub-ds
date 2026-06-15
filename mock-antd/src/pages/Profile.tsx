/* Profile - self-service for both roles. Own name / email / password only;
 * username is read-only and the admin-only controls are absent. */
import { Card, Form, Input } from 'antd'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { useRole } from '../app/RoleContext'
import { mockSuccess } from '../services/actions'

export default function Profile() {
  const { role } = useRole()
  const navigate = useNavigate()
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
          <Form.Item label="New password" name="password" extra="Leave blank to keep your current password">
            <Input.Password placeholder="••••••••" />
          </Form.Item>
        </Form>
        <FormFooter onCancel={() => navigate(-1)} onSave={() => mockSuccess('Profile saved')} />
      </Card>
    </>
  )
}
