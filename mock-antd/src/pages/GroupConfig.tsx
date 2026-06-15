/* Configure group - full tabbed screen (General / Policy / Members). Policy is
 * nine enable-toggle sections; it downloads / uploads as validated JSON. Members
 * is a typeahead add plus the member list. All writes mocked. */
import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, Switch, Tabs } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { Combo } from '../components/Combo'
import { Icon } from '../components/Icon'
import { Notice } from '../components/Notice'
import { useGroupConfig, useUserCorpus } from '../hooks/queries'
import { mockAction, mockSuccess } from '../services/actions'

export default function GroupConfig() {
  const { name = '' } = useParams()
  const navigate = useNavigate()
  const { data: cfg } = useGroupConfig(name)
  const { data: corpus = [] } = useUserCorpus()
  const [members, setMembers] = useState<string[]>([])
  const [tab, setTab] = useState('general')
  const [uploaded, setUploaded] = useState(false)

  useEffect(() => {
    if (corpus.length) setMembers(corpus.slice(0, 6))
  }, [corpus])

  const general = (
    <Form key={cfg ? `g-${cfg.name}` : 'loading'} layout="vertical" initialValues={{ name: cfg?.name, description: cfg?.description, priority: cfg?.priority }}>
      <Form.Item label="Name" name="name"><Input /></Form.Item>
      <Form.Item label="Description" name="description"><Input.TextArea rows={2} /></Form.Item>
      <Form.Item label="Priority" name="priority" extra="Higher priority wins on conflict"><InputNumber min={1} /></Form.Item>
    </Form>
  )

  const policy = (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <Button icon={<Icon name="download" size={14} />} onClick={() => mockAction(`Downloaded ${name} policy as JSON`)}>Download JSON</Button>
        <Button icon={<Icon name="upload" size={14} />} onClick={() => { setUploaded(true); mockAction('Uploaded and validated policy') }}>Upload JSON</Button>
      </div>
      {uploaded && <Notice type="success">Policy validated and applied - screen refreshed.</Notice>}
      <div style={{ marginTop: 12, border: '1px solid var(--color-border-subtle)', borderRadius: 8, overflow: 'hidden' }}>
        {cfg?.sections.map((s) => (
          <div key={s.key} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', borderBottom: '1px solid var(--color-border-subtle)' }}>
            <span className="oh-g-ic" style={{ width: 24, height: 24 }}><Icon name={(s.key === 'mem' ? 'memory' : s.key === 'volume_mounts' ? 'disk' : s.key === 'api_keys' ? 'key' : s.key === 'docker' ? 'box' : s.key === 'sudo' ? 'shield' : s.key === 'downloads' ? 'download' : s.key === 'env_vars' ? 'code' : s.key) as 'gpu'} size={14} /></span>
            <div style={{ minWidth: 120, fontWeight: 500 }}>{s.label}</div>
            <div className="oh-muted" style={{ flex: 1 }}>{s.summary}</div>
            <Switch size="small" defaultChecked={s.enabled} onChange={(v) => mockAction(`${v ? 'Enabled' : 'Disabled'} ${s.label} policy`)} />
          </div>
        ))}
      </div>
    </div>
  )

  const membersTab = (
    <div>
      <div style={{ marginBottom: 8, color: 'var(--color-text-muted)', fontSize: 13 }}>Members <span className="oh-muted">· {members.length}</span></div>
      <Combo corpus={corpus} value={members} onChange={setMembers} placeholder="Add members…" />
    </div>
  )

  const widths: Record<string, number> = { general: 640, policy: 820, members: 760 }

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
          destructive={<Button danger icon={<Icon name="close" size={14} />} onClick={() => mockAction(`Delete group ${name} - removes all members`)}>Delete group</Button>}
          onCancel={() => navigate('/groups')}
          onSave={() => mockSuccess(`Saved ${name}`)}
        />
      </Card>
    </>
  )
}
