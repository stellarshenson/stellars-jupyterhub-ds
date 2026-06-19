/* Bulk result - the credentials surface once: username / generated password /
 * groups, with a real client-side download. Credentials arrive via router state
 * from the bulk-add step; falling back to a sample set when opened directly. */
import { Button, Card, Table } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Icon } from '../components/Icon'
import { Notice } from '../components/Notice'

interface Cred {
  username: string
  password: string
  groups: string
}

const SAMPLE: Cred[] = [
  { username: 'jdoe', password: 'cyan-spawn-kernel-42', groups: 'students, nlp' },
  { username: 'asmith', password: 'amber-vector-lab-17', groups: 'students' },
  { username: 'mkovac', password: 'matrix-staple-tensor-08', groups: 'gpu, vision-lab' },
  { username: 'lwang', password: 'horse-battery-cyan-93', groups: 'research' },
]

interface BulkState {
  creds?: Array<{ username: string; password: string }>
  groups?: string
  requested?: number
}

function downloadTxt(rows: Cred[]) {
  const body = rows.map((r) => `${r.username}\t${r.password}\t${r.groups}`).join('\n')
  const blob = new Blob([`username\tpassword\tgroups\n${body}\n`], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'credentials.txt'
  a.click()
  URL.revokeObjectURL(url)
}

export default function BulkResult() {
  const navigate = useNavigate()
  const state = (useLocation().state ?? {}) as BulkState
  const groups = state.groups ?? ''
  const rows: Cred[] = state.creds ? state.creds.map((c) => ({ username: c.username, password: c.password, groups })) : SAMPLE
  const requested = state.requested ?? rows.length

  return (
    <>
      <PageHeader title="Bulk Result" sub="Credentials surface once - download them now" />
      <Card style={{ maxWidth: 820 }}>
        <Notice type="success">{rows.length} of {requested} users created. Passwords are shown once and cannot be retrieved later.</Notice>
        <Table<Cred>
          rowKey="username"
          style={{ marginTop: 12 }}
          pagination={false}
          rowClassName={(_, i) => (i % 2 ? 'doh-row-alt' : '')}
          dataSource={rows}
          columns={[
            { title: 'Username', dataIndex: 'username' },
            { title: 'Password', dataIndex: 'password', render: (v) => <span className="doh-mono">{v}</span> },
            { title: 'Groups', dataIndex: 'groups', render: (v) => <span className="doh-muted">{v}</span> },
          ]}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <Button type="primary" icon={<Icon name="download" size={14} />} onClick={() => downloadTxt(rows)}>Download .txt</Button>
          <Button onClick={() => navigate('/users')}>Done</Button>
        </div>
      </Card>
    </>
  )
}
