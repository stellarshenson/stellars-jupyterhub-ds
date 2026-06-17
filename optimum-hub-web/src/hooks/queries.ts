/* React Query read hooks over the active data source. Pages call these; they get
 * loading / error / data for free and the source (mock or live) is transparent. */
import { useQuery } from '@tanstack/react-query'
import { getDataSource } from '../services/datasource'
import type { ServerHero, ServerRow } from '../services/types'

const ds = () => getDataSource()

// Background polling for the live dashboard queries (servers/hero/stats/resources):
// poll FAST while a server is mid-transition (spawning) so a just-started server
// flips to active within a couple seconds, idle at a cheap SLOW cadence otherwise,
// and never poll when the tab is hidden (each /activity sample runs docker stats).
const FAST_POLL = 2500
const SLOW_POLL = 15000
const serversSpawning = (rows?: ServerRow[]) => !!rows?.some((r) => r.status === 'spawning')
const heroSpawning = (h?: ServerHero) => h?.status === 'spawning'

export const useHubInfo = () => useQuery({ queryKey: ['hub-info'], queryFn: () => ds().getHubInfo() })
export const useStats = () => useQuery({ queryKey: ['stats'], queryFn: () => ds().getStats() })
export const useServers = () =>
  useQuery({
    queryKey: ['servers'],
    queryFn: () => ds().getServers(),
    refetchInterval: (q) => (serversSpawning(q.state.data) ? FAST_POLL : SLOW_POLL),
    refetchIntervalInBackground: false,
  })
export const useUsers = () => useQuery({ queryKey: ['users'], queryFn: () => ds().getUsers() })
export const useGroups = () => useQuery({ queryKey: ['groups'], queryFn: () => ds().getGroups() })
export const useEvents = () => useQuery({ queryKey: ['events'], queryFn: () => ds().getEvents() })
export const useTokens = () => useQuery({ queryKey: ['tokens'], queryFn: () => ds().getTokens() })
export const useTotalResources = () => useQuery({ queryKey: ['resources'], queryFn: () => ds().getTotalResources() })
export const useLabContainer = () => useQuery({ queryKey: ['lab-container'], queryFn: () => ds().getLabContainer() })
export const useSettings = () => useQuery({ queryKey: ['settings'], queryFn: () => ds().getSettings() })
export const useSettingsReference = () => useQuery({ queryKey: ['settings-ref'], queryFn: () => ds().getSettingsReference() })
export const useSentNotifications = () => useQuery({ queryKey: ['sent-notifications'], queryFn: () => ds().getSentNotifications() })
export const useGroupCorpus = () => useQuery({ queryKey: ['group-corpus'], queryFn: () => ds().getGroupCorpus() })
export const useUserCorpus = () => useQuery({ queryKey: ['user-corpus'], queryFn: () => ds().getUserCorpus() })

export const useUser = (name: string) =>
  useQuery({ queryKey: ['user', name], queryFn: () => ds().getUser(name), enabled: !!name })
export const useUserProfile = (name: string) =>
  useQuery({ queryKey: ['user-profile', name], queryFn: () => ds().getUserProfile(name), enabled: !!name })
export const useGroupConfig = (name: string) =>
  useQuery({ queryKey: ['group-config', name], queryFn: () => ds().getGroupConfig(name), enabled: !!name })
export const useServerHero = (user: string) =>
  useQuery({
    queryKey: ['hero', user],
    queryFn: () => ds().getServerHero(user),
    refetchInterval: (q) => (heroSpawning(q.state.data) ? FAST_POLL : SLOW_POLL),
    refetchIntervalInBackground: false,
  })
export const useSessionInfo = (user: string) =>
  useQuery({ queryKey: ['session', user], queryFn: () => ds().getSessionInfo(user) })
export const useUserVolumes = (user: string) =>
  useQuery({ queryKey: ['user-volumes', user], queryFn: () => ds().getUserVolumes(user), enabled: !!user })
export const useUserVolumeSizes = (user: string) =>
  useQuery({ queryKey: ['user-volume-sizes', user], queryFn: () => ds().getUserVolumeSizes(user), enabled: !!user })
export const useEffectiveGrants = (user: string) =>
  useQuery({ queryKey: ['grants', user], queryFn: () => ds().getEffectiveGrants(user), enabled: !!user })
