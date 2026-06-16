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
  activity: number | null // 0-100 engagement, null when not running
  cpu: number | null // % of host
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
  policies: PolicyTag[]
}

export interface GroupConfig {
  name: string
  description: string
  priority: number
  members: string[]
  sections: PolicySection[]
}

export interface PolicySection {
  key: string
  label: string
  enabled: boolean
  summary: string // human summary of the configured value
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

export interface ResourceSnapshot {
  cpu: number // % host
  mem: number // % host
  gpu: number // % host (aggregate)
  gpus?: number[] // per-GPU utilisation - drives the segmented GPU meter + the count
  memTip?: string
}

export interface SessionInfo {
  timeLeftMin: number
  maxMin: number // headroom ceiling (max extension)
}

export interface ServerHero {
  user: string
  status: ServerStatus
  statusLabel: string
  activity: number
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
