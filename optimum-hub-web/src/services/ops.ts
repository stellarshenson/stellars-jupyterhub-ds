/* Live operation layer - the real writes behind every portal action.
 *
 * Each op is mode-aware: in mock mode it shows the "(mock)" toast and resolves
 * (the demo stays inert, no backend); in live mode it issues the real hub call,
 * shows a real success/error toast, and invalidates the affected React Query
 * keys so the views refetch. Server lifecycle, user create/delete/admin, group
 * CRUD + membership, tokens, broadcast, volume reset and session extend all go
 * through the standard JupyterHub API or the custom stellars-hub-services API;
 * authorize/discard + change-password go through NativeAuthenticator's handlers.
 *
 * The deep per-field group-policy editor (GroupPolicyTab) and a few unsupported
 * or client-only actions (signup-enable env, image pull, JSON export/download)
 * are intentionally not wired here - they keep their existing mock/client-side
 * behaviour. */
import { isMock } from './dataMode'
import { hubAuthForm, hubAuthGet, hubSend } from './hub/client'
import { invalidate, mockSuccess, notify } from './actions'

/** Run a live write with success/error toasts + cache invalidation; in mock mode
 * just toast. Returns the run() result (or undefined in mock mode). */
async function run<T>(
  label: string,
  fn: () => Promise<T>,
  keys: ReadonlyArray<readonly unknown[]> = [],
): Promise<T | undefined> {
  if (isMock()) {
    mockSuccess(label)
    return undefined
  }
  try {
    const out = await fn()
    notify.success(label)
    invalidate(...keys)
    return out
  } catch (e) {
    notify.error(`${label} failed: ${(e as Error).message}`)
    throw e
  }
}

const SERVER_KEYS = (user: string): unknown[][] => [['servers'], ['stats'], ['resources'], ['hero', user], ['session', user]]
const USER_KEYS = (name: string): unknown[][] => [['users'], ['stats'], ['user', name], ['servers']]
const GROUP_KEYS = (name?: string): unknown[][] => (name ? [['groups'], ['group-config', name], ['group-corpus']] : [['groups'], ['group-corpus']])

// ── Server lifecycle ────────────────────────────────────────────────────────
export const startServer = (user: string) =>
  run(`Started ${user}'s server`, () => hubSend('POST', `/users/${user}/server`), SERVER_KEYS(user))

export const stopServer = (user: string) =>
  run(`Stopped ${user}'s server`, () => hubSend('DELETE', `/users/${user}/server`), SERVER_KEYS(user))

export const restartServer = (user: string) =>
  run(`Restarted ${user}'s server`, () => hubSend('POST', `/users/${user}/restart-server`), SERVER_KEYS(user))

export const extendSession = (user: string, hours = 2) =>
  run(`Extended ${user}'s session by ${hours}h`, () => hubSend('POST', `/users/${user}/extend-session`, { hours }), [['session', user], ['servers']])

export const resetActivity = () =>
  run('Reset activity samples', () => hubSend('POST', '/activity/reset'), [['servers'], ['stats'], ['resources']])

// ── Users ─────────────────────────────────────────────────────────────────--
/** Idempotently set a user's NativeAuth authorisation. Unlike NativeAuth's
 * /authorize/{name} GET-toggle, this sets the requested state directly, so a
 * checkbox or stale value can never flip the wrong way. */
export const setUserAuthorization = (name: string, authorized: boolean) =>
  run(
    `${authorized ? 'Authorised' : 'De-authorised'} ${name}`,
    () => hubSend('POST', `/native-users/${encodeURIComponent(name)}/authorization`, { authorized }),
    USER_KEYS(name),
  )

export const discardUser = (name: string) =>
  run(`Discarded ${name}`, () => hubAuthGet(`/discard/${encodeURIComponent(name)}`), USER_KEYS(name))

export const createUser = (name: string) =>
  run(`Created user ${name}`, () => hubSend('POST', `/users/${encodeURIComponent(name)}`), USER_KEYS(name))

export const deleteUser = (name: string) =>
  run(`Removed user ${name}`, () => hubSend('DELETE', `/users/${encodeURIComponent(name)}`), USER_KEYS(name))

export const setAdmin = (name: string, admin: boolean) =>
  run(`${admin ? 'Granted' : 'Revoked'} admin for ${name}`, () => hubSend('PATCH', `/users/${encodeURIComponent(name)}`, { admin }), USER_KEYS(name))

export const renameUser = (name: string, newName: string) =>
  run(`Renamed ${name} to ${newName}`, () => hubSend('PATCH', `/users/${encodeURIComponent(name)}`, { name: newName }), USER_KEYS(name))

/** Admin sets another user's password (NativeAuth admin change-password). */
export const setUserPassword = (name: string, password: string) =>
  run(`Set password for ${name}`, async () => {
    const html = await hubAuthForm(`/change-password/${encodeURIComponent(name)}`, {
      new_password: password,
      new_password_confirmation: password,
    })
    if (/alert-danger/.test(html)) throw new Error('rejected (too short or too common)')
  })

/** Current user changes their own password (NativeAuth self change-password). */
export const changeOwnPassword = (oldPassword: string, password: string) =>
  run('Changed your password', async () => {
    const html = await hubAuthForm('/change-password', {
      old_password: oldPassword,
      new_password: password,
      new_password_confirmation: password,
    })
    if (/alert-danger/.test(html)) throw new Error('current password wrong, or new one too short/common')
  })

export interface Credential {
  username: string
  password: string
}
/** Fetch the auto-generated passwords cached when users were just created. */
export async function getCredentials(usernames: string[]): Promise<Credential[]> {
  if (isMock()) return usernames.map((u) => ({ username: u, password: 'mock-correct-horse-battery' }))
  const r = await hubSend<{ credentials?: Credential[] }>('POST', '/admin/credentials', { usernames })
  return r.credentials ?? []
}

// ── Group membership ─────────────────────────────────────────────────────────
export const addMember = (group: string, user: string) =>
  run(`Added ${user} to ${group}`, () => hubSend('POST', `/groups/${encodeURIComponent(group)}/users`, { users: [user] }), [['groups'], ['group-config', group], ['user', user]])

export const removeMember = (group: string, user: string) =>
  run(`Removed ${user} from ${group}`, () => hubSend('DELETE', `/groups/${encodeURIComponent(group)}/users`, { users: [user] }), [['groups'], ['group-config', group], ['user', user]])

// ── Groups ────────────────────────────────────────────────────────────────--
export const createGroup = (name: string, description = '') =>
  run(`Created group ${name}`, () => hubSend('POST', '/admin/groups/create', { name, description }), GROUP_KEYS(name))

export const deleteGroup = (name: string) =>
  run(`Deleted group ${name}`, () => hubSend('DELETE', `/admin/groups/${encodeURIComponent(name)}/delete`), GROUP_KEYS(name))

export const reorderGroups = (order: Array<{ name: string; priority: number }>) =>
  run('Reordered groups by priority', () => hubSend('POST', '/admin/groups/reorder', { groups: order }), [['groups']])

/** Save a group's general fields (description). Priority is owned by reorder. */
export const saveGroupConfig = (name: string, description: string) =>
  run(`Saved ${name}`, () => hubSend('PUT', `/admin/groups/${encodeURIComponent(name)}/config`, { description }), GROUP_KEYS(name))

// ── Tokens ────────────────────────────────────────────────────────────────--
export interface NewToken {
  token: string
  id: string
}
export async function createToken(user: string, note: string, scopes?: string[]): Promise<NewToken | undefined> {
  return run(
    `Requested token ${note}`,
    async () => {
      const body: Record<string, unknown> = { note }
      if (scopes && scopes.length) body.scopes = scopes
      const r = await hubSend<{ token: string; id: string }>('POST', `/users/${encodeURIComponent(user)}/tokens`, body)
      return { token: r.token, id: r.id }
    },
    [['tokens']],
  )
}

export const revokeToken = (user: string, id: string, note = '') =>
  run(`Revoked ${note || 'token'}`, () => hubSend('DELETE', `/users/${encodeURIComponent(user)}/tokens/${encodeURIComponent(id)}`), [['tokens']])

// ── Volumes ───────────────────────────────────────────────────────────────--
export const resetVolumes = (user: string, suffixes: string[]) =>
  run(`Reset volumes for ${user}`, () => hubSend('DELETE', `/users/${encodeURIComponent(user)}/manage-volumes`, { volumes: suffixes }), [['user-volumes', user], ['servers']])

// ── Notifications ─────────────────────────────────────────────────────────--
export interface BroadcastResult {
  total: number
  successful: number
  failed: number
}
export async function broadcast(message: string, variant: string, autoClose: boolean): Promise<BroadcastResult | undefined> {
  if (isMock()) {
    mockSuccess('Broadcast sent to 18 active servers')
    return { total: 18, successful: 18, failed: 0 }
  }
  try {
    const r = await hubSend<BroadcastResult>('POST', '/notifications/broadcast', { message, variant, autoClose })
    notify.success(`Broadcast delivered to ${r.successful}/${r.total} server(s)`)
    invalidate(['sent-notifications'])
    return r
  } catch (e) {
    notify.error(`Broadcast failed: ${(e as Error).message}`)
    throw e
  }
}
