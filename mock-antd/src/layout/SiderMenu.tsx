/* The sider navigation - a full antd Menu so the "Administration" group label and
 * the collapsible "Advanced" submenu match the static mock exactly. Rendered
 * inside ProLayout via menuContentRender. The Users badge shows the live pending
 * count. */
import { Menu } from 'antd'
import type { MenuProps } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'
import { Icon } from '../components/Icon'
import { useRole } from '../app/RoleContext'
import { isParent, navFor, navLeaves } from '../app/nav'
import type { NavNode } from '../app/nav'
import { useStats } from '../hooks/queries'

type Items = NonNullable<MenuProps['items']>

function countBadge(n: number) {
  return (
    <span
      style={{
        marginLeft: 'auto',
        display: 'inline-flex',
        alignItems: 'center',
        height: 18,
        lineHeight: 1,
        fontSize: 11,
        fontWeight: 600,
        padding: '0 6px',
        borderRadius: 9,
        background: 'var(--color-surface-active)',
        color: 'var(--color-text-muted)',
      }}
    >
      {n}
    </span>
  )
}

function leafLabel(label: string, badge?: number) {
  if (!badge) return label
  return (
    <span style={{ display: 'flex', alignItems: 'center', width: '100%' }}>
      <span>{label}</span>
      {countBadge(badge)}
    </span>
  )
}

export function SiderMenu() {
  const { role } = useRole()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const { data: stats } = useStats()
  const pending = stats?.users.pending ?? 0

  const toItem = (n: NavNode): Items[number] => {
    if (isParent(n)) {
      return {
        key: n.id,
        icon: <Icon name={n.icon} size={18} />,
        label: n.label,
        children: n.children.map((c) => ({ key: c.path, icon: <Icon name={c.icon} size={18} />, label: c.label })),
      }
    }
    const badge = n.id === 'users' ? pending : undefined
    return { key: n.path, icon: <Icon name={n.icon} size={18} />, label: leafLabel(n.label, badge) }
  }

  const items: Items = []
  navFor(role).forEach((g) => {
    if (g.group) items.push({ type: 'group', label: g.group, children: g.items.map(toItem) })
    else g.items.forEach((n) => items.push(toItem(n)))
  })

  // selection: the deepest nav path that prefixes the current location
  const active = navLeaves(role)
    .filter((l) => pathname === l.path || pathname.startsWith(l.path + '/'))
    .sort((a, b) => b.path.length - a.path.length)[0]
  const selectedKeys = active ? [active.path] : []
  const advancedActive = active?.path === '/settings' || active?.path === '/tokens'

  return (
    <Menu
      mode="inline"
      items={items}
      selectedKeys={selectedKeys}
      defaultOpenKeys={advancedActive ? ['advanced'] : []}
      style={{ border: 'none', background: 'transparent' }}
      onClick={({ key }) => {
        if (key.startsWith('/')) navigate(key)
      }}
    />
  )
}
