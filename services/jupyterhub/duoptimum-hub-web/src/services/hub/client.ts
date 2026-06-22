/* Hub REST client. Same-origin, cookie-authenticated (auth rides the hub
 * session cookie, credentials: include). Every call carries the hub's XSRF
 * submit-token as the X-XSRFToken header.
 *
 * JupyterHub enforces XSRF on cookie-authenticated state-changing requests
 * (POST/DELETE/PATCH); GET/HEAD/OPTIONS are exempt (`_xsrf_safe_methods`), so
 * the header on GETs is inert but harmless and kept for uniformity. The valid
 * submit-token is NOT the raw `_xsrf` cookie value: it is hub-signed
 * (`_get_signed_value_urlsafe` with the hub secret) and handed only to pages the
 * hub itself renders, where it lands in `window.jhdata.xsrf_token`. The portal
 * is served by the hub (PortalHandler renders the shell, so
 * `BaseHandler.render_template` injects the token), so we read it from there.
 * The `_xsrf` cookie is a dev-proxy fallback only.
 *
 * Two surfaces:
 *   - the JSON REST API under {hubBase}/hub/api  (hubGet / hubSend)
 *   - NativeAuthenticator's form/redirect handlers under {hubBase}/hub
 *     (hubAuthGet for the authorize/discard GET-toggles, hubAuthForm for the
 *     change-password POSTs).
 *
 * hubBase is the hub's deploy prefix: '' when the hub serves at root
 * (base_url=/), '/jupyterhub' for the repo-default path mount. Set at build
 * time via VITE_HUB_BASE; same-origin so a relative path is all that's needed. */

/* Deploy prefix resolved at RUNTIME from the hub-injected shell, so one build
 * works under any base_url (/, /jupyterhub, ...). window.jhdata.base_url is the
 * hub prefix with a trailing slash (`/hub/`, `/jupyterhub/hub/`); strip it to get
 * HUB_ROOT. Falls back to the build-time VITE_HUB_BASE for the dev proxy / mock
 * mode, where the shell is absent. */
function pageHubRoot(): string | null {
  const b = typeof window !== 'undefined' ? window.jhdata?.base_url : undefined
  return b ? b.replace(/\/$/, '') : null // '/hub' or '/jupyterhub/hub'
}
const HUB_ROOT = pageHubRoot() ?? `${(import.meta.env.VITE_HUB_BASE ?? '').replace(/\/$/, '')}/hub`
const HUB_BASE = HUB_ROOT.replace(/\/hub$/, '') // '' or '/jupyterhub'
const API_BASE = `${HUB_ROOT}/api`

/** Router basename for the hub-served SPA, resolved at runtime so one build works
 * under any base_url. Mock/dev (no shell) uses the build-time base. */
export function portalBasename(): string {
  const root = pageHubRoot()
  if (root) return root // SPA mounts at the hub root (no /portal segment)
  return import.meta.env.BASE_URL.replace(/\/$/, '') || '/'
}

/** Runtime URL prefix (trailing slash) for bundled portal assets served by the
 * hub - brand images, favicon. One build works under any base_url; mock/dev uses
 * the build-time base. */
export function portalAssetBase(): string {
  const root = pageHubRoot()
  if (root) return `${root}/` // brand/favicon served at the hub root (no /portal)
  return import.meta.env.BASE_URL // already ends with '/'
}

/** Bootstrap data the hub injects into every page it renders (see page.html /
 * the portal shell). Present on the hub-served portal; absent under the dev proxy. */
interface JhData {
  base_url?: string
  prefix?: string
  user?: string
  admin_access?: boolean
  gpu_enabled?: boolean // authoritative: does this platform have GPU (sidecar found one)
  admin_user?: string // the platform admin username (JUPYTERHUB_ADMIN_USERNAME)
  hub_name?: string // hub display name (JUPYTERHUB_BRANDING_HUB_NAME): logo tooltip + login/signup text; default "Duoptimum Hub"
  stage?: string // environment-stage label for the header badge (JUPYTERHUB_BRANDING_STAGE); empty/absent = no badge
  xsrf_token?: string
  // Set only on the overridden login/signup pages: the SPA renders the matching
  // antd auth screen instead of the app, and these carry the NativeAuth context.
  authPage?: 'login' | 'signup'
  authError?: string // login: failed-login message
  authNext?: string // login: url-escaped `next` to return to after auth
  authMessage?: string // signup: result message from NativeAuth
  authAlert?: string // signup: 'alert-success' | 'alert-danger' | 'alert-info'
  askEmail?: boolean // signup: whether NativeAuth asks for an email
}
declare global {
  interface Window {
    jhdata?: JhData
  }
}

/** Identity the hub embedded in the page shell, available before any fetch. */
export function pageUser(): { name: string; admin: boolean } | null {
  const d = typeof window !== 'undefined' ? window.jhdata : undefined
  if (!d || !d.user) return null
  return { name: d.user, admin: !!d.admin_access }
}

export class HubError extends Error {
  status: number
  detail: string
  constructor(status: number, what: string, detail = '') {
    super(`Hub ${what} -> ${status}${detail ? `: ${detail}` : ''}`)
    this.status = status
    this.detail = detail
  }
}

/** The hub's XSRF submit-token. Prefers the token the hub injected into the
 * rendered page (`window.jhdata.xsrf_token`); falls back to the `_xsrf` cookie
 * (only usable under the dev proxy, where the cookie is same-path-readable). */
function xsrf(): string {
  const t = typeof window !== 'undefined' ? window.jhdata?.xsrf_token : undefined
  if (t) return t
  if (typeof document === 'undefined') return ''
  const m = document.cookie.match(/(?:^|;\s*)_xsrf=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : ''
}

/** The hub XSRF token, for callers that can't use the fetch helpers (e.g. an
 * EventSource, which cannot set headers, must pass `_xsrf` as a query param). */
export function xsrfToken(): string {
  return xsrf()
}

/** Absolute URL for a hub page under {hubBase}/hub (login, logout, signup). */
export function hubUrl(path: string): string {
  return `${HUB_ROOT}${path}`
}

/** Absolute URL of a user's running JupyterLab server ({hubBase}/user/{name}/). */
export function userServerUrl(name: string): string {
  return `${HUB_BASE}/user/${encodeURIComponent(name)}/`
}

/** Send the browser to the hub login page, preserving where to come back to. */
export function loginRedirect(): never {
  const next = encodeURIComponent(window.location.pathname + window.location.search)
  window.location.assign(`${HUB_ROOT}/login?next=${next}`)
  // unreachable in practice; satisfies `never`
  throw new HubError(401, 'redirecting to login')
}

export async function hubGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json', 'X-XSRFToken': xsrf() },
  })
  if (!res.ok) throw new HubError(res.status, `GET ${path}`)
  return (await res.json()) as T
}

export type WriteMethod = 'POST' | 'PATCH' | 'PUT' | 'DELETE'

export async function hubSend<T = unknown>(method: WriteMethod, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json', 'X-XSRFToken': xsrf() }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: 'include',
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new HubError(res.status, `${method} ${path}`, await res.text().catch(() => ''))
  const txt = await res.text()
  return (txt ? JSON.parse(txt) : undefined) as T
}

/** NativeAuth GET-toggle (authorize / discard). Follows the redirect to the
 * authorize page; a non-error final response means the toggle ran. */
export async function hubAuthGet(path: string): Promise<void> {
  const res = await fetch(`${HUB_ROOT}${path}`, { method: 'GET', credentials: 'include' })
  if (!res.ok) throw new HubError(res.status, `GET /hub${path}`)
}

/** NativeAuth form POST (change-password). x-www-form-urlencoded + XSRF header.
 * Returns the response HTML so the caller can detect an in-body failure (these
 * handlers render `alert-danger` on a 200 rather than returning an error code). */
export async function hubAuthForm(path: string, fields: Record<string, string>): Promise<string> {
  const res = await fetch(`${HUB_ROOT}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-XSRFToken': xsrf(), 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(fields),
  })
  const body = await res.text().catch(() => '')
  if (!res.ok) throw new HubError(res.status, `POST /hub${path}`, body)
  return body
}

export interface HubCurrentUser {
  name: string
  admin: boolean
  groups: string[]
  scopes?: string[]
}

/** The authenticated identity. 401/403 here means no valid session -> login. */
export async function getCurrentUser(): Promise<HubCurrentUser> {
  const res = await fetch(`${API_BASE}/user`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json', 'X-XSRFToken': xsrf() },
  })
  if (res.status === 401 || res.status === 403) loginRedirect()
  if (!res.ok) throw new HubError(res.status, 'GET /user')
  return (await res.json()) as HubCurrentUser
}
