/* Mocked actions. Every Start / Stop / Restart / Authorize / Save / Delete /
 * Broadcast / Extend in the portal routes through mockAction - it shows a "(mock)"
 * toast and returns. There is deliberately NO write method on the hub client, so
 * a real mutation cannot leak even in live mode. */
import type { MessageInstance } from 'antd/es/message/interface'

let messageApi: MessageInstance | null = null

// bound once from inside antd's <App> (see layout/MessageBinder)
export function bindMessage(api: MessageInstance): void {
  messageApi = api
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
