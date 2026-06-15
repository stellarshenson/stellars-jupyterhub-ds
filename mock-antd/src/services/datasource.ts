/* The read API every page uses. Two implementations satisfy it: mockSource
 * (fixtures, no hub) and liveSource (readonly GETs + adapters). getDataSource()
 * picks one from VITE_DATA_MODE. Pages call these; they never touch raw hub JSON. */
import { isMock } from './dataMode'
import { mockSource } from './mockSource'
import { liveSource } from './hub/liveSource'
import type {
  EffectiveGrant,
  EventRow,
  GroupConfig,
  GroupRow,
  ResourceSnapshot,
  ServerHero,
  ServerRow,
  SessionInfo,
  SentNotification,
  SettingsGroup,
  SettingsRefCategory,
  Stats,
  TokenRow,
  UserRow,
  Volume,
} from './types'

export interface DataSource {
  getStats(): Promise<Stats>
  getServers(): Promise<ServerRow[]>
  getServerHero(user: string): Promise<ServerHero>
  getTotalResources(): Promise<ResourceSnapshot>
  getUsers(): Promise<UserRow[]>
  getUser(name: string): Promise<UserRow | undefined>
  getGroups(): Promise<GroupRow[]>
  getGroupConfig(name: string): Promise<GroupConfig | undefined>
  getEvents(): Promise<EventRow[]>
  getTokens(): Promise<TokenRow[]>
  getUserVolumes(user: string): Promise<Volume[]>
  getEffectiveGrants(user: string): Promise<EffectiveGrant[]>
  getSessionInfo(user: string): Promise<SessionInfo>
  getLabVolumes(): Promise<Volume[]>
  getSettings(): Promise<SettingsGroup[]>
  getSettingsReference(): Promise<SettingsRefCategory[]>
  getSentNotifications(): Promise<SentNotification[]>
  getGroupCorpus(): Promise<string[]>
  getUserCorpus(): Promise<string[]>
}

export function getDataSource(): DataSource {
  return isMock() ? mockSource : liveSource
}
