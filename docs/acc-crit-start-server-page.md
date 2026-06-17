# Acceptance Criteria - dedicated Start-server page with live container-log feed

Starting your OWN server leaves the lightweight modal behind and navigates to a dedicated page that shows a spawn progress bar plus a rolling 10-15 line tail of the freshly-started container's logs, then redirects into the lab when it is ready. Restart/stop keep the small popup (they settle in seconds). Supersedes the start-page items under "Live QA - round 3" in `optimum-hub-web/acc-crit-portal-fixes.md`.

Two data sources: the **progress bar** rides the hub spawn-progress SSE (`GET /hub/api/users/{name}/server/progress`, no backend change); the **log feed** is the actual container stdout/stderr via a new backend tail endpoint (the SSE `message` field is spawn-progress text, not container logs).

## Implementation status (2026-06-17)

Code-complete; backend `make test` 566+63 green, portal `tsc -b` + `build:hub` clean. The visual "must look polished" criteria below are coded to spec but await the user's image rebuild for on-screen confirmation (no live verify possible here). Elegant architecture per directive: two focused hooks own the data, the page is composition + presentation only, and the start path is unified (no duplicate modal-vs-page logic).

- Backend: `ServerLogsHandler` (`handlers/server.py`) - `GET /api/users/{name}/server/logs?tail=N`, admin-or-self, tail capped at 200, 404 before the container exists; exported + route-registered; handler count test 27->29
- Frontend data: `hooks/useSpawnProgress.ts` (spawn POST + progress SSE + bounded status-poll fallback + mock ramp) and `hooks/useContainerLogTail.ts` (1.5s poll while spawning, stops on unmount, mock sample)
- Frontend page: `pages/Starting.tsx` at route `servers/:name/starting` (not admin-gated; backend enforces admin-or-self) - centered branded card, progress bar, terminal-styled log panel (`.oh-termlog` in global.css), redirect-on-ready (own -> lab, admin-other -> Servers), failure -> error + Back
- Start path unified: ServerHero, MobileHome, Servers, Home(preview) Start buttons now navigate to the page; `ServerLifecycle` trimmed to restart/stop only (the duplicated start/SSE/modal path removed)

## Page + navigation

- [ ] **Start -> dedicated page** - clicking Start on your own server navigates to `/servers/:name/starting` (no modal); restart/stop keep the lightweight popup
  - log: 2026-06-17 criterion added
- [ ] **Progress bar** - a progress bar bound to the spawn SSE advances with the hub's reported spawn progress (0-100)
  - log: 2026-06-17 criterion added
- [ ] **Auto-navigate on ready** - on the SSE `ready` event the page redirects into the running server (`userServerUrl`); there is NO Close/Continue button on the success path
  - log: 2026-06-17 criterion added
- [ ] **Failure path** - on `failed` (or stream drop without ready) the page shows the error + a Back-to-portal action; no auto-redirect
  - log: 2026-06-17 criterion added
- [ ] **Admin starting another user's server** - lands on the page; on ready returns to the parent screen (Servers), never auto-enters someone else's lab (consistent with the open-someone-else confirm rule)
  - log: 2026-06-17 criterion added

## Live container-log feed

- [ ] **Rolling tail** - the page shows the last 10-15 lines of the freshly-started container's logs, in a fixed-height monospaced panel that scrolls with new lines (newest at bottom)
  - log: 2026-06-17 criterion added; source = docker logs tail of jupyterlab-{name}
- [ ] **Live update** - the feed refreshes while spawning (poll ~1-2s or stream) so the user watches the container come up, not a frozen snapshot
  - log: 2026-06-17 criterion added
- [ ] **Stops on ready/redirect** - polling/stream stops when the page redirects or unmounts (no leaked timer/EventSource)
  - log: 2026-06-17 criterion added
- [ ] **Admin-or-self only** - the log endpoint is authorised to the server owner or an admin; a non-owner non-admin gets 403
  - log: 2026-06-17 criterion added
- [ ] **Bounded** - only a tail (N lines, capped) is returned; never the full log; never secrets echoed by the entrypoint beyond what the container itself prints
  - log: 2026-06-17 criterion added

## Look and feel (must look polished)

- [ ] **Centered, branded** - a single centered card with the Optimum Hub mark and the server name as a clear title ("Starting konrad.jelen's lab"), generous standard panel padding, no raw full-width sprawl
  - log: 2026-06-17 criterion added
- [ ] **Terminal-styled log panel** - the log feed reads like a real terminal: monospaced, dark subdued panel, soft rounded corners, dim line text, fixed height (~10-15 rows) that scrolls, not a plain bulleted list
  - log: 2026-06-17 criterion added
- [ ] **Smooth progress** - the progress bar animates smoothly (antd Progress, accent blue), with a short human status line above it ("Pulling image...", "Starting server...") sourced from the latest SSE message
  - log: 2026-06-17 criterion added
- [ ] **No layout shift / no flicker** - the card and log panel reserve their space from first paint; new log lines append without the page jumping; the redirect on ready is clean, not a flash
  - log: 2026-06-17 criterion added
- [ ] **On-brand + design-language consistent** - colours, spacing, pills and typography match the rest of the portal (cross-check `/design-language`); dark-mode correct; tasteful, calm, not busy
  - log: 2026-06-17 criterion added
- [ ] **Graceful states look intentional** - waiting/placeholder, failure and "logs unavailable" states are styled (muted, centered, an icon), never raw error text
  - log: 2026-06-17 criterion added
- [ ] **Subtle motion** - a light spinner/pulse while spawning conveys liveness without being noisy; stops on ready
  - log: 2026-06-17 criterion added

## Edge cases

- [ ] **Edge: SSE unsupported / drops** - progress falls back to status polling (`isRunning`); the log feed still tails independently
  - log: 2026-06-17 criterion added
- [ ] **Edge: navigate away mid-spawn** - spawn continues server-side; returning to the page reflects current state (re-attaches SSE + log tail)
  - log: 2026-06-17 criterion added
- [ ] **Edge: container not created yet** - before the container exists, the log panel shows a muted "waiting for container..." placeholder, not an error
  - log: 2026-06-17 criterion added
- [ ] **Edge: logs unavailable** - if docker logs can't be read (permissions, container gone), the panel shows a muted notice and the progress bar still drives readiness
  - log: 2026-06-17 criterion added
- [ ] **Edge: very chatty container** - the tail is line-capped so a noisy container can't blow up the DOM/memory (keep last N only)
  - log: 2026-06-17 criterion added
- [ ] **Edge: spawn succeeds before page mounts** - if the server is already ready on mount, skip the wait and redirect immediately
  - log: 2026-06-17 criterion added
- [ ] **Mock parity** - in mock mode the page animates progress and shows a canned 10-15 line log sample so the demo shows the flow (no hub)
  - log: 2026-06-17 criterion added

## API

- existing: `GET /hub/api/users/{name}/server/progress` (SSE) - drives the progress bar; `_xsrf` as query param (EventSource can't set headers)
- NEW: `GET /api/users/{name}/server/logs?tail=15` -> `{lines: string[]}` (admin-or-self) - tails the spawned container (`docker logs --tail N jupyterlab-{name}`); 403 non-owner, 404 no container, capped tail
- existing: status poll (`GET /hub/api/users/{name}`) - SSE fallback for readiness

## Open decisions

- Log transport: simple short-poll of the tail endpoint (~1-2s) vs a streaming endpoint; poll is simpler and adequate for a 10-15 line tail - default to poll unless streaming is wanted
- Whether restart should also use this page or keep the popup (current: popup; restart settles in seconds)
