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

## Headers / chrome

- [x] **No page title headers** - the big page title + sub-line are removed (the breadcrumb names the page); only the optional right-aligned actions remain
  - log: 2026-06-17 implemented (PageHeader renders only actions; ~50px reclaimed on every page)
- [x] **Named edits are explicit** - editing a user profile / group is reached via an explicit named link (the username / group-name), never a whole-row click; row-click is reserved for read-only detail (Servers drawer)
  - log: 2026-06-17 verified (Users/Groups name-links to config; Servers row-click = report drawer)

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
