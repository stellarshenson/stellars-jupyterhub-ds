import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppLayout } from './layout/AppLayout'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Home from './pages/Home'
import Profile from './pages/Profile'
import Servers from './pages/Servers'
import Users from './pages/Users'
import NewUser from './pages/NewUser'
import BulkUsers from './pages/BulkUsers'
import BulkResult from './pages/BulkResult'
import UserConfig from './pages/UserConfig'
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
import DesignSystem from './pages/DesignSystem'
import DesignLanguage from './pages/DesignLanguage'

const basename = import.meta.env.BASE_URL.replace(/\/$/, '') || '/'

const usersParent = { label: 'Users', to: '/users' }
const groupsParent = { label: 'Groups', to: '/groups' }

export const router = createBrowserRouter(
  [
    { path: '/login', element: <Login /> },
    { path: '/signup', element: <Signup /> },
    {
      path: '/',
      element: <AppLayout />,
      children: [
        { index: true, element: <Navigate to="/home" replace /> },
        { path: 'home', handle: { crumb: 'Home' }, element: <Home /> },
        { path: 'profile', handle: { crumb: 'Profile' }, element: <Profile /> },

        { path: 'servers', handle: { crumb: 'Servers' }, element: <Servers /> },

        { path: 'users', handle: { crumb: 'Users' }, element: <Users /> },
        { path: 'users/new', handle: { crumb: 'New user', parent: usersParent }, element: <NewUser /> },
        { path: 'users/bulk', handle: { crumb: 'Bulk add', parent: usersParent }, element: <BulkUsers /> },
        { path: 'users/bulk/result', handle: { crumb: 'Bulk result', parent: usersParent }, element: <BulkResult /> },
        { path: 'users/:name', handle: { crumb: 'Configure user', parent: usersParent }, element: <UserConfig /> },

        { path: 'groups', handle: { crumb: 'Groups' }, element: <Groups /> },
        { path: 'groups/new', handle: { crumb: 'New group', parent: groupsParent }, element: <NewGroup /> },
        { path: 'groups/export', handle: { crumb: 'Export groups', parent: groupsParent }, element: <GroupsExport /> },
        { path: 'groups/:name', handle: { crumb: 'Configure group', parent: groupsParent }, element: <GroupConfig /> },

        { path: 'lab-container', handle: { crumb: 'Lab Container' }, element: <LabContainer /> },
        { path: 'events', handle: { crumb: 'Events' }, element: <Events /> },
        { path: 'notifications', handle: { crumb: 'Notifications' }, element: <Notifications /> },
        { path: 'settings', handle: { crumb: 'Settings' }, element: <Settings /> },
        { path: 'settings/reference', handle: { crumb: 'Full reference', parent: { label: 'Settings', to: '/settings' } }, element: <SettingsReference /> },
        { path: 'tokens', handle: { crumb: 'Tokens' }, element: <Tokens /> },
        { path: 'design-system', handle: { crumb: 'Design system' }, element: <DesignSystem /> },
        { path: 'design-language', handle: { crumb: 'Design language' }, element: <DesignLanguage /> },

        { path: '*', element: <Navigate to="/home" replace /> },
      ],
    },
  ],
  { basename },
)
