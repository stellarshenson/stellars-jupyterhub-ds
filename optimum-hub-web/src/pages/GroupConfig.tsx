/* Configure group - full tabbed screen (General / Policy / Members), symmetric
 * with Configure user. General is metadata; Policy is the complete nine-section
 * policy form (GroupPolicyTab); Members is a typeahead at scale. Policy JSON can
 * be downloaded / uploaded. All writes mocked. */
import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, Tabs } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { Combo } from '../components/Combo'
import { Icon } from '../components/Icon'
import { Notice } from '../components/Notice'
import { GroupPolicyTab } from '../components/GroupPolicyTab'
import { useGroupConfig, useUserCorpus } from '../hooks/queries'
import { isMock } from '../services/dataMode'
import { mockAction, mockSuccess } from '../services/actions'
import { addMember, deleteGroup, removeMember, reorderGroups, saveGroupConfig } from '../services/ops'

export default function GroupConfig() {
  const { name = '' } = useParams()
  const navigate = useNavigate()
  const { data: cfg } = useGroupConfig(name)
  const { data: corpus = [] } = useUserCorpus()
  const [form] = Form.useForm()
  const [members, setMembers] = useState<string[]>([])
  const [tab, setTab] = useState('general')
  const [uploaded, setUploaded] = useState(false)

  // seed the member list from the group's real membership once it loads
  useEffect(() => {
    if (cfg) setMembers(cfg.members)
  }, [cfg])

  const save = async () => {
    if (isMock()) {
      mockSuccess(`Saved ${name}`)
      return
    }
    try {
      const v = await form.validateFields()
      await saveGroupConfig(name, v.description ?? '')
      if (cfg && v.priority != null && v.priority !== cfg.priority) {
        await reorderGroups([{ name, priority: v.priority }])
      }
      const before = new Set(cfg?.members ?? [])
      const after = new Set(members)
      for (const u of members) if (!before.has(u)) await addMember(name, u)
      for (const u of cfg?.members ?? []) if (!after.has(u)) await removeMember(name, u)
    } catch {
      /* ops surfaced the error */
    }
  }

  const removeGroup = async () => {
    await deleteGroup(name)
    if (!isMock()) navigate('/groups')
  }

  const general = (
    <Form form={form} key={cfg ? `g-${cfg.name}` : 'loading'} layout="vertical" initialValues={{ name: cfg?.name, description: cfg?.description, priority: cfg?.priority }}>
      <Form.Item label="Name" name="name"><Input /></Form.Item>
      <Form.Item label="Description" name="description"><Input.TextArea rows={2} /></Form.Item>
      <Form.Item label="Priority" name="priority" extra="Lower number wins when policies conflict across a user's groups"><InputNumber min={1} /></Form.Item>
    </Form>
  )

  const policy = (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <Button icon={<Icon name="download" size={14} />} onClick={() => mockAction(`Downloaded ${name}.policy.json`)}>Download policy</Button>
        <Button icon={<Icon name="upload" size={14} />} onClick={() => { setUploaded(true); mockAction('Policy validated and applied') }}>Upload policy</Button>
      </div>
      {uploaded && <Notice type="success">Policy validated and applied - screen refreshed.</Notice>}
      <div className="oh-pol-hint" style={{ margin: '12px 0' }}>Toggle a section on to grant it to every member; off keeps its data but the hub ignores it at spawn.</div>
      <GroupPolicyTab cfg={cfg} />
    </div>
  )

  const membersTab = (
    <div>
      <div style={{ marginBottom: 8, color: 'var(--color-text-muted)', fontSize: 13 }}>Members <span className="oh-muted">· {members.length}</span></div>
      <Combo corpus={corpus} value={members} onChange={setMembers} placeholder="Add a member…" />
    </div>
  )

  const widths: Record<string, number> = { general: 640, policy: 900, members: 760 }

  return (
    <>
      <PageHeader title={`Configure ${name}`} sub="General, policy and membership" />
      <Card style={{ maxWidth: widths[tab], transition: 'max-width .18s ease' }}>
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            { key: 'general', label: 'General', children: general },
            { key: 'policy', label: 'Policy', children: policy },
            { key: 'members', label: 'Members', children: membersTab },
          ]}
        />
        <FormFooter
          destructive={<Button danger icon={<Icon name="close" size={14} />} onClick={removeGroup}>Delete group</Button>}
          onCancel={() => navigate('/groups')}
          onSave={save}
        />
      </Card>
    </>
  )
}
