# Optimum Hub portal - action audit (live mode)

Action-by-action audit of the hub-served React portal (`optimum-hub-web`) in LIVE mode (`VITE_DATA_MODE=live`), to record what is genuinely wired to the hub versus what is still mock or broken. Produced by six parallel read-only audit agents, each tracing the full path: view (`src/pages`/`src/components`) -> action layer (`src/services/ops.ts`) or read (`src/services/hub/liveSource.ts`) -> HTTP (`src/services/hub/client.ts`) -> route (`config/jupyterhub_config.py`) -> backend handler.

## Legend

- `[x] LIVE` - wired to a real, existing backend endpoint that performs the operation
- `[ ] MOCK` - intentionally stubbed: a direct `mockAction`/`mockSuccess` (fires in both modes) or a `liveSource` method bound straight to `mockSource`
- `[ ] BROKEN` - wired but non-functional in live (endpoint not called, response discarded, or render race)
- `[ ] PARTIAL` - some paths real, some mock

Key behaviour: `ops.ts run()` executes the real call only in live mode; views that call `mockAction`/`mockSuccess` outside an `if (isMock())` guard are mock in both modes.

## Server lifecycle, session, volumes  (13 live / 2 mock)

- [x] **startServer / stopServer** - `ops.ts:46,49` -> stock `POST|DELETE /hub/api/users/{u}/server`
- [x] **restartServer** - `ops.ts:52` -> `POST .../restart-server` (server.py RestartServerHandler)
- [x] **extendSession** - `ops.ts:55` -> `POST .../extend-session` (session.py)
- [x] **resetActivity** - `ops.ts:58` -> `POST /api/activity/reset` (activity.py)
- [x] **resetVolumes** - `ops.ts:162` -> `DELETE .../manage-volumes` (volumes.py)
- [x] **reads** getServers, getServerHero, getSessionInfo, getUserVolumes, getTotalResources (GPU field always 0)
- [ ] **Tail live spawn log** - MOCK - `Servers.tsx:42` - no backend
- [ ] **Download activity report** - MOCK - `Servers.tsx:189` - no export endpoint

## Users & authentication  (20 live / 1 mock / 1 broken)

- [x] **createUser, deleteUser, setAdmin, renameUser** - `ops.ts:75,78,81,84` -> stock `/hub/api/users/{name}` (+ events.py UserInfo sync)
- [x] **setUserAuthorization** - `ops.ts:65` -> `POST /api/native-users/{name}/authorization` (NativeUserAuthorizationHandler)
- [x] **discardUser** - `ops.ts:72` -> `GET /hub/discard/{name}` (NativeAuth)
- [x] **setUserPassword / changeOwnPassword** - `ops.ts:88,98` -> NativeAuth change-password handlers
- [x] **getCredentials** - `ops.ts:113` -> `POST /api/admin/credentials`
- [x] **reads** getUsers (merges `/native-users`), getUser, getUserCorpus, fetchUsers, pending-user surfacing
- [x] **views** Users / UserConfig / NewUser / BulkUsers create+save flows (mock only inside `if(isMock())`)
- [ ] **Require-password-change-at-login switch** - MOCK - `UserConfig.tsx:94`, `NewUser.tsx:61` - UI-only, never sent
- [ ] **First/last name + email fields** - BROKEN - `UserConfig.tsx:73,85-87`, `Profile.tsx:52-58` - display-only, persisted nowhere (no DB column / native field / auth_state); email is a hardcoded `{name}@lab...` template

## Groups: CRUD & membership  (11 live / 1 mock / 1 broken)

- [x] **createGroup, deleteGroup, reorderGroups** - `ops.ts:127,130,133` -> groups.py create/delete/reorder
- [x] **addMember / removeMember** - `ops.ts:120,123` -> stock `/api/groups/{name}/users`
- [x] **saveGroupConfig** - `ops.ts:137` -> `PUT /api/admin/groups/{name}/config` - sends `{description}` only (policy body omitted, see below)
- [x] **reads** getGroups, getGroupCorpus; GroupConfig **Members** tab
- [ ] **getGroupConfig / General tab** - BROKEN - `liveSource.ts:272`, `GroupConfig.tsx:60` - name/description/priority render empty in live. Root cause: the `<Form>` binds via mount-only `initialValues` + a `key` remount; antd v5 never re-applies values after the async `cfg` lands. Fix: in the existing `useEffect` (`GroupConfig.tsx:30`) add `form.setFieldsValue({name, description, priority})` alongside `setMembers`. Data path itself is correct.
- [ ] **Import groups from JSON** - MOCK - `Groups.tsx:83`

## Group policy editor (9 sections)  (0 live / 12 mock / 2 partial)

The entire `GroupPolicyTab` is mock: every section seeds local `useState` and persists nothing. The backend (`groups_config.py` + `policy/registry.py`) **already supports full read+write** for all nine policy types via `PUT /admin/groups/{name}/config` (`coerce_config` -> `validate_all` -> `save_config`), and `GET /admin/groups` already returns each group's complete `config` dict - the React data layer discards it.

- [ ] **env_vars, GPU, memory, CPU, docker (std/limited/privileged + quotas + flags), volume mounts, API keys pool, downloads, sudo** - MOCK - `GroupPolicyTab.tsx` - reads seeded constants, writes nothing
- [ ] **Section on/off toggles** - MOCK - `GroupPolicyTab.tsx:88` - enabled state IS read from `cfg.sections`, but toggling only `mockAction`s
- [ ] **Save (policy body)** - PARTIAL - `GroupConfig.tsx:34` - description/priority/members are real; the policy `config_dict` is never sent
- [ ] **Download / Upload policy JSON** - MOCK - `GroupConfig.tsx:70,71`
- [ ] **Export groups JSON** - MOCK - `GroupsExport.tsx:33`
- Hardcoded fixtures: `GPU_DEVICES` (A100/RTX 6000 Ada), `HOST_CPUS=32`, `HUB_VOLUMES` (incl. `jupyterhub_datasets`/`jupyterhub_scratch`, which do not exist)
- **Live GPU inventory exists**: `gpu.py::enumerate_gpus` -> `stellars_config['gpu_list']` (`{index,name,uuid,memory_mb}`), passed to the legacy `groups.html` but never exposed to the React portal

## Notifications & tokens  (4 live / 1 mock / 1 broken)

- [x] **Broadcast to all active servers** - `ops.ts:171` -> `POST /api/notifications/broadcast` (notifications.py, real per-server token-auth delivery)
- [x] **getTokens, token create, token revoke** - `ops.ts:145,158` + `liveSource.ts:354` -> stock tokens API (the "mocked" header comment in `Tokens.tsx` is stale)
- [ ] **Broadcast to "Selected users"** - BROKEN - `Notifications.tsx:52` - dead `Radio.Group` with no state and no user picker; backend already accepts `recipients` (notifications.py:103) and a live `GET /api/notifications/active-servers` exists but is never called
- [ ] **Notification history** - MOCK - `liveSource.ts:422` -> mockSource - no sent-history read API

## Dashboards, events, settings, misc  (5 live / 11 mock)

- [x] **getStats, getServers, getServerHero, getHubInfo** - real reads from `/users` + `/activity` + `/info`
- [x] **getTotalResources** - PARTIAL - CPU/mem real; **GPU hardcoded 0** ("host GPU utilisation not collected", `liveSource.ts:314`)
- [x] **Sign out** - `AppLayout.tsx:83` -> real `/hub/logout` in live (mock branch only in mock)
- [x] **Theme switch** - client-only by design
- [ ] **Events feed (Home widget + Events page)** - MOCK - `liveSource.ts:417` -> mockSource - **no real event source exists anywhere in the backend**
- [ ] **Settings page (read + toggles)** - MOCK - `liveSource.ts:420`, `Settings.tsx:13` - no JSON settings API for the portal
- [ ] **Notification history reads / getSettingsReference** - MOCK - `liveSource.ts:421`
- [ ] **Language switch** - MOCK/no-op - `AppLayout.tsx:49` - no i18n applied
- [ ] **Command palette quick actions** (stop/restart/manage volumes) - MOCK - `CommandPalette.tsx:52` - `mockAction`, do not call the real ops (nav entries route correctly)
- [ ] **Lab Container: image pull/set, add/remove mount, getLabVolumes** - MOCK - `LabContainer.tsx:27,37,47`, `liveSource.ts:419` - fabricated mounts, no backend

## Remediation tiers

**Tier 1 - frontend-only, backend already exists (no hub change, low risk):**
- GroupConfig General-tab empty fields -> `form.setFieldsValue` in the existing `useEffect`
- Wire the whole policy editor: `getGroupConfig` returns the real `config`; `GroupPolicyTab` binds to it; `saveGroupConfig` sends the full `config_dict` (PUT already supports it)
- Notifications "Selected users": recipient state + `Select` fed by `/api/notifications/active-servers`; pass `recipients` to `broadcast`
- Command-palette quick actions -> call the real `ops.ts` functions
- Policy JSON download/export -> generate client-side from real `config`
- Drop the stale "mocked" comment in `Tokens.tsx`

**Tier 2 - needs a small backend addition (mostly plumbing):**
- Expose `stellars_config['gpu_list']` to the portal (endpoint or portal bootstrap) -> real GPU device picker
- Lab Container: read the real lab image + configured shared mounts from hub config

**Tier 3 - needs a real backend feature / data source (design decision):**
- First/last name persistence (storage location: native-users column vs auth_state vs new table)
- GPU utilisation % (host nvidia-smi sampling collector feeding activity)
- Events feed (a real event log + endpoint, or remove the feature)
- Settings read/write (JSON settings API; some settings are not runtime-writable)
- Notification sent-history store
- Spawn-log tail / activity-report export / image pull / add-remove-mount endpoints

## Already fixed this session (pending image rebuild)

- ReadonlyBanner no longer claims "every action is simulated" on the live portal (mock-only now)
- Groups list "#" column shows a row rank, not the raw duplicated priority
- GroupConfig priority direction corrected to "higher number wins"
- Standard vs Limited Docker access made mutually exclusive in the policy UI
- Servers page default filter = all
