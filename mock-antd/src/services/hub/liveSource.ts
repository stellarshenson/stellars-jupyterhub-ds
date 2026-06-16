/* Live data source - readonly GETs to the hub, adapted into the view models.
 * Implements the endpoints the hub really exposes (users, groups, activity,
 * info, session-info); the hub-absent views (settings reference, sent
 * notifications, effective-policy resolve, lab volumes, tokens) delegate to the
 * mock source so the UI stays whole until those endpoints exist. */
import type { DataSource } from '../datasource'
import { mockSource } from '../mockSource'
import { THRESHOLDS } from '../config'
import { hubGet } from './client'
import type { ServerRow, ServerStatus, Stats, UserRow } from '../types'

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
  // NativeAuthenticator authorisation, surfaced by the custom users handler
  authorized?: boolean
  pending?: boolean
  activity?: number
}
interface RawActivity {
  cpu?: number
  mem_percent?: number
  mem_bytes?: number
  activity?: number
  gpu?: string
  volumes_gb?: number
  system_gb?: number
  time_left_minutes?: number
}

function statusFromServer(s?: RawServer): ServerStatus {
  if (!s) return 'offline'
  if (s.pending === 'spawn') return 'spawning'
  if (s.ready) return 'active'
  return 'offline'
}

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
async function fetchActivity(): Promise<Record<string, RawActivity>> {
  try {
    return await hubGet<Record<string, RawActivity>>('/activity')
  } catch {
    return {}
  }
}

export const liveSource: DataSource = {
  async getServers(): Promise<ServerRow[]> {
    const [users, activity] = await Promise.all([fetchUsers(), fetchActivity()])
    return users.map((u) => {
      const srv = u.servers?.['']
      const status = statusFromServer(srv)
      const a = activity[u.name] ?? {}
      const running = status === 'active' || status === 'idle'
      const memPct = a.mem_percent ?? null
      const timeLeft = a.time_left_minutes ?? null
      return {
        user: u.name,
        admin: !!u.admin,
        status,
        statusLabel: status[0].toUpperCase() + status.slice(1),
        activity: running ? a.activity ?? 0 : null,
        cpu: running ? a.cpu ?? null : null,
        mem: running ? memPct : null,
        memOver: memPct != null && memPct > THRESHOLDS.memPerUserPct,
        gpu: a.gpu ?? null,
        volumesGB: a.volumes_gb ?? null,
        volumesOver: (a.volumes_gb ?? 0) > THRESHOLDS.volumeTotalGB,
        systemGB: running ? a.system_gb ?? null : null,
        systemOver: (a.system_gb ?? 0) > THRESHOLDS.containerExtraSpaceGB,
        timeLeftMin: timeLeft,
        timeLeftLabel: timeLeft != null ? fmtMinutes(timeLeft) : undefined,
        timeLeftWarn: timeLeft != null && timeLeft < THRESHOLDS.timeLeftWarnMin,
      }
    })
  },

  async getUsers(): Promise<UserRow[]> {
    const users = await fetchUsers()
    return users.map((u) => ({
      name: u.name,
      admin: !!u.admin,
      authorized: u.authorized ?? true,
      pending: u.pending ?? false,
      activity: u.activity ?? 0,
      createdISO: u.created ?? new Date().toISOString(),
      lastSeenISO: u.last_activity ?? undefined,
      groups: u.groups ?? [],
    }))
  },

  async getUser(name: string): Promise<UserRow | undefined> {
    const all = await liveSource.getUsers()
    return all.find((u) => u.name === name)
  },

  async getStats(): Promise<Stats> {
    const servers = await liveSource.getServers()
    const users = await liveSource.getUsers()
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

  async getGroups() {
    // /admin/groups carries the policy summary; fall back to mock shape on failure
    try {
      const raw = await hubGet<Array<{ name: string; priority?: number; description?: string; users?: string[]; policy_summary?: Record<string, string> }>>('/admin/groups')
      return raw.map((g, i) => ({
        name: g.name,
        priority: g.priority ?? i + 1,
        description: g.description,
        members: g.users?.length ?? 0,
        policies: Object.entries(g.policy_summary ?? {}).map(([key, detail]) => ({ key, label: key, detail })),
      }))
    } catch {
      return mockSource.getGroups()
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

  async getSessionInfo(user: string) {
    try {
      const raw = await hubGet<{ time_left_minutes?: number; max_minutes?: number }>(`/users/${user}/session-info`)
      return { timeLeftMin: raw.time_left_minutes ?? 0, maxMin: raw.max_minutes ?? 720 }
    } catch {
      return mockSource.getSessionInfo(user)
    }
  },

  // hub-absent or derived views: delegate to the mock so the UI is complete
  getServerHero: mockSource.getServerHero,
  getTotalResources: mockSource.getTotalResources,
  getGroupConfig: mockSource.getGroupConfig,
  getEvents: mockSource.getEvents,
  getTokens: mockSource.getTokens,
  getUserVolumes: mockSource.getUserVolumes,
  getEffectiveGrants: mockSource.getEffectiveGrants,
  getLabVolumes: mockSource.getLabVolumes,
  getSettings: mockSource.getSettings,
  getSettingsReference: mockSource.getSettingsReference,
  getSentNotifications: mockSource.getSentNotifications,
  getGroupCorpus: mockSource.getGroupCorpus,
  getUserCorpus: mockSource.getUserCorpus,
}
