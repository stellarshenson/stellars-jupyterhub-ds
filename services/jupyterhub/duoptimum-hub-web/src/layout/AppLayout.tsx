/* The app frame on ProLayout: fixed sider (brand + role-gated menu + identity /
 * sign-out foot), a top header carrying the breadcrumb (left) and the standard
 * antd header controls - language + theme dropdowns (right) - and a footer with
 * the platform + JupyterHub versions shown antd-style as tags. The command
 * palette lives in the content. */
import { ProLayout } from '@ant-design/pro-components'
import { Button, Dropdown, Tag, Tooltip } from 'antd'
import { GlobalOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { Icon } from '../components/Icon'
import type { IconKey } from '../components/Icon'
import { useRole } from '../app/RoleContext'
import { hubName } from '../app/capabilities'
import { useTheme } from '../theme/ThemeProvider'
import { PALETTES } from '../theme/tokens'
import type { ThemeMode } from '../theme/tokens'
import { portalAssetBase } from '../services/hub/client'
import { useHubInfo } from '../hooks/queries'
import { notify } from '../services/actions'
import { hubUrl } from '../services/hub/client'
import { useIsMobile } from '../lib/useIsMobile'
import { SiderMenu } from './SiderMenu'
import { Breadcrumbs } from './Breadcrumbs'
import { CommandPalette } from './CommandPalette'
import { MessageBinder } from './MessageBinder'
import { StageBadge } from '../components/StageBadge'
import { HubConnectionIndicator } from '../components/HubConnectionIndicator'
import { ConnectionStatusPill } from '../components/ConnectionStatusPill'

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
        onClick: ({ key }) => { setLang(key); notify.info(`Language: ${LANGS.find((l) => l.key === key)?.label}`) },
      }}
    >
      {/* no Tooltip: it overlapped the open dropdown menu (aria-label keeps a11y) */}
      <Button type="text" icon={<GlobalOutlined />} aria-label="Language" />
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
      {/* no Tooltip: it overlapped the open dropdown menu (aria-label keeps a11y) */}
      <Button type="text" icon={<Icon name={current.icon} size={16} />} aria-label="Theme" />
    </Dropdown>
  )
}

function SiderFoot() {
  const { role, username } = useRole()
  const signOut = () => window.location.assign(hubUrl('/logout'))
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
        className="doh-sider-handle"
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
  const tag = { background: 'var(--color-surface-active)', color: 'var(--color-text-muted)', borderRadius: 4, marginInline: 4 }
  // click the version to copy the full version + build id to the clipboard
  const fullVersion = `Duoptimum Hub v${__APP_VERSION__} build ${__BUILD_ID__}`
  const copyVersion = () => {
    if (!navigator.clipboard) { notify.error('Clipboard unavailable'); return }
    navigator.clipboard.writeText(fullVersion).then(() => notify.success('Version copied'), () => notify.error('Copy failed'))
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', gap: 12, padding: '14px 0', color: 'var(--color-text-subtle)', fontSize: 12 }}>
      <span>
        <Tooltip title={`build ${__BUILD_ID__}`}>
          <span onClick={copyVersion} style={{ cursor: 'pointer' }}>Duoptimum Hub<Tag bordered={false} style={tag}>v{__APP_VERSION__}</Tag></span>
        </Tooltip>
        <span style={{ margin: '0 6px' }}>·</span>
        JupyterHub<Tag bordered={false} style={tag}>v{hub?.version ?? '…'}</Tag>
      </span>
    </div>
  )
}

export function AppLayout() {
  const { pathname } = useLocation()
  const { resolved } = useTheme()
  const p = PALETTES[resolved]
  const logoSrc = `${portalAssetBase()}brand/jh-logo.svg`
  const markSrc = `${portalAssetBase()}brand/jl-logo.svg`
  const [collapsed, setCollapsed] = useState(false)
  // below the mobile breakpoint we drop the sider menu entirely (the mobile home
  // is the whole surface) and never render the collapse handle
  const isMobile = useIsMobile()

  return (
    <ProLayout
      title={hubName()}
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
        <Link to="/home" style={{ display: 'flex', alignItems: 'center', justifyContent: props?.collapsed ? 'center' : 'flex-start', height: '100%', flex: 1, minWidth: 0 }} title={hubName()}>
          {props?.collapsed
            ? <img src={markSrc} alt={hubName()} style={{ width: 30, height: 30, objectFit: 'contain' }} />
            : <img className="doh-brand-logo" src={logoSrc} alt="Stellars Tech AI Lab" />}
        </Link>
      )}
      menuFooterRender={(props) => (props?.collapsed ? null : <SiderFoot />)}
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
      <HubConnectionIndicator />
      {!isMobile && <SiderHandle collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />}
      <div style={{ maxWidth: 1320, margin: '0 auto', width: '100%' }}>
        <div className="doh-topbar">
          <Breadcrumbs />
          {/* header controls live top-right: side layout renders no ProLayout
           * header (Header returns null), so actionsRender would drop these in
           * the sider - keep them in this topbar row instead. Order: language,
           * theme, then the stage badge rightmost. */}
          <div className="doh-header-actions" style={{ marginInlineStart: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <LanguageControl />
            <ThemeControl />
            <ConnectionStatusPill />
            <StageBadge />
          </div>
        </div>
        <Outlet />
      </div>
    </ProLayout>
  )
}
