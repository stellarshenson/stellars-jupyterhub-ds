/* New user - the create form. One password field pre-filled with a generated
 * value the admin can type over; groups via typeahead; authorise-now and
 * require-change switches. Create reuses the Configure-user field set in create
 * mode. */
import { useState } from 'react'
import { Button, Card, Form, Input, Space, Switch } from 'antd'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { GroupPicker } from '../components/GroupPicker'
import { mockSuccess } from '../services/actions'

const WORDS = ['correct', 'horse', 'battery', 'staple', 'amber', 'cyan', 'lab', 'spawn', 'kernel', 'matrix', 'vector', 'tensor']

function genPassword(): string {
  // deterministic-ish xkcd style from the current time (mock only)
  const t = Date.now()
  const pick = (n: number) => WORDS[(Math.floor(t / Math.pow(10, n)) + n) % WORDS.length]
  return `${pick(2)}-${pick(4)}-${pick(6)}-${pick(8)}`
}

export default function NewUser() {
  const navigate = useNavigate()
  const [groups, setGroups] = useState<string[]>([])
  const [pw, setPw] = useState(genPassword())

  return (
    <>
      <PageHeader title="New user" sub="Create an account and optionally authorise it now" />
      <Card style={{ maxWidth: 760 }}>
        <Form layout="vertical" initialValues={{ authorize: true, require: false }}>
          <Form.Item label="Username" name="username" rules={[{ required: true, message: 'Username is required' }]}>
            <Input placeholder="e.g. jdoe" />
          </Form.Item>
          <Form.Item label="Initial password" extra="Auto-generated - type to override">
            <Space.Compact style={{ width: '100%' }}>
              <Input className="oh-mono" value={pw} onChange={(e) => setPw(e.target.value)} />
              <Button onClick={() => setPw(genPassword())}>Generate</Button>
            </Space.Compact>
          </Form.Item>
          <Form.Item label="Groups">
            <GroupPicker value={groups} onChange={setGroups} label="" />
          </Form.Item>
          <Form.Item label="Authorise now" name="authorize" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label="Require password change at first login" name="require" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
        <FormFooter
          onCancel={() => navigate('/users')}
          onSave={() => {
            mockSuccess('User created')
            navigate('/users')
          }}
          saveLabel="Add user"
        />
      </Card>
    </>
  )
}
