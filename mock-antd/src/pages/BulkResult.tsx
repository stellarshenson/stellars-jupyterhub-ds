/* Bulk result - the credentials surface once: username / generated password /
 * groups, with a download. Mirrors the current credentials-file behaviour. */
import { Button, Card, Table } from 'antd'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Icon } from '../components/Icon'
import { Notice } from '../components/Notice'
import { mockAction } from '../services/actions'

interface Cred {
  username: string
  password: string
  groups: string
}

const ROWS: Cred[] = [
  { username: 'jdoe', password: 'cyan-spawn-kernel-42', groups: 'students, nlp' },
  { username: 'asmith', password: 'amber-vector-lab-17', groups: 'students' },
  { username: 'mkovac', password: 'matrix-staple-tensor-08', groups: 'gpu, vision-lab' },
  { username: 'lwang', password: 'horse-battery-cyan-93', groups: 'research' },
]

export default function BulkResult() {
  const navigate = useNavigate()
  return (
    <>
      <PageHeader title="Bulk result" sub="Credentials surface once - download them now" />
      <Card style={{ maxWidth: 820 }}>
        <Notice type="success">4 of 4 users created. Passwords are shown once and cannot be retrieved later.</Notice>
        <Table<Cred>
          rowKey="username"
          style={{ marginTop: 12 }}
          pagination={false}
          dataSource={ROWS}
          columns={[
            { title: 'Username', dataIndex: 'username' },
            { title: 'Password', dataIndex: 'password', render: (v) => <span className="oh-mono">{v}</span> },
            { title: 'Groups', dataIndex: 'groups', render: (v) => <span className="oh-muted">{v}</span> },
          ]}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <Button type="primary" icon={<Icon name="download" size={14} />} onClick={() => mockAction('Downloaded credentials.txt')}>Download .txt</Button>
          <Button onClick={() => navigate('/users')}>Done</Button>
        </div>
      </Card>
    </>
  )
}
