/* Bulk add users - paste usernames (one per line), configure once for the batch,
 * then land on the result screen. Every password is auto-generated. */
import { useState } from 'react'
import { Card, Form, Input, Switch } from 'antd'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { GroupPicker } from '../components/GroupPicker'

export default function BulkUsers() {
  const navigate = useNavigate()
  const [groups, setGroups] = useState<string[]>([])

  return (
    <>
      <PageHeader title="Bulk add users" sub="Paste usernames and configure the batch once - passwords are auto-generated" />
      <Card style={{ maxWidth: 820 }}>
        <Form layout="vertical" initialValues={{ authorize: true, require: true }}>
          <Form.Item label="Usernames" extra="One per line">
            <Input.TextArea rows={6} placeholder={'jdoe\nasmith\nmkovac'} />
          </Form.Item>
          <Form.Item label="Groups">
            <GroupPicker value={groups} onChange={setGroups} label="" />
          </Form.Item>
          <Form.Item label="Authorise now" name="authorize" valuePropName="checked"><Switch /></Form.Item>
          <Form.Item label="Require password change at first login" name="require" valuePropName="checked"><Switch /></Form.Item>
        </Form>
        <FormFooter onCancel={() => navigate('/users')} onSave={() => navigate('/users/bulk/result')} saveLabel="Create" />
      </Card>
    </>
  )
}
