import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppLayout } from './layout/AppLayout'
import { RouteError } from './app/RouteError'
import { RequireAdmin } from './app/RequireAdmin'
import { useRole } from './app/RoleContext'
import { portalBasename } from './services/hub/client'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Home from './pages/Home'
import Profile from './pages/Profile'
import Starting from './pages/Starting'
import Servers from './pages/Servers'
import Users from './pages/Users'
import NewUser from './pages/NewUser'
import BulkUsers from './pages/BulkUsers'
import BulkResult from './pages/BulkResult'
import UserConfig from './pages/UserConfig'
import ManageVolumes from './pages/ManageVolumes'
import Groups from './pages/Groups'
import NewGroup from './pages/NewGroup'
import GroupsExport from './pages/GroupsExport'
import GroupConfig from './pages/GroupConfig'
import LabContainer from './pages/LabContainer'
import Events from './pages/Events'
import Notifications from './pages/Notifications'
import Settings from './pages/Settings'
import SettingsReference from './pages/SettingsReference'
import Tokens from './pages/Tokens'
import Roles from './pages/Roles'
import DesignSystem from './pages/DesignSystem'

// Runtime-derived from the hub-injected shell (window.jhdata.base_url), so one
// build serves any base_url (/, /jupyterhub). Mock/dev falls back to BASE_URL.
const basename = portalBasename()

const usersParent = { label: 'Users', to: '/users' }
const groupsParent = { label: 'Groups', to: '/groups' }

// Profile is role-aware: an admin gets the full Configure-user screen scoped to
// themselves (UserConfig falls back to the logged-in username when there is no
// :name param); a plain user gets the self-service Profile page (own name/email/
// password only, with a current-password challenge - no admin-only controls and
// no admin-only /users fetch that would 403 for them).
function ProfileRoute() {
  const { role } = useRole()
  return role === 'admin' ? <UserConfig /> : <Profile />
}

export const router = createBrowserRouter(
  [
    { path: '/login', element: <Login /> },
    { path: '/signup', element: <Signup /> },
    {
      path: '/',
      element: <AppLayout />,
      errorElement: <RouteError />,
      children: [
        { index: true, element: <Navigate to="/home" replace /> },
        // Landing route is /home: the stock /hub/home built-in renders the portal
        // package's home.html, which is the SPA shell (template_dir shadows the
        // stock template), so the SPA owns /home directly.
        { path: 'home', handle: { crumb: 'Home' }, element: <Home /> },
        { path: 'profile', handle: { crumb: 'Profile' }, element: <ProfileRoute /> },
        // Spawn progress + live log tail. Not admin-gated: a plain user starts
        // their OWN server here; the backend endpoints enforce admin-or-self.
        { path: 'servers/:name/starting', handle: { crumb: 'Starting server' }, element: <Starting /> },
        { path: 'design-system', handle: { crumb: 'Design system' }, element: <DesignSystem /> },

        // Admin-only surfaces. RequireAdmin bounces non-admins to /home before
        // any admin-only query mounts. Server-side enforcement is the real
        // boundary; this is defense-in-depth + UX.
        {
          element: <RequireAdmin />,
          children: [
            { path: 'servers', handle: { crumb: 'Servers' }, element: <Servers /> },
            { path: 'servers/:name/volumes', handle: { crumb: 'Manage volumes', parent: { label: 'Servers', to: '/servers' } }, element: <ManageVolumes /> },

            { path: 'users', handle: { crumb: 'Users' }, element: <Users /> },
            { path: 'users/new', handle: { crumb: 'New user', parent: usersParent }, element: <NewUser /> },
            { path: 'users/bulk', handle: { crumb: 'Bulk add', parent: usersParent }, element: <BulkUsers /> },
            { path: 'users/bulk/result', handle: { crumb: 'Bulk result', parent: usersParent }, element: <BulkResult /> },
            { path: 'users/:name', handle: { crumb: 'Configure user', parent: usersParent }, element: <UserConfig /> },

            { path: 'groups', handle: { crumb: 'Groups' }, element: <Groups /> },
            { path: 'groups/new', handle: { crumb: 'New group', parent: groupsParent }, element: <NewGroup /> },
            { path: 'groups/export', handle: { crumb: 'Export groups', parent: groupsParent }, element: <GroupsExport /> },
            { path: 'groups/:name', handle: { crumb: 'Configure group', parent: groupsParent }, element: <GroupConfig /> },

            { path: 'lab-container', handle: { crumb: 'Lab Setup' }, element: <LabContainer /> },
            { path: 'events', handle: { crumb: 'Events' }, element: <Events /> },
            { path: 'notifications', handle: { crumb: 'Notifications' }, element: <Notifications /> },
            { path: 'settings', handle: { crumb: 'Settings' }, element: <Settings /> },
            { path: 'settings/reference', handle: { crumb: 'Full reference', parent: { label: 'Settings', to: '/settings' } }, element: <SettingsReference /> },
            { path: 'tokens', handle: { crumb: 'Tokens' }, element: <Tokens /> },
            { path: 'roles', handle: { crumb: 'Roles' }, element: <Roles /> },
          ],
        },

        { path: '*', element: <Navigate to="/home" replace /> },
      ],
    },
  ],
  { basename },
)
