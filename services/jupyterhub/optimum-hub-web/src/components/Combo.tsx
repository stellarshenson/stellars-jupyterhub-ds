/* Membership picker - an autocomplete input that adds a chip on selecting a
 * suggestion from the corpus, with removable chips below. Suggestions appear only
 * while typing; removing a chip never reopens a popup. Used by every group/member
 * picker. */
import { useState } from 'react'
import { AutoComplete, Tag } from 'antd'

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
  const [text, setText] = useState('')

  const add = (name: string) => {
    const n = name.trim()
    if (n && corpus.includes(n) && !value.includes(n)) onChange([...value, n])
    setText('')
  }
  const remove = (name: string) => onChange(value.filter((v) => v !== name))

  const options = corpus
    .filter((c) => !value.includes(c) && c.toLowerCase().includes(text.toLowerCase()))
    .map((c) => ({ label: c, value: c }))

  return (
    <div>
      <AutoComplete
        style={{ width: '100%' }}
        value={text}
        options={options}
        onChange={setText}
        onSelect={add}
        placeholder={placeholder}
        filterOption={false}
        allowClear
      />
      {value.length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {value.map((v) => (
            <Tag key={v} closable onClose={(e) => { e.preventDefault(); remove(v) }} style={{ marginInlineEnd: 0 }}>
              {v}
            </Tag>
          ))}
        </div>
      )}
    </div>
  )
}
