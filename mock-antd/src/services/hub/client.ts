/* Readonly hub REST client. GET only - auth rides the hub session cookie
 * (credentials: include), so no API token is needed. Base path is the hub API
 * under the platform prefix; in dev the Vite proxy forwards it to the hub. */
import { PLATFORM } from '../config'

const API_BASE = `${PLATFORM.baseUrl}/hub/api`

export async function hubGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) throw new Error(`Hub GET ${path} -> ${res.status}`)
  return (await res.json()) as T
}
