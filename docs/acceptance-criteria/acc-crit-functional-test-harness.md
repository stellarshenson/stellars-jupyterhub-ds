# Acceptance Criteria - Functional Test Harness

A standing functional regression harness that boots the built hub image in a fully isolated throwaway compose deployment and drives the running platform end-to-end (UI actions + multi-step scenarios) with a containerized Playwright runner. Purpose: validate future fundamental rebuilds; local-only (GitHub cannot run the DockerSpawner deployment); removes everything it creates on completion.

Legend: `[x]` implemented, `[ ]` planned (the test/scenario backlog). Each item is one functional test unless noted. Items needing the real `stellars-jupyterlab-ds` lab image (not the minimal singleuser one) are tagged `(real-lab)` and are out of scope for the default minimal run.

> 2026-06-18 SPA rebuild: the old `test_hub_ui` / `test_scenarios` drove the stock JupyterHub HTML (`#groups-table-body`, Bootstrap modals), dead against the React portal. The harness now drives the live SPA (visible text / antd `aria-label` / placeholders - no data-testids), authenticates by injecting the API session's hub cookies (a direct `/hub/login` self-redirects), and waits on the `.ant-layout` shell not `networkidle`. `make test-functional-all` (22 tests) green across all three setups on a GPU host.

## Setups (initial conditions, run one by one)

- [x] **Sequential multi-setup runner** - `make test-functional-all` boots each setup, runs its regime, cleans, moves to the next, and reports which passed (non-zero exit if any failed)
  - log: 2026-06-18 implemented (Makefile loop over signup / env / signup-open)
- [x] **Setup: signup-bootstrap** - fresh DB, signup off; admin via the bootstrap-signup window; runs the full SPA UI suite + container policy + GPU (when present)
  - log: 2026-06-18 18 passed (incl. GPU auto-detect: 3 GPUs)
- [x] **Setup: env-password admin** - signup off + `JUPYTERHUB_ADMIN_PASSWORD`, restart-to-provision; one focused login test
  - log: 2026-06-18 2 passed
- [x] **Setup: signup-open** - signup enabled, admin env-provisioned; a non-admin self-signs-up and the admin authorises via the SPA Users page
  - log: 2026-06-18 2 passed (`FUNCTEST_AUTH_MODE=signupopen`)
- [x] **Regime gating** - a conftest collection hook deselects (never skips) tests outside the run's regime, keyed off `FUNCTEST_AUTH_MODE` + GPU presence
  - log: 2026-06-18 signup / env / signupopen / gpu markers
- [x] **Coverage declaration + report** - every functional test declares the acc-crit it covers via `@pytest.mark.acc_crit("<doc-slug>::<label>", ...)`; a collected test with no declaration aborts the run, and the suite prints a `MET`/`UNMET` coverage report per criterion at conclusion
  - log: 2026-06-18 implemented (conftest `pytest_collection_modifyitems` enforcement + `pytest_terminal_summary` report; verified by collect-only across all three regimes)

## Harness infrastructure

- [x] **Isolated project** - runs under its own compose project `stellars-functest`, never the operator's
  - log: 2026-06-13 implemented
- [x] **Isolated network** - `stellars-functest_network`; spawned labs join only this network
  - log: 2026-06-13 implemented
- [x] **Namespaced volumes** - project-prefixed volumes; no shared `jupyterhub_*` names
  - log: 2026-06-13 implemented
- [x] **Dedicated admin** - `functestadmin`, distinct from any real `admin`
  - log: 2026-06-13 implemented
- [x] **No host port** - containerized runner reaches the hub by service name; operator `:8000` never bound
  - log: 2026-06-13 implemented
- [x] **Containerized runner** - Playwright runs in `mcr.microsoft.com/playwright/python`; no host browser deps
  - log: 2026-06-13 implemented
- [x] **Minimal spawn image** - `quay.io/jupyterhub/singleuser` pulled for spawn; hub image left intact
  - log: 2026-06-13 implemented
- [x] **Health gate** - runner waits on the HTTP health endpoint before tests (not the buggy compose pgrep healthcheck)
  - log: 2026-06-13 implemented
- [x] **Complete teardown** - on pass or fail, removes containers, spawned labs, network, all volumes, and pulled test images
  - log: 2026-06-13 implemented
- [x] **Idempotent clean target** - `make test-functional-clean` force-removes a leftover harness safely
  - log: 2026-06-13 implemented
- [x] **CI split** - pytest unit suites run as a GitHub `unit_tests` job; the harness is never wired into CI
  - log: 2026-06-13 implemented
- [ ] **Run isolation** - parallel/repeat runs do not collide (unique project suffix per run)
  - log: 2026-06-13 planned
- [ ] **Diagnostics on failure** - capture hub logs + Playwright trace/screenshot artifacts on failure
  - log: 2026-06-13 planned
- [ ] **Edge: interrupted run** - Ctrl-C / killed run still leaves zero trace (trap-based teardown)
  - log: 2026-06-13 planned
- [ ] **Edge: stale harness present** - a prior leftover deployment is cleaned before a new run starts
  - log: 2026-06-13 planned

## Fixtures

- [x] **base_url / admin_creds** - session fixtures from env
  - log: 2026-06-13 implemented
- [x] **admin_page / admin_portal** - admin page authenticated by injecting the `admin_api` session's hub cookies (no flaky form login); `admin_portal` wraps it with SPA navigation (`goto(route)` + `.ant-layout` ready wait)
  - log: 2026-06-13 implemented; 2026-06-18 reworked to cookie injection + SPA `Portal` helper
- [x] **clean_groups** - autouse fixture wiping all groups before/after each test (API), so tests are independent
  - log: 2026-06-13 implemented
- [x] **admin_api** - logged-in requests session for API-level setup/teardown
  - log: 2026-06-13 implemented
- [x] **signup_user** - factory that self-signs-up an arbitrary user via the NativeAuth form (the signup-open pending user)
  - log: 2026-06-18 implemented
- [ ] **seeded_groups** - fixture pre-creating a known set of groups for scenarios
  - log: 2026-06-13 planned
- [ ] **seeded_users** - fixture pre-creating non-admin users with set memberships
  - log: 2026-06-13 planned
- [ ] **api_client** - authenticated requests session for API-level assertions alongside the UI
  - log: 2026-06-13 planned

## Auth & bootstrap

- [x] **Login shell served** - `/hub/login` serves the SPA auth shell (`window.jhdata.authPage = "login"`), which renders the antd sign-in screen; the form login itself is exercised end-to-end by the `admin_api` fixture
  - log: 2026-06-13 implemented; 2026-06-18 reworked - the antd inputs use `id` not `name` and a direct `/hub/login` GET self-redirects, so render is asserted via the served shell
- [x] **Signup bootstrap window** - on a fresh DB (signup off, no env password) the first admin is created by signing up, then authenticates and reaches the hub
  - log: 2026-06-13 implemented (the harness default; env-password bootstrap cannot seed on a single fresh boot)
- [x] **Admin reaches the portal** - the authenticated admin loads the SPA app shell (`.ant-layout`), not bounced to login
  - log: 2026-06-18 implemented (`test_admin_reaches_portal`, cookie-injected session)
- [x] **Admin env-password login (mode 2)** - signup disabled + JUPYTERHUB_ADMIN_PASSWORD; `make test-functional-env` does the restart-to-provision and runs ONE focused test (`test_auth_env_mode`: env admin reaches the portal + signup form not served), not a full-suite re-run
  - log: 2026-06-13 implemented; 2026-06-18 strengthened to load the portal (was a trivial URL check)
- [x] **Signup enabled/disabled** - signup form present iff `JUPYTERHUB_SIGNUP_ENABLED=1`
  - log: 2026-06-18 implemented (`test_signup_form_served`, signup-open regime)
- [x] **Non-admin needs authorization** - a self-signed user lands in the pending queue (`is_authorized=False`), not authorised
  - log: 2026-06-18 implemented (signup-open: `signup_user` -> pending section)
- [x] **Admin authorizes user** - admin authorises a pending user through the SPA Users page; the pending queue empties and the backend reports `is_authorized=true`
  - log: 2026-06-18 implemented (`test_self_signup_then_admin_authorises`)
- [ ] **Logout** - logout returns to login and clears the session
  - log: 2026-06-13 planned
- [ ] **Wrong password rejected** - invalid login shows an error, no session
  - log: 2026-06-13 planned
- [ ] **Edge: failed-login lockout** - N failed attempts locks the account for the window
  - log: 2026-06-13 planned
- [ ] **Edge: admin password change ignores env** - after UI password change, env password no longer logs in
  - log: 2026-06-13 planned

## Hub pages & navigation

- [x] **SPA page-render smoke** - every major SPA screen mounts and shows its signature control: dashboard ("Active servers"), servers (user filter), users ("Inactive" pill), groups ("Add group"), events ("Clear log"), notifications ("Send broadcast"), settings ("Full reference"), lab setup ("Lab image"), design language
  - log: 2026-06-18 implemented (`test_hub_ui.py`, 9 page renders via SPA selectors)
- [x] **Groups page renders** - "Add group" button visible (SPA)
  - log: 2026-06-13 implemented; 2026-06-18 reworked to the SPA Groups page
- [x] **Settings / Notifications render** - signature controls visible (SPA)
  - log: 2026-06-13 implemented; 2026-06-18 reworked to SPA
- [ ] **Activity** - activity is folded into the dashboard / servers meters; there is no standalone `/activity` SPA page (the old 200-check is retired)
  - log: 2026-06-18 retired - covered indirectly by the dashboard/servers renders
- [ ] **Admin home renders** - admin home lists users + server controls
  - log: 2026-06-13 planned
- [ ] **Token page renders** - /hub/token page loads, can request a token
  - log: 2026-06-13 planned
- [ ] **Non-admin denied admin pages** - a non-admin user gets 403 on groups/settings/activity/notifications
  - log: 2026-06-13 planned
- [ ] **Nav links** - admin nav exposes the custom pages and they are reachable
  - log: 2026-06-13 planned

## Branding - hub

- [ ] **Custom logo** - `JUPYTERHUB_BRANDING_LOGO_URI` logo renders on hub login/home
  - log: 2026-06-13 planned
- [ ] **Custom favicon** - `JUPYTERHUB_BRANDING_FAVICON_URI` favicon served on hub pages
  - log: 2026-06-13 planned
- [ ] **file:// logo/favicon** - a `file://` URI is copied to the static dir and served
  - log: 2026-06-13 planned
- [ ] **External URL logo/favicon** - an `http(s)://` URI is passed through
  - log: 2026-06-13 planned
- [ ] **Default branding** - empty branding env yields stock JupyterHub assets
  - log: 2026-06-13 planned
- [ ] **Favicon CHP proxy route (real-lab)** - a lab session's favicon request routes back to the hub's custom favicon
  - log: 2026-06-13 planned

## Branding - lab container (injected env, asserted via docker inspect)

- [ ] **Main icon injected** - `JUPYTERLAB_MAIN_ICON_URI` present in the spawned container Env (file:// resolved to a hub static URL, else the URL passed through)
  - log: 2026-06-13 planned
- [ ] **Splash icon injected** - `JUPYTERLAB_SPLASH_ICON_URI` present in the container Env
  - log: 2026-06-13 planned
- [ ] **Busy favicon injected** - `JUPYTERHUB_BRANDING_FAVICON_BUSY_URI` resolved and reaches the lab
  - log: 2026-06-13 planned
- [ ] **System name rebrand** - `JUPYTERLAB_SYSTEM_NAME` injected into the container Env
  - log: 2026-06-13 planned
- [ ] **System name capitalize / color** - `JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME` and `JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR` injected
  - log: 2026-06-13 planned
- [ ] **Empty = no rebrand** - empty branding env leaves the lab env unset (no rebrand)
  - log: 2026-06-13 planned
- [ ] **Visual rebrand (real-lab)** - welcome page / MOTD / toolbar header badge reflect the system name
  - log: 2026-06-13 planned
- [ ] **Visual icons (real-lab)** - the lab shows the custom main/splash icons and busy favicon frames
  - log: 2026-06-13 planned

## Groups - management

- [x] **Create group** - "Add group" -> the NewGroup form -> Create -> the row appears on /groups
  - log: 2026-06-13 implemented; 2026-06-18 reworked to the SPA create flow (`test_group_create_badge_delete`)
- [x] **Name opens config** - the group-name link routes to `/groups/:name` (SPA, no modal)
  - log: 2026-06-13 implemented; 2026-06-18 SPA link
- [x] **Delete group** - the danger delete icon removes the row directly (no confirm modal in the SPA)
  - log: 2026-06-13 implemented; 2026-06-18 reworked to the SPA delete icon
- [x] **Reorder priority** - the move-up icon reorders the row above its neighbour (optimistic)
  - log: 2026-06-13 implemented; 2026-06-18 reworked to the SPA move-up action (`test_priority_reorder`)
- [ ] **Move down** - move-down reorders below its neighbour
  - log: 2026-06-13 planned
- [ ] **Priority persists** - reordered priority survives a page reload
  - log: 2026-06-13 planned
- [ ] **Description** - group description saves and displays
  - log: 2026-06-13 planned
- [ ] **Edit existing group** - reopening a saved group shows its persisted config
  - log: 2026-06-13 planned
- [ ] **Empty state** - no groups shows the "Add Group" empty message
  - log: 2026-06-13 planned
- [ ] **Edge: duplicate name** - creating a duplicate group name is rejected
  - log: 2026-06-13 planned
- [ ] **Edge: invalid name** - name not matching the pattern is rejected with a message
  - log: 2026-06-13 planned
- [ ] **Edge: cancel modal** - cancelling the add/config modal makes no change
  - log: 2026-06-13 planned

## Groups - membership

- [ ] **Add member** - chip-input adds a user to a group
  - log: 2026-06-13 planned
- [ ] **Remove member** - removing a chip removes membership
  - log: 2026-06-13 planned
- [ ] **Member count** - the row member count reflects membership
  - log: 2026-06-13 planned
- [ ] **Members tooltip** - hovering the count lists members
  - log: 2026-06-13 planned
- [ ] **Edge: unknown user** - adding a non-existent user is handled gracefully
  - log: 2026-06-13 planned
- [ ] **Edge: rename sync** - renaming a user in the admin panel keeps group membership
  - log: 2026-06-13 planned

## Policy config - per type (save + reopen + persist for each)

- [x] **Sudo** - enable section, member-sudo on/off; persists
  - log: 2026-06-13 implemented
- [x] **Downloads** - enable section, allow/block; persists
  - log: 2026-06-13 implemented
- [x] **Memory** - enable cap, set GB; persists
  - log: 2026-06-13 implemented
- [ ] **Memory swap** - swap-disabled toggle persists
  - log: 2026-06-13 planned
- [ ] **CPU** - enable cap, set cores; persists
  - log: 2026-06-13 planned
- [ ] **GPU all** - enable access, all-GPUs; persists
  - log: 2026-06-13 planned
- [ ] **GPU specific** - enable access, specific device ids; persists
  - log: 2026-06-13 planned
- [ ] **Env vars add** - enable section, add a var; persists
  - log: 2026-06-13 planned
- [ ] **Env vars remove** - remove a var row; persists
  - log: 2026-06-13 planned
- [ ] **Docker raw** - enable section, raw-socket access; persists
  - log: 2026-06-13 planned
- [ ] **Docker limited** - limited access + quotas (containers/volumes/networks/storage/cpu/mem); persists
  - log: 2026-06-13 planned
- [ ] **Docker dangerous flags** - allow-dangerous toggle persists with warning
  - log: 2026-06-13 planned
- [ ] **Docker compose project** - per-user compose-project enable + allow-override persist
  - log: 2026-06-13 planned
- [ ] **Docker hub-network** - hub-network-access toggle persists
  - log: 2026-06-13 planned
- [ ] **Docker privileged** - privileged toggle persists with warning
  - log: 2026-06-13 planned
- [ ] **API keys pair** - pair mode, id/secret var names + credentials; persists masked
  - log: 2026-06-13 planned
- [ ] **API keys single** - single mode, key var + credentials; persists masked
  - log: 2026-06-13 planned
- [ ] **Volume mounts** - add a volume->mountpoint; persists
  - log: 2026-06-13 planned
- [ ] **Section fold/unfold** - toggling a section active flag shows/hides its body
  - log: 2026-06-13 planned

## Policy config - validation (save rejected with message)

- [ ] **Reserved env var** - a reserved name (e.g. PATH / JUPYTERHUB_*) is rejected, `#config-error` shown
  - log: 2026-06-13 planned
- [ ] **Reserved api-keys target** - reserved pool target var rejected
  - log: 2026-06-13 planned
- [ ] **GPU incoherent** - access on, not-all, no device ids -> rejected
  - log: 2026-06-13 planned
- [ ] **Docker mutual exclusivity** - raw + limited in one group -> rejected
  - log: 2026-06-13 planned
- [ ] **Docker negative quota** - negative quota -> rejected
  - log: 2026-06-13 planned
- [ ] **Mem/CPU zero-when-enabled** - enabled with zero/blank value -> rejected
  - log: 2026-06-13 planned
- [ ] **Volume protected mountpoint** - mounting over /etc, /home etc. -> rejected
  - log: 2026-06-13 planned
- [ ] **Volume duplicate** - duplicate mountpoint or volume -> rejected
  - log: 2026-06-13 planned
- [ ] **API keys incomplete** - enabled pool missing mode/var/credentials -> rejected
  - log: 2026-06-13 planned

## Policy display

- [x] **Badges from policy_summary** - after an API config change the SPA row renders the server-sourced policy tag(s) (`CappedTags`)
  - log: 2026-06-13 implemented; 2026-06-18 SPA assertion (`test_group_create_badge_delete`, `test_multi_policy_badges`)
- [x] **No badges when inactive** - a group with no active policy shows the empty marker (no `.ant-tag`)
  - log: 2026-06-18 implemented (asserted before the first policy is set)
- [x] **Multiple badges** - a group with three active policies renders >= 3 inline tags (cap 4)
  - log: 2026-06-18 implemented (`test_multi_policy_badges`)
- [ ] **Hover tooltip** - the tag detail tooltip lists the valued policy line (hover; not asserted)
  - log: 2026-06-13 implemented (stock UI); 2026-06-18 the SPA tooltip is hover-only, not yet asserted
- [ ] **Badge per type** - each policy type shows its expected badge text
  - log: 2026-06-13 planned

## Policy resolution scenarios (multi-group)

- [ ] **Priority-wins (sudo/downloads)** - higher-priority configuring group wins (real-lab spawn assert)
  - log: 2026-06-13 planned
- [ ] **Biggest-wins (mem/cpu)** - largest enabled cap wins across groups
  - log: 2026-06-13 planned
- [ ] **OR-grant (gpu/docker)** - any granting group grants
  - log: 2026-06-13 planned
- [ ] **Section-off ignored** - an inactive section does not configure
  - log: 2026-06-13 planned
- [ ] **Env precedence** - higher-priority group env var wins; pool var vs plain var precedence
  - log: 2026-06-13 planned
- [ ] **Volume union** - mounts union across groups; conflict priority-wins
  - log: 2026-06-13 planned

## Spawn & lab lifecycle

- [x] **Spawn creates the container** - starting a server creates `jupyterlab-functestadmin`, inspected for policy effects (test_container_policy); the lab UI itself does not load under the minimal image, so no separate always-skip smoke
  - log: 2026-06-13 implemented (replaced the always-skip spawn smoke)
- [ ] **Spawn with overlay** - spawn-config overlay makes the minimal image spawn reliably
  - log: 2026-06-13 planned
- [ ] **Stop server** - stop returns to a stopped state
  - log: 2026-06-13 planned
- [ ] **Restart server** - one-click restart preserves the container
  - log: 2026-06-13 planned
- [ ] **Sudo applied (real-lab)** - resolved sudo reaches the lab as JUPYTERLAB_SUDO_ENABLE
  - log: 2026-06-13 planned
- [ ] **Env applied (real-lab)** - group env vars present in the lab environment
  - log: 2026-06-13 planned
- [ ] **Volume mounted (real-lab)** - group volume mounted at the configured path
  - log: 2026-06-13 planned
- [ ] **Edge: spawn failure surfaces** - an un-spawnable image shows a spawn error, not a hang
  - log: 2026-06-13 planned

## Spawned container - end-to-end policy application (docker inspect/exec)

The resolved policy *is* the container's create-time config (Env / Mounts /
HostConfig), set by DockerSpawner before the app starts - so these are
inspectable via the host docker socket regardless of the lab image.

- [x] **Container created** - spawning a member of a configured group creates `jupyterlab-<user>` (running)
  - log: 2026-06-13 planned; done (test_container_policy)
- [x] **Env: sudo** - container Env has `JUPYTERLAB_SUDO_ENABLE=<resolved>`
  - log: 2026-06-13 planned; done (test_container_policy)
- [x] **Env: group vars** - configured group env vars present in container Env
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **Env: reserved stripped** - reserved names never injected
  - log: 2026-06-13 planned
- [ ] **Env: GPU flags** - `ENABLE_GPU_SUPPORT` / `NVIDIA_VISIBLE_DEVICES` / `CUDA_VISIBLE_DEVICES` match the gpu policy
  - log: 2026-06-13 planned
- [ ] **Env: api-keys** - pool target vars present; two running containers never hold the same credential
  - log: 2026-06-13 planned
- [x] **Mounts: group volume** - the configured volume -> mountpoint appears in Mounts
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **Mounts: per-user volumes** - home/workspace/cache mounted
  - log: 2026-06-13 planned
- [ ] **Mounts: docker socket** - raw access mounts `/var/run/docker.sock`; limited mounts the proxy subpath + sets `DOCKER_HOST`
  - log: 2026-06-13 planned
- [x] **Limit: memory** - `HostConfig.Memory == cap` bytes; `MemorySwap` per swap policy
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **Limit: cpu** - `NanoCpus` / `CpuQuota` == ceil(cores)
  - log: 2026-06-13 planned
- [ ] **Privileged** - `HostConfig.Privileged` true only when granted
  - log: 2026-06-13 planned
- [ ] **Network** - attached to the test network; limited-docker hub-network visibility per flag
  - log: 2026-06-13 planned
- [x] **Labels: compose project** - `com.docker.compose.project` stamped on the lab
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **Labels: api-keys slot** - durable slot label present per pool
  - log: 2026-06-13 planned
- [ ] **Exec: sudo reality** - `exec` confirms sudo availability matches the policy
  - log: 2026-06-13 planned
- [ ] **Exec: mountpoint reality** - `exec` confirms the group mountpoint exists / is writable
  - log: 2026-06-13 planned
- [ ] **Negative: no group** - a member of no group gets defaults (no extra mounts, default sudo)
  - log: 2026-06-13 planned
- [ ] **Edge: leaving a group unmounts** - re-spawn after removal drops the group volume
  - log: 2026-06-13 planned

## Group policy -> container effect matrix (configured value -> asserted on the spawned container)

The core of the harness: for each policy value an admin can set on a group, spawn a member and assert the concrete effect on the container (via `docker inspect`/`exec`). Positive, negative, and boundary values each get a test.

- [ ] **sudo on** -> `JUPYTERLAB_SUDO_ENABLE=1` in Env
  - log: 2026-06-13 planned
- [x] **sudo off** -> `JUPYTERLAB_SUDO_ENABLE=0`
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **sudo unconfigured** -> platform default value
  - log: 2026-06-13 planned
- [x] **mem 4G** -> `HostConfig.Memory == 4*1024^3`
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **mem 4G + no-swap** -> `MemorySwap == Memory`
  - log: 2026-06-13 planned
- [ ] **mem disabled** -> no memory limit
  - log: 2026-06-13 planned
- [ ] **cpu 2** -> `NanoCpus == 2e9` (or CpuQuota/Period)
  - log: 2026-06-13 planned
- [ ] **cpu 2.5** -> ceil to 3 cores
  - log: 2026-06-13 planned
- [ ] **gpu all (gpu host)** -> `device_requests` Count -1, `NVIDIA_VISIBLE_DEVICES=all`
  - log: 2026-06-13 planned
- [ ] **gpu specific [0,2]** -> DeviceIDs [0,2], `NVIDIA_VISIBLE_DEVICES=0,2`, CUDA by uuid
  - log: 2026-06-13 planned
- [ ] **gpu none** -> `NVIDIA_VISIBLE_DEVICES=void`, no device_requests
  - log: 2026-06-13 planned
- [x] **env FOO=bar** -> `FOO=bar` in Env
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **env reserved (PATH)** -> not injected
  - log: 2026-06-13 planned
- [ ] **docker raw** -> `/var/run/docker.sock` mounted, no DOCKER_HOST
  - log: 2026-06-13 planned
- [ ] **docker limited** -> `DOCKER_HOST` set, proxy subpath mount, no raw socket
  - log: 2026-06-13 planned
- [ ] **docker privileged** -> `HostConfig.Privileged=true`
  - log: 2026-06-13 planned
- [x] **volume vol->/mnt/x** -> Mounts contains the named volume at /mnt/x
  - log: 2026-06-13 planned; done (test_container_policy)
- [ ] **api-keys pool** -> target var(s) set, durable slot label present
  - log: 2026-06-13 planned
- [ ] **downloads block** -> per-user CHP block routes registered (lab-extension effect out of scope minimal)
  - log: 2026-06-13 planned

### Combinations + multi-group resolution (asserted on the container)

- [ ] **All-policies group** -> one spawn reflects sudo+env+mem+cpu+gpu+docker+volumes+api-keys simultaneously
  - log: 2026-06-13 planned
- [ ] **Priority-wins** -> two groups configuring sudo/downloads: the higher-priority value lands in the container
  - log: 2026-06-13 planned
- [ ] **Biggest-wins** -> two groups capping mem/cpu: the larger cap lands in the container
  - log: 2026-06-13 planned
- [ ] **OR-grant** -> two groups, only one grants gpu/docker: the grant lands
  - log: 2026-06-13 planned
- [ ] **Section toggled off** -> turning a section off then re-spawning drops that effect from the container
  - log: 2026-06-13 planned
- [ ] **Membership change** -> adding/removing the user from a group changes the next spawn's container config
  - log: 2026-06-13 planned

## Server lifecycle control

- [ ] **Spawn via UI** - start server from the UI
  - log: 2026-06-13 planned
- [ ] **Spawn via API** - start server via the API
  - log: 2026-06-13 planned
- [ ] **Stop** - stop removes the container
  - log: 2026-06-13 planned
- [ ] **Restart preserves container** - restart keeps the same container (no recreate)
  - log: 2026-06-13 planned
- [ ] **Concurrent users** - two users spawn distinct containers
  - log: 2026-06-13 planned
- [ ] **Edge: re-spawn picks up new policy** - changing the group then re-spawning re-applies config
  - log: 2026-06-13 planned

## Idle culling

- [ ] **Idle culled** - an idle server is stopped after a short test timeout
  - log: 2026-06-13 planned
- [ ] **Active not culled** - an active server survives the interval
  - log: 2026-06-13 planned
- [ ] **Extension delays cull** - a granted extension delays culling
  - log: 2026-06-13 planned
- [ ] **Culled container removed** - the lab container is gone after culling
  - log: 2026-06-13 planned

## Logs

- [ ] **Resolution log** - the hub log shows the per-spawn groups/policy resolution line
  - log: 2026-06-13 planned
- [ ] **Policy apply logs** - api-keys assignment / docker-proxy / downloads-route lines appear per policy
  - log: 2026-06-13 planned
- [ ] **Spawn failure logged** - a failed spawn logs the cause
  - log: 2026-06-13 planned
- [ ] **Lab logs retrievable** - the spawned container logs are fetchable and show startup
  - log: 2026-06-13 planned

## Activity reporting

- [ ] **Active server reported** - a running server appears in activity data within the sample interval
  - log: 2026-06-13 planned
- [ ] **Resource stats** - CPU/memory for the running lab report back to the hub
  - log: 2026-06-13 planned
- [ ] **Stopped drops out** - a stopped server leaves the active set
  - log: 2026-06-13 planned
- [ ] **Manual sample** - a manual sample updates the data immediately
  - log: 2026-06-13 planned

## Limits enforcement (real effect)

- [ ] **Memory OOM** - in-container stress beyond the cap is OOM-limited
  - log: 2026-06-13 planned
- [ ] **CPU throttle** - in-container CPU beyond the cap is throttled
  - log: 2026-06-13 planned
- [ ] **Volume quota warning** - exceeding the volume/container-size threshold raises the activity warning
  - log: 2026-06-13 planned

## GPU auto-detection (GPU host only)

- [x] **Auto-detect enables on GPU host** - `make test-functional` auto-detects a host GPU, sets `JUPYTERHUB_GPU_ENABLED=2`, and the test asserts the hub `[GPU debug]` line reports `detected=1 enabled=1` with GPUs enumerated
  - log: 2026-06-13 implemented (runs for real on a GPU host)
- [x] **Deselected on CPU host** - no GPU -> the gpu test is deselected (not collected), no skip noise and no CUDA pull
  - log: 2026-06-13 implemented (conftest pytest_collection_modifyitems)
- [ ] **GPU policy spawn (GPU host)** - a gpu-access group member spawns with `device_requests` and `NVIDIA_VISIBLE_DEVICES` set
  - log: 2026-06-13 planned
- [ ] **Specific-GPU selection (GPU host)** - a device-id subset reaches the container env
  - log: 2026-06-13 planned

## Self-service

- [ ] **Manage volumes list** - the volume reset UI lists home/workspace/cache
  - log: 2026-06-13 planned
- [ ] **Manage volumes reset** - selected volume reset works (server stopped)
  - log: 2026-06-13 planned
- [ ] **Restart server (self)** - user restarts own running server
  - log: 2026-06-13 planned
- [ ] **Session extend** - idle session extend updates the remaining time
  - log: 2026-06-13 planned
- [ ] **Edge: manage volumes blocked while running** - reset refused while the server runs
  - log: 2026-06-13 planned

## Notifications broadcast

- [ ] **Page renders form** - message field, type selector, auto-close toggle
  - log: 2026-06-13 planned
- [ ] **Char limit** - 140-char limit + live counter
  - log: 2026-06-13 planned
- [ ] **Broadcast no servers** - sending with no active servers reports zero deliveries
  - log: 2026-06-13 planned
- [ ] **Broadcast delivery (real-lab)** - active lab with the extension receives the toast; per-user status shown
  - log: 2026-06-13 planned
- [ ] **Edge: extension missing** - server without the extension reports "not installed"
  - log: 2026-06-13 planned

## Settings

- [ ] **Settings list** - settings render from the dictionary
  - log: 2026-06-13 planned
- [ ] **Edit setting** - changing a setting persists
  - log: 2026-06-13 planned
- [ ] **Hidden secrets** - admin-password-style settings absent from the page
  - log: 2026-06-13 planned

## Activity monitor

- [ ] **Activity data** - the activity page shows user rows / data
  - log: 2026-06-13 planned
- [ ] **Resource stats** - CPU/memory/status columns populate
  - log: 2026-06-13 planned
- [ ] **Reset** - reset clears activity samples
  - log: 2026-06-13 planned
- [ ] **Manual sample** - trigger a sample updates the data
  - log: 2026-06-13 planned

## Lab-extension features (real-lab; out of scope for the minimal run)

- [ ] **Download blocked** - a download-blocked user gets 403 on the download surfaces
  - log: 2026-06-13 planned
- [ ] **Download toast** - a blocked attempt pushes a notification toast
  - log: 2026-06-13 planned
- [ ] **Download allowed** - an allowed user downloads normally
  - log: 2026-06-13 planned
- [ ] **Favicon proxy** - custom favicon served through the per-user CHP route
  - log: 2026-06-13 planned
- [ ] **Inline view allowed** - inline image/media still served to a blocked user
  - log: 2026-06-13 planned

## Abuse protection & ops

- [x] **Health endpoint** - /hub/health returns 200 JSON
  - log: 2026-06-13 implemented
- [ ] **Rate limit** - exceeding the ingress rate returns 429 (needs Traefik; out of scope minimal)
  - log: 2026-06-13 planned
- [ ] **Concurrent spawn limit** - spawn-storm protection caps simultaneous spawns
  - log: 2026-06-13 planned
- [ ] **Idle culler** - an idle server is culled after the timeout
  - log: 2026-06-13 planned

## Teardown verification

- [x] **No containers left** - after a run, no `stellars-functest` or spawned `jupyterlab-functestadmin` containers remain
  - log: 2026-06-13 implemented
- [x] **No network left** - `stellars-functest_network` removed
  - log: 2026-06-13 implemented
- [x] **No volumes left** - project + spawned per-user volumes removed
  - log: 2026-06-13 implemented
- [x] **Pulled images removed** - singleuser + Playwright images removed (unless KEEP_IMAGES)
  - log: 2026-06-13 implemented
- [x] **Hub image intact** - the image under test is not removed
  - log: 2026-06-13 implemented
- [ ] **Teardown asserted in-suite** - a final check confirms zero trace (or a separate verify step)
  - log: 2026-06-13 planned

## API (endpoints the harness exercises)

- `GET /hub/health` -> 200 JSON (unauthenticated)
- `GET /hub/api/admin/groups` -> groups list + `policy_summary`
- `POST /hub/api/admin/groups/create` -> create
- `PUT /hub/api/admin/groups/{name}/config` -> save policy; 400 on reserved/invalid
- `POST /hub/api/admin/groups/reorder` -> priority
- `DELETE /hub/api/admin/groups/{name}/delete` -> delete
- `POST /hub/api/notifications/broadcast` -> broadcast; `GET /hub/api/notifications/active-servers`
- `DELETE /hub/api/users/{name}/manage-volumes`; `POST /hub/api/users/{name}/restart-server`
