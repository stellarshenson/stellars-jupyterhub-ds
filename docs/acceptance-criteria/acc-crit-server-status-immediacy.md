# Acceptance Criteria - server status immediacy

After a server starts or stops, the hub status (hero + table) must reflect the new state immediately, not ~10s later. The authoritative signal is the spawner state from `/users/{user}` (`ready`/`pending`), not the activity sampler's `server_active`/`recently_active`, which lags by one ~10s sample.

- [x] **Spawner is authoritative for presence** - `statusOf` derives status from `srv.ready` / `srv.pending`, dropping the stale `|| a.server_active` OR that kept a just-stopped server showing active
  - log: 2026-06-17 `liveSource.statusOf` rewritten
- [x] **Hero fetches the spawner** - `getServerHero` now fetches `/users/{user}` and derives status from `servers['']`, so it no longer trusts only the lagging activity snapshot
  - log: 2026-06-17 `getServerHero` Promise.all includes the raw user
- [x] **Start reflects immediately** - a just-started (ready) server reads active/idle at once
  - log: 2026-06-17 `srv.ready ? (recently_active ? active : idle)`
- [x] **Stop reflects immediately** - a just-stopped server reads offline at once, not active-for-10s
  - log: 2026-06-17 spawner absence wins over the stale sample
- [x] **Spawning shown** - `srv.pending === 'spawn'` reads as spawning
  - log: 2026-06-17
- [x] **Resources still keyed on the sample** - CPU/memory stay keyed on `server_active` (they only exist once stats are sampled), while presence comes from the spawner
  - log: 2026-06-17 deliberate split
- [ ] **Runtime: no 10s lag** - on the live hub the status flips within one refresh of start/stop
  - log: 2026-06-17 code done + builds; on-screen confirm pends operator rebuild
