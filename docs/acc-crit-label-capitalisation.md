# Acceptance Criteria - Label capitalisation (Title Case)

Button labels and header labels across the portal use Title Case - every principal word capitalised, minor words lowercase unless first/last. This is a system-wide design-language rule (cross-ref [acc-crit-design-language]); the live reference is the `/design-language` Conventions card. The trigger was the Events "Clear log" button, which should read "Clear Events". Verified against the code 2026-06-18.

## The rule

- [x] **Title Case principal words** - capitalise the first word and every principal word of a label
  - log: 2026-06-18 rule defined; e.g. "Add user" -> "Add User", "Manage volumes" -> "Manage Volumes"
- [x] **Minor words stay lowercase** - a, an, the, and, or, but, nor, of, to, in, on, at, by, for, from, with, vs, per, as, into stay lowercase UNLESS first or last word
  - log: 2026-06-18 e.g. "Force Password Change on Next Login", "Add a Group"
- [x] **Acronyms preserved** - JSON, API, CPU, GPU, TLS, URL, ID, NAS, CIFS, MLflow, TTL kept as-is (never "Api"/"Gpu")
  - log: 2026-06-18 e.g. "New API Token", "Single API Key"
- [x] **Units / tokens / numbers preserved** - "+7h", "24h", "30s", "GB", ".txt", "30%" unchanged
  - log: 2026-06-18 e.g. "Download .txt", "Choose JSON File(s)…"

## Scope (Title-Cased)

- [x] **Button labels** - every button's visible text, and Modal action buttons (`okText`/`cancelText`) that are action labels
  - log: 2026-06-18 swept (e.g. Clear Events, Stop All, Start Server, Remove User, Bulk Add)
- [x] **Page / card / section headers** - `PageHeader` titles, `Card` / `CardHeadLink` titles, `oh-section-title`
  - log: 2026-06-18 swept (e.g. Active Servers, Recent Events, New User, Export Groups, Effective Policies)
- [x] **Table column headers** - the `title` of list/table columns
  - log: 2026-06-18 swept (e.g. Last Activity, Time Left, Mount Point, Key Secret)
- [x] **Section / mode tabs** - tab and segmented labels that name a section or mode (not a data value)
  - log: 2026-06-18 swept (e.g. Add User, Create Group, Single API Key)

## Out of scope (left sentence case / unchanged)

- [x] **Form-field input labels** - `Form.Item` labels (First name, Last name, Email, Change password) stay sentence case - they are field prompts, not button/header labels
  - log: 2026-06-18 excluded per the operator's "(buttons, headers)" scope
- [x] **Sentence copy** - descriptions, `sub` lines, notices, alerts, tooltips and confirm-modal prompts ("Stop all running servers?", "Clear the event log?") stay sentence case
  - log: 2026-06-18 excluded - these are sentences, not labels
- [x] **Filter data-values** - Segmented/Radio option values that are data (statuses All/Active/Idle/Offline/Culled/Unauthorised, time ranges Last 24h / Last 7 days, percentages, durations, language names) stay as-is
  - log: 2026-06-18 excluded - they are values, not labels
- [x] **Dynamic / cell content** - table cell values and interpolated runtime strings unaffected
  - log: 2026-06-18 excluded

## Edge cases

- [x] **Same string, two roles** - a literal that appears both as a button AND as a sentence/tooltip is Title-Cased only in the label occurrence, not globally
  - log: 2026-06-18 swept per-occurrence with context, never a blind global replace
- [x] **Demo / reference pages** - `/design-system` (dev kitchen-sink) showcase headings were left as-is; `/design-language` carries the canonical Conventions rule + a Title-Case example row
  - log: 2026-06-18 DesignSystem.tsx out of scope; DesignLanguage.tsx Conventions card documents the rule

## Verification

- [x] **Frontend gates** - `npx tsc -b`, `npm run lint`, `npm run build:hub` all clean after the sweep
  - log: 2026-06-18 run from optimum-hub-web after the sweep
