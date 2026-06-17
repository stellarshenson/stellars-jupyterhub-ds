# Acceptance Criteria - design language (system-wide)

The portal's visual conventions, applied consistently across every screen. `[x]` = implemented + verified (code/build/render); `[ ]` = pending. Reference page: `/design-language`.

## Tables / lists

- [x] **Zebra rows** - every antd Table / ProTable / DragSortTable gets alternating row backgrounds, globally (no per-table wiring)
  - log: 2026-06-17 verified (global.css nth-child(even) + .oh-row-alt; all tables audited)
- [x] **Row hover = accent tint** - hovering any row subtly tints its background with the accent colour (overrides zebra + antd's grey hover), system-wide
  - log: 2026-06-17 implemented (global.css `.ant-table-tbody > tr:hover` accent 8%); build green
- [ ] **Two-line cells (sub-names)** - list rows show a primary name + a muted sub (username + first/last name) - NEEDS first/last in the list payload (task #186)
  - log: 2026-06-17 captured, next pass
- [ ] **Consistent row heights** - all list rows are the same height (the two-line shape unifies them) - task #186
  - log: 2026-06-17 captured, next pass (rows currently vary 51/69px)
- [ ] **Consistent margins** - uniform spacing/margins across screens - task #186
  - log: 2026-06-17 captured, next pass

## Icons

- [x] **Wireframe default, filled on demand** - icons render as line/wireframe by default; `filled` is opt-in
  - log: 2026-06-17 verified (Icon.tsx filled=false default -> stroke)
- [x] **Tones** - primary (blue, active/go-to), secondary (gray, neutral), dangerous (red, destructive), warning (yellow, caution)
  - log: 2026-06-17 verified (IconAction tone prop; demoed on /design-language)
- [x] **List icons wireframe; non-list filled** - list/table action icons stay wireframe (fill only for emphasis e.g. stop); non-list/button icons use the filled glyph when one is available
  - log: 2026-06-17 documented + demoed (design-language: non-list filled row + list wireframe row + note)

## Text colours

- [x] **Normal-text taxonomy** - five text colours, all from the defined palette vars: neutral (`--color-text`, body), link (`--color-accent`, e.g. a user-profile link), success (`--color-success`, green), warning (`--color-warning`, orange), dangerous (`--color-danger`, red); one utility class each (`.oh-text-*`)
  - log: 2026-06-17 added `.oh-text-neutral/link/success/warning/danger` (global.css) + demoed on /design-language ("Normal text" card); first consumer = the volume-reset "removed" red text; operator "add to design language normal text"
- [x] **Named palette (dim / normal / intense)** - a named colour palette borrowed from the tokens - green (success), cyan/blue (accent), red (danger), orange (warning), gray (text-subtle) - each as `--oh-<name>` with `-dim` (mixed toward surface) and `-intense` (mixed toward text) variants, referable by name; demoed as labelled squares on /design-language ("Palette" card). Magenta is not in the current tokens
  - log: 2026-06-18 added `:root --oh-*` (global.css) via `color-mix` on the source vars; operator "design palette of colours ... dim, normal, intense ... refer to them by name ... borrow from already defined"
- [x] **Activity meter red is pale** - the activity meter's low (red) segments use `--oh-red-dim` so the solid blocks read as soft as the thin danger / stop-button glyph (both still derive from `--color-danger`)
  - log: 2026-06-18 `.oh-meter.low i.on` -> `--oh-red-dim`; operator "activity red - make it the same pale colour as the stop button"

## Headers / chrome

- [x] **No page title headers** - the big page title + sub-line are removed (the breadcrumb names the page); only the optional right-aligned actions remain
  - log: 2026-06-17 implemented (PageHeader renders only actions; ~50px reclaimed on every page)
- [x] **Named edits are explicit** - editing a user profile / group is reached via an explicit named link (the username / group-name), never a whole-row click; row-click is reserved for read-only detail (Servers drawer)
  - log: 2026-06-17 verified (Users/Groups name-links to config; Servers row-click = report drawer)

## Navigation (system-wide)

- [x] **Sub-screen footer** - every screen reached from a list (Configure user, Configure group, Manage volumes) carries the standard footer: destructive action left, Cancel + a primary Save/Done/Ok right (`FormFooter`); never a dead-end with no way back
  - log: 2026-06-17 implemented - Manage volumes joined the pattern (Reset left, Cancel + Done right); UserConfig/GroupConfig already had it; cross-ref [acc-crit-volume-reset]
- [x] **Respect the navigation path / breadcrumbs** - a screen reachable from more than one parent records its origin in the nav state; the breadcrumb parent AND the Cancel/Done (close) target both reflect where the user actually came from, not a hardcoded route parent
  - log: 2026-06-17 implemented - nav `state.from` overrides the static breadcrumb parent (`Breadcrumbs.tsx`); Manage volumes from Home returns to Home, from Servers returns to Servers (was always /servers)
- [x] **Widget actions == list actions** - the Home "Active servers" widget renders the IDENTICAL row actions as the Servers list via the shared `rowActions` (start own -> Start page; start other -> inline spinner; enter/restart/stop; manage volumes), never a divergent widget-only set
  - log: 2026-06-17 implemented - extracted `components/ServerRowActions.tsx`, reused by Servers + the Home widget; cross-ref [acc-crit-server-lifecycle-ux]

## Values / feedback

- [x] **Tooltips, not static text** - precise values (exact GB / % / dates / breakdowns) live in a hover tooltip, never as wasteful static text under the control
  - log: 2026-06-17 documented (design-language note); cells use title tooltips for breakdowns
- [x] **Progress bars** - the standard bar is base-relative and drains blue -> amber -> red toward the cull; the GPU striped bars are the alternative (one labelled bar per device) for multi-device load
  - log: 2026-06-17 verified (TtlGadget + ResourceBars + GpuMeter; documented on /design-language)
- [x] **GPU device labels = mini names** - per-GPU bars label each device with its mini name (vendor/brand boilerplate stripped: "NVIDIA GeForce RTX 5090" -> "5090") instead of the bare index; full index + name stay in the hover tooltip
  - log: 2026-06-17 implemented (shortGpuName strips NVIDIA/GeForce/RTX/Generation; GpuMeter label uses it); typecheck clean, live render pending deploy

## Mobile

- [x] **Minimal home, desktop-parity actions** - below 768px the home is the server card (same actions as desktop) + admin servers widget + a Servers link (no Users); no sider panel, no collapse handle, no header hamburger
  - log: 2026-06-17 verified by headless render (no panel/handle/hamburger; full action set)
- [x] **Mobile Servers view** - the Servers screen on mobile is a card list mirroring the old JupyterHub admin info (user + admin, status, last activity, actions)
  - log: 2026-06-17 implemented (MobileServerList); runtime render pending the next deploy

## Visual cues to digest from the 2026-06-17 servers/resource batch (#252)

These conventions must be shown on `/design-language` as VISUAL CUES (live example elements), not "this -> that" before/after pairs.

- [ ] **Resource tooltip carries the live % + the assigned reference** - every CPU/memory bar tooltip quotes the usage % alongside the assigned ceiling (cores / GB assigned vs host)
  - log: 2026-06-17 criterion added (#245/#246/#252); cross-ref [acc-crit-resource-bars]
- [ ] **Activity % may exceed 100%** - the activity tooltip shows the real uncapped % (>100% = works more than the daily target), multiline
  - log: 2026-06-17 criterion added (#247/#252); cross-ref [acc-crit-activity-scoring]
- [ ] **List vs widget: status/last-activity separate in lists** - in lists, Status and Last activity are separate columns (the widget may club them); column order Status, Last activity, Activity; meters centered in their column
  - log: 2026-06-17 criterion added (#248/#252); cross-ref [acc-crit-servers-list-layout]
- [ ] **Names are links + carry first/last** - a user name in any list links to the user and shows the first/last name (no artificial click-friction)
  - log: 2026-06-17 criterion added (#249/#252)
- [x] **Admin lifecycle = inline spinner, not navigation** - starting/restarting another user's server spins the control in place; it does not route to a progress screen
  - log: 2026-06-17 criterion added (#243/#252); 2026-06-17 verified via shared `rowActions` (Servers list + Home widget) - own start -> Start page, other start -> inline `lf.start` spinner; cross-ref [acc-crit-server-lifecycle-ux]
- [ ] **Columns sized to content** - status / last-activity columns are just wide enough, not stretched
  - log: 2026-06-17 criterion added (#250/#252)
