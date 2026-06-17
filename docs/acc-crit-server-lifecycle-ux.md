# Acceptance Criteria - server lifecycle UX (inline spinners, no modal, real log)

Server start/restart/stop show progress with an INLINE spinner on the control (no modal popup): the op fires, a background monitor polls the real hub status until the transition lands, then the affected views refresh immediately. A spawning server shows a rotating spinner (not the old ekg/activity glyph), and the spawn log opens the real Start-server page.

## Restart / Stop (no modal, inline spinner)

- [x] **No modal** - the restart/stop progress modal (creeping bar + flavour text) is removed; `ServerLifecycle` is a context provider with no popup UI
  - log: 2026-06-17 `app/ServerLifecycle.tsx` rewritten; `loading-messages` dep removed (its only use was the modal)
- [x] **Inline spinner** - while restarting/stopping, the control shows a spinner in place of its icon (hero buttons via antd `loading`; row actions via `IconAction busy`)
  - log: 2026-06-17 `ServerHero.tsx` `loading={busy===...}`, `IconAction` gained a `busy` prop, `Servers.tsx` row actions pass `busy={mode===...}`
- [x] **Background monitor + immediate refresh** - the op's `run()` toasts + invalidates on POST; `pollUntil` then monitors the real status until the transition lands, then invalidates servers/hero/resources/stats so the views update at once
  - log: 2026-06-17 `runOp` in `ServerLifecycle.tsx`
- [x] **Conflicting controls disabled** - other lifecycle buttons disable while a transition is in flight (the busy map)
  - log: 2026-06-17 `disabled={busy}`
- [x] **Failure surfaces as a toast** - a failed POST shows the op's error toast (no stuck modal); busy clears
  - log: 2026-06-17 `run()` error toast + `clearBusy` in catch

## Spawning (rotating spinner, real log)

- [x] **Rotating spinner, not ekg** - a spawning server's row shows an antd `Spin`, not the activity/ekg icon
  - log: 2026-06-17 `Servers.tsx` rowActions spawning branch
- [x] **Real spawn log** - "View spawn log" navigates to the real Start-server page (`/servers/{user}/starting`, live progress + container-log tail), not a `(mock)` toast
  - log: 2026-06-17 was `mockAction('Tail live spawn log')`; now `nav(.../starting)` - #238 mock removed
- [x] **Per-row probe/refresh on ready** - the servers list fast-polls (2.5s) while any server is spawning, so a spawning row flips to active within ~2.5s of ready; `statusOf` reads the post-spawn settle window as spawning so the fast poll engages
  - log: 2026-06-17 adaptive poll + `statusOf` settle fix (see acc-crit-background-refresh)
- [ ] **Runtime: spinner + heal** - on the live hub a spawning row shows the spinner and flips to active within ~2-3s of ready
  - log: 2026-06-17 code + build clean; on-screen confirm pends operator rebuild

## Out of scope (separate tasks)

- [ ] **Admin start shows the start screen** (#237) - confirm every admin start-another path navigates to `/servers/{user}/starting` (the Servers row offline action already does; audit any silent background-start path)
  - log: 2026-06-17 pending investigation
