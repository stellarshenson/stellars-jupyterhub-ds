/* Topbar breadcrumb - "Duoptimum Hub / [parent] / page". Pages declare their crumb
 * (and optional clickable parent that returns to the list) via the route handle;
 * this reads the deepest match. */
import { Breadcrumb } from 'antd'
import { Link, useLocation, useMatches } from 'react-router-dom'

export interface CrumbHandle {
  crumb: string
  parent?: { label: string; to: string }
}

export function Breadcrumbs() {
  const matches = useMatches()
  const { state } = useLocation()
  const withCrumb = [...matches].reverse().find((m) => (m.handle as CrumbHandle | undefined)?.crumb)
  const handle = withCrumb?.handle as CrumbHandle | undefined

  // a screen reachable from more than one place (e.g. Manage volumes from Servers
  // OR Home) carries its real origin in the nav state; it wins over the static
  // route parent so the breadcrumb reflects the path actually taken.
  const origin = (state as { from?: { to: string; label: string } } | null)?.from
  const parent = origin ?? handle?.parent

  const items: Array<{ title: React.ReactNode }> = [{ title: <Link to="/home">Duoptimum Hub</Link> }]
  if (parent) items.push({ title: <Link to={parent.to}>{parent.label}</Link> })
  items.push({ title: <b>{handle?.crumb ?? ''}</b> })

  return <Breadcrumb items={items} />
}
