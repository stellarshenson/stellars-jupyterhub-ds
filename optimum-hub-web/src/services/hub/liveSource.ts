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
import { timeAgoShort } from '../../lib/format'
import type {
  EventRow,
  EventType,
  GpuDevice,
  GroupConfig,
  GroupRow,
  LabContainerInfo,
  ResourceSnapshot,
  SettingsGroup,
  UserProfile,
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
  container_size_rootfs_mb?: number | null
}
interface RawActivity {
  users: RawActivityUser[]
  container_max_extra_space_mb?: number
  volume_max_total_size_mb?: number
  memory_max_usage_mb?: number
  gpus?: Array<{ index: string; name: string; memory_mb?: number; utilization?: number; memory_used_mb?: number }> // host GPU inventory + live load
  lab_image?: string // spawn image (Lab Container page)
  lab_volumes?: Array<{ suffix: string; mount: string; description?: string }> // standard per-user volumes
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

// event type -> icon key (the hub records type; the portal picks the icon)
const EVENT_ICON: Record<string, string> = {
  server: 'play', user: 'user', group: 'group', policy: 'shield', broadcast: 'megaphone', cull: 'stop',
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
interface NativeUser {
  username: string
  is_authorized: boolean
  is_hub_user: boolean
}
/** NativeAuth signups + authorisation state. Surfaces pending (signed-up,
 * not-yet-authorised) users that have no hub User row and so never appear in
 * /hub/api/users. Fails soft to an empty list. */
async function fetchNativeUsers(): Promise<NativeUser[]> {
  try {
    const r = await hubGet<{ users: NativeUser[] }>('/native-users')
    return r.users ?? []
  } catch {
    return []
  }
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
  // A ready/active server is never "spawning" - check readiness FIRST so a
  // lingering pending==='spawn' (a known hub transient during the ready race)
  // can't mask an actually-running server as Spawning.
  const ready = !!srv?.ready || !!a?.server_active
  if (ready) return a?.recently_active ? 'active' : 'idle'
  if (srv?.pending === 'spawn') return 'spawning'
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
      const memTotal = a?.memory_total_mb ?? null
      const volMb = a?.volume_size_mb ?? null
      const ctrMb = a?.container_size_rw_mb ?? null
      const rootfsMb = a?.container_size_rootfs_mb ?? null
      const vbreak = a?.volume_breakdown ?? {}
      const tl = a?.time_remaining_seconds != null ? Math.round(a.time_remaining_seconds / 60) : null
      const gb = (mb: number) => round1(mb / 1024)
      // mem: used vs configured per-user limit vs total host
      const memTip = memMb != null
        ? `${gb(memMb)} GB used`
          + (memMax > 0 ? ` / ${gb(memMax)} GB limit` : '')
          + (memTotal ? ` / ${gb(memTotal)} GB host` : '')
          + (memMax > 0 && memMb > memMax ? ' (over limit)' : '')
        : undefined
      // volumes: per-mount breakdown + quota when exceeded
      const volParts = Object.entries(vbreak).filter(([, mb]) => mb != null)
      const volTip = volMb != null
        ? (volParts.length ? `${volParts.map(([s, mb]) => `${s} ${gb(mb)} GB`).join(' · ')} (total ${gb(volMb)} GB)` : `${gb(volMb)} GB`)
          + (volMax > 0 && volMb > volMax ? ` / ${gb(volMax)} GB quota exceeded` : '')
        : undefined
      // system: base image size + writable layer + quota
      const baseMb = rootfsMb != null && ctrMb != null ? Math.max(0, rootfsMb - ctrMb) : null
      const sysTip = ctrMb != null
        ? (baseMb != null ? `base ${gb(baseMb)} GB + ` : '') + `writable ${gb(ctrMb)} GB`
          + (ctrMax > 0 ? ` / ${gb(ctrMax)} GB quota` : '')
          + (ctrMax > 0 && ctrMb > ctrMax ? ' (over)' : '')
        : undefined
      return {
        user: u.name,
        admin: !!u.admin,
        status,
        // match the mock's timed label ("Active 1m", "Idle 38m", "Offline 2d");
        // spawning has no last_activity so it stays a bare "Spawning"
        statusLabel: `${cap(status)}${a?.last_activity ? ` ${timeAgoShort(a.last_activity)}` : ''}`,
        lastActivityISO: a?.last_activity ?? null,
        activity: running ? clampPct(a?.activity_score ?? 0) : null,
        cpu: running && a?.cpu_percent != null ? Math.round(a.cpu_percent) : null,
        mem: running && memPct != null ? Math.round(memPct) : null,
        memTip,
        memOver: memMax > 0 && memMb != null && memMb > memMax,
        gpu: null, // per-user GPU usage not collected server-side
        volumesGB: volMb != null ? round1(volMb / 1024) : null,
        volumesTip: volTip,
        volumesOver: volMax > 0 && volMb != null && volMb > volMax,
        systemGB: running && ctrMb != null ? round1(ctrMb / 1024) : null,
        systemTip: sysTip,
        systemOver: ctrMax > 0 && ctrMb != null && ctrMb > ctrMax,
        timeLeftMin: tl,
        timeLeftLabel: tl != null ? fmtMinutes(tl) : undefined,
        timeLeftWarn: tl != null && tl < THRESHOLDS.timeLeftWarnMin,
      }
    })
  },

  async getUsers(): Promise<UserRow[]> {
    const [users, activity, native] = await Promise.all([fetchUsers(), fetchActivity(), fetchNativeUsers()])
    const byName = activityByName(activity)
    const authByName = new Map(native.map((n) => [n.username, n.is_authorized]))
    const hubNames = new Set(users.map((u) => u.name))
    const rows: UserRow[] = users.map((u) => {
      const a = byName.get(u.name)
      return {
        name: u.name,
        admin: !!u.admin,
        // NativeAuth is_authorized is authoritative; fall back to activity, then true.
        authorized: authByName.get(u.name) ?? a?.is_authorized ?? true,
        pending: false,
        activity: clampPct(a?.activity_score ?? 0),
        createdISO: u.created ?? new Date().toISOString(),
        lastSeenISO: u.last_activity ?? undefined,
        groups: u.groups ?? [],
      }
    })
    // Pending: signed up via NativeAuth, not yet authorised, no hub User row yet.
    for (const n of native) {
      if (!n.is_authorized && !hubNames.has(n.username)) {
        rows.push({
          name: n.username,
          admin: false,
          authorized: false,
          pending: true,
          activity: 0,
          createdISO: new Date().toISOString(),
          lastSeenISO: undefined,
          groups: [],
        })
      }
    }
    return rows
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
        memberNames: g.members ?? [],
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
      // the real flat policy config drives the editor (read); save PUTs it back
      const config = (g.config ?? {}) as GroupConfig['config']
      return { name: g.name, description: g.description ?? '', priority: g.priority ?? 0, members: g.members ?? [], sections, config }
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
      // Host GPU inventory is independent of active servers - surface the real
      // device count/names even when nothing is running. The background sampler
      // adds per-device `utilization` (real load %) when available, which drives
      // the striped per-GPU meter; absent it falls back to inventory chips.
      const gpuDevices: GpuDevice[] | undefined = activity.gpus
        ? activity.gpus.map((g) => ({
            index: String(g.index),
            name: g.name,
            memoryMb: g.memory_mb ?? 0,
            utilizationPct: g.utilization,
            memoryUsedMb: g.memory_used_mb,
          }))
        : undefined
      // Per-GPU utilisation array (ordered by inventory) for the striped meter,
      // only when at least one device reports a sample.
      const gpus: number[] | undefined =
        gpuDevices && gpuDevices.some((d) => d.utilizationPct !== undefined)
          ? gpuDevices.map((d) => d.utilizationPct ?? 0)
          : undefined
      // Aggregate GPU load = busiest device (host-level headline number).
      const gpuAgg = gpus && gpus.length ? Math.max(...gpus) : 0
      const active = activity.users.filter((u) => u.server_active)
      if (!active.length) return { cpu: 0, mem: 0, gpu: gpuAgg, gpus, gpuDevices }
      const totalMb = active[0].memory_total_mb || 0
      const memUsed = active.reduce((s, u) => s + (u.memory_mb ?? 0), 0)
      const cpuSum = active.reduce((s, u) => s + (u.cpu_percent ?? 0), 0)
      return {
        cpu: clampPct(cpuSum), // sum of container cpu% across servers, clamped (approximate host load)
        mem: totalMb > 0 ? clampPct((memUsed / totalMb) * 100) : 0,
        gpu: gpuAgg, // busiest GPU's real load
        gpus,
        gpuDevices,
        memTip: `${round1(memUsed / 1024)} GB across ${active.length} server(s)`,
      }
    } catch {
      // never fabricate platform facts: on a live error return empty resources
      // (no fake GPUs). keepPreviousData holds the last real snapshot on a
      // transient error; a cold error shows nothing rather than mock A100s.
      return { cpu: 0, mem: 0, gpu: 0 }
    }
  },

  async getSessionInfo(user: string): Promise<SessionInfo> {
    try {
      const r = await hubGet<{ time_remaining_seconds?: number | null; timeout_seconds?: number; max_extension_hours?: number; extensions_available_hours?: number }>(`/users/${encodeURIComponent(user)}/session-info`)
      return {
        timeLeftMin: r.time_remaining_seconds != null ? Math.round(r.time_remaining_seconds / 60) : 0,
        baseMin: r.timeout_seconds != null ? Math.round(r.timeout_seconds / 60) : IDLE_CULLER.timeoutH * 60,
        maxAddHours: r.extensions_available_hours ?? r.max_extension_hours ?? IDLE_CULLER.maxExtensionH,
      }
    } catch {
      return mockSource.getSessionInfo(user)
    }
  },

  async getUserVolumes(user: string): Promise<Volume[]> {
    try {
      const [resp, activity] = await Promise.all([
        hubGet<{ volumes: Array<{ suffix: string; name: string; description?: string }> }>(`/users/${encodeURIComponent(user)}/manage-volumes`),
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
      }>(`/users/${encodeURIComponent(me.name)}/tokens`)
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
      return { version: raw.version ?? '' }
    } catch {
      // honest empty, not a hardcoded mock version; keepPreviousData holds the
      // last real version on a transient error
      return { version: '' }
    }
  },

  // first/last name + email from the hub profile store (admin or self)
  async getUserProfile(name: string): Promise<UserProfile> {
    try {
      const r = await hubGet<{ first_name?: string; last_name?: string; email?: string }>(`/users/${encodeURIComponent(name)}/profile`)
      return { firstName: r.first_name ?? '', lastName: r.last_name ?? '', email: r.email ?? '' }
    } catch {
      return { firstName: '', lastName: '', email: '' }
    }
  },

  // real spawn image + standard per-user volumes from the /activity snapshot
  async getLabContainer(): Promise<LabContainerInfo> {
    try {
      const a = await fetchActivity()
      return {
        image: a.lab_image ?? '',
        volumes: (a.lab_volumes ?? []).map((v) => ({ name: v.suffix, mount: v.mount, description: v.description })),
      }
    } catch {
      return { image: '', volumes: [] } // honest empty, not the mock lab image
    }
  },

  // real platform settings (read-only): the live env values, grouped by category.
  // The env-var name is the tooltip; description is the row label.
  async getSettings(): Promise<SettingsGroup[]> {
    try {
      const r = await hubGet<{ settings: Array<{ category: string; name: string; value: string; description: string }> }>('/settings')
      const groups: SettingsGroup[] = []
      const byCat = new Map<string, SettingsGroup>()
      for (const s of r.settings) {
        let g = byCat.get(s.category)
        if (!g) {
          g = { title: s.category, rows: [] }
          byCat.set(s.category, g)
          groups.push(g)
        }
        g.rows.push({ key: s.description || s.name, value: s.value || '-', state: 'neutral', tip: s.name })
      }
      return groups
    } catch {
      return [] // honest empty, not the curated mock settings
    }
  },

  // real platform event log (user/group/policy/broadcast lifecycle); icon derived
  // from the event type. text is pre-escaped HTML from the hub
  async getEvents(): Promise<EventRow[]> {
    try {
      const r = await hubGet<{ events: Array<{ id: string; ts: string; type: string; text: string }> }>('/events')
      return r.events.map((e) => ({
        id: e.id,
        type: (EVENT_ICON[e.type] ? e.type : 'server') as EventType,
        icon: EVENT_ICON[e.type] ?? 'activity',
        text: e.text,
        whenISO: e.ts,
      }))
    } catch {
      return mockSource.getEvents()
    }
  },

  // backend-less or derived views: no read API yet -> mock keeps the UI whole
  getEffectiveGrants: mockSource.getEffectiveGrants,
  getSettingsReference: mockSource.getSettingsReference,
  getSentNotifications: async () => [], // no backend sent-history store yet - empty in live
}
