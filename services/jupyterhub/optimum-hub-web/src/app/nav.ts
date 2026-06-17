/* Role-gated navigation model + command-palette actions, ported from the static
 * mock's app.js. Admin watches the fleet and administers it under one
 * Administration section; a plain user only operates their own server. */
import type { IconKey } from '../components/Icon'
import type { Role } from '../services/types'

export interface NavLeaf {
  id: string
  label: string
  icon: IconKey
  path: string
  badge?: string
}
export interface NavParent {
  id: string
  label: string
  icon: IconKey
  children: NavLeaf[]
}
export type NavNode = NavLeaf | NavParent
export interface NavGroup {
  group: string
  items: NavNode[]
}

export function isParent(n: NavNode): n is NavParent {
  return (n as NavParent).children !== undefined
}

export const NAV_ADMIN: NavGroup[] = [
  {
    group: '',
    items: [
      { id: 'home', label: 'Home', icon: 'grid', path: '/dashboard' },
      { id: 'profile', label: 'Profile', icon: 'user', path: '/profile' },
    ],
  },
  {
    group: 'Administration',
    items: [
      { id: 'servers', label: 'Servers', icon: 'server', path: '/servers' },
      { id: 'users', label: 'Users', icon: 'users', path: '/users', badge: '2' },
      { id: 'groups', label: 'Groups', icon: 'group', path: '/groups' },
      { id: 'lab-container', label: 'Lab Setup', icon: 'box', path: '/lab-container' },
      { id: 'events', label: 'Events', icon: 'activity', path: '/events' },
      { id: 'notifications', label: 'Notifications', icon: 'megaphone', path: '/notifications' },
      {
        id: 'advanced',
        label: 'Advanced',
        icon: 'dots',
        children: [
          { id: 'settings', label: 'Settings', icon: 'settings', path: '/settings' },
          { id: 'tokens', label: 'Tokens', icon: 'key', path: '/tokens' },
        ],
      },
    ],
  },
]

export const NAV_USER: NavGroup[] = [
  {
    group: '',
    items: [
      { id: 'home', label: 'Home', icon: 'grid', path: '/dashboard' },
      { id: 'profile', label: 'Profile', icon: 'user', path: '/profile' },
    ],
  },
]

export function navFor(role: Role): NavGroup[] {
  return role === 'admin' ? NAV_ADMIN : NAV_USER
}

export function navLeaves(role: Role): NavLeaf[] {
  const out: NavLeaf[] = []
  navFor(role).forEach((g) =>
    g.items.forEach((n) => {
      if (isParent(n)) n.children.forEach((c) => out.push(c))
      else out.push(n)
    }),
  )
  return out
}

export type CmdAction =
  | { group: string; icon: IconKey; label: string; kind: 'nav'; to: string; hint?: string }
  | { group: string; icon: IconKey; label: string; kind: 'action'; action: 'open-server' | 'restart-server'; hint?: string }

export const ACTIONS_ADMIN: CmdAction[] = [
  { group: 'Create', icon: 'user', label: 'Add user', hint: 'U', kind: 'nav', to: '/users/new' },
  { group: 'Create', icon: 'group', label: 'Create group', hint: 'G', kind: 'nav', to: '/groups/new' },
  { group: 'Navigate', icon: 'activity', label: 'Events log', kind: 'nav', to: '/events' },
  { group: 'Navigate', icon: 'megaphone', label: 'Broadcast notification', kind: 'nav', to: '/notifications' },
]

export const ACTIONS_USER: CmdAction[] = [
  { group: 'My server', icon: 'play', label: 'Open my server', kind: 'action', action: 'open-server' },
  { group: 'My server', icon: 'restart', label: 'Restart my server', kind: 'action', action: 'restart-server' },
]

export function actionsFor(role: Role): CmdAction[] {
  return role === 'admin' ? ACTIONS_ADMIN : ACTIONS_USER
}
