/* The app frame on ProLayout: fixed sider (brand + role-gated menu + identity /
 * sign-out foot), a top header carrying the breadcrumb (left) and the standard
 * antd header controls - language + theme dropdowns (right) - and a footer with
 * the platform + JupyterHub versions shown antd-style as tags. The command
 * palette lives in the content. */
import { ProLayout } from '@ant-design/pro-components'
import { Button, Dropdown, Tag, Tooltip } from 'antd'
import { GlobalOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { createPortal } from 'react-dom'
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

// single source for the sider geometry: the expanded width we set on ProLayout and the
// collapsed width ProLayout uses by default. Both the collapse handle (straddles the
// edge) and the version footer (shifts to the page centre) derive from these, so the
// two cannot drift.
const SIDER_WIDTH = 248
const SIDER_COLLAPSED_WIDTH = 64

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
 * Fixed-positioned so it tracks the sider width; no icon. Portalled to <body> so the
 * `position: fixed` is viewport-relative: rendered in place it sits inside ProLayout's
 * content column (a box whose left edge is the sider width), and any transform/contain
 * on that subtree would capture the fixed element and offset `left` by the column origin,
 * pushing the handle off the divider into the content. The portal removes that dependency. */
function SiderHandle({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return createPortal(
    <Tooltip title={collapsed ? 'Expand' : 'Collapse'} placement="right">
      <button
        className="doh-sider-handle"
        onClick={onToggle}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        style={{
          position: 'fixed', left: collapsed ? SIDER_COLLAPSED_WIDTH : SIDER_WIDTH, top: '50%', transform: 'translate(-50%, -50%)',
          width: 6, height: 44, padding: 0, border: 0, borderRadius: 'var(--radius-sm)',
          cursor: 'pointer', zIndex: 101, transition: 'left .2s, background-color .12s',
        }}
      />
    </Tooltip>,
    document.body,
  )
}

// siderOffsetPx is the live sider width (0 on mobile, collapsed, or expanded). The
// footer lives in ProLayout's content column (offset right by the sider), so a plain
// justify-center lands it right of the true page centre; shift the centred content left
// by half the offset so the banner reads as centred across the WHOLE page, not the panel.
function VersionFooter({ siderOffsetPx, isMobile }: { siderOffsetPx: number; isMobile: boolean }) {
  const { data: hub } = useHubInfo()
  const tag = { background: 'var(--color-surface-active)', color: 'var(--color-text-muted)', borderRadius: 4, marginInline: 4 }
  // click the version to copy the full version + build id to the clipboard
  const fullVersion = `Duoptimum Hub v${__APP_VERSION__} build ${__BUILD_ID__}`
  const copyVersion = () => {
    if (!navigator.clipboard) { notify.error('Clipboard unavailable'); return }
    navigator.clipboard.writeText(fullVersion).then(() => notify.success('Version copied'), () => notify.error('Copy failed'))
  }
  const ver = <>Duoptimum Hub<Tag bordered={false} style={tag}>v{__APP_VERSION__}</Tag></>
  // desktop: click-to-copy with a build-id tooltip. mobile: plain text - no copy
  // affordance and no hover tooltip (nothing to hover/copy with on a touch screen).
  const brand = isMobile
    ? <span>{ver}</span>
    : (
      <Tooltip title={`build ${__BUILD_ID__}`}>
        <span className="doh-version-copy" onClick={copyVersion} style={{ cursor: 'pointer' }}>{ver}</span>
      </Tooltip>
    )
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', gap: 12, padding: '14px 0', color: 'var(--color-text-subtle)', fontSize: 12, transform: `translateX(-${siderOffsetPx / 2}px)`, transition: 'transform .2s' }}>
      <span>
        {brand}
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
      siderWidth={SIDER_WIDTH}
      location={{ pathname }}
      route={{ path: '/', routes: [] }}
      menuRender={isMobile ? false : undefined}
      // mobile: ProLayout collapses to a top-header layout and renders its OWN
      // brand-logo header, which doubled with the in-content doh-topbar (the
      // double header). Kill the ProLayout header on mobile so the doh-topbar
      // (logo + language + theme + stage) is the single header on every screen.
      // Desktop side-layout already renders no ProLayout header.
      headerRender={isMobile ? false : undefined}
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
      footerRender={() => <VersionFooter siderOffsetPx={isMobile ? 0 : (collapsed ? SIDER_COLLAPSED_WIDTH : SIDER_WIDTH)} isMobile={isMobile} />}
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
          {/* mobile drops the sider (and the brand logo it carries), so the topbar
           * shows the logo here instead. Everything else in the header is desktop
           * chrome: on a phone the header is just logo + language + theme - nothing
           * that steals the vertical space the status gauges and switches need. */}
          {isMobile
            ? <Link to="/home" title={hubName()} style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', minHeight: 44, minWidth: 44, paddingInline: 4 }}><img src={logoSrc} alt={hubName()} style={{ height: 28, width: 'auto', objectFit: 'contain', display: 'block' }} /></Link>
            : <Breadcrumbs />}
          {/* header controls live top-right: side layout renders no ProLayout
           * header (Header returns null), so actionsRender would drop these in
           * the sider - keep them in this topbar row instead. Order: language,
           * theme, connection (desktop only - mobile uses HubConnectionIndicator),
           * stage badge. The stage badge stays on mobile: it is a critical env cue
           * next to the mobile Stop/Restart controls (operator: env cue is critical). */}
          <div className="doh-header-actions" style={{ marginInlineStart: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <LanguageControl />
            <ThemeControl />
            {!isMobile && <ConnectionStatusPill />}
            <StageBadge />
          </div>
        </div>
        <Outlet />
      </div>
    </ProLayout>
  )
}
