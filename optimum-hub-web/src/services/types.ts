/* View models the pages and components consume. The data sources (mock or live)
 * produce these; pages never see raw hub JSON. Statuses and scopes are unions,
 * not enums (erasableSyntaxOnly forbids enums). */

export type Role = 'admin' | 'user'

export type ServerStatus = 'active' | 'idle' | 'spawning' | 'offline' | 'error'

export interface ServerRow {
  user: string
  admin: boolean
  status: ServerStatus
  statusLabel: string // "Active 1m", "Idle 38m", "Offline 2d", "Spawning"
  lastActivityISO?: string | null // last activity timestamp, for the time-ago column
  activity: number | null // 0-100 engagement, null when not running
  cpu: number | null // % of host
  cpuTip?: string // "4 cores assigned" / "8 host cores (no limit)"
  mem: number | null // % of host RAM
  memTip?: string // "19.2 GB - 30% of host RAM, over the 25% per-user limit"
  memOver?: boolean
  gpu: string | null // "0,1" or null
  volumesGB: number | null
  volumesTip?: string // per-mount breakdown
  volumesOver?: boolean
  systemGB: number | null // writable layer above the base image
  systemTip?: string
  systemOver?: boolean
  timeLeftMin: number | null // minutes until the idle culler stops it
  timeLeftLabel?: string
  timeLeftWarn?: boolean // below the warning threshold
}

export type UserScope = 'authorized' | 'inactive' | 'unauthorized' | 'all'

export interface UserProfile {
  firstName: string
  lastName: string
  email: string
}

export interface UserRow {
  name: string
  fullName?: string
  admin: boolean
  authorized: boolean
  pending: boolean // signed up, awaiting authorisation
  activity: number // 0-100; 0 = inactive
  createdISO: string
  lastSeenISO?: string
  groups: string[]
}

export interface PolicyTag {
  key: string // gpu | mem | cpu | docker | sudo | downloads | api_keys | env_vars | volume_mounts
  label: string // "GPU", "Mem"
  detail?: string // valued detail for the hover tooltip
}

export interface GroupRow {
  name: string
  priority: number
  description?: string
  members: number
  memberNames?: string[] // for the members tooltip
  policies: PolicyTag[]
  config?: PolicyConfig // raw flat policy config (live only) - drives the export bundle
}

export interface GroupConfig {
  name: string
  description: string
  priority: number
  members: string[]
  sections: PolicySection[]
  config: PolicyConfig // the real flat policy config (read + write)
}

export interface PolicySection {
  key: string
  label: string
  enabled: boolean
  summary: string // human summary of the configured value
}

// The hub stores group policy as one FLAT dict (every section's fields at the top
// level - see policy/registry.py default_config). The PUT body is {description,
// ...this}; coerce_config + validate_all on the hub are the safety net. Field
// names here MUST match the registry exactly. All fields optional - unset keys
// fall back to the stored config (PUT merges onto existing).
export interface PolicyEnvVar {
  name: string
  value: string
  description?: string
}

export interface PolicyVolumeMount {
  volume: string
  mountpoint: string
}

export interface PolicyApiCred {
  slot?: string // stable slot id - round-tripped so a running container keeps its credential
  id?: string // pair mode
  secret?: string // pair mode
  key?: string // single mode
  description?: string
}

export interface PolicyApiKeysPool {
  enabled: boolean
  mode: '' | 'single' | 'pair'
  env_var_id: string
  env_var_secret: string
  env_var_key: string
  credentials: PolicyApiCred[]
}

export interface PolicyConfig {
  env_vars_active?: boolean
  env_vars?: PolicyEnvVar[]
  gpu_access?: boolean
  gpu_all?: boolean
  gpu_device_ids?: string[]
  docker_active?: boolean
  docker_access?: boolean
  docker_limited?: boolean
  docker_privileged?: boolean
  docker_limited_max_containers?: number
  docker_limited_max_volumes?: number
  docker_limited_max_networks?: number
  docker_limited_max_storage_gb?: number
  docker_limited_cpu_cap_cores?: number
  docker_limited_mem_cap_gb?: number
  docker_limited_allow_dangerous_flags?: boolean
  docker_limited_user_compose_project_enabled?: boolean
  docker_limited_user_compose_project_allow_override?: boolean
  docker_limited_hub_network_access?: boolean
  cpu_limit_enabled?: boolean
  cpu_limit_cores?: number
  mem_limit_enabled?: boolean
  mem_limit_gb?: number
  mem_swap_disabled?: boolean
  sudo_active?: boolean
  sudo_enable?: boolean
  downloads_active?: boolean
  downloads_allow?: boolean
  api_keys_pool?: PolicyApiKeysPool
  volume_mounts_active?: boolean
  volume_mounts?: PolicyVolumeMount[]
}

export type EventType = 'server' | 'user' | 'group' | 'policy' | 'broadcast' | 'cull'

export interface EventRow {
  id: string
  type: EventType
  icon: string // IconKey
  text: string
  whenISO: string
}

export interface TokenRow {
  id: string
  note: string
  kind: 'token' | 'oauth'
  createdISO: string
  lastUsedISO?: string
  expiresISO?: string
  scopes?: string
}

export interface GpuDevice {
  index: string // nvidia-smi index ("0", "1", ...)
  name: string // e.g. "NVIDIA A100-SXM4-80GB"
  uuid?: string // stable device UUID (GPU-...)
  memoryMb: number // total device memory
  utilizationPct?: number // live per-GPU load % (sampled); absent = not sampled
  memoryUsedMb?: number // live used memory (sampled)
  temperatureC?: number // live core temp °C (sampled)
  powerW?: number // live board power draw W (sampled)
}

export interface ResourceSnapshot {
  cpu: number // % host
  cpuTip?: string // "4 cores assigned" / "8 host cores (no limit)"
  mem: number // % host
  gpu: number // % host (aggregate)
  gpus?: number[] // per-GPU utilisation % - segmented GPU meter (only when utilisation is sampled)
  gpuDevices?: GpuDevice[] // real host GPU inventory; drives the device count when utilisation is not sampled
  memTip?: string
}

export interface SessionInfo {
  timeLeftMin: number
  baseMin: number // base timeout - the bar's 100% reference (fresh session reads ~full)
  maxAddHours: number // hours still addable (gap to the ceiling) - for the extend control
}

export interface ServerHero {
  user: string
  status: ServerStatus
  statusLabel: string
  activity: number
  startedISO?: string | null // server (container) start time - drives the uptime label
  upgradeAvailable?: boolean // a newer lab image is available locally than the running container
  ttl: SessionInfo
  resources: ResourceSnapshot
}

export interface Volume {
  suffix: string // home | workspace | cache | shared | datasets
  name: string // jupyterlab-{user}_home, jupyterhub_shared, ...
  mount: string // /home, /home/lab/workspace, /mnt/shared
  description?: string
  sizeGB?: number
  standard: boolean // platform-managed core volume vs custom mount
}

// Lab Container page: the spawn image + the standard per-user volumes every lab
// gets (read-only deployment facts; shared/extra volumes are granted per group)
export interface LabMount {
  name: string // home | workspace | cache
  mount: string // /home, /home/lab/workspace, /home/lab/.cache
  description?: string
}

export interface LabContainerInfo {
  image: string
  volumes: LabMount[]
}

export interface EffectiveGrant {
  key: string // IconKey
  label: string
  value: string
  from: string // winning group
}

export interface PlatformSetting {
  key: string
  value: string
  state?: 'ok' | 'neutral' | 'accent'
  tip?: string
  control?: 'switch'
}

export interface SettingsGroup {
  title: string
  rows: PlatformSetting[]
}

export interface SettingsRefRow {
  name: string
  value: string
  description: string
}

export interface SettingsRefCategory {
  category: string
  rows: SettingsRefRow[]
}

export interface SentNotification {
  id: string
  message: string
  type: 'default' | 'info' | 'success' | 'warning' | 'error' | 'in-progress'
  sentISO: string
  delivered: number
  total: number
}

export interface Stats {
  servers: { running: number; idle: number; offline: number; total: number }
  users: { pending: number; active: number; new: number; inactive: number; total: number }
}
