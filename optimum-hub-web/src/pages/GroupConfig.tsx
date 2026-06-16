/* Configure group - full tabbed screen (General / Policy / Members), symmetric
 * with Configure user. General is metadata; Policy is the complete nine-section
 * policy form (GroupPolicyTab) bound to the real flat config; Members is a
 * typeahead at scale. Policy JSON downloads from / uploads into the live editor. */
import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, Tabs } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { Combo } from '../components/Combo'
import { Icon } from '../components/Icon'
import { Notice } from '../components/Notice'
import { GroupPolicyTab } from '../components/GroupPolicyTab'
import { useGroupConfig, useGroups, useUserCorpus } from '../hooks/queries'
import { isMock } from '../services/dataMode'
import { mockSuccess, notify } from '../services/actions'
import { addMember, deleteGroup, removeMember, reorderGroups, saveGroupConfig } from '../services/ops'
import type { PolicyConfig } from '../services/types'

export default function GroupConfig() {
  const { name = '' } = useParams()
  const navigate = useNavigate()
  const { data: cfg } = useGroupConfig(name)
  const { data: allGroups = [] } = useGroups()
  const { data: corpus = [] } = useUserCorpus()
  const [form] = Form.useForm()

  // The Groups list orders by priority descending (top = highest = rank 1). Show
  // this group's POSITION (1-based rank) here so the number matches the list,
  // not the raw stored priority (which counts the other way).
  const ordered = useMemo(() => [...allGroups].sort((a, b) => b.priority - a.priority), [allGroups])
  const curIndex = ordered.findIndex((g) => g.name === name)
  const curPos = curIndex >= 0 ? curIndex + 1 : 1
  const total = ordered.length || 1
  const [members, setMembers] = useState<string[]>([])
  const [tab, setTab] = useState('general')
  // live editor config (emitted by GroupPolicyTab); `override` re-seeds the editor
  // from an uploaded policy file so the controls visibly reflect the upload
  const [policyCfg, setPolicyCfg] = useState<PolicyConfig | null>(null)
  const [override, setOverride] = useState<PolicyConfig | null>(null)
  const [uploaded, setUploaded] = useState(false)

  // seed members + general fields once the config loads. antd reads initialValues
  // only at mount, so push the late-arriving values into the form imperatively -
  // otherwise the key-remount races the async data and leaves the fields blank.
  useEffect(() => {
    if (cfg) {
      setMembers(cfg.members)
      const idx = ordered.findIndex((g) => g.name === cfg.name)
      form.setFieldsValue({ name: cfg.name, description: cfg.description, priority: idx >= 0 ? idx + 1 : 1 })
    }
  }, [cfg, ordered, form])

  const save = async () => {
    if (isMock()) {
      mockSuccess(`Saved ${name}`)
      navigate('/groups')
      return
    }
    try {
      const v = await form.validateFields()
      await saveGroupConfig(name, v.description ?? '', policyCfg ?? cfg?.config)
      // v.priority is the 1-based POSITION; if it changed, move the group there
      // and renormalise the whole list to contiguous priorities (top = highest),
      // mirroring the Groups list's set-position so both stay consistent.
      if (curIndex >= 0 && v.priority != null && Math.round(v.priority) !== curPos) {
        const to = Math.max(0, Math.min(ordered.length - 1, Math.round(v.priority) - 1))
        const next = [...ordered]
        const [item] = next.splice(curIndex, 1)
        next.splice(to, 0, item)
        await reorderGroups(next.map((g, i) => ({ name: g.name, priority: next.length - i })))
      }
      const before = new Set(cfg?.members ?? [])
      const after = new Set(members)
      for (const u of members) if (!before.has(u)) await addMember(name, u)
      for (const u of cfg?.members ?? []) if (!after.has(u)) await removeMember(name, u)
      // ops surfaced per-write success toasts; return to the list on success
      navigate('/groups')
    } catch {
      /* ops surfaced the error - stay on the form */
    }
  }

  const removeGroup = async () => {
    await deleteGroup(name)
    if (!isMock()) navigate('/groups')
  }

  // client-side export of the live editor config (falls back to the stored config)
  const downloadPolicy = () => {
    const data = JSON.stringify(policyCfg ?? cfg?.config ?? {}, null, 2)
    const url = URL.createObjectURL(new Blob([data], { type: 'application/json' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `${name}.policy.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  // parse an uploaded policy file and re-seed the editor (Save still PUTs it)
  const uploadPolicy = (file: File) => {
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result)) as PolicyConfig
        setOverride(parsed)
        setUploaded(true)
      } catch {
        notify.error('Could not parse policy file - expected JSON')
      }
    }
    reader.readAsText(file)
  }

  // editor reads the uploaded override when present, else the stored config
  const editorCfg = override && cfg ? { ...cfg, config: override } : cfg

  const general = (
    <Form form={form} key={cfg ? `g-${cfg.name}` : 'loading'} layout="vertical" initialValues={{ name: cfg?.name, description: cfg?.description, priority: curPos }}>
      <Form.Item label="Name" name="name"><Input /></Form.Item>
      <Form.Item label="Description" name="description"><Input.TextArea rows={2} /></Form.Item>
      <Form.Item label="Position" name="priority" extra={`Rank in the Groups list - 1 = top, wins when policies conflict (1-${total})`}><InputNumber min={1} max={total} /></Form.Item>
    </Form>
  )

  const policy = (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <Button icon={<Icon name="download" size={14} />} onClick={downloadPolicy}>Download policy</Button>
        <label className="ant-btn ant-btn-default" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
          <Icon name="upload" size={14} />Upload policy
          <input
            type="file"
            accept="application/json,.json"
            style={{ display: 'none' }}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadPolicy(f); e.target.value = '' }}
          />
        </label>
      </div>
      {uploaded && <Notice type="success">Policy loaded into the editor - review, then Save to apply.</Notice>}
      <div className="oh-pol-hint" style={{ margin: '12px 0' }}>Toggle a section on to grant it to every member; off keeps its data but the hub ignores it at spawn.</div>
      <GroupPolicyTab cfg={editorCfg} onChange={setPolicyCfg} />
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
            { key: 'policy', label: 'Policy', children: policy, forceRender: true },
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
