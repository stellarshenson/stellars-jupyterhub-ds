# Optimum Hub - mock-antd

A higher-fidelity React build of the Optimum Hub JupyterHub portal on Ant Design Pro. Reads real data read-only from the hub REST API; every mutating action is mocked (toast only, no write method exists). Ports the static `../mock/` prototype to real components with a full light/dark theme.

## Stack

- **Vite + React 18 + TypeScript** - lean build, fast HMR
- **antd 5 + @ant-design/pro-components** - `ProLayout`, `ProTable`, `ProForm`, `ProCard`; standard components first, custom only where antd has no equivalent
- **TanStack Query** - read hooks with loading / empty / error
- **react-router-dom 6** - routing + breadcrumb handles

## Data modes

- **mock** (default) - fixtures shaped into view models; runs with no hub. Set by `VITE_DATA_MODE=mock`
- **live** - readonly GETs to the hub (`/users`, `/groups`, `/activity`, `/admin/groups`, `/users/{u}/session-info`) through the Vite dev proxy; auth rides the hub session cookie, no API token. Set by `VITE_DATA_MODE=live` and `VITE_HUB_ORIGIN`
- Reads only - the hub client has no POST/PUT/DELETE; actions route through `mockAction` and never mutate

## Run

```bash
make install     # npm install
make dev         # dev server on :5180
make build       # typecheck + production build
make typecheck   # tsc --noEmit
make lint        # eslint
```

Copy `.env.example` to `.env.local` to switch modes. Open `http://localhost:5180`.

## Theme

- One token source (`src/theme/tokens.ts`) feeds both the antd `ConfigProvider` theme and the injected CSS variables the bespoke components read - so the antd surface and the hand-built meters/pills/bars never drift
- Three modes (light / dark / system) persisted in `localStorage`; dark uses antd `darkAlgorithm`, light `defaultAlgorithm`
- Palette transcribed from `../mock/assets/tokens.css` (Sublime greys + Stellars cyan)

## Bespoke components (`src/components/`)

The JupyterHub metaphors antd lacks, themed by the shared tokens: `StatusPill`, `ActivityMeter`, `Spark`, `ResourceBars`, `TtlGadget`, `ServerHero`, `MetricCard`, `ScopeFilterPills`, `Notice`, `CappedTags`, `Combo`, `IconAction`. The `/design-system` route shows them live (reached from the Home mock-switch).

## Layout

```
src/
  theme/        tokens, antdTheme, cssVars, ThemeProvider
  layout/       AppLayout (ProLayout), SiderMenu, Breadcrumbs, CommandPalette, ThemeChanger, MockSwitch
  app/          RoleContext, nav model
  components/   bespoke design-system set + Icon
  services/     types, config, dataMode, datasource, mockSource, hub/ (client + liveSource), actions
  hooks/        react-query read hooks
  pages/        one file per screen (Home, Servers, Users, Groups, configs, Lab Container, Events, Notifications, Settings, Tokens, DesignSystem)
```

## Tests

`tests/smoke.spec.ts` asserts the shell renders with no console errors; `tests/shots.spec.ts` captures full-page screenshots per page in both themes (Playwright). Run `npx playwright test` against a running dev server.

## Status

Design build for review. Faithful to `../design-flows-frontend-mock.md`: every screen and action from the static mock is present, both themes verified. Not wired to a live hub by default; mocked actions throughout.
