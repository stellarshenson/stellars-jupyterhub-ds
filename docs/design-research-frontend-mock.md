# Design Research - Frontend Mock

Research grounding the new JupyterHub admin-portal mock. Synthesised from a four-stream sweep of good admin-console systems: the RustFS/MinIO console (the operator's visual reference), best-in-class dashboards (Linear, Vercel, Supabase, Clerk, Tailscale, Grafana, PlanetScale, Retool, Railway), navigation/IA literature (NN/G, Carbon, Pajamas, Smashing), and dual-theme token architecture (Radix, shadcn, Primer, Tailwind). Purpose: fix the visual language, navigation scheme and theming approach before any mock HTML is written.

## What to steal - the high-leverage decisions

- **shadcn/RustFS aesthetic** - layered near-monochrome surfaces, one restrained accent, borders over shadows, ~6-10px radius, line icons, data-dense tables; instantly modern, never dated, free to copy
- **Dimmed left sidebar + dominant content area** - the cross-system consensus layout (Linear, Grafana, Vercel, Clerk, Supabase); flat, max two levels, 5-7 top-level items
- **List-table -> side drawer for edit, full page for rich detail** - the default resource pattern; drawer preserves list context, modal reserved for destructive confirmation only
- **Cmd-K command palette** - navigate + create + search + run-action in one keystroke; shipped by 5 of 9 systems studied; the single biggest friction reducer
- **Status as pill/dot WITH text** - animated in-progress, static at terminal; never colour-only (Tailscale's a11y miss); maps directly to server lifecycle
- **Token-based dark+light theming, dark-first** - acceptable and common for ops consoles; inline anti-FOUC script; tabular-numeral mono for tables and IDs

## Reference systems - what each contributes

- **RustFS / MinIO console** - the visual target: grouped left sidebar, list-table pages with a top-right "Add X", one-time credential reveal with Copy/Export, dark-first monochrome with a single bold accent; its nav (Users `group-line`, Policies `shield-check`, Settings `settings-line`, Status `bar-chart-box`) maps almost 1:1 to our domain
- **Linear** - keyboard model and density: Cmd-K context-sensitivity, `G`-chord jumps, `Space` peek-preview, split list+detail, draft-on-close; the gold standard for frictionless power use
- **Vercel/Geist** - inline invite (email + role + "Add more", no modal), "projects as filters" to kill nav duplication, animated status dots, engineering-grade restraint, dark-first 200-step gray scale
- **Supabase** - Cmd-K with actions, side-drawer row editing, dual policy editor (form + raw + AI), and role-impersonation "view as user" - directly applicable to "view portal as user X"
- **Clerk** - user/org management: full-page profile per user (not drawer), org detail tabbed Members/Invitations/Requests/Settings, kebab per row, danger zone isolated in settings
- **Tailscale** - machines/users tables, dual-mode ACL editor (visual + JSON with bidirectional live sync), "Needs approval" badge for gated signup, built-in dark mode via CSS custom props
- **Grafana** - admin IA reference: "Users and access" grouping Users/Teams/Service-accounts, inline role-picker dropdown, Cmd-K since v9, Saga dual-theme tokens
- **PlanetScale** - context-preserving switcher (changing scope keeps the current page/tab), prod-vs-dev as first-class visual status
- **Retool** - permission vocabulary (Use/Edit/Own), group-centric AND object-centric views, bulk grants, delegated scoped group-admin
- **Railway** - topology canvas + an observability tab aggregating live logs+metrics for instant "what's healthy"

## Navigation scheme

The recommendation for a users/groups/policies/servers portal.

- **One vertical left sidebar**, flat, max two levels, 5-7 top-level items - vertical scales better than top-bar for admin and gives stable scanning
- **Top-level items**: Overview/Home, Servers, Users, Groups, Policies, Activity, Settings; each a unique line-icon + short label, active-state highlighted ("you are here")
- **Role-gated body** - admin items appear only for admins; the sidebar header (brand, workspace) stays constant
- **Context switcher at top** that preserves the current page on switch (PlanetScale/Vercel pattern) - relevant if multi-deployment is ever added
- **Cmd-K command palette** wired to four verbs: navigate ("go to Groups"), create ("new user"), search entities ("find alice"), run actions ("stop jupyterlab-alice"); fuzzy match, recent commands on top, shortcut hints shown to teach passively; `?` opens a shortcut overlay
- **Breadcrumbs + deep-linkable URLs** on every nested page; preserve list filters/scroll/selection across drawer open-close and back-navigation
- **No third nesting level, no IA churn** - moving items breaks learned muscle memory

## Management scheme

How every entity (users, groups, policies, servers) is managed, consistently.

- **List page = data table** - sortable headers, selectable rows, per-row kebab (`…`) menu, toolbar with the primary action + search + filter; selecting >1 row reveals a batch-action bar
- **One persistent "+ Add" button** top-right of every list - never buried in an overflow menu
- **Create/edit surface by complexity**: side drawer for short forms (preserves context), full page for long/multi-step config or anything deep-linkable, modal only for destructive confirmation
- **Frictionless add** - multi-select assignment via typeahead + removable chips (assign groups/policies by typing); minimise required fields with sensible defaults (new user = non-admin, standard volumes); optimistic UI that reflects the change instantly and reconciles on response - never a full-page reload
- **Inline edits** for trivial single-field changes (rename, toggle authorised) without opening a form
- **Group-centric and object-centric views** - answer both "what can this group do" and "who is affected by this policy"; impersonate / "view as user" to preview effective access
- **Empty states as onboarding** - "No groups yet - create one to grant Docker access" with a direct CTA, distinct from "no results"
- **Anti-patterns barred**: deep nesting, hidden primary actions, reload-on-action, modal-in-modal, blocking modal for forms

## Visual language

- **Surfaces** - layered backgrounds (app base -> raised card -> overlay) differentiated by lightness, not heavy shadows; thin low-chroma borders
- **Accent** - a single brand colour used "like punctuation"; everything else monochrome; status colours (success/warning/danger/info) the only other chroma
- **Density** - 14px base type (not 16px), 4px spacing grid, tight table padding, ~6px default radius; comfortable but data-dense
- **Type** - system sans for UI, monospace with tabular numerals for tables, IDs, metrics, tokens
- **Components** - buttons (primary/secondary/outline/ghost/destructive), badges/status-pills, switches, sortable tables with checkbox select, chips for multi-assignment, toasts for async feedback, drawers for edit
- **Signature touches** - one-time credential reveal with Copy/Export (for token/API-key issuance), animated in-progress status dots, peek-preview of a focused row

## Theming - token architecture

Three layers: primitive palette (raw hex) -> semantic tokens (`--color-bg`, role-based, theme-flipped) -> optional component tokens. Components reference only semantic tokens. Dark-first in `:root`, light via `[data-theme="light"]`; `color-scheme` set per theme; default from `prefers-color-scheme`, manual choice persisted in `localStorage` and applied via a `data-theme` attribute; an inline `<head>` read prevents flash-of-wrong-theme. Targets WCAG AA (4.5:1 text, 3:1 large/UI) in both themes - re-pick each step, never naively invert.

Starter token set (AA-targeted starters, to be the mock's `tokens.css`):

```css
:root {
  color-scheme: dark;

  /* surfaces */
  --color-bg:               #0d0d10;
  --color-bg-subtle:        #141417;
  --color-surface:          #1a1a1f;
  --color-surface-hover:    #212127;
  --color-surface-active:   #28282f;
  --color-surface-raised:   #1f1f25;
  --color-overlay:          rgba(0,0,0,.6);

  /* borders */
  --color-border-subtle:    #26262c;
  --color-border:           #303038;
  --color-border-strong:    #43434d;
  --color-ring:             #4f8cff;

  /* text */
  --color-text:             #ededf0;
  --color-text-muted:       #a0a0ab;
  --color-text-subtle:      #6e6e78;

  /* accent */
  --color-accent:           #4f8cff;
  --color-accent-hover:     #6ea0ff;
  --color-accent-active:    #3f78e6;
  --color-accent-fg:        #ffffff;

  /* status */
  --color-success: #2ea043; --color-success-fg: #ffffff;
  --color-warning: #d29922; --color-warning-fg: #1a1a1f;
  --color-danger:  #f85149; --color-danger-fg:  #ffffff;
  --color-info:    #4f8cff; --color-info-fg:    #ffffff;

  /* scales (theme-agnostic) */
  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px;
  --space-5:24px; --space-6:32px; --space-8:48px;
  --radius-sm:4px; --radius-md:6px; --radius-lg:8px; --radius-full:9999px;
  --text-xs:12px; --text-sm:13px; --text-base:14px; --text-lg:16px;
  --text-xl:20px; --text-2xl:24px; --leading-tight:1.25; --leading-normal:1.5;
  --font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-mono: ui-monospace, "JetBrains Mono", Menlo, monospace;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.4);
  --shadow-md: 0 4px 12px rgba(0,0,0,.5);
  --shadow-overlay: 0 8px 24px rgba(0,0,0,.6);
}

[data-theme="light"] {
  color-scheme: light;
  --color-bg:            #ffffff;
  --color-bg-subtle:     #f6f8fa;
  --color-surface:       #ffffff;
  --color-surface-hover: #f3f4f6;
  --color-surface-active:#e9ebef;
  --color-surface-raised:#ffffff;
  --color-overlay:       rgba(0,0,0,.4);
  --color-border-subtle: #eaecef;
  --color-border:        #d0d7de;
  --color-border-strong: #b6bdc6;
  --color-ring:          #2563eb;
  --color-text:          #1a1f24;
  --color-text-muted:    #57606a;
  --color-text-subtle:   #818b98;
  --color-accent:        #2563eb;
  --color-accent-hover:  #1d4fd0;
  --color-accent-active: #1a45b8;
  --color-accent-fg:     #ffffff;
  --color-success: #1a7f37; --color-success-fg: #ffffff;
  --color-warning: #9a6700; --color-warning-fg: #ffffff;
  --color-danger:  #cf222e; --color-danger-fg:  #ffffff;
  --color-info:    #2563eb; --color-info-fg:    #ffffff;
}
```

Notes: status hex differ per theme on purpose (light darkened to clear 4.5:1 on white); validate every text-on-surface and accent-on-surface pair before treating the palette as final. The accent above is a neutral blue placeholder - swap for the Stellars brand hue when chosen.

## Domain mapping - to the JupyterHub portal

- **Overview/Home** - status cards (servers running/idle/stopped, user/group counts, GPU), recent activity, quick actions; the screen built first
- **Servers** - table of spawned labs (user, state pill, uptime, CPU/mem, last-activity), per-row kebab (open, restart, stop, inspect); the "what's healthy" surface (Railway/Grafana influence)
- **Users** - table + "Add User", enable/disable switch, authorise/needs-approval badge, bulk delete, kebab (impersonate/view-as, change password, delete), full-page profile per user (Clerk)
- **Groups** - table + "Add Group", priority order, member count; detail shows members + the policy editor; group-policy binding via chips/typeahead
- **Policies** - the nine policy types surfaced as a dual-mode editor (visual form + raw JSON with live sync, Tailscale/Supabase), badges/summaries server-described (our existing `policy_summary` pattern)
- **Activity** - resource usage table + live status dots, the observability surface
- **Settings** - read-only-to-editable config hub
- **Token/API-key issuance** - the one-time reveal with Copy/Export

Security note: this is presentation only - the mock illustrates flows, the hub remains the trust boundary (see the rebuild concept in `portal-ui-catalogue.md`); every action a real build wires up is re-authorised server-side.

## Sources

RustFS console (github.com/rustfs/console `globals.css`, `config/navs.ts`), MinIO console, Linear/Vercel-Geist/Supabase/Clerk/Tailscale/Grafana-Saga/PlanetScale/Retool/Railway design docs, NN/G (empty states, you-are-here, breadcrumbs), GitLab Pajamas, Carbon data-table + empty-states, Smashing modal-vs-page decision tree, cmdk, Radix Colors, shadcn theming, GitHub Primer primitives, Tailwind v4 theming.
