# Acceptance Criteria - TTL extend bar animation

Extending the idle-session TTL must move the progress bar immediately on click and animate smoothly to the new limit, with no snap-back and no delayed flash. The bar fills on click while the time text holds, then settles when the refetched value lands.

- [x] **Immediate fill** - on Extend the bar starts filling to 100% on click (optimistic boost), not 2-3s later
  - log: 2026-06-17 `TtlGadget.apply` sets boost synchronously; `meters.tsx`
- [x] **Hold until refetch** - the boost (bar pinned full) holds until the refetched `timeLeftMin` actually changes, so the bar never snaps back to the old value mid-flight
  - log: 2026-06-17 was a fixed 1s timer that fired before the 2-3s refetch; now gated on the value landing
- [x] **Minimum fill window** - the boost lasts at least `ANIMATION.ttlExtendMs` so the growth is always visible even if the refetch is fast
  - log: 2026-06-17 `minFillDone` ref
- [x] **3s duration** - the fill/glow animation runs over 3s
  - log: 2026-06-17 `ANIMATION.ttlExtendMs` 1000 -> 3000 (`services/config.ts`), threaded to CSS via `--oh-ttl-anim`
- [x] **Time text reveals on settle** - the shown minutes freeze during the boost and reveal the new value once it lands
  - log: 2026-06-17 `displayMin` frozen while boost
- [x] **Edge: extend rejected** - if `onExtend` rejects, the boost drops immediately (no false 100%)
  - log: 2026-06-17 `.catch(() => setBoost(false))`
- [x] **Edge: value never changes** - a safety cap (`ttlExtendMs + 6s`) ends the boost so it can never stick
  - log: 2026-06-17 safety timeout in `apply`
