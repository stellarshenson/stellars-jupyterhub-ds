/* Renders the right antd control for a registry option (Segmented for exclusive
 * choices, Switch for boolean, Select for a dropdown, InputNumber for a number).
 * Generic so the options harness needs no per-option UI code. */
import { InputNumber, Segmented, Select, Switch } from 'antd'
import type { DisplayOption, PrefValue } from '../services/displayOptions'

export function OptionControl({ option, value, onChange }: {
  option: DisplayOption
  value: PrefValue
  onChange: (value: PrefValue) => void
}) {
  const c = option.control
  if (c.kind === 'switch') {
    return <Switch size="small" checked={!!value} onChange={(v) => onChange(v)} />
  }
  if (c.kind === 'select') {
    return <Select size="small" value={String(value)} options={c.choices} onChange={(v) => onChange(v)} style={{ minWidth: 200 }} />
  }
  if (c.kind === 'input') {
    return <InputNumber size="small" value={typeof value === 'number' ? value : undefined} onChange={(v) => onChange(v ?? 0)} />
  }
  // segmented: exclusive options
  return (
    <Segmented
      size="small"
      value={String(value)}
      options={(c.choices ?? []).map((o) => ({ label: o.label, value: o.value }))}
      onChange={(v) => onChange(v as string)}
    />
  )
}
