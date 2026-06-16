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

/** Invalidate one or more React Query keys so dependent views refetch. */
export function invalidate(...keys: ReadonlyArray<readonly unknown[]>): void {
  if (!queryClient) return
  for (const key of keys) queryClient.invalidateQueries({ queryKey: key as unknown[] })
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
