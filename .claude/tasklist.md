# Task List - Duoptimum Hub (persisted for recovery)

Reopen this to resume. Reconciled 2026-06-21 (v4.0.12). Current work = DEF-22 redeploy-proof
hub connect URL + spawned-lab role label; journal entry #396.

## Goal gate (this session, Stop-hook)

All tasks complete; solutions survive `claude -p` adversarial checks; acc-crit updated; unit
tests updated + functional tests added and executed; `make rebuild` succeeds; `../stop.sh &&
../start.sh` gives a good working system; live + functional checks confirm.

## Current scope

1. **DEF-22** - `c.JupyterHub.hub_connect_url` baked the hub's ephemeral container id
   (`socket.gethostname()`) into each lab's `JUPYTERHUB_API_URL`; a hub redeploy stranded
   running labs with "Name or service not known". Fix: host = `JUPYTERHUB_LABEL_CONTAINER_ROLE_HUB`
   ('hub'), stamped by compose as a `hub_network` alias + `hub.container.role` label.
2. **Lab role label** - `pre_spawn_hook` stamps `hub.container.role=lab`
   (`JUPYTERHUB_LABEL_CONTAINER_ROLE_LAB`) on every spawned lab, discoverable by role like the
   hub + gpuinfo sidecar.

## Done

- [x] **Code (both)** - `config/jupyterhub_config.py` (`_HUB_HOST` = role-hub var, boot-time
  `gethostbyname` fail-loud `log.error`, hook wiring), `hooks.py` (role-label block independent
  of compose-project grouping), `config_validator.py` (`hub_container_role_label` +
  `lab_container_role_label` required), `Dockerfile.jupyterhub`, `compose.yml` (env + label +
  `hub_network` alias), `settings_dictionary.yml`, functest `compose.functional.yml` (hub alias)
- [x] **Unit tests** - `test_config_validator.py` fixture + parametrize both new vars; suite green (902 + 65)
- [x] **Functional tests written** - new `test_hub_connect_url.py` (label + alias + DNS + :8080);
  `test_container_policy.py` binding assert (lab `JUPYTERHUB_API_URL` host + `hub.container.role=lab`)
- [x] **Adversarial review** - `claude -p` 2 rounds -> FIXES-SOUND; MAJORs fixed (test binds to
  the changed line; boot-time fail-loud added)
- [x] **acc-crit** - "Redeploy-proof hub connect URL" + hub/lab "container by role" criteria
  (checkboxes `[ ]` pending live verify)
- [x] **DEF-22 registered** - `defects-duoptimumhub.md` + Contents
- [x] **make rebuild** - `stellars/duoptimum-hub:latest` v4.0.12 (no bump); `logs/rebuild-role-hub-lab.log`
- [x] **Journal** - entry #396

## Functional run findings (2026-06-21)

- `test_container_policy.py::test_policies_applied_to_container` PASSED - STRONG end-to-end proof:
  the spawned lab's `JUPYTERHUB_API_URL` host = `hub` AND it carries `hub.container.role=lab`
- `test_hub_connect_url.py` - 3/4 passed (alias present, alias resolves to hub IP, :8080 reachable);
  `test_hub_carries_container_role_label` FAILED (`assert None == 'hub'`) - functest hub lacked the
  `hub.container.role=hub` LABEL (I added it to production `compose.yml` but forgot `compose.functional.yml`)
- FIX APPLIED: added `labels: hub.container.role: "hub"` to the functest hub in `compose.functional.yml`;
  signup regime re-running to confirm (`logs/functest-role-hub-lab-signup.log`)
- `test_role_labels.py` all PASSED

## Open (resume here)

- [ ] **Confirm signup re-run green** - after the `compose.functional.yml` label fix; expect all 4
  `test_hub_connect_url.py` + `test_container_policy.py` PASS (api-keys still fails, see below).
  Then optionally `bash tests/functional/run.sh traefik` + `... gpu` for full coverage
- [ ] **Live redeploy** - `cp compose.yml ../compose.yml` (FIRST - start.sh uses on-disk copy),
  then `../stop.sh && ../start.sh`; log `logs/redeploy-role-hub-lab-*.log`
- [ ] **Live verification** - hub reachable (`curl -k -H 'Host: jupyterhub.lab.stellars-tech.eu'
  https://localhost/hub/health` -> 200); `docker inspect <hub>` shows `hub` alias on hub_network +
  `hub.container.role=hub`; spawn a lab -> `JUPYTERHUB_API_URL=http://hub:8080/...` + `hub.container.role=lab`;
  pre-fix labs need ONE respawn
- [ ] **Flip acc-crit + DEF-22 to done** - mark criteria `[x]` and DEF-22 `[x]` / Contents "- fixed" after live verify

## Known issue surfaced (NOT this change)

- [ ] **`test_api_keys_import.py::test_import_single_keys_from_file` FAILS** post-rebuild - the
  #395 import-popup rework, first tested against a rebuilt image now (#393-#395 frontend changes
  were committed but never rebuilt). Likely the test wasn't updated for the popup flow, or a real
  popup bug. Investigate next session - unrelated to DEF-22 / lab role label

## Carried-forward open drift (prior sessions)

- acc-crit "## Traefik backend network binding" still says the `traefik.docker.network` pin is
  REQUIRED - STALE after `59502ba`/#422 removed it (Option A dual-home); rewrite offered, awaiting go-ahead
- acc-crit "Label namespace (prefix)" + project CLAUDE.md still cite `duoptimum-hub.*` keys; code/compose
  use bare `hub.` (e.g. `hub.container.role`)
- DEF-21 ux-review minors: degraded-5xx copy reads "Not responding"; uncapped elapsed + nowrap pill
  can crowd the breadcrumb; two warning visual languages
- pre-existing mount-path drift: `test_lab_setup_system_volumes.py:50` `/run/dockersock` vs compose
  `/var/run/docker-proxy-sockets`

## Notes / decisions

- Config is bind-mounted in production but BAKED in the functest image - rebuild required for
  functional tests to see new ENV defaults + config
- `make rebuild` does NOT bump the version (only `make build` / `rebuild_increment_version` do)
- Redeploy rule: always `cp compose.yml ../compose.yml` BEFORE `../stop.sh && ../start.sh`
- Git: no commit/push without explicit per-action approval; current branch `feature/new-frontend-mock`
