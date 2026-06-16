/* Live data source - real readonly GETs to the hub, adapted into the view
 * models. Backed by the hub's custom REST API (stellars-hub-services) plus the
 * standard JupyterHub API:
 *   /users                         - full roster (standard)
 *   /activity                      - per-user Docker stats, activity score,
 *                                    idle time-left, authorization (admin)
 *   /admin/groups                  - groups with config + policy_summary (admin)
 *   /users/{u}/session-info        - idle-culler countdown
 *   /users/{u}/manage-volumes      - existing per-user volumes
 *   /users/{u}/tokens, /user, /info
 *
 * Endpoints the hub does not (yet) expose stay on the mock so the UI is whole:
 *   - pending (unauthorized) users: live only in NativeAuth's users_info, no
 *     JSON list endpoint -> the pending panel reads empty in live mode
 *   - effective-policy resolve, audit events, sent-notifications history,
 *     lab volumes, settings values: no read API -> delegate to mock
 *   - per-user GPU usage: not collected (GPU is a group policy) -> gpu = null */
import type { DataSource } from '../datasource'
import { mockSource } from '../mockSource'
import { IDLE_CULLER, THRESHOLDS } from '../config'
import { hubGet, getCurrentUser } from './client'
import type {
  GroupConfig,
  GroupRow,
  ResourceSnapshot,
  ServerHero,
  ServerRow,
  ServerStatus,
  SessionInfo,
  Stats,
  TokenRow,
  UserRow,
  Volume,
} from '../types'

interface RawServer {
  ready?: boolean
  pending?: string | null
  started?: string | null
  last_activity?: string | null
}
interface RawUser {
  name: string
  admin?: boolean
  created?: string
  last_activity?: string | null
  groups?: string[]
  servers?: Record<string, RawServer>
}
interface RawActivityUser {
  username: string
  is_authorized?: boolean
  server_active?: boolean
  recently_active?: boolean
  cpu_percent?: number | null
  memory_mb?: number | null
  memory_percent?: number | null
  memory_total_mb?: number | null
  time_remaining_seconds?: number | null
  activity_score?: number | null
  last_activity?: string | null
  volume_size_mb?: number | null
  volume_breakdown?: Record<string, number>
  container_size_rw_mb?: number | null
}
interface RawActivity {
  users: RawActivityUser[]
  container_max_extra_space_mb?: number
  volume_max_total_size_mb?: number
  memory_max_usage_mb?: number
}
interface RawPolicySummary {
  key: string
  badge: string
  detail?: string
}
interface RawGroup {
  name: string
  description?: string
  priority?: number
  member_count?: number
  members?: string[]
  config?: Record<string, unknown>
  policy_summary?: RawPolicySummary[]
}
interface RawGroupsResp {
  groups: RawGroup[]
}

// registry order + display labels (mirrors stellars_hub_services POLICY_TYPES)
const POLICY_ORDER = ['env_vars', 'gpu', 'docker', 'cpu', 'mem', 'sudo', 'downloads', 'api_keys', 'volume_mounts']
const POLICY_LABELS: Record<string, string> = {
  env_vars: 'Env vars',
  gpu: 'GPU',
  docker: 'Docker',
  cpu: 'CPU',
  mem: 'Memory',
  sudo: 'Sudo',
  downloads: 'Downloads',
  api_keys: 'API keys',
  volume_mounts: 'Volume mounts',
}
const MOUNT_BY_SUFFIX: Record<string, string> = {
  home: '/home',
  workspace: '/home/lab/workspace',
  cache: '/home/lab/.cache',
}

const cap = (s: string) => s[0].toUpperCase() + s.slice(1)
const clampPct = (n: number) => Math.max(0, Math.min(100, Math.round(n)))
const round1 = (n: number) => Math.round(n * 10) / 10

function fmtMinutes(min: number): string {
  if (min >= 60) {
    const h = Math.floor(min / 60)
    const m = min % 60
    return m ? `${h}h ${m}m` : `${h}h`
  }
  return `${min}m`
}

async function fetchUsers(): Promise<RawUser[]> {
  return hubGet<RawUser[]>('/users')
}
async function fetchActivity(): Promise<RawActivity> {
  try {
    return await hubGet<RawActivity>('/activity')
  } catch {
    return { users: [] }
  }
}
function activityByName(a: RawActivity): Map<string, RawActivityUser> {
  const m = new Map<string, RawActivityUser>()
  for (const u of a.users) m.set(u.username, u)
  return m
}

function statusOf(srv: RawServer | undefined, a: RawActivityUser | undefined): ServerStatus {
  if (srv?.pending === 'spawn') return 'spawning'
  const ready = !!srv?.ready || !!a?.server_active
  if (ready) return a?.recently_active ? 'active' : 'idle'
  return 'offline'
}

export const liveSource: DataSource = {
  async getServers(): Promise<ServerRow[]> {
    const [users, activity] = await Promise.all([fetchUsers(), fetchActivity()])
    const byName = activityByName(activity)
    const memMax = activity.memory_max_usage_mb || 0
    const volMax = activity.volume_max_total_size_mb || 0
    const ctrMax = activity.container_max_extra_space_mb || 0
    return users.map((u) => {
      const srv = u.servers?.['']
      const a = byName.get(u.name)
      const status = statusOf(srv, a)
      const running = status === 'active' || status === 'idle'
      const memMb = a?.memory_mb ?? null
      const memPct = a?.memory_percent ?? null
      const volMb = a?.volume_size_mb ?? null
      const ctrMb = a?.container_size_rw_mb ?? null
      const tl = a?.time_remaining_seconds != null ? Math.round(a.time_remaining_seconds / 60) : null
      return {
        user: u.name,
        admin: !!u.admin,
        status,
        statusLabel: cap(status),
        activity: running ? clampPct(a?.activity_score ?? 0) : null,
        cpu: running && a?.cpu_percent != null ? Math.round(a.cpu_percent) : null,
        mem: running && memPct != null ? Math.round(memPct) : null,
        memTip: memMb != null ? `${round1(memMb / 1024)} GB${memPct != null ? ` - ${Math.round(memPct)}% of host RAM` : ''}` : undefined,
        memOver: memMax > 0 && memMb != null && memMb > memMax,
        gpu: null, // per-user GPU usage not collected server-side
        volumesGB: volMb != null ? round1(volMb / 1024) : null,
        volumesOver: volMax > 0 && volMb != null && volMb > volMax,
        systemGB: running && ctrMb != null ? round1(ctrMb / 1024) : null,
        systemOver: ctrMax > 0 && ctrMb != null && ctrMb > ctrMax,
        timeLeftMin: tl,
        timeLeftLabel: tl != null ? fmtMinutes(tl) : undefined,
        timeLeftWarn: tl != null && tl < THRESHOLDS.timeLeftWarnMin,
      }
    })
  },

  async getUsers(): Promise<UserRow[]> {
    const [users, activity] = await Promise.all([fetchUsers(), fetchActivity()])
    const byName = activityByName(activity)
    return users.map((u) => {
      const a = byName.get(u.name)
      return {
        name: u.name,
        admin: !!u.admin,
        authorized: a?.is_authorized ?? true,
        pending: false, // unauthorized users have no JSON list endpoint (see file header)
        activity: clampPct(a?.activity_score ?? 0),
        createdISO: u.created ?? new Date().toISOString(),
        lastSeenISO: u.last_activity ?? undefined,
        groups: u.groups ?? [],
      }
    })
  },

  async getUser(name: string): Promise<UserRow | undefined> {
    const all = await liveSource.getUsers()
    return all.find((u) => u.name === name)
  },

  async getStats(): Promise<Stats> {
    const [servers, users] = await Promise.all([liveSource.getServers(), liveSource.getUsers()])
    const by = (s: ServerStatus) => servers.filter((x) => x.status === s).length
    return {
      servers: { running: by('active') + by('spawning'), idle: by('idle'), offline: by('offline'), total: servers.length },
      users: {
        pending: users.filter((u) => u.pending).length,
        active: users.filter((u) => !u.pending && u.activity > 0).length,
        new: users.filter((u) => u.authorized && !u.pending && !u.lastSeenISO).length,
        inactive: users.filter((u) => !u.pending && u.authorized && u.activity === 0 && u.lastSeenISO).length,
        total: users.length,
      },
    }
  },

  async getGroups(): Promise<GroupRow[]> {
    try {
      const resp = await hubGet<RawGroupsResp>('/admin/groups')
      return resp.groups.map((g, i) => ({
        name: g.name,
        priority: g.priority ?? i + 1,
        description: g.description,
        members: g.member_count ?? g.members?.length ?? 0,
        policies: (g.policy_summary ?? []).map((s) => ({ key: s.key, label: s.badge || POLICY_LABELS[s.key] || s.key, detail: s.detail })),
      }))
    } catch {
      return mockSource.getGroups()
    }
  },

  async getGroupConfig(name: string): Promise<GroupConfig | undefined> {
    try {
      const resp = await hubGet<RawGroupsResp>('/admin/groups')
      const g = resp.groups.find((x) => x.name === name)
      if (!g) return undefined
      const summ = new Map((g.policy_summary ?? []).map((s) => [s.key, s] as const))
      const sections = POLICY_ORDER.map((key) => {
        const s = summ.get(key)
        return { key, label: POLICY_LABELS[key], enabled: !!s, summary: s ? s.badge : 'not set' }
      })
      return { name: g.name, description: g.description ?? '', priority: g.priority ?? 0, members: g.members ?? [], sections }
    } catch {
      return mockSource.getGroupConfig(name)
    }
  },

  async getServerHero(user: string): Promise<ServerHero> {
    const [activity, ttl] = await Promise.all([fetchActivity(), liveSource.getSessionInfo(user)])
    const a = activityByName(activity).get(user)
    const status: ServerStatus = a?.server_active ? (a.recently_active ? 'active' : 'idle') : 'offline'
    const resources: ResourceSnapshot = a?.server_active
      ? {
          cpu: Math.round(a.cpu_percent ?? 0),
          mem: Math.round(a.memory_percent ?? 0),
          gpu: 0,
          memTip: a.memory_mb != null ? `${round1(a.memory_mb / 1024)} GB of host RAM` : undefined,
        }
      : { cpu: 0, mem: 0, gpu: 0 }
    return { user, status, statusLabel: cap(status), activity: clampPct(a?.activity_score ?? 0), ttl, resources }
  },

  async getTotalResources(): Promise<ResourceSnapshot> {
    try {
      const activity = await fetchActivity()
      const active = activity.users.filter((u) => u.server_active)
      if (!active.length) return { cpu: 0, mem: 0, gpu: 0 }
      const totalMb = active[0].memory_total_mb || 0
      const memUsed = active.reduce((s, u) => s + (u.memory_mb ?? 0), 0)
      const cpuSum = active.reduce((s, u) => s + (u.cpu_percent ?? 0), 0)
      return {
        cpu: clampPct(cpuSum), // sum of container cpu% across servers, clamped (approximate host load)
        mem: totalMb > 0 ? clampPct((memUsed / totalMb) * 100) : 0,
        gpu: 0, // host GPU utilisation not collected
        memTip: `${round1(memUsed / 1024)} GB across ${active.length} server(s)`,
      }
    } catch {
      return mockSource.getTotalResources()
    }
  },

  async getSessionInfo(user: string): Promise<SessionInfo> {
    try {
      const r = await hubGet<{ time_remaining_seconds?: number | null; max_extension_hours?: number }>(`/users/${user}/session-info`)
      return {
        timeLeftMin: r.time_remaining_seconds != null ? Math.round(r.time_remaining_seconds / 60) : 0,
        maxMin: (r.max_extension_hours ?? IDLE_CULLER.maxExtensionH) * 60,
      }
    } catch {
      return mockSource.getSessionInfo(user)
    }
  },

  async getUserVolumes(user: string): Promise<Volume[]> {
    try {
      const [resp, activity] = await Promise.all([
        hubGet<{ volumes: Array<{ suffix: string; name: string; description?: string }> }>(`/users/${user}/manage-volumes`),
        fetchActivity(),
      ])
      const breakdown = activityByName(activity).get(user)?.volume_breakdown ?? {}
      return resp.volumes.map((v) => ({
        suffix: v.suffix,
        name: v.name,
        mount: MOUNT_BY_SUFFIX[v.suffix] ?? '',
        description: v.description,
        standard: true,
        sizeGB: breakdown[v.suffix] != null ? round1(breakdown[v.suffix] / 1024) : undefined,
      }))
    } catch {
      return mockSource.getUserVolumes(user)
    }
  },

  async getTokens(): Promise<TokenRow[]> {
    try {
      const me = await getCurrentUser()
      const r = await hubGet<{
        api_tokens?: Array<{ id: number | string; note?: string; created?: string; last_activity?: string | null; expires_at?: string | null; scopes?: string[] }>
        oauth_tokens?: Array<{ id: number | string; oauth_client?: string; note?: string; created?: string; last_activity?: string | null }>
      }>(`/users/${me.name}/tokens`)
      const toks: TokenRow[] = []
      for (const t of r.api_tokens ?? []) {
        toks.push({
          id: String(t.id),
          note: t.note || 'token',
          kind: 'token',
          createdISO: t.created ?? new Date().toISOString(),
          lastUsedISO: t.last_activity ?? undefined,
          expiresISO: t.expires_at ?? undefined,
          scopes: Array.isArray(t.scopes) ? t.scopes.join(', ') : undefined,
        })
      }
      for (const t of r.oauth_tokens ?? []) {
        toks.push({
          id: String(t.id),
          note: t.oauth_client || t.note || 'oauth',
          kind: 'oauth',
          createdISO: t.created ?? new Date().toISOString(),
          lastUsedISO: t.last_activity ?? undefined,
        })
      }
      return toks
    } catch {
      return mockSource.getTokens()
    }
  },

  async getGroupCorpus(): Promise<string[]> {
    try {
      const resp = await hubGet<RawGroupsResp>('/admin/groups')
      return resp.groups.map((g) => g.name)
    } catch {
      return mockSource.getGroupCorpus()
    }
  },

  async getUserCorpus(): Promise<string[]> {
    try {
      const users = await fetchUsers()
      return users.map((u) => u.name)
    } catch {
      return mockSource.getUserCorpus()
    }
  },

  async getHubInfo() {
    try {
      const raw = await hubGet<{ version?: string }>('/info')
      if (raw.version) return { version: raw.version }
      return mockSource.getHubInfo()
    } catch {
      return mockSource.getHubInfo()
    }
  },

  // backend-less or derived views: no read API yet -> mock keeps the UI whole
  getEvents: mockSource.getEvents,
  getEffectiveGrants: mockSource.getEffectiveGrants,
  getLabVolumes: mockSource.getLabVolumes,
  getSettings: mockSource.getSettings,
  getSettingsReference: mockSource.getSettingsReference,
  getSentNotifications: mockSource.getSentNotifications,
}
