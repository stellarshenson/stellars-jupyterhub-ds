# Acceptance Criteria - Open-Server Readiness Gate

The "Open" control for a running lab must be active only once the lab truly serves HTTP, not merely when the hub flips to `running`. Today the control is always active and navigates immediately, so opening a just-started / just-restarted lab lands on the hub spawn-pending / 503 page. Gate the affordance (Option A, in-place): while a running server is not yet serving it shows a disabled "Opening..." state; it activates only when the `lab-ready` probe confirms the lab answers. Defect: [DEF-25](defects-duoptimumhub.md). Reference gate: `src/pages/Starting.tsx`; probe endpoint `handlers/lab_ready.py`.

## Readiness model

- [ ] **Sub-state** - a running server is either `serving` (lab answers) or `becoming-ready` (hub running but lab not yet serving); the Open control reads this sub-state
  - log: 2026-06-23 criterion added
- [ ] **Server-side probe** - readiness uses the existing `GET /hub/api/users/{username}/lab-ready` (always-200, hub probes the lab socket); never a direct browser fetch of the lab (keeps the console clean)
  - log: 2026-06-23 criterion added
- [ ] **Poll until first ready** - while `becoming-ready`, probe ~1s (matching the Starting page); on first `ready:true` the server is `serving` and polling for it stops
  - log: 2026-06-23 criterion added
- [ ] **Deadline fallback** - if not ready within ~60s, treat as serving and activate Open anyway (the server IS running; the gate only avoids the early-race error) - matches the Starting page, never permanently stranded
  - log: 2026-06-23 criterion added

## Open control (Option A - in-place)

- [ ] **Active only when serving** - the Open control is enabled and navigates to `userServerUrl(name)` only in the `serving` sub-state
  - log: 2026-06-23 criterion added (operator chose A: in-place busy state, no Starting-page handoff for a running server)
- [ ] **Busy affordance while becoming-ready** - in `becoming-ready` the control shows a disabled "Opening..." (spinner) state in place, not a dead/clickable button that errors
  - log: 2026-06-23 criterion added
- [ ] **Immediate when already serving** - a server confirmed serving shows Open active with no perceptible delay (no spurious "Opening..." flash)
  - log: 2026-06-23 criterion added

## Triggers

- [ ] **After start** - when a server is started it enters `becoming-ready`; Open activates only once `lab-ready` confirms
  - log: 2026-06-23 criterion added
- [ ] **After restart** - a restart resets the server to `becoming-ready` (the restarted lab must re-pass the gate); Open de-activates then re-activates on ready
  - log: 2026-06-23 criterion added (operator: "restart server, so it makes 'open server' active only after it is available")
- [ ] **On page load** - an already-running server gets an initial `lab-ready` check so the Open control is correct on first render, not assumed-serving
  - log: 2026-06-23 criterion added

## Surfaces (all consistent)

- [ ] **Servers page rows** - per-row Open gated (`ServerRowActions`)
  - log: 2026-06-23 criterion added
- [ ] **Home "Active servers" widget** - the same rows behave identically (shared `ServerRowActions`)
  - log: 2026-06-23 criterion added
- [ ] **ServerHero "Open Lab"** - the own-server hero Open button gated (`ServerHero.tsx`)
  - log: 2026-06-23 criterion added
- [ ] **Admin-other** - admin opening another user's server confirms first (unchanged), and the control is still gated on that server's readiness
  - log: 2026-06-23 criterion added
- [ ] **Single implementation** - the readiness gate + sub-state is one shared piece (extracted from `Starting.tsx`), not duplicated per surface
  - log: 2026-06-23 criterion added

## Edge cases

- [ ] **Edge: server stops or fails while becoming-ready** - the row leaves `becoming-ready`, Open does not silently activate into a dead lab; the row reflects stopped/failed
  - log: 2026-06-23 criterion added
- [ ] **Edge: probe transient error** - a `lab-ready` request that errors (network blip) is treated as not-ready and retried, not a hard failure
  - log: 2026-06-23 criterion added
- [ ] **Edge: navigate away mid-wait** - leaving the page cancels the in-flight probe (no leaked timer, no late state write)
  - log: 2026-06-23 criterion added
- [ ] **Edge: rapid restart** - restarting again while becoming-ready restarts the gate cleanly (no stacked pollers, no premature activation)
  - log: 2026-06-23 criterion added
- [ ] **Edge: 403 from lab-ready** - a caller without permission degrades gracefully, no crash
  - log: 2026-06-23 criterion added

## Verification

- [ ] **Unit - shared gate** - the extracted gate marks serving on ready, retries on not-ready/error, activates on deadline, resets on restart, aborts on stop/fail
  - log: 2026-06-23 criterion added
- [ ] **Functional** - after start and after restart, Open is disabled until the lab serves, then enters the lab cleanly (never the spawn-pending/503 page)
  - log: 2026-06-23 criterion added
- [ ] **Adversarial review** - shared-gate seam + no remaining ungated open path on any surface
  - log: 2026-06-23 criterion added
- [ ] **Live** - rebuild + redeploy; Open on a freshly-started and a freshly-restarted lab both gate then enter cleanly
  - log: 2026-06-23 criterion added

## API

- Reuses `GET /hub/api/users/{username}/lab-ready` -> `{ready: bool, reason?: str, status?: int}` (always HTTP 200); no new endpoint

## Scope boundaries

- [ ] **Out: cold-start spawn page** - starting a stopped server still uses the Starting page (already gated); this defect is the running-server Open control + the post-start/restart becoming-ready window
  - log: 2026-06-23 noted
- [ ] **Out: continuous health** - once a server is confirmed serving the control stays active; this is not a live health monitor, only the start/restart readiness race
  - log: 2026-06-23 noted
