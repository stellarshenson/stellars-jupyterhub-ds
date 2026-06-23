# Acceptance Criteria - Open-Server Readiness Gate

The "Open" control for a running lab must be active only once the lab truly serves HTTP, not merely when the hub flips to `running`. Today the control is always active and navigates immediately, so opening a just-started / just-restarted lab lands on the hub spawn-pending / 503 page. Gate the affordance (Option A, in-place): while a running server is not yet serving it shows a disabled "Opening..." state; it activates only when the `lab-ready` probe confirms the lab answers. Defect: [DEF-25](defects-duoptimumhub.md). Reference gate: `src/pages/Starting.tsx`; probe endpoint `handlers/lab_ready.py`.

## Readiness model

- [x] **Sub-state** - a running server is either `serving` (lab answers) or `becoming-ready` (hub running but lab not yet serving); the Open control reads `isServing` (becoming-ready = a `pending` entry on the lifecycle)
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - `ServerLifecycle` `pending` map; `isServing(user) = !pending[user]`
- [x] **Server-side probe** - readiness uses the existing `GET /hub/api/users/{username}/lab-ready` (always-200, hub probes the lab socket); never a direct browser fetch of the lab (keeps the console clean)
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - shared `waitForLabReady` (`services/hub/labReady.ts`) calls `hubGet('/users/{u}/lab-ready')`
- [x] **Poll until first ready** - while `becoming-ready`, probe ~1s (matching the Starting page); on first `ready:true` the server is `serving`
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - `LAB_READY_POLL_MS=1000`; `settleReady` clears `pending` on resolve
- [x] **Deadline fallback** - if not ready within ~60s, treat as serving and activate Open anyway (the server IS running; the gate only avoids the early-race error) - matches the Starting page, never permanently stranded
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - `LAB_READY_DEADLINE_MS=60000`; `waitForLabReady` resolves on deadline, `settleReady` clears `pending`

## Open control (Option A - in-place)

- [x] **Active only when serving** - the Open control is enabled and navigates to `userServerUrl(name)` only in the `serving` sub-state
  - log: 2026-06-23 criterion added (operator chose A: in-place busy state, no Starting-page handoff for a running server)
  - log: 2026-06-23 done - `ServerHero` Open Lab `disabled={!!busy || opening}`; `ServerRowActions` enter `disabled={busy || opening}`
- [x] **Busy affordance while becoming-ready** - in `becoming-ready` the control shows a disabled "Opening..." (spinner) state in place, not a dead/clickable button that errors
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - Open Lab `loading={opening}` + label "Opening…"; row enter `busy={opening}` + title "Opening…"
- [x] **Immediate when already serving** - a server confirmed serving shows Open active with no perceptible delay (no spurious "Opening..." flash)
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - optimistic default (`isServing` true unless `pending`); steady-state running servers never enter the gate

## Triggers

- [x] **After start** - an inline (lifecycle) start enters `becoming-ready`; Open activates only once `lab-ready` confirms
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - `start` calls `markPending` then `runOp(..., settleReady)`
- [x] **After restart** - a restart resets the server to `becoming-ready`; Open de-activates then re-activates on ready
  - log: 2026-06-23 criterion added (operator: "restart server, so it makes 'open server' active only after it is available")
  - log: 2026-06-23 done - `restart` calls `markPending` then `runOp(..., settleReady)`; `restartServer` awaits the container restart so the probe hits the new lab (no stale-lab race)
- [x] **On page load (optimistic)** - a server already running at page load is assumed serving so Open is active immediately with NO spurious "Opening..." flash; only a start/restart this session opens the gate
  - log: 2026-06-23 criterion added (was "initial lab-ready check"; changed to optimistic - the defect is the post-start/restart race, not steady state, and a per-load probe would flash "Opening" on every reload)
  - log: 2026-06-23 done - `isServing` optimistic default; residual edge documented below

## Surfaces (all consistent)

- [x] **Servers page rows** - per-row Open gated (`ServerRowActions`)
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - enter `IconAction` gated on `lf.isServing(r.user)`
- [x] **Home "Active servers" widget** - the same rows behave identically (shared `ServerRowActions`)
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - same `rowActions` helper, no separate path
- [x] **ServerHero "Open Lab"** - the own-server hero Open button gated (`ServerHero.tsx`)
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - `opening = running && !isServing`; button `loading`/`disabled`/label gated
- [x] **Admin-other** - admin opening another user's server confirms first (unchanged), and the control is still gated on that server's readiness
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - row gate is per-`r.user`; `enterSession` (confirm modal) only reachable once serving
- [x] **Single implementation** - the readiness gate is one shared piece (`waitForLabReady` in `services/hub/labReady.ts`), used by the lifecycle and the Starting page
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - probe loop extracted from `Starting.tsx`; both call `waitForLabReady`

## Edge cases

- [x] **Edge: server stops or fails while becoming-ready** - Open does not activate into a dead lab; the row reflects stopped/failed
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - `stop` clears `pending`; a failed `runOp` clears `pending` in the catch; offline servers render the start branch (no Open control)
- [x] **Edge: probe transient error** - a `lab-ready` request that errors (network blip / lab not yet listening) is treated as not-ready and retried, not a hard failure
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - `waitForLabReady` swallows the fetch error and keeps polling
- [x] **Edge: navigate away mid-wait** - no leaked timer / late navigation
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - Starting page passes `aborted` (cancels + no enter); the lifecycle gate lives on the app-level provider (never unmounts mid-route), so its probe completes and only clears `pending` - no navigation, nothing to leak
- [x] **Edge: rapid restart** - no premature activation
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 adversarial review caught a CRITICAL here: `busy` releases before the lab-ready settle, so a 2nd restart in that window let a STALE settle clear the gate the new op opened -> Open active mid-spawn (the exact 503). Fixed with a per-user generation token (`openGate` bumps it, `closeGate(user,g)` clears only if still current); a stale settle is skipped. Re-confirm: race dead. `closeGate` also moved into a `finally` so a `waitForLabReady` throw can never strand the gate
- [x] **Edge: 403 from lab-ready** - degrades gracefully, no crash
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 done - a 403 throws in `hubGet`, caught as not-ready; the control only renders for own/admin servers so a real 403 is unreachable, the deadline still activates
- [ ] **Edge: page load during an external restart (optimistic gap)** - a server mid-restart in another tab/process shows Open active on a fresh page load (no `pending`) and could hit the race; accepted residual of the optimistic model
  - log: 2026-06-23 criterion added - known limitation of the optimistic-at-mount decision; the in-session start/restart paths (the actual defect) are gated

## Verification

- [x] **Static - typecheck** - no JS unit runner in this project (functional + tsc only); the shared gate is type-checked and covered by the functional test below
  - log: 2026-06-23 criterion added (was "Unit - shared gate"; reframed - the repo has no vitest/jest, frontend is verified by tsc + Playwright)
  - log: 2026-06-23 done - `npm run typecheck` (tsc -b --noEmit) clean
- [x] **Functional** - after restart, Open is disabled ("Opening...") until the lab serves, then the Enter action activates (never the spawn-pending/503 page)
  - log: 2026-06-23 criterion added; `test_open_readiness.py` (route-mocks `lab-ready` to make the becoming-ready window deterministic)
  - log: 2026-06-23 PASSED - signup regime against image `42fb650e1659`: 89 passed / 0 failed, 140 acc-crit met / 0 unmet; `test_server_start_background` still green (no regression)
- [x] **Adversarial review** - shared-gate seam + no remaining ungated open path on any surface
  - log: 2026-06-23 criterion added
  - log: 2026-06-23 Mode-1 bug-hunt round 1 DO-NOT-SHIP: CRITICAL stale-settle premature activation (double-restart) -> fixed with the generation token; round 2 re-confirm: race dead, one new HIGH (closeGate outside `finally` could strand on a `waitForLabReady` throw) -> fixed verbatim (try/finally). Accepted: optimistic page-load residual (#3, documented), deadline-fallback activate (#4, intended), no-op-timeout (#6, pre-existing)
- [ ] **Live** - rebuild + redeploy; Open on a freshly-restarted lab gates then enters cleanly
  - log: 2026-06-23 criterion added

## API

- Reuses `GET /hub/api/users/{username}/lab-ready` -> `{ready: bool, reason?: str, status?: int}` (always HTTP 200); no new endpoint

## Scope boundaries

- [ ] **Out: cold-start spawn page** - starting a stopped server still uses the Starting page (already gated); this defect is the running-server Open control + the post-start/restart becoming-ready window
  - log: 2026-06-23 noted
- [ ] **Out: continuous health** - once a server is confirmed serving the control stays active; this is not a live health monitor, only the start/restart readiness race
  - log: 2026-06-23 noted
