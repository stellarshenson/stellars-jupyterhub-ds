/* The complete group-policy form - the nine real sections, each a header switch
 * that folds its body (off = ignored at spawn, data persists). Faithful to the
 * hub's admin Configure-Group modal: env vars + volume mounts + API-key creds are
 * editable tables, GPU is all-or-per-device, Docker carries the full limited
 * quota set + privileged, Memory/CPU/Downloads/Sudo their real controls. All
 * writes mocked. */
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Button, Checkbox, Input, InputNumber, Select, Switch, Table } from 'antd'
import { Icon } from './Icon'
import type { IconKey } from './Icon'
import { mockAction } from '../services/actions'
import type { GroupConfig } from '../services/types'

const GPU_DEVICES = [
  { index: 0, name: 'NVIDIA A100-SXM4', mem: 40960 },
  { index: 1, name: 'NVIDIA A100-SXM4', mem: 40960 },
  { index: 2, name: 'NVIDIA RTX 6000 Ada', mem: 49140 },
]
const HOST_CPUS = 32

interface EnvVar { name: string; value: string; desc: string }
interface VolMount { volume: string; mountpoint: string }
interface ApiCred { a: string; b: string; desc: string }

function Section({ icon, title, on, onToggle, children }: { icon: IconKey; title: string; on: boolean; onToggle: (v: boolean) => void; children: ReactNode }) {
  return (
    <div className="oh-pol-sec">
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

export function GroupPolicyTab({ cfg }: { cfg?: GroupConfig }) {
  const [on, setOn] = useState<Record<string, boolean>>({})

  // section data (seeded so an enabled section reads as configured)
  const [envVars, setEnvVars] = useState<EnvVar[]>([{ name: 'HF_HOME', value: '/mnt/shared/hf', desc: 'HuggingFace cache' }, { name: 'WANDB_MODE', value: 'offline', desc: '' }])
  const [gpuAll, setGpuAll] = useState(true)
  const [gpuIds, setGpuIds] = useState<number[]>([])
  const [memGB, setMemGB] = useState<number | null>(32)
  const [memSwap, setMemSwap] = useState(false)
  const [cpuCores, setCpuCores] = useState<number | null>(8)
  const [dStd, setDStd] = useState(true)
  const [dLim, setDLim] = useState(false)
  const [dPriv, setDPriv] = useState(false)
  const [dq, setDq] = useState({ maxContainers: 10, maxVolumes: 10, maxNetworks: 3, maxStorage: 50, cpuCap: 2, memCap: 8 })
  const [dFlags, setDFlags] = useState({ dangerous: false, composeEnabled: true, composeOverride: true, hubNetwork: true })
  const [mounts, setMounts] = useState<VolMount[]>([{ volume: 'jupyterhub_shared', mountpoint: '/mnt/shared' }])
  const [apiMode, setApiMode] = useState<'' | 'single' | 'pair'>('pair')
  const [apiVarKey, setApiVarKey] = useState('')
  const [apiVarId, setApiVarId] = useState('OPENAI_ORG_ID')
  const [apiVarSecret, setApiVarSecret] = useState('OPENAI_API_KEY')
  const [apiCreds, setApiCreds] = useState<ApiCred[]>([{ a: 'org-3xK…', b: 'sk-live-…', desc: 'seat 1' }])
  const [downloadsAllow, setDownloadsAllow] = useState(true)
  const [sudoEnable, setSudoEnable] = useState(true)

  useEffect(() => {
    if (cfg) setOn(Object.fromEntries(cfg.sections.map((s) => [s.key, s.enabled])))
  }, [cfg])

  const toggle = (key: string, label: string) => (v: boolean) => {
    setOn((e) => ({ ...e, [key]: v }))
    mockAction(`${v ? 'Enabled' : 'Disabled'} ${label} policy`)
  }

  return (
    <div style={{ border: '1px solid var(--color-border-subtle)', borderRadius: 8, padding: '4px 16px' }}>
      {/* Environment variables */}
      <Section icon="code" title="Environment variables" on={on.env_vars ?? false} onToggle={toggle('env_vars', 'environment')}>
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
        <Button size="small" icon={<Icon name="plus" size={13} />} style={{ marginTop: 8 }} onClick={() => setEnvVars((p) => [...p, { name: '', value: '', desc: '' }])}>Add variable</Button>
      </Section>

      {/* GPU */}
      <Section icon="gpu" title="GPU access" on={on.gpu ?? false} onToggle={toggle('gpu', 'GPU')}>
        <div className="oh-pol-hint">Gives members the selected GPU devices in their containers.</div>
        <Checkbox checked={gpuAll} onChange={(e) => setGpuAll(e.target.checked)}>All GPUs</Checkbox>
        <div className="desc oh-pol-hint" style={{ margin: '2px 0 8px 24px' }}>Deselect to choose specific devices below.</div>
        <div style={{ marginLeft: 24, display: gpuAll ? 'none' : 'block' }}>
          {GPU_DEVICES.map((g) => (
            <div key={g.index} style={{ padding: '3px 0' }}>
              <Checkbox checked={gpuIds.includes(g.index)} onChange={(e) => setGpuIds((p) => (e.target.checked ? [...p, g.index] : p.filter((x) => x !== g.index)))}>
                GPU {g.index}: {g.name} ({g.mem} MB)
              </Checkbox>
            </div>
          ))}
        </div>
      </Section>

      {/* Memory */}
      <Section icon="memory" title="Memory" on={on.mem ?? false} onToggle={toggle('mem', 'memory')}>
        <div className="oh-pol-hint">Caps container memory. Across a member's groups the largest limit wins.</div>
        <InputNumber<number> value={memGB} onChange={(v) => setMemGB(v)} min={0.1} step={0.1} addonAfter="GB" style={{ width: 160 }} />
        <div style={{ marginTop: 10 }}>
          <CheckRow checked={memSwap} onChange={setMemSwap} label="Disable swap (hard cap)" desc="OOM-killed at the limit instead of spilling to disk swap" />
        </div>
      </Section>

      {/* CPU */}
      <Section icon="cpu" title="CPU" on={on.cpu ?? false} onToggle={toggle('cpu', 'CPU')}>
        <div className="oh-pol-hint">Caps container CPU. Largest limit across groups wins; rounded up to whole cores, minimum one.</div>
        <InputNumber<number> value={cpuCores} onChange={(v) => setCpuCores(v)} min={0.1} step={0.1} max={HOST_CPUS} addonAfter="cores" style={{ width: 180 }} />
        <div className="oh-pol-hint" style={{ marginTop: 4 }}>This host has {HOST_CPUS} cores available.</div>
      </Section>

      {/* Docker */}
      <Section icon="box" title="Docker access" on={on.docker ?? false} onToggle={toggle('docker', 'Docker')}>
        <div className="oh-pol-hint">Across groups the most permissive wins. Standard supersedes Limited; Privileged is orthogonal.</div>
        <CheckRow checked={dStd} onChange={setDStd} label="Standard Docker access" desc="Mounts the raw /var/run/docker.sock - sees all containers, no quota. For trusted users." />
        <CheckRow checked={dLim} onChange={setDLim} label="Limited Docker access" desc="Per-user filtered socket: users manage only their own containers, up to a quota. Mutually exclusive with Standard." />
        {dLim && (
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
      <Section icon="disk" title="Volume mounts" on={on.volume_mounts ?? false} onToggle={toggle('volume_mounts', 'volume mounts')}>
        <div className="oh-pol-hint">Mounts named Docker volumes into members' containers. System paths (/etc, /usr, /home, …) are rejected; use /mnt or /data.</div>
        <Table<VolMount>
          size="small"
          pagination={false}
          dataSource={mounts}
          rowKey={(_, i) => `vol-${i}`}
          rowClassName={(_, i) => (i % 2 ? 'oh-row-alt' : '')}
          columns={[
            { title: 'Volume name', width: '45%', render: (_, r, i) => <Input size="small" className="oh-mono" value={r.volume} onChange={(e) => setMounts((p) => p.map((x, j) => (j === i ? { ...x, volume: e.target.value } : x)))} /> },
            { title: 'Mountpoint', render: (_, r, i) => <Input size="small" className="oh-mono" value={r.mountpoint} placeholder="/mnt/data" onChange={(e) => setMounts((p) => p.map((x, j) => (j === i ? { ...x, mountpoint: e.target.value } : x)))} /> },
            { title: '', width: 40, render: (_, __, i) => <span style={{ cursor: 'pointer', color: 'var(--color-text-subtle)' }} onClick={() => setMounts((p) => p.filter((_, j) => j !== i))}><Icon name="close" size={14} /></span> },
          ]}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <Button size="small" icon={<Icon name="plus" size={13} />} onClick={() => setMounts((p) => [...p, { volume: '', mountpoint: '' }])}>Add volume</Button>
          <Button size="small" onClick={() => setMounts((p) => [...p, { volume: 'jupyterhub_shared', mountpoint: '/mnt/shared' }])}>Add shared volume</Button>
        </div>
      </Section>

      {/* API keys pool */}
      <Section icon="key" title="API keys pool" on={on.api_keys ?? false} onToggle={toggle('api_keys', 'API keys')}>
        <div className="oh-pol-hint">Hands out one credential per running container so no two members share a key. Keys return to the pool on stop.</div>
        <div className="oh-pol-field-label">Credential type</div>
        <Select<'' | 'single' | 'pair'>
          value={apiMode}
          onChange={setApiMode}
          style={{ maxWidth: 320 }}
          options={[{ value: '', label: '- select -' }, { value: 'single', label: 'Single API key' }, { value: 'pair', label: 'Key ID + Key secret pair' }]}
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
                { title: apiMode === 'pair' ? 'Key ID' : 'API key', render: (_, r, i) => <Input size="small" className="oh-mono" value={r.a} onChange={(e) => setApiCreds((p) => p.map((x, j) => (j === i ? { ...x, a: e.target.value } : x)))} /> },
                ...(apiMode === 'pair' ? [{ title: 'Key secret', render: (_: unknown, r: ApiCred, i: number) => <Input size="small" className="oh-mono" value={r.b} onChange={(e) => setApiCreds((p) => p.map((x, j) => (j === i ? { ...x, b: e.target.value } : x)))} /> }] : []),
                { title: 'Description', render: (_, r, i) => <Input size="small" value={r.desc} onChange={(e) => setApiCreds((p) => p.map((x, j) => (j === i ? { ...x, desc: e.target.value } : x)))} /> },
                { title: '', width: 40, render: (_, __, i) => <span style={{ cursor: 'pointer', color: 'var(--color-text-subtle)' }} onClick={() => setApiCreds((p) => p.filter((_, j) => j !== i))}><Icon name="close" size={14} /></span> },
              ]}
            />
            <Button size="small" icon={<Icon name="plus" size={13} />} style={{ marginTop: 8 }} onClick={() => setApiCreds((p) => [...p, { a: '', b: '', desc: '' }])}>Add key</Button>
          </>
        )}
      </Section>

      {/* Downloads */}
      <Section icon="download" title="File downloads" on={on.downloads ?? false} onToggle={toggle('downloads', 'downloads')}>
        <div className="oh-pol-hint">Allow or block members downloading files out of their lab through the browser. Best-effort - does not stop terminal or kernel transfers.</div>
        <div className="oh-row"><Switch size="small" checked={downloadsAllow} onChange={setDownloadsAllow} /><span>Allow downloads for members</span></div>
      </Section>

      {/* Sudo */}
      <Section icon="shield" title="Sudo access" on={on.sudo ?? false} onToggle={toggle('sudo', 'sudo')}>
        <div className="oh-pol-hint">Grant or deny members root via sudo inside their lab - needed to install system packages.</div>
        <div className="oh-row"><Switch size="small" checked={sudoEnable} onChange={setSudoEnable} /><span>Enable sudo for members</span></div>
      </Section>
    </div>
  )
}
