/* Route guard: admin-only surfaces.
 *
 * The hub serves the portal behind @web.authenticated, and every admin REST
 * endpoint enforces `current_user.admin` server-side - so this guard cannot be
 * the security boundary, and is not relied on as one. It is defense-in-depth and
 * UX: a non-admin who types an admin URL (or follows a stale link) is bounced to
 * Home instead of mounting a page that fires admin-only calls and 403s. The role
 * is resolved from the real session before children render (see RoleContext
 * `ready` gate), so there is no flash of admin chrome. */
import { Navigate, Outlet } from 'react-router-dom'
import { useRole } from './RoleContext'

export function RequireAdmin() {
  const { role } = useRole()
  if (role !== 'admin') return <Navigate to="/home" replace />
  return <Outlet />
}
