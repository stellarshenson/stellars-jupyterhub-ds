# Optimum Hub - frontend mock

A static HTML/CSS prototype of a redesigned JupyterHub portal. Design exploration only - **not wired to the hub, not part of the runtime, no build step**. Open `home.html` (admin) or `home-user.html` (plain user).

## The idea

Navigate to nouns, not views. One entity lives in exactly one place. Split the chrome into what you *watch* (Operate) and what you *administer* (Administration), and gate the second by role. Every dashboard widget is a mini-view that drills into its dedicated page. Show only what drives a decision.

## Navigation

```
OPERATE
  Overview     dashboard - counts + what needs attention now
  Servers      every lab: lifecycle + engagement + resources + time-left

ADMINISTRATION  (admin only)
  Users        people, authorisation, membership
  Groups       priority groups; each group's policies edited in its drawer
  Settings     platform config
```

- **Servers absorbs the old Activity page** - a running lab *is* its activity, so engagement and resource usage are columns, not a second page
- **Groups absorbs the old Policies page** - a policy is an attribute of a group, not a destination; the nine types are edited inside the group
- **Events** is the audit log behind the Overview feed - a dedicated page reached by clicking the widget (and via Cmd-K), not a permanent rail item
- **Broadcast** is a topbar action (megaphone), not a page

## Roles

The portal is role-aware (`<body data-role="user">`):

- **Admin** (`home.html`) - fleet dashboard, both nav sections, broadcast, all pages
- **User** (`home-user.html`) - one launchpad: their server (open/restart/stop), what their groups grant (read-only), their storage. No Administration section, no fleet pages

## Servers - the merged operational surface

- **Status** = lifecycle: Running / Spawning / Stopped / Failed
- **Activity** = engagement: Active / Idle 38m / - (the reclaim signal; a distinct axis from status)
- **Time left** = cull countdown (actionable); uptime dropped (vanity)
- **Image dropped** - uniform across the platform, drives no decision

## Users - pending-on-top

- **Pending authorisation** is a separate list at the top, shown only when something waits, each row carrying Authorize / Discard
- Below, authorised users carry an **Authorised switch** - off means a deliberate admin de-authorisation (the admin's lever), distinct from never-approved pending signups
- **Configure user** is a tabbed detail borrowed from the RustFS/MinIO console: Identity, Groups (membership is the only lever - it grants policy), Access (effective policy, read-only + view-as), Keys (API-key pool slot), Storage (volumes). In the real app it opens as a right-side drawer

## Theme

Two variants, `optimum-hub-dark` and `optimum-hub-light`: JupyterLab **Stellars Sublime** surfaces + **Stellars-Tech** accents (cyan `#0096d1`, orange `#da8230`). `tokens.css` is variable-driven - a semantic layer (`--color-bg`, `--color-surface`, `--color-text`, `--color-accent`, status colours, spacing/radius/type scales) defined dark-first, with the light variant overriding colour vars only. Components reference semantic vars exclusively, so retheming is a handful of edits. An inline `<head>` script applies the saved theme before paint (no flash).

## Try it

- Toggle theme with the sun/moon button (top-right); choice persists in `localStorage`
- Press `Cmd/Ctrl+K` for the command palette - navigate, create, run actions (scoped to role)
- Buttons fire mock toasts; nothing calls a real API

## Layout

```
mock/
  index.html        redirect to home
  home.html         admin Overview (fleet dashboard, full)
  home-user.html    plain-user Overview (personal launchpad)
  servers.html      every lab - lifecycle + activity + resources
  users.html        pending-on-top + RustFS-style user config
  groups.html       priority groups + the nine policy types
  events.html       audit log (behind the Overview feed)
  settings.html     platform config
  assets/
    tokens.css      the two themes as CSS custom properties
    app.css         shell + components
    app.js          role-aware shell render + theme + Cmd-K + tabs
    brand/          logo + favicon (from ../branding)
```

## Status

Mock for design review. The rebuild concept and the hub-as-trust-boundary security model live in `../docs/portal-ui-catalogue.md`; the design research behind this mock is in `../docs/design-research-frontend-mock.md`.
