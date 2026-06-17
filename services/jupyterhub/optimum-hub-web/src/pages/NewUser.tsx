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
import { isMock } from '../services/dataMode'
import { addMember, setUserAuthorization, createUser, setUserPassword } from '../services/ops'
import { genPassword } from '../lib/password'

export default function NewUser() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [groups, setGroups] = useState<string[]>([])
  const [pw, setPw] = useState(genPassword())

  const submit = async () => {
    const v = await form.validateFields().catch(() => null)
    if (!v) return
    if (isMock()) {
      mockSuccess('User created')
      navigate('/users')
      return
    }
    try {
      await createUser(v.username) // creates + auto-authorises with a generated password
      if (pw) await setUserPassword(v.username, pw) // honour the password shown to the admin
      for (const g of groups) await addMember(g, v.username)
      if (!v.authorize) await setUserAuthorization(v.username, false) // create auto-authorises; turn it back off
      navigate('/users')
    } catch {
      /* ops already surfaced the error toast */
    }
  }

  return (
    <>
      <PageHeader title="New user" sub="Create an account and optionally authorise it now" />
      <Card style={{ maxWidth: 760 }}>
        <Form form={form} layout="vertical" initialValues={{ authorize: true }}>
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
        </Form>
        <FormFooter onCancel={() => navigate('/users')} onSave={submit} saveLabel="Add user" />
      </Card>
    </>
  )
}
