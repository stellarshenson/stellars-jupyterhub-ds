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
