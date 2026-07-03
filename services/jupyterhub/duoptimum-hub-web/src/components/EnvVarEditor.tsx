/* Shared environment-variable editor - a name/value/description table + Add button.
 * Extracted from the group policy tab so the per-user Environment tab reuses the exact
 * same control. When `reserved` is supplied it flags reserved/invalid/duplicate names
 * live (error status + tooltip); the backend enforces the same rules on save regardless. */
import { Button, Input, Table, Tooltip } from 'antd'
import { Icon } from './Icon'
import { envNameError } from '../lib/envVars'
import type { EnvReserved } from '../lib/envVars'

export interface EnvVar { name: string; value: string; desc: string }

export function EnvVarEditor({ value, onChange, reserved }: {
  value: EnvVar[]
  onChange: (next: EnvVar[]) => void
  reserved?: EnvReserved
}) {
  const allNames = value.map((v) => v.name)
  const setRow = (i: number, patch: Partial<EnvVar>) => onChange(value.map((x, j) => (j === i ? { ...x, ...patch } : x)))
  return (
    <>
      <Table<EnvVar>
        size="small"
        pagination={false}
        dataSource={value}
        rowKey={(_, i) => `env-${i}`}
        rowClassName={(_, i) => ((i ?? 0) % 2 ? 'doh-row-alt' : '')}
        columns={[
          {
            title: 'Name',
            width: '30%',
            render: (_, r, i) => {
              const err = envNameError(r.name, allNames, reserved)
              const input = <Input size="small" className="doh-mono" status={err ? 'error' : undefined} value={r.name} placeholder="MY_VAR" onChange={(e) => setRow(i, { name: e.target.value })} />
              return err ? <Tooltip title={err}>{input}</Tooltip> : input
            },
          },
          { title: 'Value', width: '30%', render: (_, r, i) => <Input size="small" value={r.value} onChange={(e) => setRow(i, { value: e.target.value })} /> },
          { title: 'Description', render: (_, r, i) => <Input size="small" value={r.desc} onChange={(e) => setRow(i, { desc: e.target.value })} /> },
          { title: '', width: 40, render: (_, __, i) => <span style={{ cursor: 'pointer', color: 'var(--color-text-subtle)' }} onClick={() => onChange(value.filter((_, j) => j !== i))}><Icon name="close" size={14} /></span> },
        ]}
      />
      <Button size="small" icon={<Icon name="plus" size={13} />} style={{ marginTop: 8 }} onClick={() => onChange([...value, { name: '', value: '', desc: '' }])}>Add Variable</Button>
    </>
  )
}
