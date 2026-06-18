# Acceptance Criteria - activity reporting consistency

The Activity meter is a 7-DAY engagement metric (capped score + average active hours vs the daily target), not a live reading. It must render the same value on every surface that reports it - the Home servers widget, the Servers screen and the Users screen - whether or not the server is running. Regression (2026-06-18): the server-row builder gated the meter on the server being running, so an offline-but-active user read e.g. 30% on Users and "none" (a muted dash) on Servers and the Home widget.

## Consistency

- [x] **Same value on Servers and Users** - the server-list rows (`getServers`, used by Servers + the Home widget) and the user-list rows (`getUsers`, used by Users) derive `activity` / `activityHours` / `activityPct` from ONE shared helper, so the two builders cannot diverge
  - log: 2026-06-18 `liveSource.ts::activityFields(a, target)` spread into both row builders; was two separate expressions (one gated on `running`)
- [x] **Reported on every surface** - Home servers widget, Servers screen and Users screen show the identical meter for the same user
  - log: 2026-06-18 all three render `<ActivityMeter value hours pct>` from the same fields
- [x] **7-day metric, not gated on run state** - `activity` reflects the trailing-window engagement, never nulled because the server is offline / spawning; only live readings (CPU, memory, system) stay gated on `running`
  - log: 2026-06-18 dropped the `running ?` gate from the server-row activity; CPU/mem/system remain gated
- [x] **Shown when the server is stopped** - an offline user with a non-zero `activity_score` shows the meter (not a muted dash) on Servers and the Home widget, matching Users
  - log: 2026-06-18 confirmed live: admin `activity_score=31`, server offline -> was 30% on Users, dash on Servers; fixed
- [x] **Mock matches live** - the demo source applies the same rule (offline + spawning rows show the 7-day meter), so `/design-language` and the mock screens never contradict the rule
  - log: 2026-06-18 `mockSource.ts::mockActivity(p)` spread into `toServerRow` (offline + main) and `toUserRow`; offline branch was `activity: null`, main branch gated on `spawning`

## Edge cases

- [x] **Edge: never sampled** - a user with no activity samples reads `activity = 0` (a 0-lit meter), the same on all surfaces - not a dash on one and a meter on another
  - log: 2026-06-18 `clampPct(a?.activity_score ?? 0)` yields 0 (not null) in both builders
- [x] **Edge: spawning** - a coming-up server shows the 7-day meter (historical engagement exists independent of the in-progress spawn); live CPU/mem stay blank until ready
  - log: 2026-06-18 activity no longer gated on spawning in either source
- [ ] **Edge: pending signup (no hub user)** - a not-yet-authorised signup with no hub User row reads `activity = 0`; it appears on Users (pending bucket) only, not on Servers/Home
  - log: 2026-06-18 `getUsers` pushes pending rows with `activity: 0`; pending users have no server row by definition

## Tests

- [x] **Functional: launch -> stop -> observe** - a Playwright test creates a user, starts their lab, leaves it ~10s, samples activity while active, stops it, then asserts the Activity meter is present (not a dash) and identical across Servers, Users and the Home widget
  - log: 2026-06-18 `tests/functional/test_activity_consistency.py`; carries `@pytest.mark.acc_crit("activity-consistency::...")`; runs against a live stack (needs the rebuilt image to validate the fix)
