# Acceptance Criteria - environment-stage badge

A small outlined rectangle in the portal header naming the deployment stage (DEV/STG/TST/PRD), coloured per stage, so operators can tell environments apart at a glance. Driven by `JUPYTERHUB_BRANDING_STAGE` -> `window.jhdata.stage` (frozen at hub start); empty = no badge. Frontend: `components/StageBadge.tsx` in `AppLayout` `actionsRender`. Backend: `branding.py::setup_branding(stage=...)` -> `branding['stage']` -> `template_vars['branding_stage']` -> `portal.html`. Verified against the code 2026-06-18.

## Behaviour

- [x] **Env-driven** - the badge text and presence come from `JUPYTERHUB_BRANDING_STAGE`, read once at hub start
  - log: 2026-06-18 operator: "environment stage 'logo' ... env JUPYTERHUB_BRANDING_STAGE"; config `JUPYTERHUB_BRANDING_STAGE`, threaded through `setup_branding`
- [x] **None by default** - empty/unset env renders nothing (no element, no padding gap)
  - log: 2026-06-18 `StageBadge` returns null when `window.jhdata.stage` is falsy
- [x] **Top-right placement** - badge sits in the header's top-right action cluster (with the language/theme controls), standard padding
  - log: 2026-06-18 first item in `AppLayout` `actionsRender`
- [x] **Outlined rectangle** - 1px border + text both in the stage colour (`currentColor`), transparent fill, square-ish corners (`--radius-sm`)
  - log: 2026-06-18 `.oh-stage-badge` in `global.css`
- [x] **Colour per stage** - DEV green, TST blue (accent/cyan per the design theme), STG orange, PRD red
  - log: 2026-06-18 `STAGE_TONE` maps to `--oh-green` / `--oh-cyan` / `--oh-orange` / `--oh-red`
- [x] **Unknown text grey** - any value not in {DEV,STG,TST,PRD} still renders, in neutral grey (`--oh-gray`)
  - log: 2026-06-18 `?? 'var(--oh-gray)'` fallback
- [x] **Case-insensitive match** - the stage key is matched uppercased, so `dev`/`Dev`/`DEV` all map to green
  - log: 2026-06-18 `raw.toUpperCase()` for the lookup
- [x] **Raw value displayed** - the badge shows the operator's text (CSS uppercases it for display), not a remapped label
  - log: 2026-06-18 renders `{raw}`; `text-transform: uppercase` in CSS
- [x] **Stripped server-side** - leading/trailing whitespace is trimmed before injection
  - log: 2026-06-18 `branding['stage'] = (stage or '').strip()`
- [x] **Injected via window.jhdata** - the value reaches the SPA through `portal.html` `window.jhdata.stage`, same channel as `admin_user`/`gpu_enabled`
  - log: 2026-06-18 `template_vars['branding_stage']` -> `stage: "{{ branding_stage }}"`
- [x] **Restart to change** - the value is frozen into `template_vars` at config load; changing the env takes effect on hub restart
  - log: 2026-06-18 read at module load, no live reload

## Env namespace

- [x] **Branding env namespace** - all branding env vars share the `JUPYTERHUB_BRANDING_*` prefix: STAGE, LOGO_URI, FAVICON_URI, FAVICON_BUSY_URI, LAB_MAIN_ICON_URI, LAB_SPLASH_ICON_URI
  - log: 2026-06-18 operator: "rename branding envs for logo, favicon etc to have _BRANDING like this one"; renamed in config, `settings_dictionary.yml`, Dockerfile, `compose.yml`, README, `custom-branding.md`, mock Settings page
- [x] **Settings + dictionary updated** - the renamed keys appear on the Settings page (data-driven from `settings_dictionary.yml`); STAGE added as an editable entry
  - log: 2026-06-18 `settings_dictionary.yml` + `mockSource.ts` Branding category

## Edge cases

- [x] **Edge: whitespace-only value** - a value that is only spaces trims to empty -> no badge
  - log: 2026-06-18 `.strip()` server-side; `?.trim()` client-side, then null
- [x] **Edge: lowercase stage** - `dev` matches green and displays `DEV`
  - log: 2026-06-18 uppercase match + CSS uppercase display
- [x] **Edge: long/custom text** - arbitrary text (e.g. `STAGING`) renders grey without breaking the header layout (`white-space: nowrap`)
  - log: 2026-06-18 grey fallback, nowrap badge
- [x] **Edge: auth pages** - login/signup screens have no app header, so the badge does not appear there (portal only)
  - log: 2026-06-18 badge lives in `AppLayout`, not the auth shell

## Tests

- [x] **Unit: stage normalization** - `setup_branding(stage=...)` returns `branding['stage']` stripped, `''` when unset; default-keys test includes `stage`
  - log: 2026-06-18 `optimum-hub-services/tests/test_branding.py::TestStage`; `make test`
- [ ] **Functional: no badge by default** - default (signup) deployment has no stage env -> the header shows no `.oh-stage-badge`
  - log: 2026-06-18 `tests/functional/test_branding_stage.py::test_no_stage_badge_by_default`; pends an image rebuild (badge ships in the bundle)
- [ ] **Functional: badge shows configured stage** - env-mode deployment with `JUPYTERHUB_BRANDING_STAGE=TST` shows a `TST` badge in the blue/accent tone
  - log: 2026-06-18 `tests/functional/test_branding_stage.py::test_stage_badge_shows_configured_stage` (envauth); `compose.functional-env.yml`; pends an image rebuild

## Configuration

- `JUPYTERHUB_BRANDING_STAGE` - environment-stage badge text; `DEV` / `STG` / `TST` / `PRD` recognised (coloured), any other text renders grey, empty/unset = no badge
