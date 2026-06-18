# Acceptance Criteria - background refresh + immediate update

The portal keeps lists/status current without manual navigation: mutations reflect at once (optimistic + immediate background refetch), and the live dashboard self-polls so a background change (a server coming up, status flips) shows on its own. Paradigm: when something happens in the background, a monitor watches and the affected view refreshes immediately on completion.

## Mutation-side (immediate effect on change)

- [x] **Immediate background refetch** - `invalidate()` uses `refetchType: 'all'` so a mutation refetches the affected list even when it is unmounted (RQ default only refetches active observers); navigating back shows fresh data, not stale-until-next-mount
  - log: 2026-06-17 `services/actions.ts::invalidate`
- [x] **Optimistic patch** - `patchQuery()` patches the query cache at once (e.g. `saveUserProfile` updates the `['users']` fullName immediately, like the Groups page's inline-edit immediacy); the PUT + invalidation reconcile, and a failure refetches to roll back
  - log: 2026-06-17 `actions.ts::patchQuery`, `ops.ts::saveUserProfile`
- [x] **Why it was slow** - the user list's name comes via `getUsers` which `Promise.all`s the fast `/users`+`/user-profiles` with the heavy `/activity`; without the optimistic patch the saved name only appeared after the slow refetch
  - log: 2026-06-17 root-caused

## Background polling (self-refresh)

- [x] **Adaptive poll on live queries** - `servers`, `hero`, `stats`, `resources` carry `refetchInterval`: FAST (2.5s) while a server is spawning, SLOW (15s) when stable
  - log: 2026-06-17 `hooks/queries.ts` `FAST_POLL`/`SLOW_POLL`, `serversSpawning`/`heroSpawning`
- [x] **No poll for slow data** - `users`/`groups`/`settings`/`tokens` are not polled (they change only on admin action)
  - log: 2026-06-17 deliberately left unpolled
- [x] **Paused when hidden** - `refetchIntervalInBackground: false` so a backgrounded tab stops polling (each `/activity` sample runs docker stats)
  - log: 2026-06-17
- [x] **Server-status-after-start heals** - root cause: the Start page navigates on the SSE `ready`, the hub's `/users/{user}` can still report `ready:false` for a few seconds, Home did ONE refetch that caught the mid-settle state, and nothing re-polled (no `refetchInterval`) so it stuck "Offline" until the 30s staleTime. Fast poll while spawning now flips it to active within ~2.5s
  - log: 2026-06-17 fixed via the adaptive poll; `statusOf` already spawner-authoritative
- [ ] **Runtime: status flips within ~2-3s of start** - confirm on the live hub the post-start Offline window is gone
  - log: 2026-06-17 code + build clean; on-screen confirm pends operator rebuild

## Prefetch (already present)

- [x] **Boot prefetch** - `App.tsx::prefetchCore` warms 12 list queries at app init; `persistCache` hydrates from localStorage so first paint is instant
  - log: 2026-06-17 pre-existing, confirmed
- [ ] **Edge: prefetch on nav hover** - optional Phase 3 (sider link `onMouseEnter` -> `prefetchQuery`) - not yet implemented
  - log: 2026-06-17 deferred

## Adversarial-critic fixes (2026-06-17)

- [x] **C1: settle window heals** - the original adaptive poll only fast-polled on `status==='spawning'`, but the post-spawn settle window (spawner present, not ready, no pending) mapped to `offline` and fell to the 15s poll. `statusOf` now reads that window as `spawning`, and `useSpawnProgress` invalidates servers/hero/stats/resources on the SSE `ready` - so the started server heals in ~2-3s, not up to 15s
  - log: 2026-06-17 `liveSource.statusOf`, `useSpawnProgress` ready effect
- [x] **H1/H3: /activity storm coalesced** - `refetchType:'all'` + the fact that getUsers/getServers/getStats/getServerHero all fetch `/activity` meant one mutation fired 3-4 concurrent docker-stat sweeps. A 1.5s in-flight coalescing cache on `fetchActivity` collapses them to one
  - log: 2026-06-17 `liveSource.fetchActivity` `_activityInFlight`
- [x] **H2: drop wasteful idle poll** - `stats`/`resources` no longer poll on a flat 15s interval (each dragged `/activity`); they refresh on mutation
  - log: 2026-06-17 `queries.ts`
- [x] **M1: optimistic patch live-only** - `saveUserProfile`'s `patchQuery` is guarded by `!isMock()` so it doesn't desync the mock cache
  - log: 2026-06-17
- [x] **M2: fullName matches backend** - optimistic `fullName` falls to `undefined` when both names blank (matching `getUsers`), no empty-string flicker
  - log: 2026-06-17 `\`${first} ${last}\`.trim() || undefined`
- [x] **M3: synchronous rollback** - the prior rows are snapshotted and restored synchronously on a failed write (not a refetch that shows the wrong value until it lands)
  - log: 2026-06-17

## Prefetch (already present)

- [x] **Boot prefetch** - `App.tsx::prefetchCore` warms 12 list queries at app init; `persistCache` hydrates from localStorage so first paint is instant
  - log: 2026-06-17 pre-existing, confirmed
- [ ] **Edge: prefetch on nav hover** - optional Phase 3 (sider link `onMouseEnter` -> `prefetchQuery`) - not yet implemented
  - log: 2026-06-17 deferred

## Out of scope (follow-up)

- [ ] **Slow/fast split** - decouple the light list fields from the heavy `/activity` so lists paint instantly and CPU/mem/activity cells fill in after (Phase 2); the coalescing cache mitigates the cost in the interim
  - log: 2026-06-17 planned, not yet implemented
