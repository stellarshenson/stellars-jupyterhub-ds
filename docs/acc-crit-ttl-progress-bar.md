# Acceptance Criteria - TTL progress bar behaviour matrix

The idle-session TTL bar (`TtlGadget`, `components/meters.tsx`) reads ~100% when time is ample and drains as the session is used, shifting blue -> orange -> red as the cull nears; the used-up remainder is the gray trail. Extend opens a popover to type the hours to add, capped at the configured ceiling. The bar measures remaining against the BASE timeout (not the extension ceiling), so a fresh session reads ~100%, and an extended session caps at 100%. Verified against the code 2026-06-17, warn threshold = 60 min (`THRESHOLDS.timeLeftWarnMin`).

## Rules (verified in meters.tsx)

- [x] **Base-relative pct** - `pct = baseMin ? min(100, round(timeLeftMin / baseMin * 100)) : 0`
  - log: 2026-06-17 verified (meters.tsx)
- [x] **Caps at 100** - an extended session (timeLeft > base) shows 100%, never over
  - log: 2026-06-17 verified (Math.min(100, ...))
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
- [x] **Extended-capped** - timeLeft 300 (> base), maxAdd 6 -> pct 100 (capped), blue, Extend enabled (max 6h)
  - log: 2026-06-17 verified (min(100,125)=100)
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

## Extend refetches the bar

- [x] **Extend invalidates hero** - `extendSession` invalidates `['hero', user]` (plus session, servers) so the bar refetches and grows after a successful extend
  - log: 2026-06-17 FIXED - was `['session', user]` + `['servers']` only; the bar reads from the hero query so an extend updated the backend but only a toast showed, the bar never moved
- [ ] **Runtime: extend grows the bar** - on a running session below full, Extend visibly refills the bar to the new remaining (pinned at 100% if pushed above base), like the old design
  - log: 2026-06-17 invalidation fixed; live round-trip pending deploy

## Staged extend animation

On Extend the gadget plays a three-step animation instead of a single jump (`TtlGadget` boost state + `.oh-ttl-boost` in global.css).

- [x] **Step 1 - bar fills, time held** - on click the bar animates to 100% immediately (optimistic) while the time text holds its pre-extend value ("keep 24h on")
  - log: 2026-06-17 implemented - `boost` state forces `shownPct=100`; `displayMin` freezes the shown minutes during the fill
- [x] **Step 2 - grow to new limit** - the bar fills to the new ceiling with a brief accent glow (`oh-ttl-pulse` keyframe ~0.9s) so the extend reads as deliberate, not a flicker
  - log: 2026-06-17 implemented - antd Progress transitions the fill; `.oh-ttl-boost` adds the drop-shadow pulse
- [x] **Step 3 - time text updates** - once the refetched `timeLeftMin` lands the bar settles on the real % and the clock text reveals the new remaining time
  - log: 2026-06-17 implemented - `displayMin` snaps to the new value and `boost` clears after the fill (~900ms) or as soon as new data arrives
- [x] **Clock icon before the time** - the clock glyph renders immediately left of the remaining-time text in the gadget
  - log: 2026-06-17 present (`Icon name="clock"` before `<b>` in `.oh-ttl-val`)
- [ ] **Edge: partial extend below base** - extending only part-way (remaining still < base) fills to 100% then settles back to the real % when data lands; acceptable since Extend normally tops toward the ceiling
  - log: 2026-06-17 noted; common path (extend exceeds base) ends at 100% with no settle-back
- [ ] **Runtime: animation on the live hub** - the three-step sequence is visible end-to-end on a real extend round-trip
  - log: 2026-06-17 coded; visual confirm pends rebuild

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
