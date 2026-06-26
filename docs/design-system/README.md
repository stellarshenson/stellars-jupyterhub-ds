# DuOptimum Hub - Design System

The design language artifact for the DuOptimum Hub portal, plus how it maps to the shipped code.

## Contents

- `Design Language.dc.html` - the design system reference, authoritative (Claude design artifact: tokens, palette, type, components, motion, per-component **Build notes** + **Watchout** gotchas - prescriptive down to CSS values, keyframes and the stripe palette)
- `Design Language.html` - the same system fully rendered to a standalone page; open directly in a browser to read it without the runtime
- `support.js` - the `.dc.html` artifact's runtime (rendering only, no design data)
- `screenshots/full.png` - rendered preview
- `.thumbnail` - preview metadata

## Where the design system lives in the app

- **Tokens** - `src/theme/tokens.ts` is the single source of truth for both themes; it feeds the antd `ConfigProvider` (`src/theme/antdTheme.ts`) and the injected `--color-*` / `--space-*` / `--radius-*` CSS variables (`src/theme/cssVars.ts`) so a theme flip restyles antd and the bespoke widgets together
- **Bespoke component styles** - `src/styles/global.css` (`doh-*` classes)
- **Live reference page** - the in-app `/design-system` route (`src/pages/DesignSystem.tsx`) renders the full token + widget gallery in both themes; it is the canonical, runnable view of the language

## Motion reconciliation (read before editing animations)

The `.dc.html` motion section is authoritative. The shipped code conforms to it:

- **Connection diode** (conforms) - the artifact specifies a pure-opacity pulse with severity in CADENCE only (`doh-pulse-calm` 3.6s connected, `doh-pulse-alert` 1.2s / 3x down); no scale (scaling nudges the pill baseline). Realigned 2026-06-25 from a prior opacity+scale "amplitude" override back to the artifact's opacity-only/cadence model; frozen under `prefers-reduced-motion`.
- **TTL motion** (conforms) - the fill runs the artifact's mid-extend `doh-ttl-boost-bar` (brightness + a forward-only accent box-shadow cropped by the track's `overflow:hidden`; the artifact keyframe's width stops are dropped so the rAF-driven fill width wins), the counter blurs (`doh-ttl-boost-num`), the clock glyph glows on extend (`doh-ttl-boost-clock`) and on expiry (`doh-ttl-glow-soft` at warn, `doh-ttl-glow` at end), the readout shows the +delta, and the trigger reads "Extending…". Realigned 2026-06-25 to the updated artifact (a prior pass used a non-spec `-halo`/`-fill` pair); all gated by `prefers-reduced-motion`.

Everything else in the artifact (palette, type scale, spacing, radii, shadows, the icon dual-weight model, component specs) is authoritative; the code conforms to it.
