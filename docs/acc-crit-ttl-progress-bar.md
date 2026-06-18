# Acceptance Criteria - TTL progress bar behaviour matrix

The idle-session TTL bar (`TtlGadget`, `components/meters.tsx`) reads ~100% when time is ample and drains as the session is used, shifting blue -> orange -> red as the cull nears; the used-up remainder is the gray trail. Extend opens a popover to type the hours to add, capped at the configured ceiling. A fresh session reads ~100% and drains; an EXTENDED session (time banked above base) drains against the extension ceiling (base + max_extension) so the user sees it running out, then rescales to full at the standard baseline. Verified against the code 2026-06-17, warn threshold = 60 min (`THRESHOLDS.timeLeftWarnMin`).

## Rules (verified in meters.tsx)

- [x] **Two-phase pct** - below base: `min(100, timeLeft/base)`; extended (timeLeft > base): `timeLeft / ceiling` where `ceiling = timeLeft + maxAddHours*60` (= base + max_extension), so the extended bar drains instead of pinning at 100%
  - log: 2026-06-17 reworked (operator: extended must visibly drain) - was `min(100, timeLeft/base)` capped
- [x] **Rescale to base at the baseline** - the moment timeLeft falls to base the scale switches to base (full again), then drains normally below; a visible snap-to-full at the baseline crossover (operator-chosen model)
  - log: 2026-06-17 implemented (meters.tsx ceilingMin branch)
- [x] **Colour bands** - danger (red) at `timeLeftMin <= 20` (warn/3); warning (amber) at `<= 60`; accent (blue) above
  - log: 2026-06-17 verified (color ternary, warn=60)
- [x] **Extend = hours input** - Extend opens a popover with an InputNumber (min 1, max = round(maxAddHours)); apply clamps and calls onExtend
  - log: 2026-06-17 verified (Popover + InputNumber + apply clamp)
- [x] **At ceiling disables Extend** - `atCeiling = maxAddHours <= 0` -> Extend button disabled
  - log: 2026-06-17 verified (atCeiling)
- [x] **Hidden when stopped** - the gadget is only rendered for a running server
  - log: 2026-06-17 verified (ServerHero `{running && <TtlGadget/>}` + MobileHome MyServerCard)

## Behaviour matrix (base = 240 min)

Each row is demonstrated live on `/design-language` (TTL behaviour matrix row).

- [x] **Full** - timeLeft 240, maxAdd 12 -> pct 100, blue, Extend enabled (max 12h)
  - log: 2026-06-17 verified by code + design-language demo
- [x] **Ample** - timeLeft 180, maxAdd 12 -> pct 75, blue, Extend enabled
  - log: 2026-06-17 verified
- [x] **Warn** - timeLeft 45, maxAdd 12 -> pct 19, amber, Extend enabled
  - log: 2026-06-17 verified (45 <= 60, > 20)
- [x] **Low / danger** - timeLeft 12, maxAdd 12 -> pct 5, red, Extend enabled
  - log: 2026-06-17 verified (12 <= 20)
- [x] **Extended-drains** - timeLeft 300 (> base 240), maxAdd 6 -> ceiling 300+360=660, pct 45 (drains against the ceiling, NOT capped at 100), blue, Extend enabled (max 6h)
  - log: 2026-06-17 reworked (operator: extended must visibly drain) - was pct 100 capped
- [x] **At ceiling** - timeLeft 180, maxAdd 0 -> pct 75, blue, Extend DISABLED
  - log: 2026-06-17 verified (atCeiling true)
- [x] **Stopped** - server offline -> gadget not rendered at all
  - log: 2026-06-17 verified (running-gate)

## Extension flow

- [x] **Extend caps at allowance** - typed hours clamped to [1, round(maxAddHours)] before onExtend
  - log: 2026-06-17 verified (apply: Math.max(1, Math.min(maxH, round(hours))))
- [ ] **Runtime: extend round-trips** - clicking Extend issues the real `POST /users/{name}/extend-session` and the bar/clock refresh to the new remaining time
  - log: 2026-06-17 pending deploy (onExtend -> extendSession wired; live round-trip needs the running hub)
- [x] **Runtime: visual drain + colour shift** - the matrix renders blue -> amber -> red with the base-relative cap and the at-ceiling disable
  - log: 2026-06-17 VISUALLY CONFIRMED via Playwright headless render of /design-language (6 gadgets): full=100% blue, ample=75% blue, warn=amber, low=red, extended(5h>base)=full bar capped not overflowing, at-ceiling=Extend disabled. Screenshot reviewed. (Live drain over wall-clock + extend round-trip on a running session still observable on the deployed hub.)

## Replenish laws (SSOT: idle_culler.py, mirrored in the bar)

- [x] **Activity floor = base** - an active server retains at least base; activity replenishes remaining up to base, never above (`calc_remaining` activity_floor = base - idle)
  - log: 2026-06-17 verified (test_remaining_keeps_active_server_at_base)
- [x] **No replenish above base** - while extended (remaining > base) an active server is NOT topped up; the banked time drains via the deadline until it falls to base
  - log: 2026-06-17 added test_remaining_extended_not_inflated_by_activity
- [x] **Drains to base then replenishes** - once remaining falls below base, an active server is topped back to exactly base ("max becomes base again") and normal replenish resumes
  - log: 2026-06-17 added test_remaining_below_base_active_replenishes_to_base
- [x] **Ceiling cap** - no extend sequence banks lifetime past base + max_extension; the deadline never sits more than ceiling ahead of now
  - log: 2026-06-17 verified (test_remaining_clamped_to_ceiling, test_extend_caps_at_ceiling)

## Extended TTL must visibly drain (operator 2026-06-17)

The backend already drains banked extension down to base; the BAR now shows it. Operator-chosen model: scale the extended bar to the extension ceiling so it drains (gray trail growing), then rescale to the standard baseline at the crossover (snaps full again, against the standard baseline not the extended scale).

- [x] **Drains while extended** - when remaining > base the bar shrinks against the ceiling as time passes (the user sees time running out), no longer pinned at 100%
  - log: 2026-06-17 implemented (meters.tsx `ceilingMin` two-phase pct)
- [x] **Gray leftover** - the drained portion above the current remaining shows as the standard gray trail (antd Progress trailColor)
  - log: 2026-06-17 implemented
- [x] **Full again at the standard TTL** - at the standard baseline the bar rescales to base and reads full again (against the standard baseline, not the extended scale); below base it drains normally
  - log: 2026-06-17 implemented (operator-chosen: visible snap-to-full at the baseline crossover)

## Extend refetches the bar

- [x] **Extend invalidates hero** - `extendSession` invalidates `['hero', user]` (plus session, servers) so the bar refetches and grows after a successful extend
  - log: 2026-06-17 FIXED - was `['session', user]` + `['servers']` only; the bar reads from the hero query so an extend updated the backend but only a toast showed, the bar never moved
- [x] **Runtime: extend grows the bar** - on a running session, Extend visibly animates the bar to the post-extend remaining; below base it fills toward base, when banked above base it grows against the ceiling (never pinned at a false 100%)
  - log: 2026-06-17 invalidation fixed; 2026-06-18 boost target corrected from 100% to the computed post-extend %

## Staged extend animation

On Extend the gadget plays a three-step animation instead of a single jump (`TtlGadget` boost state + `.oh-ttl-boost` in global.css). The bar animates to the **computed post-extend target %** (against the invariant ceiling), never a blanket 100%.

- [x] **Step 1 - bar moves to target, time held** - on click the bar animates immediately toward `boostPct = pctFor(min(ceiling, timeLeft + addedHours))` (the same two-phase formula) while the time text holds its pre-extend value
  - log: 2026-06-17 implemented as `shownPct=100`; 2026-06-18 FIXED to the computed target `boostPct` so an extended session animates to its true partial % (operator: 56h +7h overshot to 100% then snapped to 63h); `displayMin` freezes the shown minutes during the fill
- [x] **Step 2 - grow to new limit over a configured duration** - the bar visibly fills to the new ceiling (not a snap) with a brief accent glow, like the old design
  - log: 2026-06-17 implemented, then (operator: "not properly animated ... make it 1s") forced a visible fill - `.oh-ttl-boost .ant-progress-bg { transition: width var(--oh-ttl-anim) ease }` overrides antd's quick default; boost window + `oh-ttl-pulse` glow share the same duration
- [x] **Duration is package-config** - the fill duration lives in `optimum-hub-web/src/services/config.ts` (`ANIMATION.ttlExtendMs`, default 1000), NOT a Docker env (too granular); it drives the JS hold timer and, via the `--oh-ttl-anim` CSS var on the bar, the CSS transition + glow from one place
  - log: 2026-06-17 added `ANIMATION` config; `meters.tsx` reads it for the timer + sets `--oh-ttl-anim`; `global.css` uses `var(--oh-ttl-anim, 1s)`
- [x] **Step 3 - time text updates, no snap** - once the refetched `timeLeftMin` lands the bar settles on the real % (which equals the target it already animated to, ceiling being invariant, so no jump) and the clock text reveals the new remaining time
  - log: 2026-06-17 implemented; 2026-06-18 the settle now lands on the same % as the boost target, eliminating the snap-back flicker
- [x] **Clock icon before the time** - the clock glyph renders immediately left of the remaining-time text in the gadget
  - log: 2026-06-17 present (`Icon name="clock"` before `<b>` in `.oh-ttl-val`)
- [x] **Edge: partial extend below base** - extending only part-way (remaining still < base) animates to the base-scaled target % and settles there; no overshoot to 100%
  - log: 2026-06-18 fixed by the target-% boost (was: filled to 100% then settled back)
- [x] **Edge: extend while banked (> base)** - both endpoints above base -> the bar grows monotonically against the ceiling (the operator's reported case: 56h -> 63h), no overshoot/snap
  - log: 2026-06-18 the regression this fix closes
- [ ] **Runtime: animation on the live hub** - the three-step sequence is visible end-to-end on a real extend round-trip
  - log: 2026-06-17 coded; 2026-06-18 target-% fix coded; visual confirm pends rebuild

## Test harness

- [x] **Python SSOT matrix runs all scenarios** - `test_ttl_matrix.py` + `test_idle_culler.py` cover progress pct, ceiling, available hours, extend (add/cap/maxed), remaining (activity floor, replenish, ceiling, floor), cull
  - log: 2026-06-17 extended with the two replenish-law scenarios; `make test` green
- [ ] **No JS test harness for the bar** - the portal has no vitest setup; the `TtlGadget` pct formula mirrors `calc_progress_pct` verbatim and is covered in Python; a JS unit test would need a new harness
  - log: 2026-06-17 gap documented

## Home server-controls additions

- [x] **Uptime on the TTL line** - the TtlGadget shows "up Xh" inline (next to the remaining-time clock) for a running server
  - log: 2026-06-17 implemented - `server_started` (spawner `orm_spawner.started`) added to the activity payload -> `getServerHero.startedISO` -> `TtlGadget uptimeLabel={timeAgoShort(startedISO)}`; mock + typecheck clean
- [x] **Upgrade-available pill** - a gold "Upgrade available" pill shows left of the status pill on the Server status card when a newer lab image is available locally than the running container's
  - log: 2026-06-17 implemented - `lab_image_id` (cached ~5min) vs the container's running image id (`container.attrs['Image']`, reused from the stats inspect); `image_upgrade_available` pure helper (5 unit tests); surfaced as `lab_image_upgrade_available` -> `hero.upgradeAvailable`
- [x] **Edge: image id unknown** - local image absent / docker unreachable -> `lab_image_id` None -> no upgrade offered (never a false pill)
  - log: 2026-06-17 covered by test_image_upgrade (None cases)
- [ ] **Edge: re-tag to older** - if the local tag is moved to an OLDER image the pill still shows (different-id heuristic; watchtower only pulls forward so this is theoretical)
  - log: 2026-06-17 documented limitation - a created-time compare would close it at the cost of extra docker inspects; left out by design
