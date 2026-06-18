/* Map the Duoptimum Hub palette onto an antd 5 ConfigProvider theme.
 * The semantic tokens come straight from the palette; the algorithm flips the
 * neutral ramp light/dark. Component overrides land the calm control-room look
 * (transparent table headers, accent-soft menu selection, compact controls). */
import { theme as antdAlgorithm } from 'antd'
import type { ThemeConfig } from 'antd'
import type { Palette, ResolvedTheme } from './tokens'
import { FONT } from './tokens'

export function buildAntdTheme(mode: ResolvedTheme, p: Palette): ThemeConfig {
  return {
    algorithm: mode === 'dark' ? antdAlgorithm.darkAlgorithm : antdAlgorithm.defaultAlgorithm,
    token: {
      colorPrimary: p.accent,
      colorInfo: p.info,
      colorSuccess: p.success,
      colorWarning: p.warning,
      colorError: p.danger,
      colorLink: p.accent,
      colorLinkHover: p.accentHover,

      colorBgLayout: p.bg,
      colorBgContainer: p.surface,
      colorBgElevated: p.surfaceRaised,
      colorBgSpotlight: p.surfaceRaised,

      colorBorder: p.border,
      colorBorderSecondary: p.borderSubtle,

      colorText: p.text,
      colorTextSecondary: p.textMuted,
      colorTextTertiary: p.textSubtle,
      colorTextQuaternary: p.textSubtle,

      borderRadius: 6,
      borderRadiusLG: 10,
      borderRadiusSM: 4,
      fontFamily: FONT.sans,
      fontFamilyCode: FONT.mono,
      fontSize: 14,
      controlHeight: 32,
      wireframe: false,
      colorTextHeading: p.text,
    },
    components: {
      Layout: {
        siderBg: p.bg,
        headerBg: p.bg,
        bodyBg: p.bg,
        headerHeight: 56,
        headerPadding: '0 24px',
      },
      Menu: {
        itemBg: 'transparent',
        subMenuItemBg: 'transparent',
        itemColor: p.textMuted,
        itemHoverColor: p.text,
        itemHoverBg: p.surfaceHover,
        itemSelectedBg: p.accentSoft,
        itemSelectedColor: p.text,
        itemHeight: 38,
        iconSize: 18,
        itemBorderRadius: 6,
        itemMarginInline: 8,
      },
      Table: {
        headerBg: 'transparent',
        headerColor: p.textSubtle,
        headerSplitColor: 'transparent',
        borderColor: p.borderSubtle,
        rowHoverBg: p.surfaceHover,
        cellPaddingBlock: 10,
        cellPaddingInline: 16,
        colorBgContainer: p.surface,
      },
      Card: {
        colorBgContainer: p.surface,
        colorBorderSecondary: p.borderSubtle,
        borderRadiusLG: 10,
        paddingLG: 16,
      },
      Button: {
        controlHeight: 32,
        controlHeightSM: 26,
        fontWeight: 500,
        primaryShadow: 'none',
        defaultShadow: 'none',
        dangerShadow: 'none',
      },
      Tag: {
        borderRadiusSM: 4,
        defaultBg: p.bgSubtle,
        defaultColor: p.textMuted,
      },
      Input: {
        colorBgContainer: p.bg,
        activeBorderColor: p.accent,
        hoverBorderColor: p.borderStrong,
      },
      Select: {
        colorBgContainer: p.bg,
        optionSelectedBg: p.accentSoft,
      },
      Tabs: {
        inkBarColor: p.accent,
        itemSelectedColor: p.text,
        itemColor: p.textMuted,
        itemHoverColor: p.text,
        horizontalItemPadding: '8px 12px',
      },
      Tooltip: {
        colorBgSpotlight: p.surfaceRaised,
        colorTextLightSolid: p.text,
      },
      Progress: {
        defaultColor: p.accent,
        remainingColor: p.bgSubtle,
      },
      Modal: {
        contentBg: p.surfaceRaised,
        headerBg: p.surfaceRaised,
      },
      Segmented: {
        itemSelectedBg: p.accentSoft,
        itemSelectedColor: p.accent,
        trackBg: p.surface,
      },
      Statistic: {
        contentFontSize: 30,
      },
    },
  }
}
