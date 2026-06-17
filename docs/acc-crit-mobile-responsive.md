# Acceptance Criteria - Mobile Responsive Portal

Below a mobile breakpoint the Optimum Hub portal switches to a JupyterHub-style minimal home: status plus the few controls that make sense on a phone. The lab itself (JupyterLab) is not mobile-friendly, so the portal never navigates into the user server on mobile.

- [x] **Breakpoint** - below a mobile width (target < 768px) the portal renders the mobile layout; the desktop layout is unchanged at/above it
  - log: 2026-06-17 implemented + code-verified (useIsMobile `(max-width: 767px)`; Home returns MobileHome when mobile, else desktop unchanged)
- [x] **Mobile home content** - shows server status (pill + time-left) and exactly these controls: Start (launch), Stop, Extend TTL
  - log: 2026-06-17 implemented (MobileHome.MyServerCard: StatusPill + Start|Stop + TtlGadget time-left/Extend)
- [x] **No lab navigation on mobile** - no Open-lab / Enter-session affordance anywhere on mobile; the portal never links into the user server UI
  - log: 2026-06-17 verified by code (MobileHome does not import userServerUrl; no Open-lab control)
- [x] **Allowed mobile actions (closed set)** - launch server, stop server, extend session TTL; nothing else for a regular user
  - log: 2026-06-17 verified (regular user sees only MyServerCard = Start/Stop/Extend)
- [x] **No Restart on mobile** - restart is a desktop action; mobile exposes only Start/Stop/Extend
  - log: 2026-06-17 confirmed by user ("no other mobile actions"); no Restart button in MobileHome
- [x] **Admin extras** - admin additionally sees the servers widget below the home card, plus a link to the Servers screen and a link to the Users screen
  - log: 2026-06-17 implemented (MobileServersWidget + Servers/Users Links, gated on role==='admin')
- [x] **No other admin mobile actions** - beyond the two links and the widget, no admin actions on mobile (no groups / tokens / settings / notifications inline)
  - log: 2026-06-17 verified (MobileHome renders only the widget + two links for admin)
- [x] **Servers/Users via link** - the Servers and Users screens are reached as links (navigation), not embedded inline on the mobile home
  - log: 2026-06-17 verified (react-router Link to /servers + /users; widget is read-only, not the inline screens)
- [x] **Edge: resize / rotate across breakpoint** - layout swaps without losing query state (shared TanStack cache)
  - log: 2026-06-17 verified by code (useIsMobile subscribes to matchMedia change -> live swap; single QueryClient so cache is shared across layouts)
- [ ] **Edge: deep link to a desktop-only route on mobile** - degrade gracefully (redirect to mobile home or show a brief "desktop only" note), never a broken screen
  - log: 2026-06-17 NOT handled - desktop routes (Servers/Users/etc.) still render their ProTable on mobile (horizontally scrollable, not broken, but no deliberate degrade); follow-up
- [x] **Edge: TTL/extend on mobile** - the extend control works on mobile (touch-friendly hours input); the bar follows the same base-relative behaviour as desktop
  - log: 2026-06-17 verified (TtlGadget reused: InputNumber hours popover + base-relative pct, identical to desktop)
- [x] **Look good on a phone (runtime)** - visual polish, spacing, touch targets confirmed on an actual narrow viewport
  - log: 2026-06-17 VISUALLY CONFIRMED via Playwright headless render at 390px (mock build): clean single column, big Start button, Offline status pill, read-only Active-servers list, full-width Servers/Users links, JupyterHub-5 chip - looks good. Screenshot reviewed.

## Open questions

- Which actions, if any, are allowed on the admin Servers screen on mobile (view-only vs the same Start/Stop/Extend per row)? - widget is read-only; the Servers screen itself is reached via link and renders its desktop table for now
- Should Restart be available on mobile for one's own running server, or is Stop+Start the only path? - RESOLVED: no Restart on mobile (user: "no other mobile actions")
