# Task List - Duoptimum Hub session (persisted for recovery)

Mirrors the harness task list (#396-#423). Single source of truth for open vs done; reconciled 2026-06-21 (post network-fix commit).

Goal gate (this session): all tasks complete; solutions survive adversarial `claude -p`/skill checks; acc-crit updated; tests updated/added and green; `make rebuild` succeeds; redeploy yields a good live system; live + functional checks confirm.

HEAD: `59502ba` (pushed, `feature/new-frontend-mock` -> github). Wrapper repo `main` at `e0bfe4d` (-> gitlab).

## Uncommitted (working tree - awaiting rebuild + commit approval)
- [x] #408 docker resource tester `test_docker_resources.py` (untracked) - names/labels/characteristics, default regime
- [x] #411 API keys import-from-file - `GroupPolicyTab.tsx` (`parseApiKeysFile` + Import button) + `test_api_keys_import.py` (untracked); acc-crit AC-4a
- [x] #421 per-key Description removed from API keys pool (`GroupPolicyTab.tsx`, `types.ts`, `mockSource.ts`); acc-crit AC-4
- [x] #423 terse hub-unreachable message, LEADS WITH the branding hub name (`hubName()` <- `JUPYTERHUB_BRANDING_HUB_NAME` via `window.jhdata`); `ConnectionStatusPill.tsx` (`downTitle()` + healthy tooltip), `HubConnectionIndicator.tsx` (`body()`); acc-crit Copy criterion; typecheck+lint green
- [x] acc-crit edits riding along (AC-4, AC-4a, #408 + #409 sections, Copy)
- NOTE the frontend edits (#411/#421/#423) bake into the bundle -> need a `make rebuild` before they show live; the two new functional tests are mounted (no rebuild)

## Pending (human)
- [ ] #400 visual sign-off of the unreachable state desktop + mobile (only-human; code-level UX review done)

## Committed + pushed
- [x] #422 traefik->hub network-name DECOUPLING (Option A): dropped the `traefik.docker.network` pin, dual-homed traefik on both hub nets so the backend IP is always reachable - name-free, no 504. `compose.yml` -> submodule `59502ba` (github); wrapper `compose_override.yml` -> `e0bfe4d` (gitlab); journal 392; validated read-only via `docker compose config`; no rebuild/redeploy
- [x] #396-#420 across `b64fb9d`..`914816e`: connection-indicator redesign (header pill, soft pulse, `downSince` elapsed, mobile panel, ux MAJORs); loguru + SQLAlchemy 2; `html_templates_enhanced` ELIMINATION + CLOSE-GAP cold-start redirect; Events "Clear"; antd sort-tooltip off + `COL_HELP` tooltips; theme scrollbars; functional suite (7 regimes). #409 investigation later SUPERSEDED by #422

## Open drift to resolve
- acc-crit "## Traefik backend network binding" (~L4543) still says the pin is REQUIRED - STALE after #422 removed it; rewrite to Option A (reachability-based, name-free) - offered, awaiting operator go-ahead
- DEF-21 ux-review minors: 5xx copy reads "Not responding"; uncapped elapsed + nowrap can crowd breadcrumb; two warning visual languages

## Deferred minors
- Dedicated per-page `COL_HELP` functional checks (feature done; CPU/MEM covered in `test_servers_resources.py`)
- loguru "None -" logger name on config-emitted lines (exec'd config has no `__name__`; needs rebuild)
- Project CLAUDE.md env docs still cite `duoptimum-hub.*` keys (doc-only)
- pre-existing mount-path drift: `test_lab_setup_system_volumes.py:50` `/run/dockersock` vs compose `/var/run/docker-proxy-sockets`

## Notes / decisions
- loguru over JupyterHub stdlib logger; Option A (convert our emitters) not InterceptHandler
- `html_templates_enhanced`: ELIMINATION framing - only basic JupyterHub framework persists; SPA owns every user/admin journey
- `hub.*` label namespace propagated forward to honor the rename
- #422 chose dual-home over a pin because Traefik's docker provider has NO label-based backend selector; lab isolation preserved (labs on `hub_network` only)
- `_screens/` (functional screenshots) root-owned by the test runner - excluded from commits (sudo rm or gitignore)
- Plan file `~/.claude/plans/majestic-percolating-sprout.md` = the #422 decoupling plan (approved + implemented)
