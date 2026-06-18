/* The complete group-policy form - the nine real sections, each a header switch
 * that folds its body (off = ignored at spawn, data persists). Faithful to the
 * hub's admin Configure-Group modal: env vars + volume mounts + API-key creds are
 * editable tables, GPU is all-or-per-device (real host inventory), Docker carries
 * the full limited quota set + privileged, Memory/CPU/Downloads/Sudo their real
 * controls. Reads the group's stored flat config and emits an updated flat config
 * on every change (the parent PUTs it; the hub coerces + validates). */
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Button, Checkbox, Input, InputNumber, Radio, Select, Switch, Table } from 'antd'
import { Icon } from './Icon'
import type { IconKey } from './Icon'
import { useTotalResources } from '../hooks/queries'
import { gpuSupported } from '../app/capabilities'
import type { GroupConfig, PolicyConfig } from '../services/types'

interface EnvVar { name: string; value: string; desc: string }
interface ApiCred { slot?: string; a: string; b: string; desc: string }
interface VolMount { volume: string; mountpoint: string }

function Section({ icon, title, on, onToggle, children }: { icon: IconKey; title: string; on: boolean; onToggle: (v: boolean) => void; children: ReactNode }) {
  return (
    <div className={on ? 'oh-pol-sec' : 'oh-pol-sec collapsed'}>
      <div className="oh-pol-head">
        <Switch size="small" checked={on} onChange={onToggle} />
        <Icon name={icon} size={15} />
        <span className="oh-pol-title">{title}</span>
      </div>
      {on && <div className="oh-pol-body">{children}</div>}
    </div>
  )
}

function CheckRow({ checked, onChange, label, desc }: { checked: boolean; onChange: (v: boolean) => void; label: string; desc: string }) {
  return (
    <div className="oh-pol-check">
      <Checkbox checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <div>
        <div>{label}</div>
        <div className="desc">{desc}</div>
      </div>
    </div>
  )
}

export function GroupPolicyTab({ cfg, onChange }: { cfg?: GroupConfig; onChange?: (config: PolicyConfig) => void }) {
  // real host GPU inventory (shared cache with the Home resource bar); empty when
  // GPU is disabled or none are present -> the per-device list renders empty
  const { data: resources } = useTotalResources()
  const gpuDevices = resources?.gpuDevices ?? []

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
    setVolMounts((c.volume_mounts ?? []).map((v) => ({ volume: v.volume, mountpoint: v.mountpoint })))
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
      desc: cr.description ?? '',
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
      gpu_device_ids: gpuIds,
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
      volume_mounts: volMounts.map((v) => ({ volume: v.volume, mountpoint: v.mountpoint })),
      api_keys_pool: {
        enabled: on.api_keys ?? false,
        mode: apiMode,
        env_var_id: apiVarId,
        env_var_secret: apiVarSecret,
        env_var_key: apiVarKey,
        credentials: apiCreds.map((c) => (apiMode === 'pair'
          ? { slot: c.slot, id: c.a, secret: c.b, description: c.desc }
          : { slot: c.slot, key: c.a, description: c.desc })),
      },
    }
    onChange(config)
  }, [onChange, on, envVars, gpuAll, gpuIds, memGB, memSwap, cpuCores, dStd, dPriv, dq, dFlags, volMounts, apiMode, apiVarKey, apiVarId, apiVarSecret, apiCreds, downloadsAllow, sudoEnable])

  const toggle = (key: string) => (v: boolean) => setOn((e) => ({ ...e, [key]: v }))

  return (
    <div style={{ border: '1px solid var(--color-border-subtle)', borderRadius: 8, padding: '4px 16px' }}>
      {/* Environment variables */}
      <Section icon="code" title="Environment Variables" on={on.env_vars ?? false} onToggle={toggle('env_vars')}>
        <div className="oh-pol-hint">Set in members' containers. On a name clash across groups, the highest-priority group wins.</div>
        <Table<EnvVar>
          size="small"
          pagination={false}
          dataSource={envVars}
          rowKey={(_, i) => `env-${i}`}
          rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
          columns={[
            { title: 'Name', width: '30%', render: (_, r, i) => <Input size="small" className="oh-mono" value={r.name} placeholder="MY_VAR" onChange={(e) => setEnvVars((p) => p.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} /> },
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
        <div className="oh-pol-hint">Gives members the selected GPU devices in their containers.</div>
        <Checkbox checked={gpuAll} onChange={(e) => setGpuAll(e.target.checked)}>All GPUs</Checkbox>
        <div className="desc oh-pol-hint" style={{ margin: '2px 0 8px 24px' }}>Deselect to choose specific devices below.</div>
        <div style={{ marginLeft: 24, display: gpuAll ? 'none' : 'block' }}>
          {gpuDevices.length === 0 ? (
            <div className="oh-pol-hint">No GPUs detected on this host.</div>
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
        <div className="oh-pol-hint">Caps container memory. Across a member's groups the largest limit wins.</div>
        <InputNumber<number> value={memGB} onChange={(v) => setMemGB(v)} min={0.1} step={0.1} addonAfter="GB" style={{ width: 160 }} />
        <div style={{ marginTop: 10 }}>
          <CheckRow checked={memSwap} onChange={setMemSwap} label="Disable swap (hard cap)" desc="OOM-killed at the limit instead of spilling to disk swap" />
        </div>
      </Section>

      {/* CPU */}
      <Section icon="cpu" title="CPU" on={on.cpu ?? false} onToggle={toggle('cpu')}>
        <div className="oh-pol-hint">Caps container CPU. Largest limit across groups wins; rounded up to whole cores, minimum one.</div>
        <InputNumber<number> value={cpuCores} onChange={(v) => setCpuCores(v)} min={0.1} step={0.1} addonAfter="cores" style={{ width: 180 }} />
      </Section>

      {/* Docker */}
      <Section icon="box" title="Docker Access" on={on.docker ?? false} onToggle={toggle('docker')}>
        <div className="oh-pol-hint">Across groups the most permissive wins. Standard supersedes Limited; Privileged is orthogonal.</div>
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
                  <div className="oh-pol-field-label">{label}</div>
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
        <div className="oh-pol-hint">Mount named Docker volumes into members' containers. Mountpoints must be absolute and outside protected paths; a missing volume is created on first spawn.</div>
        <Table<VolMount>
          size="small"
          pagination={false}
          dataSource={volMounts}
          rowKey={(_, i) => `vol-${i}`}
          rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
          columns={[
            { title: 'Volume', width: '45%', render: (_, r, i) => <Input size="small" className="oh-mono" value={r.volume} placeholder="my_volume" onChange={(e) => setVolMounts((p) => p.map((x, j) => (j === i ? { ...x, volume: e.target.value } : x)))} /> },
            { title: 'Mountpoint', render: (_, r, i) => <Input size="small" className="oh-mono" value={r.mountpoint} placeholder="/mnt/…" onChange={(e) => setVolMounts((p) => p.map((x, j) => (j === i ? { ...x, mountpoint: e.target.value } : x)))} /> },
            { title: '', width: 40, render: (_, __, i) => <span style={{ cursor: 'pointer', color: 'var(--color-text-subtle)' }} onClick={() => setVolMounts((p) => p.filter((_, j) => j !== i))}><Icon name="close" size={14} /></span> },
          ]}
        />
        <Button size="small" icon={<Icon name="plus" size={13} />} style={{ marginTop: 8 }} onClick={() => setVolMounts((p) => [...p, { volume: '', mountpoint: '' }])}>Add Mount</Button>
      </Section>

      {/* API keys pool */}
      <Section icon="key" title="API Keys Pool" on={on.api_keys ?? false} onToggle={toggle('api_keys')}>
        <div className="oh-pol-hint">Hands out one credential per running container so no two members share a key. Keys return to the pool on stop.</div>
        <div className="oh-pol-field-label">Credential type</div>
        <Select<'' | 'single' | 'pair'>
          value={apiMode}
          onChange={setApiMode}
          style={{ maxWidth: 320 }}
          options={[{ value: '', label: '- select -' }, { value: 'single', label: 'Single API Key' }, { value: 'pair', label: 'Key ID + Key Secret Pair' }]}
        />
        {apiMode === 'single' && (
          <div style={{ marginTop: 10, maxWidth: 320 }}>
            <div className="oh-pol-field-label">API key variable name</div>
            <Input className="oh-mono" value={apiVarKey} onChange={(e) => setApiVarKey(e.target.value)} placeholder="OPENAI_API_KEY" />
          </div>
        )}
        {apiMode === 'pair' && (
          <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, maxWidth: 480 }}>
            <div><div className="oh-pol-field-label">Key ID variable name</div><Input className="oh-mono" value={apiVarId} onChange={(e) => setApiVarId(e.target.value)} placeholder="AWS_ACCESS_KEY_ID" /></div>
            <div><div className="oh-pol-field-label">Key secret variable name</div><Input className="oh-mono" value={apiVarSecret} onChange={(e) => setApiVarSecret(e.target.value)} placeholder="AWS_SECRET_ACCESS_KEY" /></div>
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
              rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
              columns={[
                { title: apiMode === 'pair' ? 'Key ID' : 'API Key', render: (_, r, i) => <Input size="small" className="oh-mono" value={r.a} onChange={(e) => setApiCreds((p) => p.map((x, j) => (j === i ? { ...x, a: e.target.value } : x)))} /> },
                ...(apiMode === 'pair' ? [{ title: 'Key Secret', render: (_: unknown, r: ApiCred, i: number) => <Input size="small" className="oh-mono" value={r.b} onChange={(e) => setApiCreds((p) => p.map((x, j) => (j === i ? { ...x, b: e.target.value } : x)))} /> }] : []),
                { title: 'Description', render: (_, r, i) => <Input size="small" value={r.desc} onChange={(e) => setApiCreds((p) => p.map((x, j) => (j === i ? { ...x, desc: e.target.value } : x)))} /> },
                { title: '', width: 40, render: (_, __, i) => <span style={{ cursor: 'pointer', color: 'var(--color-text-subtle)' }} onClick={() => setApiCreds((p) => p.filter((_, j) => j !== i))}><Icon name="close" size={14} /></span> },
              ]}
            />
            <Button size="small" icon={<Icon name="plus" size={13} />} style={{ marginTop: 8 }} onClick={() => setApiCreds((p) => [...p, { a: '', b: '', desc: '' }])}>Add Key</Button>
          </>
        )}
      </Section>

      {/* Downloads */}
      <Section icon="download" title="File Downloads" on={on.downloads ?? false} onToggle={toggle('downloads')}>
        <div className="oh-pol-hint">Allow or block members downloading files out of their lab through the browser. Best-effort - does not stop terminal or kernel transfers.</div>
        <div className="oh-row"><Switch size="small" checked={downloadsAllow} onChange={setDownloadsAllow} /><span>Allow downloads for members</span></div>
      </Section>

      {/* Sudo */}
      <Section icon="shield" title="Sudo Access" on={on.sudo ?? false} onToggle={toggle('sudo')}>
        <div className="oh-pol-hint">Grant or deny members root via sudo inside their lab - needed to install system packages.</div>
        <div className="oh-row"><Switch size="small" checked={sudoEnable} onChange={setSudoEnable} /><span>Enable sudo for members</span></div>
      </Section>
    </div>
  )
}
