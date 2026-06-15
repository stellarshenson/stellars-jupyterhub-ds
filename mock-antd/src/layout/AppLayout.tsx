/* The app frame on ProLayout: fixed sider (brand + role-gated menu + identity /
 * theme / sign-out foot), header breadcrumb, and the routed content. The command
 * palette, readonly banner, version badge and (Home-only) mock switch live here. */
import { ProLayout } from '@ant-design/pro-components'
import { Tooltip } from 'antd'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { Icon } from '../components/Icon'
import { useRole } from '../app/RoleContext'
import { useTheme } from '../theme/ThemeProvider'
import { PALETTES } from '../theme/tokens'
import { mockAction } from '../services/actions'
import { SiderMenu } from './SiderMenu'
import { Breadcrumbs } from './Breadcrumbs'
import { ThemeChanger } from './ThemeChanger'
import { MockSwitch } from './MockSwitch'
import { VersionBadge } from './VersionBadge'
import { CommandPalette } from './CommandPalette'
import { MessageBinder } from './MessageBinder'
import { ReadonlyBanner } from './ReadonlyBanner'

function SiderFoot() {
  const { role } = useRole()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 12, borderTop: '1px solid var(--color-border-subtle)' }}>
      <div style={{ fontSize: 13, lineHeight: 1.2 }}>
        {role === 'admin' ? 'admin' : 'alice'}
        <small style={{ display: 'block', color: 'var(--color-text-subtle)', fontSize: 11 }}>
          {role === 'admin' ? 'Administrator' : 'Data scientist'}
        </small>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <ThemeChanger />
        <Tooltip title="Sign out">
          <button
            onClick={() => mockAction('Sign out')}
            style={{ width: 28, height: 28, display: 'inline-grid', placeItems: 'center', border: 0, background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', borderRadius: 6 }}
            aria-label="Sign out"
          >
            <Icon name="logout" size={16} />
          </button>
        </Tooltip>
      </div>
    </div>
  )
}

export function AppLayout() {
  const { pathname } = useLocation()
  const { resolved } = useTheme()
  const p = PALETTES[resolved]
  const isHome = pathname === '/home' || pathname === '/'
  const logoSrc = `${import.meta.env.BASE_URL}brand/jh-logo.svg`

  return (
    <ProLayout
      title="Optimum Hub"
      layout="side"
      fixSiderbar
      fixedHeader
      collapsed={false}
      onCollapse={() => {}}
      siderWidth={248}
      location={{ pathname }}
      route={{ path: '/', routes: [] }}
      menuContentRender={() => <SiderMenu />}
      menuHeaderRender={() => (
        <Link to="/home" style={{ display: 'flex', alignItems: 'center', height: '100%' }} title="Optimum Hub">
          <img className="oh-brand-logo" src={logoSrc} alt="Stellars Tech AI Lab" />
        </Link>
      )}
      menuFooterRender={(props) => (props?.collapsed ? null : <SiderFoot />)}
      headerRender={false}
      collapsedButtonRender={false}
      footerRender={false}
      token={{
        bgLayout: p.bg,
        header: { colorBgHeader: p.bg, heightLayoutHeader: 56 },
        sider: { colorMenuBackground: p.bg, colorTextMenu: p.textMuted, colorTextMenuSelected: p.text, colorBgMenuItemSelected: p.accentSoft },
      }}
      contentStyle={{ padding: '28px 24px', background: p.bg }}
    >
      <MessageBinder />
      <CommandPalette />
      <div style={{ maxWidth: 1320, margin: '0 auto', width: '100%' }}>
        <div className="oh-topbar">
          <Breadcrumbs />
        </div>
        <ReadonlyBanner />
        <Outlet />
      </div>
      <VersionBadge />
      {isHome && <MockSwitch />}
    </ProLayout>
  )
}
