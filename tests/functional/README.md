# Functional Test Harness

A standing functional regression harness for the whole deployment. It boots the
actual built hub image in a fully isolated throwaway compose project and drives
the running platform end-to-end - UI actions and multi-step scenarios - with
Playwright. Its purpose is to validate **future fundamental rebuilds** (major
version jumps, base-image / JupyterHub upgrades, architectural changes): after a
deep rebuild, `make test-functional` confirms the platform still works.

## Local only

GitHub-hosted runners cannot run this DockerSpawner container deployment, so the
harness is never wired into CI. The fast pytest unit suites
(`optimum-hub-services`, `stellars-docker-proxy`) cover CI; this covers the
running system locally.

## Isolation

Nothing here touches a real deployment:

- **Own compose project** - `stellars-functest`
- **Own network** - `stellars-functest_network` (spawned labs join only this)
- **Project-namespaced volumes** - no shared `jupyterhub_*` names
- **Dedicated admin** - `functestadmin` (no clash with a real `admin`)
- **No host port** - the containerized Playwright runner reaches the hub by
  service name on the test network; the operator's `:8000` is never bound

## Teardown

After the run (pass **or** fail), the harness removes everything it created -
containers, spawned labs, the network, and all volumes. The pulled test images
(`quay.io/jupyterhub/singleuser`, the Playwright runner) are **kept** to avoid
wasteful re-pulls on the next run; the hub image under test is never touched.
`make test-functional` always cleans up; `make test-functional-clean`
force-cleans a leftover harness. Add `REMOVE_IMAGES=1` to also drop the pulled
images.

## Run

```bash
make build            # or reuse the current stellars/stellars-jupyterhub-ds:latest
make test-functional  # boot -> run -> full teardown
```

`KEEP_IMAGES=1 make test-functional` skips removing the pulled test images (faster
re-runs during development).

## Layout

- `compose.functional.yml` - the isolated hub + Playwright runner stack
- `conftest.py` - fixtures: hub-health wait, `base_url`, `admin_creds`,
  `admin_page` (logged-in admin). The fresh-DB + bootstrapped admin per run is
  the baseline initial state; add seed/clean fixtures here as scenarios grow
- `test_hub_ui.py` - single UI actions (login, branding, the group/policy page,
  settings/activity/notifications, health)
- `test_scenarios.py` - multi-step operator scenarios (configure several policies
  and verify badges + tooltip, reorder priority). Add new scenarios here
- `test_spawn_smoke.py` - best-effort lab spawn (skipped if the minimal image
  does not spawn cleanly)

## Coverage boundary

Lab-extension-dependent UI (download-block 403 + toast, favicon CHP proxy,
notification ingest) needs the real `stellars-jupyterlab-ds` image, not the
minimal one, and is out of scope here.
