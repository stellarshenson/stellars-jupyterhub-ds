/* Live data source - real readonly GETs to the hub, adapted into the view
 * models. Backed by the hub's custom REST API (duoptimum-hub-services) plus the
 * standard JupyterHub API:
 *   /users                         - full roster (standard)
 *   /activity                      - per-user Docker stats, activity score,
 *                                    idle time-left, authorization (admin)
 *   /admin/groups                  - groups with config + policy_summary (admin)
 *   /users/{u}/session-info        - idle-culler countdown
 *   /users/{u}/manage-volumes      - existing per-user volumes
 *   /users/{u}/effective-grants    - group policy resolved per user (+ source)
 *   /users/{u}/tokens, /user, /info
 *
 * Endpoints the hub does not (yet) expose stay on the mock so the UI is whole:
 *   - pending (unauthorized) users: live only in NativeAuth's users_info, no
 *     JSON list endpoint -> the pending panel reads empty in live mode
 *   - sent-notifications history, lab volumes, settings values: no read API ->
 *     delegate to mock or an honest empty
 *   - per-user GPU usage: not collected (GPU is a group policy) -> gpu = null */
import type { DataSource } from '../datasource'
import { THRESHOLDS } from '../config'
import { hubGet, getCurrentUser } from './client'
import { cpuCounterPct, memCounterGb, cpuQuotaPct, memQuotaPct, cpuTooltip, memTooltip, heroCpuTooltip, hostCpuTooltip, cpuAggregateLabel } from './serverMetrics'
import { timeAgoShort } from '../../lib/format'
import type {
  EventRow,
  EffectiveGrant,
  EventType,
  GpuDevice,
  GroupConfig,
  GroupRow,
  LabContainerInfo,
  ResourceSnapshot,
  SentNotification,
  SettingsGroup,
  SettingsRefCategory,
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
  cpu_cores?: number | null
  cpu_cores_limited?: boolean
  memory_mb?: number | null
  memory_percent?: number | null
  memory_total_mb?: number | null // assigned ceiling when memory_limited, else host RAM
  memory_limited?: boolean // an explicit per-user mem limit is set (vs host fallback)
  time_remaining_seconds?: number | null
  timeout_seconds?: number | null // base idle-culler TTL (the configurable "standard limit")
  server_started?: string | null
  lab_image_upgrade_available?: boolean
  activity_score?: number | null
  activity_hours?: number | null
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
  memory_host_total_mb?: number | null // real host RAM - the "% of total" denominator
  cpu_host_total?: number | null // real host logical-core count - the "% of host" CPU denominator
  activity_target_hours?: number // daily active-hours target (uncapped-% denominator)
  gpus?: Array<{ index: string; name: string; uuid?: string; memory_mb?: number; utilization?: number; memory_used_mb?: number; temperature_c?: number; power_w?: number }> // host GPU inventory + live load
  gpu_connected?: boolean // gpuinfo sidecar is live (fresh sample); false = inventory is stale, hide GPU widgets
  lab_image?: string // spawn image (Lab Container page)
  lab_volumes?: Array<{ suffix: string; mount: string; description?: string; role?: string }> // standard per-user volumes (role = duoptimum-hub.volume.role)
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
  server: 'play', user: 'user', group: 'group', policy: 'shield', broadcast: 'megaphone', cull: 'stop', volume: 'disk',
}

// registry order + display labels (mirrors duoptimum_hub_services POLICY_TYPES)
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
// CPU bar as a fraction of the assigned cores (parallel to the memory bar's
// usage/limit). docker's cpu_percent is cores-used x 100, so a multi-core
// container exceeds 100%; dividing by the assigned cores keeps the bar 0-100 and
// makes a quota-limited user's bar measure against their ceiling, not the host.
const cpuBarPct = (cpuPercent: number | null | undefined, cores: number | null | undefined): number | null =>
  cpuPercent == null ? null : clampPct(cores && cores > 0 ? cpuPercent / cores : cpuPercent)

function fmtMinutes(min: number): string {
  if (min >= 60) {
    const h = Math.floor(min / 60)
    const m = min % 60
    return `${h}h ${m}m`  // always show minutes (e.g. "4h 0m"), never bare "4h"
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
// /activity runs docker stats on the hub and is the heavy call; getServers,
// getUsers, getStats (which calls both) and getServerHero all need it, so a single
// mutation or poll tick can otherwise fire it 3-4x concurrently. Coalesce calls
// within a short window to one in-flight request so they share the result.
let _activityInFlight: { ts: number; p: Promise<RawActivity> } | null = null
const ACTIVITY_COALESCE_MS = 1500
async function fetchActivity(): Promise<RawActivity> {
  const now = Date.now()
  if (_activityInFlight && now - _activityInFlight.ts < ACTIVITY_COALESCE_MS) return _activityInFlight.p
  const p = hubGet<RawActivity>('/activity').catch(() => ({ users: [] }) as RawActivity)
  _activityInFlight = { ts: now, p }
  // Release the slot once settled so this is genuine in-flight coalescing, not a
  // 1.5s stale-result cache: the invalidate(refetchType:'all') storm fires its
  // refetches synchronously so concurrent callers still share this one promise,
  // but a later fast-poll tick gets fresh /activity instead of a settled snapshot.
  void p.finally(() => { if (_activityInFlight?.p === p) _activityInFlight = null })
  return p
}
// Bulk display profiles -> {username: "First Last"} (blank when no name set), so
// the Users list can show a sub-name without an N+1 per-user profile fetch.
async function fetchFullNames(): Promise<Map<string, string>> {
  const m = new Map<string, string>()
  try {
    const r = await hubGet<{ profiles: Record<string, { first_name?: string; last_name?: string }> }>('/user-profiles')
    for (const [name, p] of Object.entries(r.profiles ?? {})) {
      const full = `${p.first_name ?? ''} ${p.last_name ?? ''}`.trim()
      if (full) m.set(name, full)
    }
  } catch { /* profiles unavailable - list just omits sub-names */ }
  return m
}
function activityByName(a: RawActivity): Map<string, RawActivityUser> {
  const m = new Map<string, RawActivityUser>()
  for (const u of a.users) m.set(u.username, u)
  return m
}

// Activity is a 7-DAY engagement metric (capped score + avg active hours vs the
// daily target), NOT a live reading - it is meaningful whether or not the server
// is running right now. Server-list rows and user-list rows derive it from this
// ONE helper so the meter reads identically on every surface (Home widget,
// Servers, Users). A `running ?` gate on the server rows was the regression that
// made an offline-but-active user show e.g. 30% on Users and "none" on Servers.
function activityFields(a: RawActivityUser | undefined, target: number) {
  return {
    activity: clampPct(a?.activity_score ?? 0),
    activityHours: a?.activity_hours ?? null,
    activityPct: a?.activity_hours != null && target > 0 ? Math.round((a.activity_hours / target) * 100) : null,
  }
}

function statusOf(srv: RawServer | undefined, a: RawActivityUser | undefined): ServerStatus {
  // The JupyterHub spawner state is authoritative on presence so start/stop
  // reflect IMMEDIATELY: a ready server is up the instant the hub marks it, and a
  // user with no spawner object is down the instant it's stopped. The activity
  // sampler's `server_active` lags ~10s, so it must NOT be ORed in here.
  // `recently_active` (also sampled) only refines active-vs-idle once up.
  if (!srv) return 'offline'
  if (srv.ready) return a?.recently_active ? 'active' : 'idle'
  if (srv.pending === 'stop') return 'offline' // tearing down -> reads as offline
  // pending 'spawn' OR the post-spawn settle window (spawner present, not yet
  // ready, no pending) - both are "coming up". Treating settle as spawning (not
  // offline) is what lets the adaptive fast-poll heal it in ~2-3s instead of
  // sticking offline until the slow poll / staleTime.
  return 'spawning'
}

export const liveSource: DataSource = {
  async getServers(): Promise<ServerRow[]> {
    const [users, activity, fullNames] = await Promise.all([fetchUsers(), fetchActivity(), fetchFullNames()])
    const byName = activityByName(activity)
    const memHostTotal = activity.memory_host_total_mb || 0 // real host RAM ("% of total")
    const target = activity.activity_target_hours || 0 // uncapped-% denominator (real backend value; 0 = unknown)
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
      const baseTtl = a?.timeout_seconds != null ? Math.round(a.timeout_seconds / 60) : null
      const gb = (mb: number) => round1(mb / 1024)
      // cpu: the cell is total CPU used (docker/top: cpu_percent is cores-used x 100,
      // 100% = one core) - NOT divided by host cores, NOT clamped; the colour is the
      // % of the assigned cores (cpuQuotaPct), and the tooltip reveals cores used,
      // the assigned ceiling and the % of assigned (+ quota-crossing)
      const cores = a?.cpu_cores ?? null
      const cpuPercent = a?.cpu_percent ?? null
      const cpuVal = running ? cpuCounterPct(cpuPercent) : null
      const cpuAssigned = running ? cpuBarPct(cpuPercent, cores) : null // % of assigned (the 'normalized' cell mode)
      const cpuQp = running ? cpuQuotaPct(cpuPercent, cores) : null
      const cpuTip = running && cpuPercent != null
        ? cpuTooltip({ cpuPercent, cores, coresLimited: !!a?.cpu_cores_limited })
        : undefined
      // mem: the cell is GB used (absolute); the colour is the % of the assigned
      // memory limit (memQuotaPct = memory_percent), and the tooltip reveals GB used,
      // the assigned ceiling, the % of assigned (+ crossing) and the % of host RAM
      const memLimited = !!a?.memory_limited
      const memVal = running ? memCounterGb(memMb) : null
      const memQp = running ? memQuotaPct(memPct) : null
      const memTip = running && memMb != null
        ? memTooltip({ memMb, memTotalMb: memTotal, memLimited, memoryPercent: memPct, memHostTotalMb: memHostTotal })
        : undefined
      // volumes: per-mount breakdown + quota (multiline tooltip, one entry per line)
      const volParts = Object.entries(vbreak).filter(([, mb]) => mb != null)
      const volTip = volMb != null
        ? [
            ...volParts.map(([s, mb]) => `${s}: ${gb(mb)} GB`),
            `total ${gb(volMb)} GB`,
            volMax > 0 ? `quota ${gb(volMax)} GB${volMb > volMax ? ' (exceeded)' : ''}` : '',
          ].filter(Boolean).join('\n')
        : undefined
      // system: base image size + writable layer + quota (multiline tooltip)
      const baseMb = rootfsMb != null && ctrMb != null ? Math.max(0, rootfsMb - ctrMb) : null
      const sysTip = ctrMb != null
        ? [
            baseMb != null ? `base image ${gb(baseMb)} GB` : '',
            `writable ${gb(ctrMb)} GB${ctrMax > 0 && ctrMb > ctrMax ? ' (over)' : ''}`,
            ctrMax > 0 ? `quota ${gb(ctrMax)} GB` : '',
          ].filter(Boolean).join('\n')
        : undefined
      return {
        user: u.name,
        name: fullNames.get(u.name) || undefined,
        admin: !!u.admin,
        status,
        // match the mock's timed label ("Active 1m", "Idle 38m", "Offline 2d");
        // spawning has no last_activity so it stays a bare "Spawning"
        statusLabel: `${cap(status)}${a?.last_activity ? ` ${timeAgoShort(a.last_activity)}` : ''}`,
        lastActivityISO: a?.last_activity ?? null,
        // 7-day engagement meter - NOT gated on `running` (see activityFields)
        ...activityFields(a, target),
        cpu: cpuVal,
        cpuAssignedPct: cpuAssigned,
        cpuQuotaPct: cpuQp,
        cpuTip,
        mem: memVal,
        memQuotaPct: memQp,
        memTip,
        gpu: null, // per-user GPU usage not collected server-side
        volumesGB: volMb != null ? round1(volMb / 1024) : null,
        volumesTip: volTip,
        volumesOver: volMax > 0 && volMb != null && volMb > volMax,
        systemGB: running && ctrMb != null ? round1(ctrMb / 1024) : null,
        systemTip: sysTip,
        systemOver: ctrMax > 0 && ctrMb != null && ctrMb > ctrMax,
        timeLeftMin: tl,
        baseTimeoutMin: baseTtl,
        timeLeftLabel: tl != null ? fmtMinutes(tl) : undefined,
        timeLeftWarn: tl != null && tl < THRESHOLDS.timeLeftWarnMin,
      }
    })
  },

  async getUsers(): Promise<UserRow[]> {
    const [users, activity, native, fullNames] = await Promise.all([fetchUsers(), fetchActivity(), fetchNativeUsers(), fetchFullNames()])
    const byName = activityByName(activity)
    const target = activity.activity_target_hours || 0 // uncapped-% denominator (real backend value; 0 = unknown)
    const authByName = new Map(native.map((n) => [n.username, n.is_authorized]))
    const hubNames = new Set(users.map((u) => u.name))
    const rows: UserRow[] = users.map((u) => {
      const a = byName.get(u.name)
      return {
        name: u.name,
        fullName: fullNames.get(u.name),
        admin: !!u.admin,
        // NativeAuth is_authorized is authoritative; fall back to activity, then true.
        authorized: authByName.get(u.name) ?? a?.is_authorized ?? true,
        pending: false,
        // identical 7-day engagement meter as the server rows (see activityFields):
        // real avg hours + the uncapped % behind the capped score
        ...activityFields(a, target),
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
        // raw flat config for the export bundle (the live payload carries it)
        config: (g.config ?? {}) as GroupRow['config'],
      }))
    } catch {
      return [] // honest empty - never fabricate groups on a 403/404/500 in live mode
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
      return undefined // honest - never feed a fabricated policy config into the editor (it would PUT back)
    }
  },

  async getServerHero(user: string): Promise<ServerHero> {
    // Fetch the authoritative spawner state (/users/{user}) alongside activity so
    // the status flips the instant the hub marks the server ready/stopped, not a
    // sampler interval later. statusOf trusts srv.ready over the lagging sample.
    const [activity, ttl, ru] = await Promise.all([
      fetchActivity(),
      liveSource.getSessionInfo(user),
      hubGet<RawUser>(`/users/${encodeURIComponent(user)}`),
    ])
    const a = activityByName(activity).get(user)
    const srv = ru?.servers?.['']
    const status = statusOf(srv, a)
    const memMax = activity.memory_max_usage_mb || 0
    const memHostTotal = activity.memory_host_total_mb || 0
    const target = activity.activity_target_hours || 0 // real backend value; 0 = unknown
    const cpuPct = a?.server_active ? cpuBarPct(a.cpu_percent, a.cpu_cores) ?? 0 : 0
    // host cores for the "% of host compute" tooltip line - the REAL host logical-core
    // count from the backend (cpu_host_total), NOT the largest per-server assignment
    // (that read high when every active server was CPU-capped). null when unavailable
    // -> heroCpuTooltip omits the "% of host compute" line rather than guessing.
    const heroHostCores = activity.cpu_host_total ?? null
    const cpuHostPct = a?.cpu_percent != null && heroHostCores && heroHostCores > 0 ? clampPct(a.cpu_percent / heroHostCores) : null
    const memPctTotal = a?.memory_mb != null && memHostTotal > 0 ? Math.round((a.memory_mb / memHostTotal) * 100) : null
    const resources: ResourceSnapshot = a?.server_active
      ? {
          cpu: cpuPct, // bar FILL = % of assigned cores (capped) - the one bar capped at assigned
          cpuAggregateLabel: cpuAggregateLabel(a.cpu_percent) ?? undefined, // 'cores' mode label
          cpuTip: a.cpu_cores != null
            ? heroCpuTooltip({ cpuPercent: a.cpu_percent ?? 0, cores: a.cpu_cores, coresLimited: !!a.cpu_cores_limited, assignedPct: cpuPct, hostPct: cpuHostPct })
            : undefined,
          mem: Math.round(a.memory_percent ?? 0), // usage vs the assigned ceiling (server-side)
          gpu: 0,
          memTip: a.memory_mb != null
            ? [
                `${a.memory_percent != null ? Math.round(a.memory_percent) : 0}% used${memMax > 0 && a.memory_mb > memMax ? ' (over warning threshold)' : ''}`,
                a.memory_total_mb ? `${round1(a.memory_mb / 1024)} of ${round1(a.memory_total_mb / 1024)} GB ${a.memory_limited ? 'assigned' : 'host (no limit)'}` : `${round1(a.memory_mb / 1024)} GB used`,
                a.memory_limited && memPctTotal != null ? `${memPctTotal}% of ${round1(memHostTotal / 1024)} GB host` : '',
              ].filter(Boolean).join('\n')
            : undefined,
        }
      : { cpu: 0, mem: 0, gpu: 0 }
    const activityPct = a?.activity_hours != null && target > 0 ? Math.round((a.activity_hours / target) * 100) : null
    // include the time-ago suffix so the hero status pill reads "Active 1m" like
    // the Servers list, not a bare "Active"
    const statusLabel = `${cap(status)}${a?.last_activity ? ` ${timeAgoShort(a.last_activity)}` : ''}`
    return { user, status, statusLabel, activity: clampPct(a?.activity_score ?? 0), activityHours: a?.activity_hours ?? null, activityPct, startedISO: a?.server_started ?? srv?.started ?? null, upgradeAvailable: !!a?.lab_image_upgrade_available, ttl, resources }
  },

  async getTotalResources(): Promise<ResourceSnapshot> {
    try {
      const activity = await fetchActivity()
      // GPU devices reflect LIVE availability ("available" = sidecar connected AND
      // GPUs detected; a -> b). The inventory is enumerated at startup and seeded from
      // a persisted cache that OUTLIVES the sidecar, so activity.gpus alone is not
      // "available" - the devices are exposed ONLY when gpu_connected. When the sidecar
      // is down: the Host Status GPU row hides (gpuDisconnected) AND the group
      // GPU-grant editor lists no devices, so editing re-syncs the grant to reality
      // (none) - the stored grant is preserved until the admin saves.
      const hasGpuInventory = !!(activity.gpus && activity.gpus.length)
      const gpuConnected = hasGpuInventory && !!activity.gpu_connected
      const gpuDisconnected = hasGpuInventory && !gpuConnected
      const gpuDevices: GpuDevice[] | undefined = gpuConnected
        ? activity.gpus!.map((g) => ({
            index: String(g.index),
            name: g.name,
            uuid: g.uuid,
            memoryMb: g.memory_mb ?? 0,
            utilizationPct: g.utilization,
            memoryUsedMb: g.memory_used_mb,
            temperatureC: g.temperature_c,
            powerW: g.power_w,
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
      // Host CPU/MEM bars aggregate ACTIVE user servers as a % of the host total.
      // With zero active servers the figure is an honest 0% - but it MUST still carry
      // a tooltip and the host-total error flags. The early return that dropped both
      // was the "blank bar, no tooltip" regression.
      const active = activity.users.filter((u) => u.server_active)
      // host RAM, NOT the first user's cgroup ceiling. NO fallback: if the backend
      // could not read the host total (_host_total_memory_mb -> null) the memory bar
      // shows an explicit "unavailable" rather than a fabricated denominator
      const hostRam = activity.memory_host_total_mb ?? null
      const memError = hostRam == null || hostRam <= 0
      const totalMb = hostRam ?? 0
      const memUsed = active.reduce((s, u) => s + (u.memory_mb ?? 0), 0)
      const cpuSum = active.reduce((s, u) => s + (u.cpu_percent ?? 0), 0) // cores-used x 100, summed
      const coresUsed = cpuSum / 100
      // host cores: the REAL host logical-core count from the backend (cpu_host_total,
      // /proc/cpuinfo). NOT the largest per-server assignment - that approximation only
      // equalled the host count when an UNLIMITED server happened to be active; with
      // every active server CPU-capped it read ~2x high (the host bar exceeding the
      // user's own % of assigned, which looks impossible). NO fallback: if the backend
      // could not read it the bar shows "unavailable" rather than a fabricated
      // denominator (same rule as host RAM).
      const hostCores = activity.cpu_host_total ?? null
      const cpuError = hostCores == null || hostCores <= 0
      // the Host CPU bar FILL is the % of total host compute; the tooltip reveals
      // cores used + the % of host compute (the host has no "assigned" - that is
      // per-server, shown only on the Server Status hero)
      const cpuBar = hostCores && hostCores > 0 ? clampPct((coresUsed / hostCores) * 100) : 0
      const memBar = memError ? 0 : clampPct((memUsed / totalMb) * 100)
      const svrs = `${active.length} server${active.length === 1 ? '' : 's'}`
      return {
        cpu: cpuBar,
        cpuAggregateLabel: cpuAggregateLabel(cpuSum) ?? undefined, // 'cores' mode: summed cores-used x 100
        cpuError,
        cpuTip: hostCores && hostCores > 0
          ? hostCpuTooltip({ coresUsed, hostCores, hostPct: cpuBar, servers: svrs })
          : 'Host CPU core count unavailable',
        mem: memBar,
        memError,
        gpu: gpuAgg, // busiest GPU's real load
        gpus,
        gpuDevices,
        gpuDisconnected, // sidecar down -> hide the GPU row entirely (no stale inventory)
        memTip: memError ? 'Host RAM total unavailable' : `${memBar}% used\n${round1(memUsed / 1024)} of ${round1(totalMb / 1024)} GB across ${svrs}`,
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
        baseMin: r.timeout_seconds != null ? Math.round(r.timeout_seconds / 60) : 0,
        maxAddHours: r.extensions_available_hours ?? r.max_extension_hours ?? 0,
      }
    } catch {
      // never fabricate a TTL: with no real backend value the gadget shows an empty
      // bar and a disabled extend (baseMin 0 -> 0% in TtlGadget, maxAddHours 0 -> at ceiling)
      return { timeLeftMin: 0, baseMin: 0, maxAddHours: 0 }
    }
  },

  async getUserVolumes(user: string): Promise<Volume[]> {
    try {
      // Names only - the fast /manage-volumes call, decoupled from the slow
      // /activity sizes (getUserVolumeSizes) so the table paints at once and the
      // size cells fill in when the docker-stats sample lands.
      const resp = await hubGet<{ volumes: Array<{ suffix: string; name: string; description?: string; role?: string }> }>(`/users/${encodeURIComponent(user)}/manage-volumes`)
      return resp.volumes.map((v) => ({
        suffix: v.suffix,
        name: v.name,
        mount: MOUNT_BY_SUFFIX[v.suffix] ?? '',
        description: v.description,
        role: v.role,
        standard: !!v.role, // system volume iff it carries a platform role (identify by role, not name)
      }))
    } catch {
      return [] // honest empty - no fabricated volume list
    }
  },

  async getUserVolumeSizes(user: string): Promise<Record<string, number>> {
    try {
      const activity = await fetchActivity()
      const breakdown = activityByName(activity).get(user)?.volume_breakdown ?? {}
      const out: Record<string, number> = {}
      for (const [suffix, mb] of Object.entries(breakdown)) out[suffix] = round1(mb / 1024)
      return out
    } catch {
      return {} // honest empty - no fabricated sizes
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
      return [] // honest empty - never fabricate tokens (incl. fake admin-scoped ones)
    }
  },

  async getGroupCorpus(): Promise<string[]> {
    try {
      const resp = await hubGet<RawGroupsResp>('/admin/groups')
      return resp.groups.map((g) => g.name)
    } catch {
      return [] // honest empty - no fabricated group names in pickers
    }
  },

  async getUserCorpus(): Promise<string[]> {
    try {
      const users = await fetchUsers()
      return users.map((u) => u.name)
    } catch {
      return [] // honest empty - no fabricated usernames in pickers
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
      const r = await hubGet<{ first_name?: string; last_name?: string; email?: string; must_change_password?: boolean }>(`/users/${encodeURIComponent(name)}/profile`)
      return { firstName: r.first_name ?? '', lastName: r.last_name ?? '', email: r.email ?? '', mustChangePassword: !!r.must_change_password }
    } catch {
      return { firstName: '', lastName: '', email: '', mustChangePassword: false }
    }
  },

  // real spawn image + standard per-user volumes from the /activity snapshot
  async getLabContainer(): Promise<LabContainerInfo> {
    try {
      const a = await fetchActivity()
      return {
        image: a.lab_image ?? '',
        volumes: (a.lab_volumes ?? []).map((v) => ({ name: v.suffix, mount: v.mount, description: v.description, role: v.role })),
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
      return [] // honest empty - never fabricate a named event feed as the real log
    }
  },

  // real effective policy resolved across the user's groups; each grant cites
  // the winning group. Honest empty when no group grants anything special (the
  // user runs on platform defaults) - never the fabricated mock grants.
  async getEffectiveGrants(user: string): Promise<EffectiveGrant[]> {
    try {
      const r = await hubGet<{ grants: EffectiveGrant[] }>(`/users/${encodeURIComponent(user)}/effective-grants`)
      return r.grants ?? []
    } catch {
      return []
    }
  },

  // real settings reference: the same /settings payload (env name + live value +
  // description), grouped by category. Honest empty on error - never mock fixtures.
  async getSettingsReference(): Promise<SettingsRefCategory[]> {
    try {
      const r = await hubGet<{ settings: Array<{ category: string; name: string; value: string; description: string }> }>('/settings')
      const cats: SettingsRefCategory[] = []
      const byCat = new Map<string, SettingsRefCategory>()
      for (const s of r.settings) {
        let c = byCat.get(s.category)
        if (!c) { c = { category: s.category, rows: [] }; byCat.set(s.category, c); cats.push(c) }
        c.rows.push({ name: s.name, value: s.value || '-', description: s.description })
      }
      return cats
    } catch {
      return [] // honest empty
    }
  },
  // sent-broadcast history from the hub store (self-healing SQLite); newest first,
  // empty on any failure so the panel degrades to "no broadcasts" rather than erroring
  getSentNotifications: async () => {
    const r = await hubGet<{ notifications: SentNotification[] }>('/notifications/sent').catch(() => ({ notifications: [] }))
    return r.notifications ?? []
  },
}
