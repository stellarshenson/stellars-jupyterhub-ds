# Optimum Hub - frontend mock

A static HTML/CSS prototype of a redesigned JupyterHub admin portal. Design exploration only - **not wired to the hub, not part of the runtime, no build step**. Open `home.html` in a browser.

## What it is

- A clickable mock of the management portal: Home dashboard (high fidelity) plus Servers, Users, Groups, Policies, Activity and Settings as navigable list-table pages
- Visual metaphor: a calm control room - one rail to move (sidebar), one stage to work (content); simple yet functional
- Theme: JupyterLab **Stellars Sublime** surfaces + **Stellars-Tech** accents (cyan `#0096d1`, orange `#da8230`), in two variants - `optimum-hub-dark` and `optimum-hub-light`
- Borrows from RustFS/MinIO (grouped sidebar, list-table + top-right Add, monochrome surfaces + one bold accent) and best-in-class portals (Cmd-K palette, status pills, drawer edit, inline approve)
- Real Stellars Tech AI Lab branding: the hub logo (`assets/brand/jh-logo.svg`) sits in the sidebar, the favicon (`assets/brand/favicon.ico`) on every page (copied from `../branding`)

## Try it

- Open `mock/home.html`
- Toggle theme with the sun/moon button (top-right); choice persists in `localStorage`
- Press `Cmd/Ctrl+K` for the command palette - navigate, create, run actions
- Buttons fire mock toasts; nothing calls a real API

## Layout

```
mock/
  index.html        redirect to home
  home.html         Overview dashboard (full)
  servers.html      running labs - single pane of glass
  users.html        people, authorisation, membership
  groups.html       priority groups -> policy
  policies.html     the nine policy types
  activity.html     live resource usage
  settings.html     platform config hub
  assets/
    tokens.css      the two themes as CSS custom properties (swap a handful to retheme)
    app.css         shell + components
    app.js          shared shell render + theme toggle + Cmd-K palette
```

## Theming

`tokens.css` is variable-driven: a semantic layer (`--color-bg`, `--color-surface`, `--color-text`, `--color-accent`, status colours, spacing/radius/type scales) defined dark-first in `:root` / `[data-theme="optimum-hub-dark"]`, with `[data-theme="optimum-hub-light"]` overriding the colour vars only. Components reference semantic vars exclusively, so retheming is a handful of edits. An inline `<head>` script applies the saved theme before paint (no flash).

## Status

Mock for design review. The real rebuild concept and the hub-as-trust-boundary security model live in `../docs/portal-ui-catalogue.md`; the design research behind this mock is in `../docs/design-research-frontend-mock.md`.
