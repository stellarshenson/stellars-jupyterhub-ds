/* The app frame on ProLayout: fixed sider (brand + role-gated menu + identity /
 * sign-out foot), a top header carrying the breadcrumb (left) and the standard
 * antd header controls - language + theme dropdowns (right) - and a footer with
 * the platform + JupyterHub versions shown antd-style as tags. The command
 * palette, readonly banner and (Home-only) mock switch live in the content. */
import { ProLayout } from '@ant-design/pro-components'
import { Button, Dropdown, Tag, Tooltip } from 'antd'
import { GlobalOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Icon } from '../components/Icon'
import type { IconKey } from '../components/Icon'
import { useRole } from '../app/RoleContext'
import { useTheme } from '../theme/ThemeProvider'
import { PALETTES } from '../theme/tokens'
import type { ThemeMode } from '../theme/tokens'
import { portalAssetBase } from '../services/hub/client'
import { useHubInfo } from '../hooks/queries'
import { mockAction } from '../services/actions'
import { hubUrl } from '../services/hub/client'
import { useIsMobile } from '../lib/useIsMobile'
import { SiderMenu } from './SiderMenu'
import { Breadcrumbs } from './Breadcrumbs'
import { MockSwitch } from './MockSwitch'
import { CommandPalette } from './CommandPalette'
import { MessageBinder } from './MessageBinder'
import { ReadonlyBanner } from './ReadonlyBanner'

const THEME_MODES: Array<{ mode: ThemeMode; icon: IconKey; label: string }> = [
  { mode: 'light', icon: 'sun', label: 'Light' },
  { mode: 'dark', icon: 'moon', label: 'Dark' },
  { mode: 'system', icon: 'monitor', label: 'System' },
]

const LANGS: Array<{ key: string; label: string }> = [
  { key: 'en', label: 'English' },
  { key: 'pl', label: 'Polski' },
]

function LanguageControl() {
  const [lang, setLang] = useState('en')
  return (
    <Dropdown
      trigger={['click']}
      menu={{
        items: LANGS,
        selectable: true,
        selectedKeys: [lang],
        onClick: ({ key }) => { setLang(key); mockAction(`Language: ${LANGS.find((l) => l.key === key)?.label}`) },
      }}
    >
      <Tooltip title="Language">
        <Button type="text" icon={<GlobalOutlined />} aria-label="Language" />
      </Tooltip>
    </Dropdown>
  )
}

function ThemeControl() {
  const { mode, setMode } = useTheme()
  const current = THEME_MODES.find((m) => m.mode === mode) ?? THEME_MODES[0]
  return (
    <Dropdown
      trigger={['click']}
      menu={{
        items: THEME_MODES.map((m) => ({ key: m.mode, label: m.label, icon: <Icon name={m.icon} size={14} /> })),
        selectable: true,
        selectedKeys: [mode],
        onClick: ({ key }) => setMode(key as ThemeMode),
      }}
    >
      <Tooltip title="Theme">
        <Button type="text" icon={<Icon name={current.icon} size={16} />} aria-label="Theme" />
      </Tooltip>
    </Dropdown>
  )
}

function SiderFoot() {
  const { role, username, live } = useRole()
  const navigate = useNavigate()
  const signOut = () => {
    if (live) {
      window.location.assign(hubUrl('/logout'))
      return
    }
    mockAction('Signed out')
    navigate('/login')
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, padding: 12, borderTop: '1px solid var(--color-border-subtle)' }}>
      <div style={{ fontSize: 13, lineHeight: 1.2, minWidth: 0 }}>
        {username}
        <small style={{ display: 'block', color: 'var(--color-text-subtle)', fontSize: 11 }}>
          {role === 'admin' ? 'Administrator' : 'Data scientist'}
        </small>
      </div>
      <Tooltip title="Sign out">
        <button
          onClick={signOut}
          style={{ width: 28, height: 28, display: 'inline-grid', placeItems: 'center', border: 0, background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', borderRadius: 6 }}
          aria-label="Sign out"
        >
          <Icon name="logout" size={16} />
        </button>
      </Tooltip>
    </div>
  )
}

/* Thin rectangular grab handle straddling the sider's right edge at mid-height.
 * Fixed-positioned so it tracks the sider width; no icon. */
function SiderHandle({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <Tooltip title={collapsed ? 'Expand' : 'Collapse'} placement="right">
      <button
        className="oh-sider-handle"
        onClick={onToggle}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        style={{
          position: 'fixed', left: collapsed ? 64 : 248, top: '50%', transform: 'translate(-50%, -50%)',
          width: 6, height: 44, padding: 0, border: 0, borderRadius: 3,
          cursor: 'pointer', zIndex: 101, transition: 'left .2s, background-color .12s',
        }}
      />
    </Tooltip>
  )
}

function VersionFooter() {
  const { data: hub } = useHubInfo()
  // JupyterHub major derived from the live version (5.5.0 -> "5"), not hardcoded
  const hubMajor = hub?.version ? hub.version.split('.')[0] : '5'
  const stackChips = [
    { k: 'JupyterHub', v: hubMajor, c: '#d97f3f' },
    { k: 'JupyterLab', v: '4', c: '#d97f3f' },
    { k: 'Ant Design', v: '6', c: '#4f86d6' },
  ]
  const tag = { background: 'var(--color-surface-active)', color: 'var(--color-text-muted)', borderRadius: 4, marginInline: 4 }
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', gap: 12, padding: '14px 0', color: 'var(--color-text-subtle)', fontSize: 12 }}>
      <span>
        Optimum Hub<Tag bordered={false} style={tag}>v{__APP_VERSION__}</Tag>
        <span style={{ margin: '0 6px' }}>·</span>
        JupyterHub<Tag bordered={false} style={tag}>v{hub?.version ?? '…'}</Tag>
      </span>
      <span className="oh-techchips" style={{ marginTop: 0 }}>
        {stackChips.map((c) => (
          <span className="oh-chip" key={c.k}>
            <span className="k">{c.k}</span>
            <span className="v" style={{ background: c.c }}>{c.v}</span>
          </span>
        ))}
      </span>
    </div>
  )
}

export function AppLayout() {
  const { pathname } = useLocation()
  const { resolved } = useTheme()
  const { live } = useRole()
  const p = PALETTES[resolved]
  const isHome = pathname === '/dashboard' || pathname === '/'
  const logoSrc = `${portalAssetBase()}brand/jh-logo.svg`
  const markSrc = `${portalAssetBase()}brand/jl-logo.svg`
  const [collapsed, setCollapsed] = useState(false)
  // below the mobile breakpoint we drop the sider menu entirely (the mobile home
  // is the whole surface) and never render the collapse handle
  const isMobile = useIsMobile()

  return (
    <ProLayout
      title="Optimum Hub"
      layout="side"
      fixSiderbar
      fixedHeader
      collapsed={collapsed}
      onCollapse={setCollapsed}
      siderWidth={248}
      location={{ pathname }}
      route={{ path: '/', routes: [] }}
      menuRender={isMobile ? false : undefined}
      menuContentRender={(props) => <SiderMenu collapsed={!!props?.collapsed} />}
      menuHeaderRender={(_logo, _title, props) => (
        <Link to="/dashboard" style={{ display: 'flex', alignItems: 'center', justifyContent: props?.collapsed ? 'center' : 'flex-start', height: '100%', flex: 1, minWidth: 0 }} title="Optimum Hub">
          {props?.collapsed
            ? <img src={markSrc} alt="Optimum Hub" style={{ width: 30, height: 30, objectFit: 'contain' }} />
            : <img className="oh-brand-logo" src={logoSrc} alt="Stellars Tech AI Lab" />}
        </Link>
      )}
      menuFooterRender={(props) => (props?.collapsed ? null : <SiderFoot />)}
      actionsRender={() => [<LanguageControl key="lang" />, <ThemeControl key="theme" />]}
      collapsedButtonRender={false}
      footerRender={() => <VersionFooter />}
      token={{
        bgLayout: p.bg,
        header: { colorBgHeader: p.bg, heightLayoutHeader: 64 },
        sider: { colorMenuBackground: p.bg, colorTextMenu: p.textMuted, colorTextMenuSelected: p.text, colorBgMenuItemSelected: p.accentSoft },
      }}
      contentStyle={{ padding: '0 24px 8px', background: p.bg }}
    >
      <MessageBinder />
      <CommandPalette />
      {!isMobile && <SiderHandle collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />}
      <div style={{ maxWidth: 1320, margin: '0 auto', width: '100%' }}>
        <div className="oh-topbar">
          <Breadcrumbs />
        </div>
        <ReadonlyBanner />
        <Outlet />
      </div>
      {isHome && !live && <MockSwitch />}
    </ProLayout>
  )
}
