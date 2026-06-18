# Acceptance Criteria - TTL extend bar animation

Extending the idle-session TTL must move the progress bar immediately on click and animate smoothly to the **computed post-extend target %**, with no overshoot, no snap-back and no delayed flash. The bar and the time-left counter animate on click in lockstep, then settle when the refetched value lands - landing on the same % it animated to, so there is no jump.

- [x] **Immediate animate to target** - on Extend the bar starts moving on click (optimistic boost) toward the post-extend target %, not 2-3s later
  - log: 2026-06-17 `TtlGadget.apply` sets boost synchronously; `meters.tsx`
- [x] **Target = computed post-extend %, not 100%** - the boost target is `pctFor(min(ceiling, timeLeft + addedHours))` through the same two-phase formula (base scale below base, ceiling scale when extended), NOT a hard-coded 100%; so an already-extended session animates to its true partial % and never overshoots to full
  - log: 2026-06-18 FIXED - was `shownPct = boost ? 100 : pct`; overshot to 100% then snapped down to the real ceiling-scaled % (operator: 56h +7h animated to 100% then flickered to 63h). Now `boostPct` captured at click from the optimistic remaining against the invariant ceiling
- [x] **No snap-back on settle** - because the ceiling is invariant across an extend, the optimistic target equals the refetched %, so when the value lands the bar is already there (no visible jump)
  - log: 2026-06-18 added with the target-% fix
- [x] **Hold until refetch** - the boost (bar held at the target) holds until the refetched `timeLeftMin` actually changes, so the bar never snaps back to the old value mid-flight
  - log: 2026-06-17 was a fixed 1s timer that fired before the 2-3s refetch; now gated on the value landing
- [x] **Minimum fill window** - the boost lasts at least `ANIMATION.ttlExtendMs` so the growth is always visible even if the refetch is fast
  - log: 2026-06-17 `minFillDone` ref
- [x] **3s duration** - the fill/glow animation runs over 3s
  - log: 2026-06-17 `ANIMATION.ttlExtendMs` 1000 -> 3000 (`services/config.ts`), threaded to CSS via `--oh-ttl-anim`
- [x] **Time counter climbs with the bar** - during the boost the shown minutes count UP from the captured baseline to the post-extend target over the SAME `ttlExtendMs` duration and CSS-`ease` easing as the bar fill, so the number climbs in lockstep with the bar; on settle it lands on the live refetched value
  - log: 2026-06-17 originally the shown minutes FROZE during the boost and revealed the new value only on settle (`displayMin` held)
  - log: 2026-06-18 changed to a synchronized count-up (operator "animate the time-left counter to climb alongside the bar"): a `requestAnimationFrame` tween in `TtlGadget` drives `displayMin` from `baselineMin` to `boostTargetMin` via `EASE` (cubic-bezier(.25,.1,.25,1), matching the bar's CSS `ease`); cancels on reject/unmount; `meters.tsx`
- [x] **Edge: extend rejected** - if `onExtend` rejects, the boost drops immediately (bar returns to the real %)
  - log: 2026-06-17 `.catch(() => setBoost(false))`
- [x] **Edge: value never changes** - a safety cap (`ttlExtendMs + 6s`) ends the boost so it can never stick
  - log: 2026-06-17 safety timeout in `apply`
- [x] **Edge: extend across the base crossover** - extending a session from below base up past base animates to the post-extend ceiling-scaled % (a one-time scale-switch drop is the operator-chosen two-phase model, not the bug); within the banked regime (both endpoints > base) the bar grows monotonically
  - log: 2026-06-18 documented - the target-% boost makes the crossover land on the true % with no overshoot
