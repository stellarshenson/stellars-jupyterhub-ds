# Acceptance Criteria - restart/stop progress feedback

During a server restart or stop the progress modal must clearly read as "something is happening": the bar creeps (it no longer sits at a static full bar that looks done) and a rotating funny "loading…" line plays underneath, sourced from a ready package.

- [x] **Creeping bar** - while busy the bar eases toward (never reaching) 90%, so it reads as ongoing work instead of a static 100% that looks complete
  - log: 2026-06-17 creep interval in `ServerLifecycle.tsx` (was indeterminate-at-100, which looked finished)
- [x] **Active style** - the bar keeps antd's `status="active"` shimmer while busy
  - log: 2026-06-17
- [x] **Rotating flavour line** - a random message rotates every ~1.6s below the bar
  - log: 2026-06-17 `getRandomMessage()` from the `loading-messages` package
- [x] **Ready package** - flavour text comes from the `loading-messages` npm package (MIT, 305 messages), not a hand-rolled list
  - log: 2026-06-17 added as a dependency; resolved via `make install`; no docker-specific package exists, this is the closest maintained one
- [x] **Untyped shim** - a `declare module 'loading-messages'` ambient type lets TS import the untyped package
  - log: 2026-06-17 `src/vite-env.d.ts`
- [x] **Settle** - on success the bar jumps to 100% (success colour) and the modal auto-closes; the flavour line and timers stop
  - log: 2026-06-17 intervals cleared on leaving `busy`
- [x] **Edge: error** - on failure the bar shows the exception state and the flavour line is hidden; modal stays open with Close
  - log: 2026-06-17 flavour rendered only in `busy` phase
