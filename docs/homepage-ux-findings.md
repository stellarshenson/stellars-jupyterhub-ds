# Homepage UX vs Design-System Spec - Actionable Findings

Adversarial UX review of the DuOptimum Hub homepage, each aspect compared against the canonical design artifact (`docs/design-system/Design Language.dc.html`), the in-app gallery (`src/pages/DesignSystem.tsx`), and the tokens. Six independent ux-designer reviewers; findings deduped and severity-ordered here. Every item is actionable - file:line, spec reference, concrete fix. Checkboxes are the execution backlog.

Paths are under `services/jupyterhub/duoptimum-hub-web/` unless noted. Artifact line refs are `dc:<line>`.

## Verdict summary

| Aspect | Verdict | B | M | m | T |
|---|---|---|---|---|---|
| Resource bars | SHIP WITH FIXES | 0 | 3 | 3 | 1 |
| TTL gadget | SHIP WITH FIXES | 2 | 1 | 1 | 1 |
| GPU meter | DO NOT SHIP | 3 | 3 | 3 | 1 |
| Spark / activity / metric card | SHIP WITH FIXES | 0 | 3 | 3 | 2 |
| Server Control hero | SHIP WITH FIXES | 0 | 1 | 2 | 1 |
| Layout / cards / feed / conventions | SHIP WITH FIXES | 0 | 4 | 5 | 1 |
| **Total (pre-dedup)** | | **5** | **15** | **17** | **7** |

B = BLOCKER, M = MAJOR, m = MINOR, T = TASTE. The GPU meter is the only DO-NOT-SHIP. After cross-aspect dedup (per-GPU % readout, GPU label width) the unique count is ~42.

## Decisions required first (artifact vs operator-tuned shipped)

These are NOT blind fixes - the shipped code intentionally diverges from the artifact on a prior operator call. Resolve the source-of-truth before executing the related items.

- [ ] **TTL motion: restore per artifact, or amend the artifact** - the artifact models a full TTL motion set (expiry clock-glow ramp; mid-extend bar glow + brightness + box-shadow, counter blur, clock glow; "+2h" boost number; "Extending…" button). The shipped gadget has NONE of it (recently removed). Operator has signalled the artifact is authoritative → lean **restore (option b)**. Gates TTL-1..TTL-6 below.
- [ ] **Connection diode: opacity-only (artifact) vs opacity+scale (shipped)** - artifact `dc:389,53-54` mandates opacity-only at 3.6s/1.2s; shipped uses opacity+scale at 3s/1s, a deliberate operator decision recorded in `docs/design-system/README.md` ("amplitude carries meaning"). DECIDE: keep the tuned scale (then fix the artifact + `DesignSystem.tsx:221` copy to match) OR revert to opacity-only. Gates LAY-1.
- [ ] **TTL boost number: "+delta" (artifact) vs absolute count-up (shipped)** - artifact shows `+2h 0m` (amount added); shipped counts absolute remaining up. Pick one; amend the loser. Gates TTL-5.

## Cross-cutting themes (fix once, lands everywhere)

- [ ] **X1 [MAJOR] prefers-reduced-motion gaps** - the reduced-motion guard (`global.css:292-294`) covers only the connection diode. NOT covered: the resource-bar fill `width/background .4s` transition (`meters.tsx:218`), the spawning-pill / in-progress pulse `doh-pulse` (`global.css:77,82`), and (if TTL motion is restored) the TTL glows. Fix: extend the `@media (prefers-reduced-motion: reduce)` block to `animation:none`/`transition:none` for `.doh-res-bar > i`, `.doh-gpurow .track > i`, `.doh-pill.spawning .doh-dot`, and any TTL glow. (Sources: RES-3, HERO-1.)
- [ ] **X2 [MAJOR] colour-and-hover-only signalling (a11y)** - the activity meter, spark, and GPU stripes convey state through colour + a hover-only native `title`: no `role`/`aria-label`/`aria-valuenow`, unreachable by keyboard/touch/SR. Fix: add `role="img"` + `aria-label` (reuse `activityTitle`/`gpuTip` strings) to `.doh-meter`, `.doh-spark`, and the GPU rows; always include a non-colour identifier (GPU device index in the label). (Sources: ACT-3, GPU-6.)
- [ ] **X3 [MAJOR] WCAG AA contrast on muted text** - `--color-text-subtle` measures 3.25:1 (dark) / 4.03:1 (light), under 4.5:1, on small (10-12px) text: feed timestamp, grant "from" label, Quick-Actions sub-caption, name-hint, plus several spark segments unverified. Fix: darken/lighten `--color-text-subtle` (`tokens.ts:64,103`) to ≥4.5:1 on `--color-surface` in both themes, or promote those elements to `--color-text-muted`. (Sources: LAY-3, ACT-4.)
- [ ] **X4 [MAJOR] in-app DesignSystem page drifted from the artifact** - `DesignSystem.tsx` now contradicts the canonical artifact in three places: ramp label "calm to 50%" vs 70% (`:268`), TTL note stripped of all motion language (`:252-255`), connection-diode copy documents the scale version (`:221`). Fix each as its source aspect is resolved so the in-app gallery and the artifact agree again. (Sources: RES-1, TTL-3, LAY-1.)
- [ ] **X5 [MAJOR] per-GPU % readout missing (flagged by 2 reviewers)** - the artifact GPU row carries a 34px right-aligned `{{ g.pct }}` per device (`dc:425`); shipped `GpuMeter` shows label+bar only, load is hover-only. Fix under GPU-5. (Sources: GPU-5, RES-2.)

## Resource bars

- [ ] **RES-1 [MAJOR]** In-app spec label contradicts the canonical threshold - `DesignSystem.tsx:268` says "calm to 50%" but artifact `dc:444` + code (`config.ts:24` warnPct 70, `meters.tsx:172-178`) say 70%; the page even contradicts its own `:253` note and 60% demo. Fix: relabel to "calm to 70%, then warning → danger". (See X4.)
- [ ] **RES-2 [MAJOR]** Per-GPU bars have no glanceable % readout - see X5 / GPU-5 (`meters.tsx:78-101` vs `dc:422-426`).
- [ ] **RES-3 [MAJOR]** Resource-bar fill transition not gated by reduced-motion - `meters.tsx:218`. See X1.
- [ ] **RES-4 [MINOR]** GPU fill has a 3% phantom floor - `meters.tsx:91` `Math.max(3, g)%` paints a 0% GPU as lightly loaded; bar disagrees with the "0%" tooltip. Fix: drop the floor to `${g}%` (striped empty track already reads as a GPU bar), or floor only the visible stripe.
- [ ] **RES-5 [MINOR]** CPU bar fill unclamped above 100% - `meters.tsx:218` `width: ${r.value}%`; a 130% reading shows a full-but-undistinguished bar beside "130%". Fix: clamp fill with `Math.min(100, r.value)`, leave the label uncapped (mirrors the activity meter).
- [ ] **RES-6 [MINOR]** GPU label column drifts (112px vs spec 118px) and GPU rows lack the 84px value gutter, so bar right-edges don't align with CPU/Mem rows in one panel - `global.css:119,112-115` vs `dc:425`. Fix: 112→118px and reserve a matching right gutter. (Dedup with GPU-7.)
- [ ] **RES-7 [TASTE]** Warn→danger blend is spec-correct but the perceptual jump is at the 70% accent→warning edge, not at danger - `meters.tsx:172-178`. Note only; no change.

## TTL gadget

Gated on the TTL-motion decision above. If "restore per artifact" (recommended):

- [ ] **TTL-1 [BLOCKER]** Expiry clock-glow ramp is absent - the artifact's core "catch the eye near expiry" promise (`dc:444`, keyframes `dc:55,56`, rows `dc:433,434`). Shipped clock is a static `<Icon>` (`meters.tsx:387`). Fix: port `doh-ttl-glow` / `doh-ttl-glow-soft` into `global.css`; in `meters.tsx` derive the glow from `frac = timeLeftMin/baseMin` (`<=dangerFrac` → `doh-ttl-glow 1s`, `<=warnFrac` → `doh-ttl-glow-soft 2.4s`, else none); forward `style` to the clock (wrap in `<span>` if `Icon` doesn't). Gate behind reduced-motion (X1).
- [ ] **TTL-2 [BLOCKER]** Mid-extend boost loses all three cues + the "Extending…" label - bar glow+brightness+box-shadow (`doh-ttl-boost-bar` `dc:57`), counter blur (`doh-ttl-boost-num` `dc:58`), clock glow (`doh-ttl-boost-clock` `dc:59`), button `Extending…` (`dc:440`). Shipped has none (`meters.tsx:379,384,387,388,418-420`; comment owns the removal `meters.tsx:374-376`). Fix: add the three keyframes, apply under `.doh-ttl-boost` to `.ant-progress-bg`, the counter `<b>`, and the clock for the `ttlExtendMs` window; render `boost ? 'Extending…' : 'Extend'` with the accent-fill style.
- [ ] **TTL-3 [MAJOR]** In-app design-system matrix silently dropped the TTL motion spec - `DesignSystem.tsx:252-255` documents only thresholds/slider/tooltips; no boost demo cell. Fix: restore the motion language + a boost demo once direction is set. (See X4.)
- [ ] **TTL-5 [MINOR]** Boost number shows absolute remaining, not the modelled "+delta" - `meters.tsx:332,388`, `format.ts:56`. See the boost-number decision; if matching artifact, render `'+' + fmtMinutes(boostTarget - baseline)` during boost.
- [ ] **TTL-6 [TASTE]** On a tone change the counter colour eases `.4s` but the bar `strokeColor` swaps instantly - `meters.tsx:386` vs `global.css:156`. Optional: add `.doh-ttl-bar:not(.doh-ttl-boost) .ant-progress-bg{transition:background-color .4s ease}`.

> [!NOTE]
> Reverting TTL-1/TTL-2 also reverts this turn's earlier edits: `test_ttl_extend.py::test_extend_has_no_glow_or_blur` must flip back to asserting the glow/blur, and the acc-crit + `docs/design-system/README.md` "no-glow" edits must be undone.

## GPU meter (DO NOT SHIP)

- [ ] **GPU-1 [BLOCKER]** Stripe algorithm is a computed hue-rotation, not the spec's fixed 10-hue identity palette - `gpuStripes.ts:80-100` rotates hue by `(index*360)/count` + WCAG lightness-solve; spec `dc:444,814-817` hardcodes 10 `[h,s,l]` triples indexed `i % 10`. Fix: replace with the 10-entry palette (`[197,95,32],[26,95,42],[140,80,32],[262,90,44],[212,10,47],[322,90,42],[95,85,38],[225,95,42],[45,95,40],[170,90,31]`), select by `index % 10`, drop the count/contrast machinery and the `accent`/`count` args at `meters.tsx:92`.
- [ ] **GPU-2 [BLOCKER]** Per-device stripe colour changes when device count changes - `(index*360)/count` makes "device 2" one colour at 2 GPUs, another at 4; spec's `i % 10` fixes a colour to an index forever. Fix: same as GPU-1.
- [ ] **GPU-3 [BLOCKER]** No `↻` cycle marker past 10 GPUs - spec `dc:444,422,822-824` appends `↻` when `i >= 10`; absent in `meters.tsx:87`. Fix: `const wrapped = i >= 10` → append `↻` (or recycle glyph) to wrapped labels.
- [ ] **GPU-4 [MAJOR]** Computed hues can emit orange/red stripes the spec forbids (read as "warning") - the formula sweeps the full wheel; a red-ish GPU stripe next to a danger-red CPU bar is an attention-without-alarm violation. Fix: the fixed palette (GPU-1) is pre-vetted to avoid alarm hues.
- [ ] **GPU-5 [MAJOR]** No per-device % readout - artifact row has a 34px right-aligned `{{ g.pct }}` (`dc:425`); shipped is tooltip-only (`meters.tsx:86-95`), untouchable on touch. Fix: add the per-device `%` column to `.doh-gpurow`, or get an explicit tooltip-only waiver. (Dedup with RES-2 / X5.)
- [ ] **GPU-6 [MAJOR]** Colour is the sole device identity - identical cards (4× "RTX 5090") give identical labels, only the hue differs; fails colour-vision-deficient users. Spec keeps the index in the label (`dc:824`). Fix: prefix index always, `${d.index} · ${shortGpuName(d.name)}`. (See X2.)
- [ ] **GPU-7 [MINOR]** Label width 112px vs spec 118px - `global.css:119` vs `dc:425`. (Dedup with RES-6.)
- [ ] **GPU-8 [MINOR]** Double truncation (4-word JS truncate AND ellipsis CSS) both fire - `meters.tsx:110-113` + `global.css:119`. Fix: pick one.
- [ ] **GPU-9 [MINOR]** Zero-utilisation device renders a 3px stub with no "0%"/idle cue - `meters.tsx:92,214`. Resolved once GPU-5 adds the % column.
- [ ] **GPU-10 [TASTE]** `Math.max(3, g)` overstates sub-3% load - acceptable once the % readout shows the truth.

## Spark / activity meter / metric card

- [ ] **ACT-1 [MAJOR]** Activity-meter tone boundary not pinned in the artifact - code cuts orange→green at lit=4 (`meters.tsx:33,46`); the artifact only ever shows 5/2/1-bar references (`dc:401-403`), never the 4-lit case. Fix: add 3-lit + 4-lit reference swatches to the artifact and confirm `lit<=3 orange, >=4 green` is intended; else change both code sites.
- [ ] **ACT-2 [MAJOR]** value=0 renders an empty grey meter indistinguishable from "no data" - `meters.tsx:32` (lit=0, no `on` bar); a real 0%-active server looks identical to a null one, and the `.low` pale-red tone has no lit bar to colour. Fix: light the first bar in `.low` pale-red at a real value=0 (reserve the dash for null), matching the artifact "12%" one-bar reference (`dc:403`).
- [ ] **ACT-3 [MAJOR]** Meter + spark are colour-and-hover-only - no `role`/`aria`/visually-hidden (`meters.tsx:30-41,61-69`). Fix: `role="img"` + `aria-label` reusing computed strings. (See X2.)
- [ ] **ACT-4 [MINOR]** Spark segments: contrast unverified + no inter-segment divider - `--color-accent` (new) sits beside `--color-success` (active) at 6px with no hairline; the `--color-border` offline filler is near-invisible on the track (`meters.tsx:65`, `global.css:106-107`). Fix: 1px track-coloured gap between segments; verify each segment ≥3:1 (WCAG 1.4.11); lift the offline filler toward `--color-border-strong`. (Contrast → X3.)
- [ ] **ACT-5 [MINOR]** Shipped Spark drops the artifact's rounded trailing pill cap - artifact rounds the last coloured segment + uses no grey filler (`dc:408-411`); shipped rounds the container and `DesignSystem.tsx:232` appends a grey filler, so the on-page reference doesn't match the artifact. Fix: match the artifact in the demo, or update the artifact to the track-filler convention.
- [ ] **ACT-6 [MINOR]** Breakdown legend colours don't fully reuse the spark segment colours - Servers `offline` / Users `inactive` segments are neutral tokens but their breakdown labels inherit `--color-text-muted` (`Home.tsx:223,229,244,251`), so swatch ≠ bar for the two states users scan most. Fix: colour those labels with the segment token, or document the neutral exception.
- [ ] **ACT-7 [TASTE]** `ActivityMeter` / `ActivityMeterFill` duplicate the lit/tone/render block verbatim (`meters.tsx:30-54`) - extract one helper so ACT-1/ACT-2 fixes don't drift.
- [ ] **ACT-8 [TASTE]** >100% activity is correct but surfaced only in the hover tooltip - a 130%-of-target user looks identical to 100% (five green bars). Optional over-target glyph.

## Server Control hero

- [ ] **HERO-1 [MAJOR]** Spawning pill pulse ignores prefers-reduced-motion - `global.css:77,82`; spec promises a steady halo (`dc:389`, `DesignSystem.tsx:221`). Fix: add `.doh-pill.spawning .doh-dot { animation: none }` to the reduced-motion block (also fixes the in-progress NotificationPill). (See X1.)
- [ ] **HERO-2 [MINOR]** `error` status falls through to the "stopped Xago / never started" readout under a red pill - `ServerHero.tsx:76-81`, `format.ts:45-49`; understates a failure and contradicts the pill. Fix: add an explicit `hero.status === 'error'` branch showing the failure line (`statusLabel`) + a retry hint.
- [ ] **HERO-3 [MINOR]** "Update available" pill renders left of the StatusPill, so the secondary advisory reads before the primary lifecycle truth - `ServerHero.tsx:40-43`, `MobileHome.tsx:37-40`. Fix: order StatusPill first in both surfaces.
- [ ] **HERO-4 [TASTE]** Stopped own-server shows "Manage Volumes" only to admins, leaving a non-admin owner a lone "Start Server" - `ServerHero.tsx:60-69`. Confirm intent with product; if hidden by design, add a one-line comment so it isn't re-flagged.

## Layout / cards / feed / conventions

- [ ] **LAY-1 [MAJOR]** Connection diode adds scaling the artifact forbids - shipped opacity+scale at 3s/1s vs artifact opacity-only at 3.6s/1.2s (`global.css:283-290` vs `dc:389,53-54`). DECISION item (operator tuned this; see top). If reverting: make keyframes opacity-only, fix periods, correct `DesignSystem.tsx:221` + the `global.css:255-258` comment.
- [ ] **LAY-2 [MAJOR]** Card headers render at two sizes in one grid - bare `<h3>` (Quick Actions `Home.tsx:136`; Your Groups / grants `Home.tsx:291,295`) default to ~18px beside 14px-pinned siblings (Host Status `:260`, CardHeadLink `:14`). Fix: pin `fontSize:14, fontWeight:600, margin:'0 0 12px'` on the three bare `<h3>`s, or route through a shared heading component.
- [ ] **LAY-3 [MAJOR]** Muted/subtle text fails WCAG AA - see X3 (`tokens.ts:64,103`; `global.css:47,195,202,224`).
- [ ] **LAY-4 [MAJOR]** "What your groups grant" rows signal type by colour/icon only - accent tile + `aria-hidden` icon, no pill, against the "type = coloured pill on the shared palette, never colour-only" rule (`dc:610-611`, `Home.tsx:296-305`). Fix: render the category as a `doh-pill`, or drop the tile to a neutral glyph.
- [ ] **LAY-5 [MINOR]** Hardcoded px paddings/radii bypass the SPACE/RADIUS scale - `PendingCallout` `borderRadius:10`/`padding '12px 16px'`/`gap:12` (`Home.tsx:43`), tags `borderRadius:4` (`Home.tsx:32`, `MobileHome.tsx:18`), `MetricCard` `padding:16`/`font-size:30px` (`MetricCard.tsx:28`, `global.css:171`). Fix: replace literals with `var(--space-*)` / `var(--radius-*)`.
- [ ] **LAY-6 [MINOR]** RecentEvents zeroes card body padding then re-pads inline (`Home.tsx:155-159`) - one-off padding model vs the standard-body-padding convention. Fix: drive inner pads from `var(--space-*)`, or use the default body padding.
- [ ] **LAY-7 [MINOR]** Feed text via `dangerouslySetInnerHTML` with no client guard / no accessible label - `Home.tsx:166`; backend escapes today (no live XSS) but zero defense-in-depth, and long strings truncate with no hover/SR fallback. Fix: render the known-safe shape client-side from structured fields, or sanitize + add `title`.
- [ ] **LAY-8 [MINOR]** Mobile "Active Servers" widget drops zebra - `MobileHome.tsx:78-92` plain flex rows vs the mandatory-zebra convention (`dc:601`). Fix: alt-row background on even mobile rows, or scope the convention to "tables only".
- [ ] **LAY-9 [MINOR]** PageHeader silently discards the documented "at a glance" sub-line - `PageHeader` returns null with no actions, so `sub=` is dead on `Home.tsx:210,287`. Fix: drop the dead `title`/`sub` props, or render the sub-line.
- [ ] **LAY-10 [TASTE]** PendingCallout (accent-2 fill + Review pill) can out-shout the hero - `Home.tsx:38-55`. Optional: soften to the `doh-notice` left-edge treatment, or co-locate under the Users metric.

## Execution order (suggested)

1. Resolve the three decisions (TTL motion, connection diode, boost number).
2. GPU meter BLOCKERs GPU-1..GPU-3 (the only DO-NOT-SHIP).
3. Cross-cutting X1-X4 (reduced-motion, a11y roles, contrast, in-app drift) - each clears several findings at once.
4. TTL-1/TTL-2 if "restore" is chosen.
5. Remaining MAJORs, then MINORs, then TASTE.
