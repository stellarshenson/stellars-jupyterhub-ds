/* Group import dialog: pick one or more JSON exports, validate every entry
 * BEFORE anything is written (missing name, duplicate within the selection,
 * a name that already exists on the hub, malformed file), then import only the
 * valid ones. Rejections are listed inline with their reason so the operator
 * sees exactly why a group could not be imported. */
import { useRef, useState } from 'react'
import { Button, Modal } from 'antd'
import { Notice } from './Notice'
import { Icon } from './Icon'
import { importGroups } from '../services/ops'
import type { ImportGroup } from '../services/ops'
import { fromPolicies } from '../lib/policyShape'
import type { PolicySection } from '../lib/policyShape'
import type { PolicyConfig } from '../services/types'

type Row = { name: string; source: string; ok: boolean; reason?: string; group?: ImportGroup }

// Parse one file into raw group entries, or an error string if it is not a
// JSON { groups: [...] } bundle (or a bare array).
async function readEntries(file: File): Promise<{ entries?: unknown[]; error?: string }> {
  try {
    const parsed = JSON.parse(await file.text())
    const list = Array.isArray(parsed) ? parsed : parsed?.groups
    if (!Array.isArray(list)) return { error: 'expected a { groups: [...] } bundle or an array' }
    return { entries: list }
  } catch {
    return { error: 'not valid JSON' }
  }
}

export function GroupImportModal({ open, existing, onClose }: { open: boolean; existing: string[]; onClose: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [rows, setRows] = useState<Row[] | null>(null)
  const [fileCount, setFileCount] = useState(0)
  const [busy, setBusy] = useState(false)

  const close = () => { setRows(null); setFileCount(0); setBusy(false); onClose() }

  const onFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    e.target.value = '' // let the same files be re-picked
    if (!files.length) return
    setFileCount(files.length)
    const out: Row[] = []
    const seen = new Set<string>()
    const taken = new Set(existing)
    for (const file of files) {
      const { entries, error } = await readEntries(file)
      if (error) { out.push({ name: file.name, source: file.name, ok: false, reason: error }); continue }
      for (const raw of entries!) {
        const g = raw as { name?: unknown; description?: unknown; policies?: unknown; config?: unknown }
        const name = typeof g.name === 'string' ? g.name.trim() : ''
        if (!name) { out.push({ name: '(unnamed)', source: file.name, ok: false, reason: 'missing group name' }); continue }
        let reason: string | undefined
        if (taken.has(name)) reason = 'a group with this name already exists'
        else if (seen.has(name)) reason = 'duplicated within the selected files'
        if (!reason) seen.add(name)
        const config = Array.isArray(g.policies) ? fromPolicies(g.policies as PolicySection[]) : ((g.config as PolicyConfig) ?? {})
        out.push({
          name,
          source: file.name,
          ok: !reason,
          reason,
          group: reason ? undefined : { name, description: typeof g.description === 'string' ? g.description : '', config },
        })
      }
    }
    setRows(out)
  }

  const valid = (rows ?? []).filter((r) => r.ok)
  const invalid = (rows ?? []).filter((r) => !r.ok)

  const doImport = async () => {
    const groups = valid.map((r) => r.group).filter((g): g is ImportGroup => !!g)
    if (!groups.length) return
    setBusy(true)
    try {
      await importGroups(groups) // owns its success/error toast + ['groups'] invalidation
      close()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      title="Import Groups"
      onCancel={close}
      footer={[
        <Button key="cancel" onClick={close}>Cancel</Button>,
        <Button key="import" type="primary" loading={busy} disabled={!valid.length} onClick={doImport}>
          {valid.length ? `Import ${valid.length} group${valid.length === 1 ? '' : 's'}` : 'Import'}
        </Button>,
      ]}
    >
      <Notice type="info">Select one or more JSON exports. Every group is validated before anything is written - duplicates and malformed entries are rejected with a reason.</Notice>
      <div style={{ marginTop: 12 }}>
        <input ref={fileRef} type="file" multiple accept=".json,application/json" style={{ display: 'none' }} onChange={onFiles} />
        <Button icon={<Icon name="download" size={14} />} onClick={() => fileRef.current?.click()}>Choose JSON File(s)…</Button>
        {fileCount > 0 && <span className="oh-muted" style={{ marginLeft: 8 }}>{fileCount} file{fileCount === 1 ? '' : 's'} selected</span>}
      </div>

      {valid.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <Notice type="success">{valid.length} group{valid.length === 1 ? '' : 's'} ready to import.</Notice>
          <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 12 }}>
            {valid.map((r) => <span key={`${r.source}:${r.name}`} className="oh-mono">{r.name}</span>)}
          </div>
        </div>
      )}

      {invalid.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <Notice type="error">{invalid.length} group{invalid.length === 1 ? '' : 's'} cannot be imported:</Notice>
          <div style={{ marginTop: 8 }}>
            {invalid.map((r, i) => (
              <div key={i} className="oh-row" style={{ gap: 8, padding: '3px 0' }}>
                <span className="oh-mono">{r.name}</span>
                <span className="oh-muted">- {r.reason}</span>
                <span className="oh-muted" style={{ marginLeft: 'auto', fontSize: 12 }}>{r.source}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  )
}
