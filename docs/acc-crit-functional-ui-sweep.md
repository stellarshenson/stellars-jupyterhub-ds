# Acceptance Criteria - Functional UI Sweep

Completeness gates for `docs/portal-ui-catalogue.md`, the hub-portal inventory feeding a future rebuild. These criteria do not test the running portal; they assert the catalogue itself is complete and at the right fidelity - every hub screen mapped to its actions, capabilities, conditionals, messages, navigation, dynamic behaviour and API, with no JupyterLab UI and no CSS/DOM detail.

## Scope gates

- [x] **Hub only** - catalogue covers hub-served screens; no JupyterLab in-session UI
  - log: 2026-06-14 added, satisfied (catalogue Coverage map lists hub screens, lab out of scope)
- [x] **Functional fidelity** - entries describe routes, actions, endpoints, states; no CSS selectors, class names or DOM structure
  - log: 2026-06-14 added, satisfied (CSS/DOM-level agent output stripped during synthesis)
- [x] **Single source** - one master doc, one section per screen plus a shared global-layer section
  - log: 2026-06-14 added, satisfied
- [x] **Provenance** - catalogue names the source files (templates, handlers, config) it was built from
  - log: 2026-06-14 added, satisfied

## Per-screen completeness

Every screen section must carry, where applicable: route, purpose, actions (+ target endpoint), inputs/validation, conditionals (role/state gating), messages, navigation, modals, dynamic behaviour, API. A label is omitted only when genuinely N/A.

- [x] **Route present** - each screen states its URL path(s)
  - log: 2026-06-14 added, satisfied
- [x] **Actions enumerated** - every button/link/form submit listed with what it does and the endpoint it hits
  - log: 2026-06-14 added, satisfied
- [x] **Inputs + validation** - form fields, limits and validation rules captured (char limits, name regex, reserved/protected rejections)
  - log: 2026-06-14 added, satisfied
- [x] **Conditionals** - role gating (admin vs user vs anon) and state gating (server running/stopped/pending, bootstrap window) captured per screen
  - log: 2026-06-14 added, satisfied
- [x] **Messages** - error/success/info text and the trigger condition captured
  - log: 2026-06-14 added, satisfied
- [x] **Navigation** - outbound links per screen captured
  - log: 2026-06-14 added, satisfied
- [x] **Modals** - confirmation/config dialogs and what they guard captured
  - log: 2026-06-14 added, satisfied
- [x] **Dynamic behaviour** - JS-driven polling, timers, redirects, auto-close, spinners, live counters captured
  - log: 2026-06-14 added, satisfied
- [x] **API** - method, path, payload shape and error codes captured for screens that call endpoints
  - log: 2026-06-14 added, satisfied

## Screen inventory (every hub screen accounted for)

- [x] **Auth + landing** - login, native-login, signup, logout, change-password, change-password-admin, authorization-area, oauth, accept-share, error, 404, message, token
  - log: 2026-06-14 added, satisfied
- [x] **Spawn + home + self-service** - home, named-servers, manage-volumes, restart, extend-session, spawn, spawn_pending, stop_pending, not_running
  - log: 2026-06-14 added, satisfied
- [x] **Groups + policy** - groups page with layout regions, actions, all nine policy types, badges, tooltip, validation, persistence, API
  - log: 2026-06-14 added, satisfied
- [x] **Admin platform** - admin, settings, activity, notifications
  - log: 2026-06-14 added, satisfied
- [x] **Global layer** - page.html base, navigation map, branding, dark mode, mobile.js, session-timer.js, shared messaging
  - log: 2026-06-14 added, satisfied

## Capability depth gates

- [x] **Branding fully mapped** - every branding env var (logo, favicon, favicon-busy, lab main/splash icons, base url), file:// vs URL handling, and the favicon CHP proxy mechanism captured
  - log: 2026-06-14 added, satisfied
- [x] **Navigation role matrix** - which nav items each role sees (anonymous/user/admin) captured, not just the link list
  - log: 2026-06-14 added, satisfied
- [x] **Policy types complete** - all nine (env, gpu, docker, cpu, mem, sudo, downloads, api-keys, volume-mounts), each with config inputs, badge, tooltip detail, cross-group resolve rule and apply effect
  - log: 2026-06-14 added, satisfied
- [x] **Badge/tooltip provenance** - documented as server-computed `policy_summary` consumed verbatim by the client, not recomputed in the browser
  - log: 2026-06-14 added, satisfied
- [x] **Self-service flows** - manage-volumes, restart, extend-session each carry their poll loops, timeouts and reload behaviour
  - log: 2026-06-14 added, satisfied
- [x] **Spawn lifecycle** - spawn -> spawn_pending (EventSource + lab-ready fallback) -> not_running/stop_pending state machine captured
  - log: 2026-06-14 added, satisfied
- [x] **Bootstrap window** - first-admin signup-window behaviour and its gating env vars captured on the signup screen
  - log: 2026-06-14 added, satisfied

## Edge cases

- [x] **Edge: empty states** - no-groups, no-volumes-yet, no-active-servers, no-tokens captured as distinct UI states
  - log: 2026-06-14 added, satisfied
- [x] **Edge: failure paths** - spawn-failed (Relaunch), broadcast partial-failure, validation 400/409, restart timeout captured
  - log: 2026-06-14 added, satisfied
- [x] **Edge: external state drift** - home drift detector reloading on externally-stopped server, spawn-pending fallback poll on mid-spawn hub restart captured
  - log: 2026-06-14 added, satisfied
- [x] **Edge: admin-acting-for-user** - admin spawning/managing another user's server and volumes captured
  - log: 2026-06-14 added, satisfied
- [x] **Edge: mobile vs desktop divergence** - device-specific controls (mobile start/stop interception, status strip, card views, inline extend panel) captured where behaviour differs
  - log: 2026-06-14 added, satisfied
- [x] **Edge: one-time secrets** - token "you won't see it again" card and api-keys masked-on-read noted as non-recoverable display states
  - log: 2026-06-14 added, satisfied

## Sign-off

- [x] **No orphan screens** - every template in `html_templates_enhanced/*.html` maps to a catalogue section or is explicitly out of scope
  - log: 2026-06-14 added, satisfied (24 templates + 2 static JS accounted for in Coverage map)
- [x] **No orphan handlers** - custom page/API handlers referenced by a catalogued screen appear in that screen's API list
  - log: 2026-06-14 added, satisfied
- [ ] **Rebuild-ready** - a developer can rebuild any single screen from its section without reading the source
  - log: 2026-06-14 criterion added, pending owner review
