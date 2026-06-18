# Acceptance Criteria - drop the `/portal` URL segment

Serve the React SPA at the hub root (`/hub/...`) instead of `/hub/portal/...`, so the address bar and bookmarks carry no `portal` segment. The SPA's own routes become `/hub/servers`, `/hub/users`, etc.

## Implementation status (2026-06-17)

IMPLEMENTED and verified to the extent possible offline: backend `make test` 566+63 green, `py_compile` + pyflakes clean, portal `tsc -b` + `build:hub` clean, manifest entry is relative (`assets/index-*.js`) so `portal.html` resolves to `/hub/assets/*` matching the route. Decision taken: home client-route renamed to `/dashboard` (nav label stays "Home"); legacy server-rendered page handlers removed (the SPA owns those features). Login/signup are safe - `main.tsx` renders `<AuthApp/>` off `window.jhdata.authPage`, independent of the router/basename. Runtime asset resolution + deep-link routing against the live hub need the user's image rebuild to confirm on-screen. Revert = `git revert` of this change set (cohesive).

## Hard constraint (the reason `/portal` exists today)

JupyterHub registers its built-in page + API handlers BEFORE `c.JupyterHub.extra_handlers` and Tornado matches first-wins (`jupyterhub/app.py` ~1790-1794: `h.extend(default_handlers)` then `h.extend(self.extra_handlers)`). The portal handlers are `extra_handlers`, so they can only claim `/hub/<path>` that no built-in already owns. Built-ins that DO own a path (`jupyterhub/handlers/pages.py:772+`, `apihandlers`): `/hub/` (RootHandler), `/hub/home`, `/hub/admin`, `/hub/login`, `/hub/logout`, `/hub/token`, `/hub/spawn`, `/hub/spawn-pending`, `/hub/user-redirect`, `/hub/error`, `/hub/health`, `/hub/api/*`, `/hub/static/*`, `/hub/metrics`, `/hub/oauth_login`, `/hub/oauth2callback`.

Consequence: the SPA can serve at `/hub/<route>` for every route EXCEPT the reserved ones - and its current landing route `/home` collides with the built-in `/hub/home` (stock page wins on hard-refresh / deep-link), and bare `/hub/` is RootHandler.

## Decision required

- [ ] **Landing-route rename** - move the SPA's home view off the reserved `/home` path (recommended `/dashboard`, keep the nav LABEL "Home"); this is the one user-facing choice and the only thing blocking a clean drop
  - log: 2026-06-17 criterion added; alternatives: (b) accept stock hub home on a hard-refresh of the home view (poor), (c) override JupyterHub's RootHandler/HomeHandler (invasive, version-fragile, fights the framework - not recommended)

## Backend (duoptimum_hub_web)

- [ ] **Routes drop `/portal`** - `ASSETS_ROUTE` `/portal/assets/(.*)` -> `/assets/(.*)`, `BRAND_ROUTE` `/portal/brand/(.*)` -> `/brand/(.*)`, `PORTAL_ROUTE` `/portal/?(.*)` -> `/(.*)` (the SPA shell catch-all, still after built-ins so reserved paths win)
  - log: 2026-06-17 criterion added
- [ ] **PORTAL_URL** - `/hub/portal` -> the chosen landing (`/hub/dashboard`); `default_url = base_prefix + PORTAL_URL` so post-login + `/hub/` land on the portal
  - log: 2026-06-17 criterion added
- [ ] **Asset/brand precedence** - `/hub/assets/*` and `/hub/brand/*` matched before the `/(.*)` shell catch-all and do NOT collide with built-in `/hub/static/*`
  - log: 2026-06-17 criterion added
- [ ] **Shell still gets XSRF** - PortalHandler renders the shell for the catch-all so `window.jhdata.xsrf_token` is injected exactly as today
  - log: 2026-06-17 criterion added
- [x] **Old-path redirect (no /portal flash)** - `/hub/portal[/...]` 302s server-side to the hub-root SPA (`/portal/home` -> `/dashboard`) via `PortalRedirectHandler`, registered before the catch-all - so a stale `next`/bookmark/cached link never loads the shell at `/portal` and then client-redirects (the ~1s "portal" flash after login the operator hit)
  - log: 2026-06-17 implemented (`handlers.py::PortalRedirectHandler`, `LEGACY_PORTAL_ROUTE` before `PORTAL_ROUTE` in `portal_handlers`)
  - log: 2026-06-17 criterion added

## Frontend (duoptimum-hub-web)

- [ ] **Vite base** - `VITE_BASE` `/hub/portal/` -> `/hub/` (`.env.hub`); drives asset URLs + router base
  - log: 2026-06-17 criterion added
- [ ] **Router basename** - `portalBasename()` / `portalAssetBase()` drop the `/portal` suffix (read `window.jhdata.base_url` -> `<base>/hub` not `<base>/hub/portal`)
  - log: 2026-06-17 criterion added
- [ ] **Home route** - `/home` -> `/dashboard` in `router.tsx` (index redirect, `*` fallback), `nav.ts`, and every `navigate('/home')` / `to="/home"` (label stays "Home")
  - log: 2026-06-17 criterion added

## Edge cases

- [ ] **Reserved paths still work** - `/hub/login`, `/hub/logout`, `/hub/api/*`, `/hub/static/*`, `/hub/spawn`, `/hub/health` are served by JupyterHub built-ins, never the SPA catch-all
  - log: 2026-06-17 criterion added
- [ ] **Deep-link / refresh** - hard refresh on `/hub/servers`, `/hub/users`, `/hub/dashboard`, `/hub/servers/:name/starting` serves the shell (no 404, no stock page)
  - log: 2026-06-17 criterion added
- [ ] **Edge: `/hub/home` typed directly** - shows stock hub home (built-in, unavoidable while extra_handlers run after built-ins); the SPA never links there once the landing is `/dashboard`
  - log: 2026-06-17 criterion added
- [ ] **Edge: bare `/hub/`** - RootHandler redirects to `default_url` (the portal landing)
  - log: 2026-06-17 criterion added
- [ ] **Edge: wrapper Traefik** - the live stack routes the public root to `/hub`; dropping `/portal` is internal to the hub image and needs no wrapper change (the wrapper is a separate repo - do not edit)
  - log: 2026-06-17 criterion added
- [ ] **Mock/dev** - dev-proxy + mock (no shell) fall back to `BASE_URL`; `/dashboard` works there too
  - log: 2026-06-17 criterion added

## API / routes (after)

- `/hub/assets/(.*)` -> ImmutableStaticFileHandler (hashed bundle)
- `/hub/brand/(.*)` -> StaticFileHandler (public, no auth)
- `/hub/(.*)` -> PortalHandler (`@authenticated` shell; reserved paths already claimed by built-ins)
- `default_url = <base_prefix>/hub/dashboard`
