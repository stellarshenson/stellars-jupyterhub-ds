/* Mock data source - fixtures shaped into view models. Runs with no hub.
 * The visible cast (alice, konrad, milan, nina, jakub, piotr, marta) matches the
 * static mock exactly; deterministic filler scales the lists to a realistic few
 * hundred so search / scope / sort / pagination are exercised for real. */
import type { DataSource } from './datasource'
import { IDLE_CULLER, PLATFORM, THRESHOLDS } from './config'
import { cpuCounterPct, cpuQuotaPct, memQuotaPct, cpuTooltip, memTooltip, cpuAssignedPct, cpuAggregateLabel, heroCpuTooltip, hostCpuTooltip } from './hub/serverMetrics'
import type {
  EffectiveGrant,
  EventRow,
  GroupConfig,
  GroupRow,
  LabContainerInfo,
  PolicyConfig,
  PolicyTag,
  ResourceSnapshot,
  ServerHero,
  ServerRow,
  ServerStatus,
  SessionInfo,
  SentNotification,
  SettingsGroup,
  SettingsRefCategory,
  Stats,
  TokenRow,
  UserProfile,
  UserRow,
  Volume,
} from './types'

// ---------- corpora ----------
const GROUP_NAMES = [
  'research', 'data-science', 'gpu', 'keys-openai', 'interns', 'admins', 'staff',
  'students', 'ml-platform', 'vision-lab', 'nlp', 'robotics', 'finance',
  'bioinformatics', 'physics',
]

const FILLER_NAMES = [
  'ola', 'piotr2', 'marta2', 'ewa', 'tomek', 'dawid', 'kasia', 'marek', 'agnieszka',
  'bartek', 'sofia', 'hugo', 'lena', 'noah', 'emma', 'liam', 'olivia', 'mateusz',
  'zofia', 'jan', 'maja', 'kacper', 'julia', 'filip', 'wiktoria', 'antoni', 'zuzanna',
  'szymon', 'hanna', 'franciszek', 'aleksandra', 'mikolaj', 'amelia', 'jakub2',
  'natalia', 'wojciech', 'gabriela', 'igor', 'oliwia', 'adam', 'laura', 'leon',
  'nadia', 'oskar', 'pola', 'tymon', 'helena', 'borys', 'liliana', 'fabian', 'rozalia',
  'cyprian', 'malgorzata', 'krzysztof', 'barbara', 'andrzej', 'magdalena', 'pawel',
  'monika', 'grzegorz', 'katarzyna', 'tomasz', 'anna', 'lukasz', 'agata', 'michal',
  'dorota', 'rafal', 'beata', 'damian', 'iwona', 'sebastian', 'renata', 'kamil',
  'joanna', 'patryk', 'aneta', 'przemyslaw', 'sylwia', 'arkadiusz', 'edyta', 'marcin',
  'justyna', 'dominik', 'klaudia', 'radoslaw', 'paulina', 'maciej', 'weronika',
  'norbert', 'sandra', 'emil', 'karolina', 'dariusz', 'ewelina', 'konrad2', 'milena',
  'jacek', 'gabriel', 'roman', 'wanda', 'olaf', 'irena', 'czeslaw', 'halina',
  'ryszard', 'krystyna', 'zdzislaw', 'jadwiga', 'henryk', 'teresa', 'stanislaw',
  'danuta', 'tadeusz', 'genowefa', 'kazimierz', 'bronislawa',
]

interface ServerState {
  status: Exclude<ServerStatus, 'offline'>
  since: string
  cpu: number
  memPct: number
  memGB: number
  gpu?: string
  volumesGB: number
  volMounts: string
  systemGB: number
  timeLeftMin: number
}

interface Person {
  name: string
  admin?: boolean
  authorized: boolean
  pending?: boolean
  fullName?: string
  activity: number
  createdDaysAgo: number
  lastSeenMinAgo?: number
  groups: string[]
  server?: ServerState
  offlineSince?: string
  offlineVolumesGB?: number
  offlineVolMounts?: string
}

// ---------- the visible cast (mirrors the static mock) ----------
const CAST: Person[] = [
  {
    name: 'admin', admin: true, authorized: true, fullName: 'Platform Admin', activity: 40,
    createdDaysAgo: 320, lastSeenMinAgo: 2, groups: ['admins', 'staff'],
  },
  {
    name: 'alice', authorized: true, fullName: 'Alice Nowak', activity: 96, createdDaysAgo: 210,
    lastSeenMinAgo: 1, groups: ['research', 'data-science', 'gpu', 'ml-platform', 'vision-lab'],
    server: { status: 'active', since: '1m', cpu: 38, memPct: 30, memGB: 19.2, gpu: '0,1', volumesGB: 12, volMounts: 'home 2.1 GB · workspace 9.8 GB · cache 0.5 GB', systemGB: 11.2, timeLeftMin: 228 },
  },
  {
    name: 'konrad', admin: true, authorized: true, fullName: 'Konrad Jelen', activity: 78,
    createdDaysAgo: 300, lastSeenMinAgo: 5, groups: ['admins', 'research', 'gpu'],
    server: { status: 'active', since: '5m', cpu: 12, memPct: 5, memGB: 3.1, gpu: '0', volumesGB: 28, volMounts: 'home 4.0 GB · workspace 22.5 GB · cache 1.5 GB', systemGB: 1.1, timeLeftMin: 1320 },
  },
  {
    name: 'milan', authorized: true, fullName: 'Milan Kovac', activity: 0, createdDaysAgo: 64,
    lastSeenMinAgo: 0, groups: ['gpu', 'vision-lab'],
    server: { status: 'spawning', since: '', cpu: 0, memPct: 0, memGB: 0, gpu: '0,1', volumesGB: 41, volMounts: 'home 6.2 GB · workspace 33.0 GB · cache 1.8 GB', systemGB: 0, timeLeftMin: 0 },
  },
  {
    name: 'nina', authorized: true, fullName: 'Nina Schulz', activity: 12, createdDaysAgo: 120,
    lastSeenMinAgo: 38, groups: ['students', 'nlp'],
    server: { status: 'idle', since: '38m', cpu: 2, memPct: 2, memGB: 1.4, volumesGB: 8, volMounts: 'home 1.2 GB · workspace 6.4 GB · cache 0.4 GB', systemGB: 0.4, timeLeftMin: 22 },
  },
  {
    name: 'jakub', authorized: true, activity: 0, createdDaysAgo: 150, lastSeenMinAgo: 2880,
    groups: ['research', 'bioinformatics'], offlineSince: '2d', offlineVolumesGB: 52,
    offlineVolMounts: 'home 8.0 GB · workspace 42.0 GB · cache 2.0 GB',
  },
  {
    name: 'piotr', authorized: true, fullName: 'Piotr Zielinski', activity: 5, createdDaysAgo: 90,
    lastSeenMinAgo: 360, groups: ['students'], offlineSince: '6h', offlineVolumesGB: 6,
    offlineVolMounts: 'home 1.0 GB · workspace 4.6 GB · cache 0.4 GB',
  },
  {
    name: 'marta', authorized: true, activity: 0, createdDaysAgo: 12, groups: ['interns'],
  },
]

// pending signups (top section on Users)
const PENDING: Person[] = [
  { name: 'lena', authorized: false, pending: true, fullName: 'Lena Brandt', activity: 0, createdDaysAgo: 0, groups: ['research', 'data-science'] },
  { name: 'hugo', authorized: false, pending: true, activity: 0, createdDaysAgo: 0, groups: ['students'] },
]

const ACT_CYCLE = [0, 12, 35, 58, 78, 96]

function fillerPerson(name: string, i: number): Person {
  const pending = i % 53 === 0
  const authorized = !pending && i % 17 !== 0
  const activity = pending || !authorized ? 0 : ACT_CYCLE[i % ACT_CYCLE.length]
  const groups = [GROUP_NAMES[i % GROUP_NAMES.length], GROUP_NAMES[(i * 3 + 2) % GROUP_NAMES.length]]
    .filter((v, k, a) => a.indexOf(v) === k)
  const createdDaysAgo = 5 + ((i * 7) % 340)
  let server: ServerState | undefined
  let offlineSince: string | undefined
  let offlineVolumesGB: number | undefined
  let offlineVolMounts: string | undefined
  if (authorized && i % 8 === 3) {
    const mem = 6 + (i % 20)
    server = {
      status: activity <= 12 ? 'idle' : 'active',
      since: activity <= 12 ? `${10 + (i % 40)}m` : `${1 + (i % 9)}m`,
      cpu: activity <= 12 ? 2 + (i % 4) : 10 + (i % 50),
      memPct: mem,
      memGB: +(mem * 0.62).toFixed(1),
      gpu: i % 5 === 0 ? '0' : undefined,
      volumesGB: 4 + (i % 30),
      volMounts: `home ${1 + (i % 4)}.0 GB · workspace ${3 + (i % 20)}.0 GB · cache 0.5 GB`,
      systemGB: +(0.2 + (i % 6)).toFixed(1),
      timeLeftMin: activity <= 12 ? 15 + (i % 50) : 120 + (i % 600),
    }
  } else if (authorized && i % 4 === 0) {
    offlineSince = `${1 + (i % 6)}d`
    offlineVolumesGB = i % 11 === 0 ? 51 + (i % 8) : 3 + (i % 20)
    offlineVolMounts = `home ${1 + (i % 3)}.0 GB · workspace ${2 + (i % 15)}.0 GB · cache 0.4 GB`
  }
  return {
    name,
    authorized,
    pending,
    activity,
    createdDaysAgo,
    lastSeenMinAgo: server ? 0 : authorized ? 60 + ((i * 13) % 5000) : undefined,
    groups,
    server,
    offlineSince,
    offlineVolumesGB,
    offlineVolMounts,
  }
}

const PEOPLE: Person[] = [
  ...PENDING,
  ...CAST,
  ...FILLER_NAMES.map((n, i) => fillerPerson(n, i)),
]

// ---------- derivations ----------
const NOW = new Date()
function iso(daysAgo: number, minAgo = 0): string {
  return new Date(NOW.getTime() - daysAgo * 86400000 - minAgo * 60000).toISOString()
}

function fmtMinutes(min: number): string {
  if (min >= 60) {
    const h = Math.floor(min / 60)
    const m = min % 60
    return `${h}h ${m}m`  // always show minutes (e.g. "4h 0m"), never bare "4h"
  }
  return `${min}m`
}

function toServerRow(p: Person): ServerRow {
  const s = p.server
  if (!s) {
    const volumesGB = p.offlineVolumesGB ?? null
    const volOver = volumesGB != null && volumesGB > THRESHOLDS.volumeTotalGB
    return {
      user: p.name,
      name: p.fullName,
      admin: !!p.admin,
      status: 'offline',
      statusLabel: p.offlineSince ? `Offline ${p.offlineSince}` : 'Offline',
      // 7-day engagement is independent of run state - shown even when offline
      ...mockActivity(p),
      cpu: null,
      mem: null,
      gpu: null,
      volumesGB,
      volumesTip: volumesGB == null ? 'No volumes yet' : volOver ? `Total volumes ${volumesGB} GB, over the ${THRESHOLDS.volumeTotalGB} GB quota` : p.offlineVolMounts,
      volumesOver: volOver,
      systemGB: null,
      timeLeftMin: null,
    }
  }
  const sysOver = s.systemGB > THRESHOLDS.containerExtraSpaceGB
  const volOver = s.volumesGB > THRESHOLDS.volumeTotalGB
  const warn = s.status !== 'spawning' && s.timeLeftMin > 0 && s.timeLeftMin < THRESHOLDS.timeLeftWarnMin
  const spawning = s.status === 'spawning'
  return {
    user: p.name,
    name: p.fullName,
    admin: !!p.admin,
    status: s.status,
    statusLabel: s.status === 'active' ? `Active ${s.since}` : s.status === 'idle' ? `Idle ${s.since}` : 'Spawning',
    lastActivityISO: spawning ? null : iso(0, parseInt(s.since, 10) || 0),
    ...mockActivity(p),
    // mock: unlimited servers on an 8-core host (matches the hero/total tips); cpu
    // is cores-used % (docker/top), mem is GB used, colour is % of the assigned quota
    cpu: spawning ? null : cpuCounterPct(s.cpu),
    cpuAssignedPct: spawning ? null : cpuAssignedPct(s.cpu, 8),
    cpuQuotaPct: spawning ? null : cpuQuotaPct(s.cpu, 8),
    cpuTip: spawning ? undefined : cpuTooltip({ cpuPercent: s.cpu, cores: 8, coresLimited: false }),
    mem: spawning ? null : s.memGB,
    memQuotaPct: spawning ? null : memQuotaPct(s.memPct),
    memTip: spawning ? undefined : memTooltip({ memMb: s.memGB * 1024, memTotalMb: 64 * 1024, memLimited: false, memoryPercent: s.memPct, memHostTotalMb: 64 * 1024 }),
    // per-user GPU usage is not collected live (only host inventory) - keep the
    // mock honest so the demo's Servers GPU column hides exactly as it does live
    gpu: null,
    volumesGB: s.volumesGB,
    volumesTip: s.volMounts,
    volumesOver: volOver,
    systemGB: spawning ? null : s.systemGB,
    systemTip: spawning ? undefined : `Writable layer +${s.systemGB} GB${sysOver ? `, over the ${THRESHOLDS.containerExtraSpaceGB} GB quota` : ' above the base image'}`,
    systemOver: sysOver,
    timeLeftMin: spawning ? null : s.timeLeftMin,
    baseTimeoutMin: spawning ? null : IDLE_CULLER.timeoutH * 60,
    timeLeftLabel: spawning ? undefined : fmtMinutes(s.timeLeftMin),
    timeLeftWarn: warn,
  }
}

// 7-day engagement meter - same value on every surface (Servers, Home, Users)
// regardless of the current server state. Mirrors liveSource's activityFields.
function mockActivity(p: Person) {
  return {
    activity: p.activity,
    activityPct: p.activity,
    activityHours: Math.round((p.activity / 100) * 8 * 10) / 10,
  }
}

function toUserRow(p: Person): UserRow {
  return {
    name: p.name,
    fullName: p.fullName,
    admin: !!p.admin,
    authorized: p.authorized,
    pending: !!p.pending,
    ...mockActivity(p),
    createdISO: iso(p.createdDaysAgo),
    lastSeenISO: p.lastSeenMinAgo != null ? iso(0, p.lastSeenMinAgo) : undefined,
    groups: p.groups,
  }
}

function statusOf(p: Person): ServerStatus {
  return p.server ? p.server.status : 'offline'
}

// ---------- groups ----------
const POLICY_LABELS: Record<string, string> = {
  gpu: 'GPU', mem: 'Memory', cpu: 'CPU', docker: 'Docker', sudo: 'Sudo',
  downloads: 'Downloads', api_keys: 'API keys', env_vars: 'Env vars', volume_mounts: 'Volume mounts',
}

interface GroupSeed {
  name: string
  priority: number
  description: string
  policies: Array<[string, string]> // [key, detail]
}

const GROUP_SEEDS: GroupSeed[] = [
  { name: 'admins', priority: 1, description: 'Platform administrators', policies: [['sudo', 'enabled'], ['docker', 'socket + privileged'], ['gpu', 'all'], ['api_keys', 'openai, anthropic']] },
  { name: 'gpu', priority: 2, description: 'GPU-enabled workloads', policies: [['gpu', 'all devices'], ['mem', '32 GB'], ['cpu', '8 cores']] },
  { name: 'ml-platform', priority: 3, description: 'ML platform engineers', policies: [['gpu', '0,1'], ['mem', '48 GB'], ['docker', 'socket'], ['volume_mounts', '/mnt/datasets']] },
  { name: 'research', priority: 4, description: 'Research staff', policies: [['mem', '24 GB'], ['cpu', '6 cores'], ['downloads', 'allowed']] },
  { name: 'vision-lab', priority: 5, description: 'Computer-vision lab', policies: [['gpu', '2'], ['mem', '32 GB'], ['volume_mounts', '/mnt/shared']] },
  { name: 'data-science', priority: 6, description: 'Data science team', policies: [['mem', '16 GB'], ['cpu', '4 cores'], ['env_vars', '3 set']] },
  { name: 'keys-openai', priority: 7, description: 'OpenAI key pool', policies: [['api_keys', 'openai']] },
  { name: 'nlp', priority: 8, description: 'NLP group', policies: [['gpu', '1'], ['mem', '24 GB']] },
  { name: 'staff', priority: 9, description: 'All staff', policies: [['downloads', 'allowed'], ['mem', '12 GB']] },
  { name: 'students', priority: 10, description: 'Enrolled students', policies: [['mem', '8 GB'], ['cpu', '2 cores']] },
  { name: 'interns', priority: 11, description: 'Interns', policies: [['mem', '8 GB']] },
  { name: 'bioinformatics', priority: 12, description: 'Bioinformatics', policies: [['mem', '32 GB'], ['volume_mounts', '/mnt/genomes']] },
]

function policyTags(seed: GroupSeed): PolicyTag[] {
  return seed.policies.map(([key, detail]) => ({ key, label: POLICY_LABELS[key] ?? key, detail }))
}

function memberCount(group: string): number {
  return PEOPLE.filter((p) => p.groups.includes(group)).length
}

// ---------- the source ----------
function delay<T>(value: T): Promise<T> {
  return Promise.resolve(value)
}

export const mockSource: DataSource = {
  getHubInfo() {
    return delay({ version: PLATFORM.jupyterhubVersion })
  },

  async getStats(): Promise<Stats> {
    const servers = PEOPLE.map(statusOf)
    const running = servers.filter((s) => s === 'active').length
    const idle = servers.filter((s) => s === 'idle').length
    const spawning = servers.filter((s) => s === 'spawning').length
    const offline = servers.filter((s) => s === 'offline').length
    const pending = PEOPLE.filter((p) => p.pending).length
    const active = PEOPLE.filter((p) => !p.pending && p.activity > 0).length
    const neu = PEOPLE.filter((p) => p.authorized && !p.pending && p.lastSeenMinAgo == null).length
    const inactive = PEOPLE.filter((p) => !p.pending && p.authorized && p.activity === 0 && p.lastSeenMinAgo != null).length
    return delay({
      servers: { running: running + spawning, idle, offline, total: PEOPLE.length },
      users: { pending, active, new: neu, inactive, total: PEOPLE.length },
    })
  },

  getServers() {
    return delay(PEOPLE.map(toServerRow))
  },

  async getServerHero(user: string): Promise<ServerHero> {
    const p = PEOPLE.find((x) => x.name === user) ?? CAST[1]
    const s = p.server
    const status = statusOf(p)
    return delay({
      user: p.name,
      status,
      statusLabel: s ? (status === 'active' ? `Active ${s.since}` : status === 'idle' ? `Idle ${s.since}` : 'Spawning') : 'Offline',
      activity: p.activity,
      activityPct: p.activity,
      activityHours: Math.round((p.activity / 100) * 8 * 10) / 10,
      startedISO: s ? new Date(Date.now() - 3 * 3600_000).toISOString() : null,
      upgradeAvailable: false,
      ttl: { timeLeftMin: s ? s.timeLeftMin : 0, baseMin: IDLE_CULLER.timeoutH * 60, maxAddHours: IDLE_CULLER.maxExtensionH },
      // per-user GPU is not collected live (only host inventory), so the hero
      // never shows a per-server GPU meter - keep the mock's shape matching live
      resources: s
        ? { cpu: cpuAssignedPct(s.cpu, 8), cpuAggregateLabel: cpuAggregateLabel(s.cpu) ?? undefined, mem: s.memPct, gpu: 0, cpuTip: heroCpuTooltip({ cpuPercent: s.cpu, cores: 8, coresLimited: false, assignedPct: cpuAssignedPct(s.cpu, 8), hostPct: cpuAssignedPct(s.cpu, 8) }), memTip: `${s.memPct}% used\n${s.memGB} GB of host RAM (no limit)` }
        : { cpu: 0, mem: 0, gpu: 0 },
    })
  },

  getTotalResources() {
    return delay<ResourceSnapshot>({
      cpu: 41, cpuAggregateLabel: cpuAggregateLabel(330) ?? undefined, mem: 63, gpu: 62, gpus: [62, 41, 18],
      cpuTip: hostCpuTooltip({ coresUsed: 3.3, hostCores: 8, hostPct: 41, servers: '3 servers' }),
      memTip: '63% used\n40.3 of 64 GB across 3 servers',
      gpuDevices: [
        { index: '0', name: 'NVIDIA A100-SXM4-80GB', memoryMb: 81920, utilizationPct: 62, memoryUsedMb: 40000 },
        { index: '1', name: 'NVIDIA A100-SXM4-80GB', memoryMb: 81920, utilizationPct: 41, memoryUsedMb: 22000 },
        { index: '2', name: 'NVIDIA RTX 6000 Ada', memoryMb: 49140, utilizationPct: 18, memoryUsedMb: 8000 },
      ],
    })
  },

  getUsers() {
    return delay(PEOPLE.map(toUserRow))
  },

  getUser(name: string) {
    const p = PEOPLE.find((x) => x.name === name)
    return delay(p ? toUserRow(p) : undefined)
  },

  getUserProfile(name: string) {
    const p = PEOPLE.find((x) => x.name === name)
    const [firstName = '', lastName = ''] = (p?.fullName ?? '').split(' ')
    return delay<UserProfile>({ firstName, lastName, email: p ? `${name}@lab.stellars-tech.eu` : '', mustChangePassword: false })
  },

  getGroups() {
    return delay<GroupRow[]>(
      GROUP_SEEDS.map((g) => ({
        name: g.name,
        priority: g.priority,
        description: g.description,
        members: memberCount(g.name),
        memberNames: PEOPLE.filter((p) => p.groups.includes(g.name)).map((p) => p.name),
        policies: policyTags(g),
      })),
    )
  },

  async getGroupConfig(name: string): Promise<GroupConfig | undefined> {
    const g = GROUP_SEEDS.find((x) => x.name === name)
    if (!g) return undefined
    const has = (k: string) => g.policies.some(([key]) => key === k)
    const val = (k: string) => g.policies.find(([key]) => key === k)?.[1] ?? ''
    const sections = Object.keys(POLICY_LABELS).map((key) => ({
      key,
      label: POLICY_LABELS[key],
      enabled: has(key),
      summary: has(key) ? val(key) : 'not set',
    }))
    const members = PEOPLE.filter((p) => p.groups.includes(g.name)).map((p) => p.name)
    // representative flat config so the policy editor reads as configured in the demo
    const config: PolicyConfig = {
      env_vars_active: has('env_vars'),
      env_vars: has('env_vars') ? [{ name: 'HF_HOME', value: '/mnt/shared/hf', description: 'HuggingFace cache' }] : [],
      gpu_access: has('gpu'),
      gpu_all: true,
      gpu_device_ids: [],
      docker_active: has('docker'),
      docker_access: has('docker'),
      docker_limited: false,
      docker_privileged: false,
      docker_limited_max_containers: 10,
      docker_limited_max_volumes: 10,
      docker_limited_max_networks: 3,
      docker_limited_max_storage_gb: 50,
      docker_limited_cpu_cap_cores: 2,
      docker_limited_mem_cap_gb: 8,
      docker_limited_allow_dangerous_flags: false,
      docker_limited_user_compose_project_enabled: true,
      docker_limited_user_compose_project_allow_override: true,
      docker_limited_hub_network_access: true,
      cpu_limit_enabled: has('cpu'),
      cpu_limit_cores: has('cpu') ? 8 : 0,
      mem_limit_enabled: has('mem'),
      mem_limit_gb: has('mem') ? 32 : 0,
      mem_swap_disabled: false,
      sudo_active: has('sudo'),
      sudo_enable: true,
      downloads_active: has('downloads'),
      downloads_allow: true,
      api_keys_pool: {
        enabled: has('api_keys'),
        mode: has('api_keys') ? 'pair' : '',
        env_var_id: 'OPENAI_ORG_ID',
        env_var_secret: 'OPENAI_API_KEY',
        env_var_key: '',
        credentials: has('api_keys') ? [{ slot: 'mock-1', id: 'org-3xK', secret: 'sk-live-9f2a', description: 'seat 1' }] : [],
      },
      volume_mounts_active: has('volume_mounts'),
      volume_mounts: has('volume_mounts') ? [{ volume: 'jupyterhub_shared', mountpoint: '/mnt/shared' }] : [],
    }
    return delay({ name: g.name, description: g.description, priority: g.priority, members, sections, config })
  },

  getEvents() {
    const base: EventRow[] = [
      { id: 'e1', type: 'server', icon: 'play', text: '<b>milan</b> started a server with <b>gpu</b>', whenISO: iso(0, 0) },
      { id: 'e2', type: 'user', icon: 'user', text: '<b>lena</b> signed up - awaiting approval', whenISO: iso(0, 6) },
      { id: 'e3', type: 'policy', icon: 'shield', text: 'Policy <b>docker</b> changed on group <b>research</b>', whenISO: iso(0, 22) },
      { id: 'e4', type: 'cull', icon: 'stop', text: "<b>jakub</b>'s server was culled (idle 2h)", whenISO: iso(0, 60) },
      { id: 'e5', type: 'group', icon: 'group', text: '<b>alice</b> added to group <b>data-science</b>', whenISO: iso(0, 180) },
      { id: 'e6', type: 'broadcast', icon: 'megaphone', text: 'Broadcast sent to <b>18</b> active servers', whenISO: iso(0, 300) },
      { id: 'e7', type: 'user', icon: 'user', text: '<b>hugo</b> signed up - awaiting approval', whenISO: iso(0, 420) },
      { id: 'e8', type: 'server', icon: 'restart', text: "<b>konrad</b> restarted their server", whenISO: iso(0, 600) },
      { id: 'e9', type: 'volume', icon: 'disk', text: '<b>natalia</b> reset volumes: workspace', whenISO: iso(0, 90) },
    ]
    const filler: EventRow[] = FILLER_NAMES.slice(0, 24).map((n, i) => ({
      id: `f${i}`,
      type: (['server', 'user', 'group', 'policy', 'cull'] as const)[i % 5],
      icon: (['play', 'user', 'group', 'shield', 'stop'] as const)[i % 5],
      text: `<b>${n}</b> ${['started a server', 'updated their profile', 'joined a group', 'changed a policy', 'was culled (idle)'][i % 5]}`,
      whenISO: iso(0, 700 + i * 90),
    }))
    return delay([...base, ...filler])
  },

  getTokens() {
    return delay<TokenRow[]>([
      { id: 't1', note: 'claude-code', kind: 'token', createdISO: iso(40), lastUsedISO: iso(0, 120), expiresISO: iso(-50), scopes: 'read:users, read:servers' },
      { id: 't2', note: 'ci-pipeline', kind: 'token', createdISO: iso(120), lastUsedISO: iso(2), scopes: 'admin:users' },
      { id: 't3', note: 'notebook-export', kind: 'token', createdISO: iso(8), scopes: 'self' },
      { id: 'o1', note: 'JupyterLab', kind: 'oauth', createdISO: iso(210), lastUsedISO: iso(0, 5) },
      { id: 'o2', note: 'MLflow', kind: 'oauth', createdISO: iso(60), lastUsedISO: iso(1) },
    ])
  },

  getUserVolumes(user: string) {
    const vols: Volume[] = [
      { suffix: 'home', name: `jupyterlab-${user}_home`, mount: '/home', description: 'User home directory, configs', standard: true },
      { suffix: 'workspace', name: `jupyterlab-${user}_workspace`, mount: '/home/lab/workspace', description: 'Project files, notebooks, code', standard: true },
      { suffix: 'cache', name: `jupyterlab-${user}_cache`, mount: '/home/lab/.cache', description: 'pip / conda cache', standard: true },
    ]
    return delay(vols)
  },
  getUserVolumeSizes(user: string) {
    const p = PEOPLE.find((x) => x.name === user)
    return delay({ home: 2.1, workspace: p?.server?.volumesGB ?? 9.8, cache: 0.5 } as Record<string, number>)
  },

  getEffectiveGrants(user: string) {
    const p = PEOPLE.find((x) => x.name === user)
    const grants: EffectiveGrant[] = []
    if (!p) return delay(grants)
    if (p.groups.includes('gpu') || p.groups.includes('admins')) grants.push({ key: 'gpu', label: 'GPU', value: 'all devices', from: p.groups.includes('admins') ? 'admins' : 'gpu' })
    grants.push({ key: 'memory', label: 'Memory', value: p.groups.includes('gpu') ? '32 GB' : '16 GB', from: p.groups.includes('gpu') ? 'gpu' : 'data-science' })
    grants.push({ key: 'cpu', label: 'CPU', value: '8 cores', from: 'gpu' })
    if (p.admin) grants.push({ key: 'shield', label: 'Sudo', value: 'enabled', from: 'admins' })
    if (p.groups.includes('admins') || p.groups.includes('ml-platform')) grants.push({ key: 'box', label: 'Docker', value: 'socket', from: p.groups.includes('admins') ? 'admins' : 'ml-platform' })
    return delay(grants)
  },

  getSessionInfo(user: string) {
    const p = PEOPLE.find((x) => x.name === user)
    return delay<SessionInfo>({ timeLeftMin: p?.server?.timeLeftMin ?? 0, baseMin: IDLE_CULLER.timeoutH * 60, maxAddHours: IDLE_CULLER.maxExtensionH })
  },

  getLabContainer() {
    return delay<LabContainerInfo>({
      image: PLATFORM.labImage,
      volumes: [
        { name: 'home', mount: '/home', description: 'User home directory files, configurations' },
        { name: 'workspace', mount: '/home/lab/workspace', description: 'Project files, notebooks, code' },
        { name: 'cache', mount: '/home/lab/.cache', description: 'Temporary files, pip cache, conda cache' },
      ],
    })
  },

  getSettings() {
    return delay<SettingsGroup[]>([
      { title: 'Spawning', rows: [
        { key: 'Lab image', value: 'stellars-ds:latest', state: 'neutral' },
        { key: 'GPU mode', value: 'auto-detect', state: 'accent' },
        { key: 'Idle culler', value: 'enabled', state: 'ok' },
      ] },
      { title: 'Authentication', rows: [
        { key: 'Admin user', value: PLATFORM.admin, state: 'neutral' },
        { key: 'Signup', value: 'disabled', control: 'switch', tip: 'Default from JUPYTERHUB_SIGNUP_ENABLED - toggle to override' },
        { key: 'Allow all users', value: 'enabled', state: 'ok', tip: 'All registered users may sign in; new accounts still need authorisation' },
      ] },
      { title: 'Idle Culler', rows: [
        { key: 'Timeout', value: `${IDLE_CULLER.timeoutH}h` },
        { key: 'Activity target', value: `${IDLE_CULLER.activityTargetH}h` },
        { key: 'Max extension', value: `${IDLE_CULLER.maxExtensionH}h` },
        { key: 'Time-left warning', value: `< ${THRESHOLDS.timeLeftWarnMin}m`, tip: 'Time left turns amber on the dashboard and Servers list below this threshold' },
      ] },
      { title: 'Activity Monitor', rows: [
        { key: 'Sampling', value: 'enabled', state: 'ok' },
        { key: 'Sample interval', value: '10s' },
        { key: 'Score window', value: '1h' },
      ] },
      { title: 'Platform', rows: [
        { key: 'Version', value: PLATFORM.version, state: 'neutral' },
        { key: 'Base URL', value: PLATFORM.baseUrl, state: 'neutral' },
        { key: 'Timezone', value: PLATFORM.timezone, state: 'neutral' },
        { key: 'SSL', value: 'enabled', state: 'ok' },
      ] },
      { title: 'Quotas', rows: [
        { key: 'Memory warning', value: `${THRESHOLDS.memPerUserPct}% of host` },
        { key: 'Container extra space', value: `${THRESHOLDS.containerExtraSpaceGB} GB` },
        { key: 'Volume total', value: `${THRESHOLDS.volumeTotalGB} GB` },
      ] },
    ])
  },

  getSettingsReference() {
    return delay<SettingsRefCategory[]>([
      { category: 'Core', rows: [
        { name: 'JUPYTERHUB_ADMIN', value: 'admin', description: 'Admin username granted the admin role at login' },
        { name: 'JUPYTERHUB_BASE_URL', value: '/jupyterhub', description: 'URL prefix for all hub routes' },
        { name: 'JUPYTERHUB_LAB_IMAGE', value: 'stellars/stellars-jupyterlab-ds:latest', description: 'Image spawned for each user' },
        { name: 'JUPYTERHUB_NETWORK_NAME', value: 'jupyterhub_network', description: 'Docker network for spawned containers' },
      ] },
      { category: 'GPU', rows: [
        { name: 'JUPYTERHUB_GPU_ENABLED', value: '2', description: '0 disabled, 1 enabled, 2 auto-detect' },
        { name: 'JUPYTERHUB_GPUINFO_NVIDIA_IMAGE', value: 'stellars/stellars-gpuinfo-nvidia:latest', description: 'GPU-info sidecar image (detection + utilisation)' },
      ] },
      { category: 'Services', rows: [
        { name: 'JUPYTERHUB_LAB_SERVICE_MLFLOW', value: '1', description: 'Enable MLflow tracking' },
        { name: 'JUPYTERHUB_LAB_SERVICE_TENSORBOARD', value: '0', description: 'Enable TensorBoard' },
        { name: 'JUPYTERHUB_LAB_SERVICE_RESOURCES_MONITOR', value: '1', description: 'Enable the resources monitor' },
      ] },
      { category: 'Quotas', rows: [
        { name: 'JUPYTERHUB_LAB_MEMORY_MAX_USAGE_FRACTION', value: '0.25', description: 'Per-user memory warning threshold as fraction of host RAM' },
        { name: 'JUPYTERHUB_LAB_CONTAINER_MAX_EXTRA_SPACE_GB', value: '10', description: 'Writable-layer quota in GB before warning' },
        { name: 'JUPYTERHUB_LAB_VOLUME_MAX_TOTAL_SIZE_GB', value: '50', description: 'Total per-user volume quota in GB' },
      ] },
      { category: 'Branding', rows: [
        { name: 'JUPYTERHUB_BRANDING_STAGE', value: 'DEV', description: 'Environment-stage header badge (DEV/STG/TST/PRD); empty = none' },
        { name: 'JUPYTERHUB_BRANDING_LOGO_URI', value: 'file:///srv/branding/logo.svg', description: 'Custom logo (file:// or URL)' },
        { name: 'JUPYTERHUB_BRANDING_FAVICON_URI', value: 'file:///srv/branding/favicon.ico', description: 'Custom favicon' },
      ] },
    ])
  },

  getSentNotifications() {
    return delay<SentNotification[]>([
      { id: 'n1', message: 'Maintenance window tonight 22:00-23:00 UTC', type: 'warning', sentISO: iso(0, 30), delivered: 18, total: 18 },
      { id: 'n2', message: 'New GPU nodes are available - request access in Groups', type: 'info', sentISO: iso(1), delivered: 16, total: 17 },
      { id: 'n3', message: 'Please save your work and restart idle kernels', type: 'default', sentISO: iso(2), delivered: 22, total: 22 },
      { id: 'n4', message: 'Platform upgraded to 1.0.0', type: 'success', sentISO: iso(5), delivered: 14, total: 14 },
    ])
  },

  getGroupCorpus() {
    return delay(GROUP_NAMES)
  },

  getUserCorpus() {
    return delay(PEOPLE.map((p) => p.name))
  },
}
