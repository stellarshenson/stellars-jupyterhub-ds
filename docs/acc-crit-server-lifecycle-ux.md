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

## Starting / restarting ANOTHER user's server - inline, no nav (#243, supersedes #237)

Starting or restarting another user's server from the Servers widget or list must NOT navigate to the start/progress screen. It behaves exactly like Stop/Restart already do: an inline spinner on the play (or restart) button until the server is up, then an immediate row refresh.

- [ ] **No start-screen navigation** - starting another user's server does not route to `/servers/{user}/starting`
  - log: 2026-06-17 criterion added (#243) - reverses the earlier #237 decision (which routed admin starts to the start screen)
- [ ] **Inline play spinner** - the play button shows the SAME inline spinner pattern as the stop button (`IconAction busy` / hero `loading`) while the server starts
  - log: 2026-06-17 criterion added (#243)
- [ ] **Restart same** - restarting another user's server is also inline-spinner + refresh, no navigation
  - log: 2026-06-17 criterion added (#243)
- [ ] **Background monitor + immediate refresh on ready** - the existing `runOp`/`pollUntil` monitor drives the start too; the row flips to active immediately when the server is up (reuse the start op, add a `start` mode to the lifecycle busy map)
  - log: 2026-06-17 criterion added (#243)
- [ ] **Self-start unchanged** - a user starting their OWN server keeps the start page (this only changes starting someone ELSE's server); confirm the self path still shows progress
  - log: 2026-06-17 criterion added (#243) - clarify scope vs the dedicated start page
- [ ] **Reflected in the design language** - the "admin start = inline spinner, not a nav" cue is on /design-language
  - log: 2026-06-17 criterion added (#252)
