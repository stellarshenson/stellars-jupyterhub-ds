/* Topbar breadcrumb - "Optimum Hub / [parent] / page". Pages declare their crumb
 * (and optional clickable parent that returns to the list) via the route handle;
 * this reads the deepest match. */
import { Breadcrumb } from 'antd'
import { Link, useMatches } from 'react-router-dom'

export interface CrumbHandle {
  crumb: string
  parent?: { label: string; to: string }
}

export function Breadcrumbs() {
  const matches = useMatches()
  const withCrumb = [...matches].reverse().find((m) => (m.handle as CrumbHandle | undefined)?.crumb)
  const handle = withCrumb?.handle as CrumbHandle | undefined

  const items: Array<{ title: React.ReactNode }> = [{ title: <Link to="/home">Optimum Hub</Link> }]
  if (handle?.parent) items.push({ title: <Link to={handle.parent.to}>{handle.parent.label}</Link> })
  items.push({ title: <b>{handle?.crumb ?? ''}</b> })

  return <Breadcrumb items={items} />
}
