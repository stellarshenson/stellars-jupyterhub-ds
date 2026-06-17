# Acceptance Criteria - live data honesty (no mock masquerade)

In live mode the portal must never present fabricated mock data as if it were real. A live `DataSource` method either returns real hub data, returns an honest empty/disabled state, or the surface is hidden - it never silently delegates to `mockSource` for content a user reads as fact. Mock mode (the design pages) keeps full mock data so the UI demos whole.

## Effective grants (per-user resolved policy)

- [x] **Real resolve endpoint** - `getEffectiveGrants(user)` calls `GET /api/users/{user}/effective-grants`, not `mockSource`
  - log: 2026-06-17 FIXED - was `getEffectiveGrants: mockSource.getEffectiveGrants` (liveSource.ts:606); now a real async method
- [x] **Backend resolves across the user's groups** - `EffectiveGrantsHandler` loads the user's ORM groups, runs `resolve_policies`, then `effective_grants(matched, resolved)`
  - log: 2026-06-17 added `handlers/effective_grants.py`, `policy.effective_grants`
- [x] **Source attribution** - each grant cites the highest-priority group that granted it (`from`), resolved by walking the priority-descending matched configs
  - log: 2026-06-17 `winner()` helper in `effective_grants`
- [x] **Honest empty** - a user whose groups grant nothing special returns `[]` (runs on platform defaults), not fabricated CPU/memory rows
  - log: 2026-06-17 mock fabricated "8 cores"/"16 GB" for everyone; real version emits a row only when a group sets it
- [x] **GPU hardware-gated** - the GPU grant appears only when `gpu_available` (resolver gates `gpu_access` on it); `gpu_available` threaded into `stellars_config`
  - log: 2026-06-17 added `'gpu_available': bool(gpu_enabled)` to tornado_settings
- [x] **Grant value formatting** - memory `N GB` (`(no swap)` annotated), CPU `N cores`, GPU `all devices` or `GPU 0, 1`, sudo `enabled`/`disabled`, docker `socket`/`limited`/`privileged` (privileged annotated onto the same row)
  - log: 2026-06-17 `num()` drops trailing `.0`
- [x] **Unique icon keys** - the full grant fanout uses distinct `key`s (gpu/memory/cpu/shield/box) so the React row keys never collide; docker+privileged collapse to one `box` row
  - log: 2026-06-17 covered by `test_unique_keys_for_react`
- [x] **Self-or-admin** - non-admin may read only their own grants (403 otherwise), same rule as the profile handler
  - log: 2026-06-17 `_authorize`
- [x] **Failure falls to honest empty** - a fetch error returns `[]`, never the mock grants
  - log: 2026-06-17 `catch { return [] }`
- [x] **Edge: unknown user** - handler returns 404 when the ORM user does not exist
  - log: 2026-06-17 implemented
- [x] **Edge: biggest-wins attribution** - when two groups set memory/cpu, the row cites the highest-priority group at the winning (max) value
  - log: 2026-06-17 covered by `test_biggest_wins_with_attribution`
- [ ] **Runtime: konrad sees real grants** - on the live hub the Home / UserConfig grants reflect his actual group policy with correct source, not the mock list
  - log: 2026-06-17 backend + frontend done; on-screen confirm pends operator rebuild

## Activity report download

- [x] **Real report** - the Servers "Report" action downloads a real CSV of the servers currently in scope (one row per server, the same activity / CPU / memory / volume / time-left numbers the table shows), client-side from already-fetched data
  - log: 2026-06-17 FIXED - was `mockAction('Downloaded activity report')`; now `downloadCsv` from `filtered`, real success toast, disabled when scope is empty
- [x] **Edge: empty scope** - the Report button is disabled when no server is in scope (nothing to export)
  - log: 2026-06-17 implemented

## Group policy import / export

- [x] **Export uses real configs** - "Export N groups" downloads `{groups:[{name, description, priority, config}]}` built from the live `/admin/groups` configs (raw flat `config` now carried on `GroupRow`), client-side, real success toast
  - log: 2026-06-17 FIXED - was `mockAction('Exported N groups as JSON')`; `downloadJson`, importable shape
- [x] **Import writes via real endpoints** - the Import file-picker parses the bundle and `importGroups` creates each group (409 already-exists falls through) then PUTs `/admin/groups/{name}/config`; one toast + one `['groups']` invalidation for the batch
  - log: 2026-06-17 FIXED - was `mockAction('Import groups from JSON')`; real create + config PUT, mock-toast only in mock mode
- [x] **Round-trips** - an exported bundle re-imports through the same flat-config shape the editor PUTs (hub coerces + validates)
  - log: 2026-06-17 export/import share `{name, description, priority, config}`
- [x] **Edge: malformed file** - a non-JSON / shapeless file shows "Import failed: ..." and writes nothing; the same file can be re-picked (input value cleared)
  - log: 2026-06-17 parse guarded before any write

## General rule

- [ ] **Audit remaining mock delegations** - every `mockSource.*` still wired into `liveSource` is either a deliberate honest-empty fallback (documented in the file header) or a tracked gap; no content-bearing method masquerades
  - log: 2026-06-17 remaining live delegations: `getSettingsReference` (static reference copy), `getSentNotifications` (honest empty), `getEvents`/`getSessionInfo` (mock only on fetch error) - all documented

## API

- `GET /api/users/{user}/effective-grants` -> `{grants: [{key, label, value, from}]}`; 403 not-self-not-admin, 404 unknown user
