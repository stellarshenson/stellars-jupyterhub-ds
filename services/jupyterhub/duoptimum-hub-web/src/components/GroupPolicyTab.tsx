/* The complete group-policy form - the nine real sections, each a header switch
 * that folds its body (off = ignored at spawn, data persists). Faithful to the
 * hub's admin Configure-Group modal: env vars + volume mounts + API-key creds are
 * editable tables, GPU is all-or-per-device (real host inventory), Docker carries
 * the full limited quota set + privileged, Memory/CPU/Downloads/Sudo their real
 * controls. Reads the group's stored flat config and emits an updated flat config
 * on every change (the parent PUTs it; the hub coerces + validates). */
import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Alert, Button, Checkbox, Input, InputNumber, Modal, Radio, Select, Switch, Table, Tooltip } from 'antd'
import { Icon } from './Icon'
import type { IconKey } from './Icon'
import { useTotalResources } from '../hooks/queries'
import { gpuSupported } from '../app/capabilities'
import { notify } from '../services/actions'
import type { GroupConfig, PolicyConfig, VolumeMode } from '../services/types'

// the standard shared volume's fixed mountpoint (mirrors policy/base.py SHARED_MOUNTPOINT);
// the volume itself is resolved by label at spawn, never stored by name
const SHARED_MOUNTPOINT = '/mnt/shared'
const MODE_OPTIONS = [{ value: 'rw', label: 'Read-Write' }, { value: 'ro', label: 'Read' }]

interface EnvVar { name: string; value: string; desc: string }
interface ApiCred { slot?: string; a: string; b: string }
interface VolMount { volume: string; mountpoint: string; mode: VolumeMode }

// Parse an uploaded key file into pool credentials - one credential per non-blank line.
// single: the whole trimmed line is the API key. pair: "id,secret" or "id secret" (comma or
// whitespace separated) -> id + secret. Lines that do not match the mode are counted skipped.
function parseApiKeysFile(text: string, mode: 'single' | 'pair'): { creds: ApiCred[]; skipped: number } {
  const creds: ApiCred[] = []
  let skipped = 0
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim()
    if (!line) continue
    if (mode === 'single') {
      creds.push({ a: line, b: '' })
    } else {
      const parts = line.split(line.includes(',') ? ',' : /\s+/).map((s) => s.trim()).filter(Boolean)
      if (parts.length === 2) creds.push({ a: parts[0], b: parts[1] })
      else skipped++
    }
  }
  return { creds, skipped }
}

function Section({ icon, title, on, onToggle, children }: { icon: IconKey; title: string; on: boolean; onToggle: (v: boolean) => void; children: ReactNode }) {
  return (
    <div className={on ? 'doh-pol-sec' : 'doh-pol-sec collapsed'}>
      <div className="doh-pol-head">
        <Switch size="small" checked={on} onChange={onToggle} />
        <Icon name={icon} size={15} />
        <span className="doh-pol-title">{title}</span>
      </div>
      {on && <div className="doh-pol-body">{children}</div>}
    </div>
  )
}

function CheckRow({ checked, onChange, label, desc }: { checked: boolean; onChange: (v: boolean) => void; label: string; desc: string }) {
  return (
    <div className="doh-pol-check">
      <Checkbox checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <div>
        <div>{label}</div>
        <div className="desc">{desc}</div>
      </div>
    </div>
  )
}

export function GroupPolicyTab({ cfg, onChange }: { cfg?: GroupConfig; onChange?: (config: PolicyConfig) => void }) {
  // CURRENTLY-available host GPUs (shared with the Home resource bar) - empty when GPU
  // is off, none are present, or the gpuinfo sidecar is disconnected. The list reflects
  // live availability, so saving re-syncs the grant to the real devices (see the
  // gpu_device_ids reconcile below)
  const { data: resources } = useTotalResources()
  const gpuDevices = resources?.gpuDevices ?? []
  // the standard shared volume exists on this host (label-resolved by the hub); when
  // absent the standard-mount controls are disabled (grant has no effect at spawn).
  // name = the resolved docker volume; description = its hub.volume.description label
  const sharedVolExists = !!cfg?.sharedVolume?.exists
  const sharedName = cfg?.sharedVolume?.name ?? ''
  const sharedDesc = cfg?.sharedVolume?.description ?? ''

  const [on, setOn] = useState<Record<string, boolean>>({})
  const [envVars, setEnvVars] = useState<EnvVar[]>([])
  const [gpuAll, setGpuAll] = useState(true)
  const [gpuIds, setGpuIds] = useState<string[]>([])
  const [memGB, setMemGB] = useState<number | null>(null)
  const [memSwap, setMemSwap] = useState(false)
  const [cpuCores, setCpuCores] = useState<number | null>(null)
  const [dStd, setDStd] = useState(false) // standard (raw socket) vs limited (proxy); limited is the default when the section is on
  const [dPriv, setDPriv] = useState(false)
  const [dq, setDq] = useState({ maxContainers: 10, maxVolumes: 10, maxNetworks: 3, maxStorage: 50, cpuCap: 2, memCap: 8 })
  const [dFlags, setDFlags] = useState({ dangerous: false, composeEnabled: true, composeOverride: true, hubNetwork: true })
  const [volMounts, setVolMounts] = useState<VolMount[]>([])
  const [sharedAllow, setSharedAllow] = useState(false)
  const [sharedMode, setSharedMode] = useState<VolumeMode>('rw')
  const [apiMode, setApiMode] = useState<'' | 'single' | 'pair'>('')
  const [apiVarKey, setApiVarKey] = useState('')
  const [apiVarId, setApiVarId] = useState('')
  const [apiVarSecret, setApiVarSecret] = useState('')
  const [apiCreds, setApiCreds] = useState<ApiCred[]>([])
  const [downloadsAllow, setDownloadsAllow] = useState(true)
  const [sudoEnable, setSudoEnable] = useState(true)

  // seed every control from the group's stored flat config when it loads
  useEffect(() => {
    const c = cfg?.config
    if (!c) return
    setOn({
      env_vars: !!c.env_vars_active,
      gpu: !!c.gpu_access,
      mem: !!c.mem_limit_enabled,
      cpu: !!c.cpu_limit_enabled,
      docker: !!c.docker_active,
      volume_mounts: !!c.volume_mounts_active,
      api_keys: !!c.api_keys_pool?.enabled,
      downloads: !!c.downloads_active,
      sudo: !!c.sudo_active,
    })
    setEnvVars((c.env_vars ?? []).map((e) => ({ name: e.name, value: e.value, desc: e.description ?? '' })))
    const gpuIdsSeed = (c.gpu_device_ids ?? []).map(String)
    // default all-GPUs only when no specific devices are granted - never silently
    // widen a device-scoped group to all GPUs on load
    setGpuAll(c.gpu_all ?? gpuIdsSeed.length === 0)
    setGpuIds(gpuIdsSeed)
    setMemGB(c.mem_limit_gb ? c.mem_limit_gb : null)
    setMemSwap(!!c.mem_swap_disabled)
    setCpuCores(c.cpu_limit_cores ? c.cpu_limit_cores : null)
    setDStd(!!c.docker_access) // not-standard (incl. a legacy "no access" config) reads as limited, the default
    setDPriv(!!c.docker_privileged)
    setDq({
      maxContainers: c.docker_limited_max_containers ?? 10,
      maxVolumes: c.docker_limited_max_volumes ?? 10,
      maxNetworks: c.docker_limited_max_networks ?? 3,
      maxStorage: c.docker_limited_max_storage_gb ?? 50,
      cpuCap: c.docker_limited_cpu_cap_cores ?? 2,
      memCap: c.docker_limited_mem_cap_gb ?? 8,
    })
    setDFlags({
      dangerous: !!c.docker_limited_allow_dangerous_flags,
      composeEnabled: c.docker_limited_user_compose_project_enabled ?? true,
      composeOverride: c.docker_limited_user_compose_project_allow_override ?? true,
      hubNetwork: c.docker_limited_hub_network_access ?? true,
    })
    // standard shared mount: allow flag + access level. Legacy migration - the old
    // one-click quick-add stored the literal shared name as a custom mount at
    // /mnt/shared; fold any such row into the standard allow toggle so it shows as
    // the standard row (not a custom one) and re-saves without the stale name.
    const norm = (m: string) => '/' + (m || '').trim().replace(/\/+$/, '').replace(/^\/+/, '')
    const legacy = (c.volume_mounts ?? []).find((v) => norm(v.mountpoint) === SHARED_MOUNTPOINT)
    setSharedAllow(!!c.shared_mount_allow || !!legacy)
    setSharedMode((c.shared_mount_mode ?? legacy?.mode ?? 'rw') as VolumeMode)
    setVolMounts((c.volume_mounts ?? [])
      .filter((v) => norm(v.mountpoint) !== SHARED_MOUNTPOINT)
      .map((v) => ({ volume: v.volume, mountpoint: v.mountpoint, mode: (v.mode ?? 'rw') as VolumeMode })))
    const pool = c.api_keys_pool
    const mode = pool?.mode ?? ''
    setApiMode(mode)
    setApiVarKey(pool?.env_var_key ?? '')
    setApiVarId(pool?.env_var_id ?? '')
    setApiVarSecret(pool?.env_var_secret ?? '')
    setApiCreds((pool?.credentials ?? []).map((cr) => ({
      slot: cr.slot,
      a: mode === 'pair' ? (cr.id ?? '') : (cr.key ?? ''),
      b: cr.secret ?? '',
    })))
    setDownloadsAllow(c.downloads_allow ?? true)
    setSudoEnable(c.sudo_enable ?? true)
  }, [cfg])

  // emit the assembled flat config on every change - field names match the hub
  // policy registry exactly; the PUT coerces + validates, so unset/extra is safe
  useEffect(() => {
    if (!onChange) return
    const config: PolicyConfig = {
      env_vars_active: on.env_vars ?? false,
      env_vars: envVars.map((e) => ({ name: e.name, value: e.value, description: e.desc })),
      // when the platform has no GPU the section is hidden; never let a seeded
      // gpu_access:true round-trip invisibly through Save on a GPU-less host
      gpu_access: gpuSupported() ? (on.gpu ?? false) : false,
      gpu_all: gpuAll,
      // reconcile granted devices against what is CURRENTLY available: once the device
      // inventory has loaded, drop any granted id no longer present (sidecar down -> none,
      // or hardware changed) so saving re-syncs the grant to reality; while it is still
      // loading keep the stored grant untouched
      gpu_device_ids: resources === undefined
        ? gpuIds
        : gpuIds.filter((id) => (resources.gpuDevices ?? []).some((d) => d.index === id)),
      docker_active: on.docker ?? false,
      // section on = access granted; the radio only chooses how. Standard = raw
      // socket; otherwise limited (the default). Both false when the section is off.
      docker_access: (on.docker ?? false) && dStd,
      docker_limited: (on.docker ?? false) && !dStd,
      docker_privileged: dPriv,
      docker_limited_max_containers: dq.maxContainers,
      docker_limited_max_volumes: dq.maxVolumes,
      docker_limited_max_networks: dq.maxNetworks,
      docker_limited_max_storage_gb: dq.maxStorage,
      docker_limited_cpu_cap_cores: dq.cpuCap,
      docker_limited_mem_cap_gb: dq.memCap,
      docker_limited_allow_dangerous_flags: dFlags.dangerous,
      docker_limited_user_compose_project_enabled: dFlags.composeEnabled,
      docker_limited_user_compose_project_allow_override: dFlags.composeOverride,
      docker_limited_hub_network_access: dFlags.hubNetwork,
      cpu_limit_enabled: on.cpu ?? false,
      cpu_limit_cores: cpuCores ?? 0,
      mem_limit_enabled: on.mem ?? false,
      mem_limit_gb: memGB ?? 0,
      mem_swap_disabled: memSwap,
      sudo_active: on.sudo ?? false,
      sudo_enable: sudoEnable,
      downloads_active: on.downloads ?? false,
      downloads_allow: downloadsAllow,
      volume_mounts_active: on.volume_mounts ?? false,
      shared_mount_allow: sharedAllow,
      shared_mount_mode: sharedMode,
      volume_mounts: volMounts.map((v) => ({ volume: v.volume, mountpoint: v.mountpoint, mode: v.mode })),
      api_keys_pool: {
        enabled: on.api_keys ?? false,
        mode: apiMode,
        env_var_id: apiVarId,
        env_var_secret: apiVarSecret,
        env_var_key: apiVarKey,
        credentials: apiCreds.map((c) => (apiMode === 'pair'
          ? { slot: c.slot, id: c.a, secret: c.b }
          : { slot: c.slot, key: c.a })),
      },
    }
    onChange(config)
  }, [onChange, on, envVars, gpuAll, gpuIds, resources, memGB, memSwap, cpuCores, dStd, dPriv, dq, dFlags, volMounts, sharedAllow, sharedMode, apiMode, apiVarKey, apiVarId, apiVarSecret, apiCreds, downloadsAllow, sudoEnable])

  const toggle = (key: string) => (v: boolean) => setOn((e) => ({ ...e, [key]: v }))

  // import keys from a text file - a popup picks the file, validates immediately, then
  // the operator submits (append to the pool) or cancels; no export. importGen invalidates
  // any in-flight FileReader callback when the file is re-picked or the popup is closed/reopened
  // (a stale onload must never land in a fresh popup and import the wrong file's keys)
  const apiFileRef = useRef<HTMLInputElement>(null)
  const importGen = useRef(0)
  const [importOpen, setImportOpen] = useState(false)
  const [importName, setImportName] = useState('')
  const [importParsed, setImportParsed] = useState<{ creds: ApiCred[]; skipped: number } | null>(null)
  const [importError, setImportError] = useState('')
  const openImport = () => { importGen.current++; setImportName(''); setImportParsed(null); setImportError(''); setImportOpen(true) }
  const closeImport = () => { importGen.current++; setImportOpen(false); setImportName(''); setImportParsed(null); setImportError('') }
  const validateImport = (file: File) => {
    const mode = apiMode === 'pair' ? 'pair' : 'single'
    const gen = ++importGen.current
    setImportName(file.name)
    setImportParsed(null)
    setImportError('')
    const reader = new FileReader()
    reader.onerror = () => { if (gen === importGen.current) setImportError('the file could not be read') }
    reader.onload = () => {
      if (gen !== importGen.current) return
      const { creds, skipped } = parseApiKeysFile(String(reader.result), mode)
      if (!creds.length) {
        setImportError(mode === 'pair'
          ? 'no valid "id,secret" lines found'
          : 'no keys found - the file is empty or every line is blank')
        return
      }
      setImportParsed({ creds, skipped })
    }
    reader.readAsText(file)
  }
  const confirmImport = () => {
    if (!importParsed) return
    const { creds, skipped } = importParsed
    setApiCreds((p) => [...p, ...creds])
    notify.success(`Imported ${creds.length} key${creds.length === 1 ? '' : 's'}${skipped ? ` (${skipped} skipped)` : ''}`)
    closeImport()
  }

  return (
    <div style={{ border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-lg)', padding: '4px 16px' }}>
      {/* Environment variables */}
      <Section icon="code" title="Environment Variables" on={on.env_vars ?? false} onToggle={toggle('env_vars')}>
        <div className="doh-pol-hint">Set in members' containers. On a name clash across groups, the highest-priority group wins.</div>
        <Table<EnvVar>
          size="small"
          pagination={false}
          dataSource={envVars}
          rowKey={(_, i) => `env-${i}`}
          rowClassName={(_, i) => (i % 2 ? 'doh-row-alt' : '')}
          columns={[
            { title: 'Name', width: '30%', render: (_, r, i) => <Input size="small" className="doh-mono" value={r.name} placeholder="MY_VAR" onChange={(e) => setEnvVars((p) => p.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} /> },
            { title: 'Value', width: '30%', render: (_, r, i) => <Input size="small" value={r.value} onChange={(e) => setEnvVars((p) => p.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))} /> },
            { title: 'Description', render: (_, r, i) => <Input size="small" value={r.desc} onChange={(e) => setEnvVars((p) => p.map((x, j) => (j === i ? { ...x, desc: e.target.value } : x)))} /> },
            { title: '', width: 40, render: (_, __, i) => <span style={{ cursor: 'pointer', color: 'var(--color-text-subtle)' }} onClick={() => setEnvVars((p) => p.filter((_, j) => j !== i))}><Icon name="close" size={14} /></span> },
          ]}
        />
        <Button size="small" icon={<Icon name="plus" size={13} />} style={{ marginTop: 8 }} onClick={() => setEnvVars((p) => [...p, { name: '', value: '', desc: '' }])}>Add Variable</Button>
      </Section>

      {/* GPU - only when the platform has GPU */}
      {gpuSupported() && (
      <Section icon="gpu" title="GPU Access" on={on.gpu ?? false} onToggle={toggle('gpu')}>
        <div className="doh-pol-hint">Gives members the selected GPU devices in their containers.</div>
        <Checkbox checked={gpuAll} onChange={(e) => setGpuAll(e.target.checked)}>All GPUs</Checkbox>
        <div className="desc doh-pol-hint" style={{ margin: '2px 0 8px 24px' }}>Deselect to choose specific devices below.</div>
        <div style={{ marginLeft: 24, display: gpuAll ? 'none' : 'block' }}>
          {gpuDevices.length === 0 ? (
            <div className="doh-pol-hint">No GPUs detected on this host.</div>
          ) : (
            gpuDevices.map((g) => (
              <div key={g.index} style={{ padding: '3px 0' }}>
                <Checkbox checked={gpuIds.includes(g.index)} onChange={(e) => setGpuIds((p) => (e.target.checked ? [...p, g.index] : p.filter((x) => x !== g.index)))}>
                  GPU {g.index}: {g.name}{g.memoryMb ? ` (${Math.round(g.memoryMb / 1024)} GB)` : ''}
                </Checkbox>
              </div>
            ))
          )}
        </div>
      </Section>
      )}

      {/* Memory */}
      <Section icon="memory" title="Memory" on={on.mem ?? false} onToggle={toggle('mem')}>
        <div className="doh-pol-hint">Caps container memory. Across a member's groups the largest limit wins.</div>
        <InputNumber<number> value={memGB} onChange={(v) => setMemGB(v)} min={0.1} step={0.1} addonAfter="GB" style={{ width: 160 }} />
        <div style={{ marginTop: 10 }}>
          <CheckRow checked={memSwap} onChange={setMemSwap} label="Disable swap (hard cap)" desc="OOM-killed at the limit instead of spilling to disk swap" />
        </div>
      </Section>

      {/* CPU */}
      <Section icon="cpu" title="CPU" on={on.cpu ?? false} onToggle={toggle('cpu')}>
        <div className="doh-pol-hint">Caps container CPU. Largest limit across groups wins; rounded up to whole cores, minimum one.</div>
        <InputNumber<number> value={cpuCores} onChange={(v) => setCpuCores(v)} min={0.1} step={0.1} addonAfter="cores" style={{ width: 180 }} />
      </Section>

      {/* Docker */}
      <Section icon="box" title="Docker Access" on={on.docker ?? false} onToggle={toggle('docker')}>
        <div className="doh-pol-hint">Across groups the most permissive wins. Standard supersedes Limited; Privileged is orthogonal.</div>
        <Radio.Group
          value={dStd ? 'std' : 'limited'}
          onChange={(e) => setDStd((e.target.value as string) === 'std')}
          style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 4 }}
        >
          <Radio value="std">
            Standard Docker access
            <div className="desc">Mounts the raw /var/run/docker.sock - sees all containers, no quota. For trusted users.</div>
          </Radio>
          <Radio value="limited">
            Limited Docker access
            <div className="desc">Per-user filtered socket: users manage only their own containers, up to a quota.</div>
          </Radio>
        </Radio.Group>
        {!dStd && (
          <div style={{ marginLeft: 24, marginTop: 8 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, maxWidth: 560 }}>
              {([['maxContainers', 'Max containers'], ['maxVolumes', 'Max volumes'], ['maxNetworks', 'Max networks'], ['maxStorage', 'Max storage (GB)'], ['cpuCap', 'CPU cap (cores)'], ['memCap', 'Memory cap (GB)']] as const).map(([k, label]) => (
                <div key={k}>
                  <div className="doh-pol-field-label">{label}</div>
                  <InputNumber<number> value={dq[k]} onChange={(v) => setDq((p) => ({ ...p, [k]: v ?? 0 }))} min={0} step={k === 'cpuCap' ? 0.5 : 1} style={{ width: '100%' }} />
                </div>
              ))}
            </div>
            <div style={{ marginTop: 8 }}>
              <CheckRow checked={dFlags.dangerous} onChange={(v) => setDFlags((p) => ({ ...p, dangerous: v }))} label="Allow dangerous Docker flags" desc="Bypass the proxy safety filter for host bind mounts, host namespaces, added capabilities and device passthrough." />
              <CheckRow checked={dFlags.composeEnabled} onChange={(v) => setDFlags((p) => ({ ...p, composeEnabled: v }))} label="Enforce per-user compose project" desc="Group each user's docker run containers under their own compose project." />
              <CheckRow checked={dFlags.composeOverride} onChange={(v) => setDFlags((p) => ({ ...p, composeOverride: v }))} label="Allow override of compose project" desc="Respect a project name the user supplies via docker compose -p." />
              <CheckRow checked={dFlags.hubNetwork} onChange={(v) => setDFlags((p) => ({ ...p, hubNetwork: v }))} label="Access hub network" desc="Reach hub services and other containers by DNS on the hub's docker network." />
            </div>
          </div>
        )}
        <CheckRow checked={dPriv} onChange={setDPriv} label="Privileged Docker (root)" desc="Runs the user container with --privileged (kernel-root inside the container). Orthogonal to the access mode." />
      </Section>

      {/* Volume mounts */}
      <Section icon="disk" title="Volume Mounts" on={on.volume_mounts ?? false} onToggle={toggle('volume_mounts')}>
        {/* Standard shared volume: a fixed row, granted by a toggle + access level.
           The volume is resolved by label at spawn (never a saved name), so a rename
           never strands the group. Disabled when the host has no shared volume. */}
        <div className="doh-pol-field-label">Standard shared volume</div>
        <div className="doh-pol-hint">{sharedDesc || `The platform shared volume mounted at ${SHARED_MOUNTPOINT}.`} Resolved by label at spawn, so a rename never strands the group.</div>
        <div className="doh-row" style={{ gap: 12, alignItems: 'center', marginBottom: 4 }}>
          {/* disabled when the host has no shared volume - but never strand an existing
             grant: if it is already allowed, keep it un-checkable so the admin can revoke it */}
          <Checkbox checked={sharedAllow} disabled={!sharedVolExists && !sharedAllow} onChange={(e) => setSharedAllow(e.target.checked)}>Grant</Checkbox>
          {/* show the RESOLVED volume name -> its fixed mountpoint (the name is never stored
             in the group config, only displayed here, so the operator sees what backs the mount) */}
          <span><span className="doh-mono">{sharedName || '—'}</span> <span className="doh-muted">→</span> <span className="doh-mono">{SHARED_MOUNTPOINT}</span></span>
          <Select<VolumeMode> size="small" value={sharedMode} disabled={!sharedAllow || !sharedVolExists} onChange={setSharedMode} options={MODE_OPTIONS} style={{ width: 150 }} />
          {!sharedVolExists && <span className="doh-muted" style={{ fontSize: 12 }}>no shared volume on this host - unavailable</span>}
        </div>

        <div className="doh-pol-field-label" style={{ marginTop: 12 }}>Additional mounts</div>
        <div className="doh-pol-hint">Mount more named Docker volumes into members' containers. Mountpoints must be absolute, outside protected paths, and not {SHARED_MOUNTPOINT} (use the toggle above); a missing volume is created on first spawn.</div>
        <Table<VolMount>
          size="small"
          pagination={false}
          dataSource={volMounts}
          rowKey={(_, i) => `vol-${i}`}
          rowClassName={(_, i) => (i % 2 ? 'doh-row-alt' : '')}
          columns={[
            { title: 'Volume', width: '38%', render: (_, r, i) => <Input size="small" className="doh-mono" value={r.volume} placeholder="my_volume" onChange={(e) => setVolMounts((p) => p.map((x, j) => (j === i ? { ...x, volume: e.target.value } : x)))} /> },
            { title: 'Mountpoint', render: (_, r, i) => <Input size="small" className="doh-mono" value={r.mountpoint} placeholder="/mnt/…" onChange={(e) => setVolMounts((p) => p.map((x, j) => (j === i ? { ...x, mountpoint: e.target.value } : x)))} /> },
            { title: 'Access', width: 150, render: (_, r, i) => <Select<VolumeMode> size="small" value={r.mode} onChange={(v) => setVolMounts((p) => p.map((x, j) => (j === i ? { ...x, mode: v } : x)))} options={MODE_OPTIONS} style={{ width: 138 }} /> },
            { title: '', width: 40, render: (_, __, i) => <span style={{ cursor: 'pointer', color: 'var(--color-text-subtle)' }} onClick={() => setVolMounts((p) => p.filter((_, j) => j !== i))}><Icon name="close" size={14} /></span> },
          ]}
        />
        <Button size="small" icon={<Icon name="plus" size={13} />} style={{ marginTop: 8 }} onClick={() => setVolMounts((p) => [...p, { volume: '', mountpoint: '', mode: 'rw' }])}>Add Mount</Button>
      </Section>

      {/* API keys pool */}
      <Section icon="key" title="API Keys Pool" on={on.api_keys ?? false} onToggle={toggle('api_keys')}>
        <div className="doh-pol-hint">Hands out one credential per running container so no two members share a key. Keys return to the pool on stop.</div>
        <div className="doh-pol-field-label">Credential type</div>
        <Select<'' | 'single' | 'pair'>
          value={apiMode}
          onChange={setApiMode}
          style={{ maxWidth: 320 }}
          options={[{ value: '', label: '- select -' }, { value: 'single', label: 'Single API Key' }, { value: 'pair', label: 'Key ID + Key Secret Pair' }]}
        />
        {apiMode === 'single' && (
          <div style={{ marginTop: 10, maxWidth: 320 }}>
            <div className="doh-pol-field-label">API key variable name</div>
            <Input className="doh-mono" value={apiVarKey} onChange={(e) => setApiVarKey(e.target.value)} placeholder="OPENAI_API_KEY" />
          </div>
        )}
        {apiMode === 'pair' && (
          <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, maxWidth: 480 }}>
            <div><div className="doh-pol-field-label">Key ID variable name</div><Input className="doh-mono" value={apiVarId} onChange={(e) => setApiVarId(e.target.value)} placeholder="AWS_ACCESS_KEY_ID" /></div>
            <div><div className="doh-pol-field-label">Key secret variable name</div><Input className="doh-mono" value={apiVarSecret} onChange={(e) => setApiVarSecret(e.target.value)} placeholder="AWS_SECRET_ACCESS_KEY" /></div>
          </div>
        )}
        {apiMode && (
          <>
            <Table<ApiCred>
              size="small"
              style={{ marginTop: 12 }}
              pagination={false}
              dataSource={apiCreds}
              rowKey={(_, i) => `cred-${i}`}
              rowClassName={(_, i) => (i % 2 ? 'doh-row-alt' : '')}
              columns={[
                { title: apiMode === 'pair' ? 'Key ID' : 'API Key', render: (_, r, i) => <Input size="small" className="doh-mono" value={r.a} onChange={(e) => setApiCreds((p) => p.map((x, j) => (j === i ? { ...x, a: e.target.value } : x)))} /> },
                ...(apiMode === 'pair' ? [{ title: 'Key Secret', render: (_: unknown, r: ApiCred, i: number) => <Input size="small" className="doh-mono" value={r.b} onChange={(e) => setApiCreds((p) => p.map((x, j) => (j === i ? { ...x, b: e.target.value } : x)))} /> }] : []),
                { title: '', width: 40, render: (_, __, i) => <span style={{ cursor: 'pointer', color: 'var(--color-text-subtle)' }} onClick={() => setApiCreds((p) => p.filter((_, j) => j !== i))}><Icon name="close" size={14} /></span> },
              ]}
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <Tooltip title="Add an empty row to enter one credential by hand">
                <Button size="small" icon={<Icon name="plus" size={13} />} onClick={() => setApiCreds((p) => [...p, { a: '', b: '' }])}>Add Key</Button>
              </Tooltip>
              <Tooltip title="Import credentials from a text file - one per line">
                <Button size="small" icon={<Icon name="upload" size={13} />} onClick={openImport}>Import Keys</Button>
              </Tooltip>
            </div>
            <Modal
              open={importOpen}
              title="Import API keys"
              onCancel={closeImport}
              onOk={confirmImport}
              okText={importParsed ? `Import ${importParsed.creds.length} key${importParsed.creds.length === 1 ? '' : 's'}` : 'Import'}
              okButtonProps={{ disabled: !importParsed }}
              destroyOnHidden
            >
              <div className="doh-pol-hint" style={{ marginBottom: 12 }}>
                {apiMode === 'pair'
                  ? 'Upload a text file with one "id,secret" per line (comma or whitespace separated). Blank lines are ignored.'
                  : 'Upload a text file with one API key per line. Blank lines are ignored.'}
              </div>
              <Button icon={<Icon name="upload" size={13} />} onClick={() => apiFileRef.current?.click()}>{importName || 'Choose file'}</Button>
              <input
                ref={apiFileRef}
                type="file"
                accept=".txt,.csv,.env,.keys,text/*"
                style={{ display: 'none' }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) validateImport(f); e.target.value = '' }}
              />
              {importError && <Alert type="error" showIcon style={{ marginTop: 12 }} message={`Import failed: ${importError}`} />}
              {importParsed && (
                <Alert
                  type="success"
                  showIcon
                  style={{ marginTop: 12 }}
                  message={`${importParsed.creds.length} valid key${importParsed.creds.length === 1 ? '' : 's'} ready${importParsed.skipped ? ` - ${importParsed.skipped} line${importParsed.skipped === 1 ? '' : 's'} skipped (bad format)` : ''}`}
                />
              )}
            </Modal>
          </>
        )}
      </Section>

      {/* Downloads */}
      <Section icon="download" title="File Downloads" on={on.downloads ?? false} onToggle={toggle('downloads')}>
        <div className="doh-pol-hint">Allow or block members downloading files out of their lab through the browser. Best-effort - does not stop terminal or kernel transfers.</div>
        <div className="doh-row"><Switch size="small" checked={downloadsAllow} onChange={setDownloadsAllow} /><span>Allow downloads for members</span></div>
      </Section>

      {/* Sudo */}
      <Section icon="shield" title="Sudo Access" on={on.sudo ?? false} onToggle={toggle('sudo')}>
        <div className="doh-pol-hint">Grant or deny members root via sudo inside their lab - needed to install system packages.</div>
        <div className="doh-row"><Switch size="small" checked={sudoEnable} onChange={setSudoEnable} /><span>Enable sudo for members</span></div>
      </Section>
    </div>
  )
}
