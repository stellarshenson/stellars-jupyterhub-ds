/* New group - name + optional description. Policy is configured afterwards on the
 * group config screen. */
import { Card, Form, Input } from 'antd'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { createGroup } from '../services/ops'

export default function NewGroup() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const submit = async () => {
    const v = await form.validateFields().catch(() => null)
    if (!v) return
    try {
      await createGroup(v.name, v.description ?? '')
      // land on the new group's config screen so policy/members can be set right
      // away - the create form only takes name + description
      navigate(`/groups/${encodeURIComponent(v.name)}`)
    } catch {
      /* ops surfaced the error */
    }
  }
  return (
    <>
      <PageHeader title="New Group" sub="Create a group - set its policy after it exists" />
      <Card style={{ maxWidth: 640 }}>
        <Form form={form} layout="vertical">
          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, pattern: /^[a-zA-Z][a-zA-Z0-9_-]*$/, message: 'Letters, digits, _ and - ; starts with a letter' }]}
          >
            <Input placeholder="e.g. vision-lab" />
          </Form.Item>
          <Form.Item label="Description" name="description">
            <Input.TextArea rows={2} placeholder="What this group is for" />
          </Form.Item>
        </Form>
        <FormFooter onCancel={() => navigate('/groups')} onSave={submit} saveLabel="Create Group" />
      </Card>
    </>
  )
}
