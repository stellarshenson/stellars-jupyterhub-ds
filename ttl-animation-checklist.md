# TTL Animation - Signoff Checklist

Complete requirements contract for the idle-session TTL gadget (`TtlGadget`, `services/jupyterhub/duoptimum-hub-web/src/components/meters.tsx`; keyframes in `src/styles/global.css`; timing in `src/services/config.ts`). The gadget shows time remaining as a progress bar + an absolute-time counter + a clock glyph, with an Extend control. It carries two animations: the resting expiry glow as time runs low, and the one-shot extend "boost" envelope. Every box below must pass before the animation is signed off.

Status legend: `[x]` verified with evidence, `[ ]` open or unverified. Items blocked by an open defect name it inline.

Evidence anchor: a live frame-capture (functest, +4h extend, 60ms cadence) is the duration / motion source of truth, referenced below as "capture".

## Scope

- [x] **Components** - bar (custom `.doh-ttl-track` > `.doh-ttl-fill` inside `.doh-ttl-bar`, NOT antd `Progress`), counter (`.doh-ttl-val b`), clock glyph (`.doh-ttl-clock-*`), Extend trigger + popover slider
- [x] **Two animation families** - resting expiry glow (`doh-ttl-glow-soft` / `doh-ttl-glow`) and the extend boost envelope (`doh-ttl-fill-boost` + `doh-ttl-sweep` / `-num` / `-clock`)
- [x] **Timing source** - `ANIMATION.ttlExtendMs` (`config.ts`, 3000ms) drives both the rAF tween and the inline CSS var `--doh-ttl-anim`

## Resting bar (no boost)

- [x] **Fill = time-vs-high-water-mark** - fill % is remaining measured against the high-water mark (`display_ceiling`), not the far absolute ceiling (DEF-13); a just-extended session reads ~100%
- [x] **Tone bands** - blue at `frac >= warnFrac`, a red↔warning gradient mid, red at `frac <= dangerFrac` (`ttlTone`)
- [x] **Counter = absolute remaining** - shows the live absolute remaining duration (e.g. `26h 5m`), tabular-nums, never a static `+delta`
- [x] **No success flip at 100%** - `Progress status="normal"` pinned so antd does not toggle the success style at percent >= 100 (identical render at 99 and 100)
- [ ] **Edge: stopped server** - the TTL slot shows "stopped Xh ago" / "never started", never a live bar (covered by `test_stopped_server_shows_stopped_ago_readout`)

## Resting clock expiry glow

- [x] **No glow above warn** - `frac > warnFrac` → no clock animation
- [x] **Soft glow at warn** - `frac <= warnFrac` → `doh-ttl-glow-soft` (2.4s ease-in-out infinite), a gentle pulse
- [x] **Bright/fast glow at end** - `frac <= dangerFrac` → `doh-ttl-glow` (1s ease-in-out infinite), brighter and faster
- [x] **Boost overrides expiry** - while boosting, the clock runs `doh-ttl-clock-boost`, not the expiry glow

## Extend trigger and popover

- [x] **Trigger visible when running** - the Extend button shows when the server is running and below ceiling
- [x] **At ceiling: disabled** - `atCeiling` → button disabled, tooltip "Already at the maximum session length"
- [x] **Popover slider** - opens a slider, default a stable +4h (not the shifting max), marks `1h` and `max`
- [x] **Apply label** - the apply button reads "Extend +Nh" reflecting the slider value
- [x] **In-flight: disabled, label unchanged** - during the extend the trigger is disabled and the label STAYS "Extend" (never "Extending") (task #547)

## Boost envelope - duration and lifetime

- [x] **Single one-shot envelope** - one ramp-up / steady / ramp-down per extend, NOT a repeating pulse (`linear`, no `infinite`)
- [x] **3s duration resolves at runtime** - capture: `getComputedStyle(fill).animationDuration === "3s"` on every frame; deployed JS `ttlExtendMs:3e3` = 3000ms; CSS `animation: doh-ttl-boost-bar var(--doh-ttl-anim, 3s)`; inline var wired from `ttlExtendMs`
- [x] **CSS-var fallback equals the default** - the `3s` literal fallback in `global.css` must equal `ANIMATION.ttlExtendMs` (3000ms); drift between them is a defect
- [x] **Class held the full envelope** - capture: `.doh-ttl-boost` present t=60ms → t=2940ms (~2.88s), then dropped cleanly at t=3000ms; held for the in-flight extend AND at least one full envelope (`setTimeout(..., ttlExtendMs)`)
- [x] **rAF and CSS in lockstep** - the rAF counter/fill tween and the three CSS keyframes both span `ttlExtendMs`; the 25%/75% keyframe stops match `rampEase` a=0.25

## Boost envelope - fill (bar)

- [ ] **Bar shows a visible boost cue REGARDLESS of fill %** - FIX APPLIED (pending live verify): a bright sheen sweeps the WHOLE track once (`doh-ttl-sweep`, cropped by the track `overflow:hidden`) + an inner inset bloom on the fill, so the bar reads as "charging" even at a pinned 100%; replaces the earlier wrapper box-shadow halo that bled onto the controls ([DEF-29](docs/acceptance-criteria/defects-duoptimumhub.md))
  - capture evidence (pre-fix): fill `width` = `100%` on all 49 boost frames of a +4h extend, with no perceptible bar motion
- [ ] **Fill grows when below base** - extending a sub-base session (bar < 100%) must grow the fill from the current % to the target % over 3s (rAF owns width); needs a dedicated below-base capture to verify (the at/above-base capture cannot show growth)
- [x] **Target = post-extend % vs the new mark** - boost target `pctFor(targetMin, targetMin)`; a banked extend lands at 100%, a still-sub-base extend fills toward base; no momentary 100%-then-drop (DEF-13)
- [x] **No flip-to-100** - the fill grows, it does not snap to 100% then settle (DEF-15)
- [ ] **Fill glow on the same hue** - FIX APPLIED (pending live verify): `doh-ttl-fill-boost` lifts brightness/saturation on the SAME accent hue (theme-aware `--doh-ttl-boost-bright`: dark 1.35, light 1.65), never a hue change, plus an inner inset bloom `--doh-ttl-glow-core` clipped to the fill
- [ ] **Glow is CLIPPED, never bleeds** - FIX APPLIED (pending live verify): the boost glow (inset fill bloom + sheen sweep) lives entirely inside the track `overflow:hidden`; it can NEVER bleed onto the Open/Restart/Stop buttons or Extend the way the old wrapper box-shadow did ([DEF-29])
- [ ] **No color-mix in the ramped glow** - FIX APPLIED (pending live verify): the inset bloom + sheen use solid rgba tokens (`--doh-ttl-glow-core`, `--doh-ttl-sheen`), not a `color-mix()` endpoint (a `color-mix` endpoint makes Chromium discrete-step the shadow → it pops instead of ramping) (DEF-14 lineage)

## Boost envelope - counter

- [x] **Counts to the new absolute remaining** - capture: counter ticks `24h 0m → 28h 0m` smoothly across the full 3s (rAF on the integer), minutes shown so it is a smooth count, not sparse hour steps
- [x] **Absolute time, no +delta** - the readout is the absolute remaining duration, never a leading `+` (asserted by `test_extend_boost_motion`)
- [x] **Blur envelope** - `doh-ttl-boost-num` blur 0 → 1.4px → 0 (sharp at rest, no 0% spike)
- [x] **Scale only, shared baseline** - `transform: scale(.99)` only (no translateY) so the number keeps its baseline with the clock glyph

## Boost envelope - clock

- [x] **Clock glow envelope** - `doh-ttl-clock-boost` → `doh-ttl-boost-clock`, drop-shadow radius 0 → 3/5px → 0 (operator -50% from 6/10px), ramps in lockstep; counter blur 0.83px (operator -25% from 1.1px)
- [x] **currentColor, no color-mix** - both drop-shadows use `currentColor` and ramp ONLY the radius; no `color-mix()` (a `color-mix` shadow made Chromium discrete-fall-back the whole filter list → the clock blinked at segment midpoints) (DEF-14)

## Boost - colour

- [x] **Gadget recolours to accent** - the whole gadget tones to `var(--color-accent)` while boosting (fixed hue); the glow is brightness/saturation on that hue, never a mid-pulse hue change (`test_extend_boost_motion` asserts the fill background == the resolved accent rgb)

## Settle (post-boost)

- [x] **Bar settles onto the new remaining** - when the class drops, antd's width transition returns and the bar settles on the refetched value
- [x] **No snap-back** - the backend stores the same mark the boost targeted, so optimistic % == refetched %; the bar is already there when the value lands
- [x] **Hold target across refetch** - `pendingTarget` is held across the boost release until the parent's refetch lands, so there is no backward flash to the stale pre-extend prop
- [x] **Counter ends on the new value** - capture: counter rests at `28h 0m` after t=2940ms

## Failure path

- [ ] **Reject ends boost immediately + error toast** - on extend reject the boost ends at once, `pendingTarget` is cleared, the bar falls back to the live prop, and an error toast fires; verify the abort is graceful (no half-grown bar stuck)

## Reduced motion (WCAG 2.3.3)

- [x] **Boost is EXEMPT under reduce (deliberate)** - the one-shot, user-triggered extend boost PLAYS under `prefers-reduced-motion: reduce` (rAF tweens, CSS keyframes run, 3s hold armed) - it is a confirmation the operator wants in all cases. Gating it (the old `minCycle = reduce ? null : timer` + `@media` guard) collapsed it to ~0ms and WAS the root cause of "lasts a fraction of a second" ([DEF-28]); now exempt and verified 2939ms under emulated reduce
- [x] **Only infinite ambient pulses are gated** - the `@media (prefers-reduced-motion: reduce)` block stops only the continuous/ambient animations (expiry clock glows `doh-ttl-clock-warn`/`-end`, connection diode, spawning dot, bar slide transitions); the boost selectors are NOT listed, so they survive

## Perceptual quality (the headline contract)

> [!IMPORTANT]
> A technically-correct 3s timeline is NOT sufficient. The animation must READ as ~3s of deliberate "effort", not a sub-second flash. This is where [DEF-28] lives.

- [x] **Reads as ~3s, not a flash** - ROOT CAUSE was `prefers-reduced-motion` (OS "reduce motion") collapsing the boost to ~0ms, NOT the frozen fill; the boost is now exempt from both the CSS `@media` guard and the JS reduce-branch; functest under emulated `reduced_motion=reduce` measured 2939ms (was ~0); operator confirmed "now animation works" ([DEF-28])
- [ ] **Perceptible motion spread across the envelope** - the dominant visual must move through the whole 3s, not front-load all change into the first <1s and sit on a steady plateau
- [ ] **Bar carries perceptible motion in the common case** - FIX APPLIED (pending live verify): the sheen sweep + inner bloom make the bar visibly move on EVERY extend, including when the fill is already at 100%, all CONTAINED inside the track ([DEF-29])
- [ ] **Light-theme brightness reads as a glow** - confirm `--doh-ttl-boost-bright` = 1.65 (light) reads as a glow, not a wash-out, on the live hub (operator eyeball)

### Full-bar boost (no growth) - operator contract

When the bar is already full and an extend only tops it up (no width growth), the boost must still earn its keep:

- [x] **(1) Duration holds at 3s** - the envelope still runs the full 3s (capture: class lives ~2.88s, duration 3s)
- [x] **(2) Counter still blurs + counts with ramp** - the counter blurs and counts up with `rampEase` (speed up → count → slow down) regardless of fill (capture: 24h 0m → 28h 0m over 3s)
- [ ] **(3) Whole bar glows the bright accent (contained)** - FIX v3 (pending verify): the box-shadow halo cuts (ring rgba .35, then solid accent 26px) bled onto the controls and read as "awful" ([DEF-29]); now a bright sheen sweeps the whole track once + an inner inset bloom on the fill + the brightness lift, ALL clipped inside the track `overflow:hidden` - it glows as a whole even at a pinned 100% yet never bleeds

## Technical / non-regression

- [x] **No stale deployed bundle** - the served bundle must carry the current duration + keyframes (the stale-`:latest` hazard); verified this session against `/srv/venv/.../duoptimum_hub_web/static`
- [x] **No color-mix in any RAMPED filter** - color-mix endpoints force Chromium's discrete-animation fallback → blink/pop; all ramped shadows use currentColor / a solid rgba token (DEF-14)
- [x] **animation-name stable while boosting** - the boost animation-name is constant while the class is on, so functional assertions are race-free

## Verification gates

- [x] **Functional: `test_extend_boost_motion`** - boost class lands, fill runs `doh-ttl-boost-bar`, fill bg == accent rgb, counter runs `doh-ttl-boost-num` + absolute time + no `+`, clock runs `doh-ttl-boost-clock`, trigger disabled with label "Extend"
- [x] **Live frame-capture: duration + class lifetime** - boost class ~2.88s, animation-duration 3s, counter 24h→28h over 3s (this checklist's evidence anchor)
- [ ] **Live frame-capture: below-base fill growth** - a separate capture with the session below base TTL, confirming the fill actually grows 3s (the at/above-base capture cannot show this)
- [ ] **Perceptual signoff (DEF-28)** - operator + ux-designer confirm the boost reads as deliberate ~3s effort once the fill-independent cue lands
- [ ] **Adversarial signoff** - ux-designer (motion comfort, afterimage, the front-loading) + architect (keyframe-contract: each keyframe consumed once, var wired, no color-mix) come back clean on the fix
- [ ] **Design-system parity** - the `/design-system` (a.k.a. design-language) TTL demo matches the shipped widget after the fix

## Open defects referenced

- DEF-28 - TTL extend animation reads as ~0.5s (bar frozen at 100% under high-water-mark) - `docs/acceptance-criteria/defects-duoptimumhub.md`
- DEF-13 - TTL bar scaled to high-water mark (the reason the fill pins at 100% on extend) - fixed, but it is the upstream cause of DEF-28's frozen bar
- DEF-14 - color-mix in ramped filters caused blink/pop - fixed; the no-color-mix rules above prevent regression
- DEF-15 - bar flipped to 100% instead of growing - the fill-growth rules above prevent regression
