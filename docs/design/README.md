# DuOptimum Hub - Design System

The design language artifact for the DuOptimum Hub portal, plus how it maps to the shipped code.

## Contents

- `Design Language.dc.html` - the design system reference (self-contained Claude design artifact: tokens, palette, type, components, motion)
- `support.js` - the artifact's runtime (rendering only, no design data)
- `screenshots/full.png` - rendered preview
- `.thumbnail` - preview metadata

## Where the design system lives in the app

- **Tokens** - `src/theme/tokens.ts` is the single source of truth for both themes; it feeds the antd `ConfigProvider` (`src/theme/antdTheme.ts`) and the injected `--color-*` / `--space-*` / `--radius-*` CSS variables (`src/theme/cssVars.ts`) so a theme flip restyles antd and the bespoke widgets together
- **Bespoke component styles** - `src/styles/global.css` (`doh-*` classes)
- **Live reference page** - the in-app `/design-system` route (`src/pages/DesignSystem.tsx`) renders the full token + widget gallery in both themes; it is the canonical, runnable view of the language

## Motion reconciliation (read before editing animations)

The `.dc.html` motion section describes an idealized motion model. The shipped implementation intentionally differs in two places, on the strength of explicit operator tuning, and the **shipped behaviour + the in-app `/design-system` page are canonical for motion**:

- **Connection diode** - the artifact specifies a pure-opacity pulse (no scale); the shipped diode pulses on opacity **and** scale so severity reads in amplitude, not only speed (operator: "amplitude carries meaning")
- **TTL extend** - the artifact specifies `doh-ttl-boost-bar` / `-num` / `-clock` width-pulse keyframes plus a clock-glyph glow; the shipped TTL uses the one-shot `doh-ttl-pulse` accent flourish driven by rAF, after held-halo variants were rejected (DEF-15)

Everything else in the artifact (palette, type scale, spacing, radii, shadows, the icon dual-weight model, component specs) is authoritative; the code conforms to it.
