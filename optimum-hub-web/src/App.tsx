import { QueryClient, QueryClientProvider, keepPreviousData } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import { ThemeProvider } from './theme/ThemeProvider'
import { RoleProvider } from './app/RoleContext'
import { ServerLifecycleProvider } from './app/ServerLifecycle'
import { hydrateQueryCache, persistQueryCache } from './app/persistCache'
import { getDataSource } from './services/datasource'
import { router } from './router'

// Cache aggressively so revisiting a page renders the last data instantly while it
// revalidates in the background (no blank wait): keepPreviousData holds the prior
// result across key changes, gcTime keeps it warm after a view unmounts, and the
// cache is persisted to localStorage so a full reload also paints from cache first.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 30_000,
      gcTime: 30 * 60_000,
      placeholderData: keepPreviousData,
      retry: false,
    },
  },
})

// Rehydrate last session's cache before first render, then keep persisting it so
// the next portal load paints from cache and only revalidates what changed.
hydrateQueryCache(queryClient)
persistQueryCache(queryClient)

// Warm every key page's data at startup so navigating to any of them paints
// immediately instead of empty-then-lazy (routes are statically bundled, so the
// page code is already loaded - only the data is the gap). prefetchQuery honours
// staleTime, so a fresh hydrated cache is not refetched; a cold start fetches now.
function prefetchCore() {
  const ds = getDataSource()
  const warm: Array<[string, () => Promise<unknown>]> = [
    ['servers', () => ds.getServers()],
    ['users', () => ds.getUsers()],
    ['groups', () => ds.getGroups()],
    ['events', () => ds.getEvents()],
    ['stats', () => ds.getStats()],
    ['resources', () => ds.getTotalResources()],
    ['hub-info', () => ds.getHubInfo()],
    ['tokens', () => ds.getTokens()],
    ['lab-container', () => ds.getLabContainer()],
    ['settings', () => ds.getSettings()],
    ['sent-notifications', () => ds.getSentNotifications()],
  ]
  for (const [key, queryFn] of warm) void queryClient.prefetchQuery({ queryKey: [key], queryFn })
}
prefetchCore()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <RoleProvider>
          <ServerLifecycleProvider>
            <RouterProvider router={router} />
          </ServerLifecycleProvider>
        </RoleProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
