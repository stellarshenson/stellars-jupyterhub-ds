# Acceptance Criteria - Mobile Scope & GPU Card Name

The mobile view is a status-and-control panel for the account owner (or admin) checking in from a phone, not an entry point to the workspace - nobody does data science on a phone. It must show the status gauges and a few own-server switches and nothing that ushers the user toward work they will not do here; the extended hero header is desktop ceremony and is removed on mobile. Admins see other people's servers read-only. Separately, the host-status GPU card name is truncated to the first N words. Mobile detection: `lib/useIsMobile.ts` (`max-width: 767px`). Reference: `pages/MobileHome.tsx`, `pages/Servers.tsx` (`MobileServerList`), `components/meters.tsx` (`shortGpuName`), `services/config.ts`. Verified by `tests/functional/test_mobile_scope.py` (signup regime, 92 passed / 0 failed, 148 acc-crit met).

## Mobile header

- [x] **Minimal chrome** - the mobile header shows the branding logo, the theme switcher, the connection pill, and the stage badge; the language switcher is dropped on mobile to make room for the full-text pill; nothing else
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `AppLayout` topbar renders the logo (left) + language + theme + `StageBadge` on mobile; verified `test_mobile_header_minimal`
  - log: 2026-07-03 operator "the mobile header must carry the connection indicator, normal height + full text; you can hide the language switcher" - added `ConnectionStatusPill` on mobile (full text), gated `LanguageControl` `!isMobile`; `test_mobile_header_minimal` realigned (Language absent, pill present "Connected"); verified tsc/eslint/vitest/build, functional re-verify pending rebuild
  - log: 2026-07-03 (ux) adversarial-review fix - logo restored 22 -> 24px (level with the chips again), shrinking via flex only when a narrow viewport actually demands it
- [x] **No extra header text** - no greeting, no identity text, no breadcrumbs, no extended hero block - every line of header text costs vertical space that belongs to the status and switches
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - breadcrumbs replaced by the logo on mobile, `ConnectionStatusPill` gated `!isMobile`; verified `test_mobile_header_minimal`
  - log: 2026-07-03 the "no connection pill" clause REMOVED - operator now wants the connection pill on mobile (see the Connection pill criterion below); breadcrumbs / greeting / hero stay excluded
- [x] **Connection pill (mobile)** - the connection pill renders on mobile at full text and normal height (level with the stage badge): a calm "Connected" while the hub answers, a warning "Not responding" when it stops; only the ticking elapsed suffix (`.doh-conn-elapsed`) is hidden on mobile so the full-text pill fits the phone header - the in-flow `HubConnectionIndicator` panel still carries the full down-state detail with elapsed below
  - log: 2026-07-03 criterion added (operator: "you have made the connected indicator tiny, not even the same height as stage indicator; make it normal height and full text; you can hide the language switcher"); `ConnectionStatusPill` no longer gated `!isMobile`, elapsed span wrapped `.doh-conn-elapsed` and hidden under 768px, `LanguageControl` dropped on mobile; verified tsc/eslint/vitest/build; `test_mobile_header_minimal` asserts the pill present with "Connected"; functional re-verify pending rebuild
  - log: 2026-07-03 (ux) adversarial-review fixes - pill `aria-hidden` on mobile (the in-flow panel is the sole live region there, no double screen-reader announcement); mobile header overflow-guarded (`.doh-header-actions` flex-shrink:0, logo Link flex-shrinks + img `max-width:100%`, `.doh-stage-badge` capped + ellipsis) so the full-text pill plus a long custom stage label can never push the header past the viewport
- [x] **Stage badge kept** - when `JUPYTERHUB_BRANDING_STAGE` is set, the stage badge stays in the mobile header - it is a critical env cue next to the mobile Stop/Restart controls (prevents "stopped PRD thinking it was STG"); unset = renders nothing
  - log: 2026-06-23 criterion added (operator: env cue is critical, keep it in the header)
  - log: 2026-06-24 done - `StageBadge` ungated (shown on mobile too); `StageBadge` self-hides when stage unset

## Mobile own-server panel

- [x] **Status** - the panel shows whether the user's own server is online or offline
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `MyServerCard` `StatusPill` (pre-existing, retained)
- [x] **TTL bar** - the TTL progress bar is shown for a running server (the same gadget as desktop)
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `TtlGadget` progress bar (pre-existing, retained)
- [x] **Uptime** - an uptime counter is shown for a running server
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `TtlGadget` `uptimeLabel` ("up X"), fed `hero.startedISO`
- [x] **Time-left** - a time-left counter (until idle-cull) is shown for a running server
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `TtlGadget` counter (`fmtMinutes`) + clock icon
- [x] **Extend TTL** - the user can extend the TTL from the panel
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `TtlGadget` extend popover -> `extendSession`
- [x] **Controls** - start, stop, restart, and reset-volumes are available for the user's own server, gated by status the same way as desktop (start when offline, stop/restart when running, reset-volumes when offline)
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `MyServerCard` Restart/Stop (running) or Start / Manage-Volumes (offline)
- [x] **No Open-Lab** - the panel does NOT offer Open-Lab or any navigation into the lab session, even for a serving server; there is nowhere useful to go on a phone
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - Open-Lab button removed from `MyServerCard` + orphaned `userServerUrl` import dropped; verified `test_mobile_home_has_no_open_lab`
- [x] **Edge: offline server** - TTL bar, uptime, and time-left are absent (or show an offline state) when the server is offline; only Start (and reset-volumes) are offered
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `TtlGadget` block is gated on `running`; offline shows Start / Manage-Volumes only

## Mobile permissions

- [x] **Own-server control only** - on mobile, start/stop/restart/reset act only on the requesting user's own server
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - only `MyServerCard` (bound to `hero.user`) has controls; verified `test_mobile_servers_readonly_with_telemetry` + adversarial review (permission closure)
- [x] **Others read-only** - other users' servers are shown read-only (status + telemetry); no start/stop/restart/reset/enter control on another user's server from mobile, even for an admin
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `MobileServerList` row actions removed, drawer `extra` + Start-All/Stop-All gated `!isMobile`; verified `test_mobile_servers_readonly_with_telemetry`
- [x] **Admin fleet visibility** - an admin on mobile can see how many people are working and each server's status read-only
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `MobileServersWidget` (Home) + `MobileServerList` (Servers) read-only lists, retained
- [x] **Edge: admin's own server** - an admin acting on their OWN server from mobile keeps the full own-server control set (the read-only rule is about OTHERS, not self)
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `MyServerCard` controls the admin's own server on the Home card
- [x] **Edge: non-admin user** - a non-admin sees only their own server panel; no fleet list
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `MobileHome` gates the fleet widget + Servers link on `role === 'admin'`

## Per-server status telemetry

- [x] **CPU** - each server's read-only CPU usage is shown in the mobile per-server status
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `MobileServerList` card CPU readout (quota-coloured); verified `test_mobile_servers_readonly_with_telemetry`
- [x] **Memory** - each server's read-only memory usage is shown
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `MobileServerList` card Mem readout (quota-coloured); verified test
- [x] **Activity** - each server's read-only activity level is shown
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `MobileServerList` card `ActivityMeter`; verified test
- [x] **Compact** - the three readouts are compact (the mobile constraint), read-only, and sourced from the existing `ServerRow` fields (no backend change)
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - single flex row on the card, fields from `ServerRow` (cpu/mem/activity)
- [x] **Edge: metric unavailable** - a null cpu/mem/activity renders an empty/`-` state, not a crash or a zero that reads as real
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - CPU/Mem render `dash` when null; `ActivityMeter` returns a dash for null value

## GPU card name

- [x] **Full name, first N words** - the host-status GPU card name shows the full device name starting "NVIDIA", truncated to the first N words (e.g. "NVIDIA GeForce RTX 4090 Laptop GPU" -> "NVIDIA GeForce RTX 4090" at N=4)
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `shortGpuName` rewritten to first-N-words (was strip-boilerplate); applies to the host-status GPU rows + inventory chips
- [x] **Config constant** - N is a fixed visual constant in `services/config.ts` (default 4), not a per-user preference
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `GPU_NAME_MAX_WORDS = 4` in `config.ts`, default arg of `shortGpuName`
- [x] **Edge: name shorter than N** - a name with fewer than N words renders in full, no trailing separator or ellipsis artifact
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `split/slice(0,N).join(' ')` yields the whole name when words < N
- [x] **Edge: empty/missing name** - a missing GPU name falls back to the existing placeholder (e.g. `GPU {i}`), not an empty string
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - row label keeps `d ? shortGpuName(d.name) : \`GPU ${i}\``; `shortGpuName('')` returns `''` only when there is a name

## Verification

- [x] **tsc + build** - `tsc -b` and `npm run build:hub` clean
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - typecheck + `build:hub` exit 0; `make rebuild` baked image `b5640782e1fd` (smoke test ok)
- [x] **Functional** - functional suite green; mobile-scope behaviours covered by a Playwright test (viewport at mobile breakpoint)
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - `test_mobile_scope.py` (mobile viewport) added; signup regime 92 passed / 0 failed, 148 acc-crit met
- [x] **Adversarial review** - ux-designer + bug-hunt review of the mobile-scope diff, fixed and re-confirmed clean
  - log: 2026-06-23 criterion added
  - log: 2026-06-24 done - ux-designer + bug-hunt (Mode 1) -> fixed drawer width + logo tap target; re-confirm round SHIP (permission closure verified)
