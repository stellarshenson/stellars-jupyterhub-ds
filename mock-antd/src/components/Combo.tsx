/* Typeahead membership picker - a port of the live hub's admin chip editor, here
 * a native antd multi-select (type to filter, click to add, x to remove). Used by
 * every group/member picker. */
import { Select } from 'antd'

export function Combo({
  corpus,
  value,
  onChange,
  placeholder,
}: {
  corpus: string[]
  value: string[]
  onChange: (v: string[]) => void
  placeholder?: string
}) {
  return (
    <Select
      mode="multiple"
      allowClear
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      style={{ width: '100%' }}
      optionFilterProp="label"
      options={corpus.map((c) => ({ label: c, value: c }))}
    />
  )
}
