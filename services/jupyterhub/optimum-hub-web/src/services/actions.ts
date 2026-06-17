/* Action plumbing shared by the mock toasts and the live operation layer (ops.ts).
 *
 * - mockAction / mockSuccess: the "(mock)" toasts used in mock mode and by views
 *   whose backend write does not exist yet (client-only or unsupported actions).
 * - notify: real success/info/error toasts for live operations.
 * - bindQueryClient / invalidate: lets ops.ts refresh the React Query cache after
 *   a successful live write, without each call site threading the query client. */
import type { MessageInstance } from 'antd/es/message/interface'
import type { QueryClient } from '@tanstack/react-query'

let messageApi: MessageInstance | null = null
let queryClient: QueryClient | null = null

// bound once from inside antd's <App> (see layout/MessageBinder)
export function bindMessage(api: MessageInstance): void {
  messageApi = api
}

export function bindQueryClient(qc: QueryClient): void {
  queryClient = qc
}

/** Invalidate one or more React Query keys so dependent views refetch.
 *
 * `refetchType: 'all'` refetches matching queries immediately even when they are
 * not currently mounted (RQ's default only refetches active observers and leaves
 * unmounted ones stale-until-next-mount). After a mutation on a detail page the
 * list view is unmounted, so the default left it stale and it only refetched -
 * slowly, gated behind the heavy `/activity` call - once navigated back to. An
 * immediate background refetch means the users/groups/servers list is already
 * fresh by the time the user returns. */
export function invalidate(...keys: ReadonlyArray<readonly unknown[]>): void {
  if (!queryClient) return
  for (const key of keys) queryClient.invalidateQueries({ queryKey: key as unknown[], refetchType: 'all' })
}

/** Optimistically patch a cached query so a mutation shows in dependent views at
 * once - the same instant-effect the Groups page gets from its local row state,
 * but on the shared cache so it survives a detail-page -> list navigation. The
 * follow-up invalidate() reconciles against the server (and rolls back on error). */
export function patchQuery<T>(key: readonly unknown[], updater: (prev: T | undefined) => T | undefined): void {
  if (!queryClient) return
  queryClient.setQueryData(key as unknown[], updater)
}

export const notify = {
  success(text: string) {
    if (messageApi) messageApi.success(text)
    else console.info(text)
  },
  info(text: string) {
    if (messageApi) messageApi.info(text)
    else console.info(text)
  },
  error(text: string) {
    if (messageApi) messageApi.error(text)
    else console.error(text)
  },
}

export function mockAction(label: string): void {
  const text = `${label} (mock)`
  if (messageApi) messageApi.info(text)
  else console.info(text)
}

export function mockSuccess(label: string): void {
  if (messageApi) messageApi.success(`${label} (mock)`)
  else console.info(`${label} (mock)`)
}
