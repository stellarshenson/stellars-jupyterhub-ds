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
(`duoptimum-hub-services`, `duoptimum-docker-proxy`) cover CI; this covers the
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
`make test-functional` always cleans up; `tests/functional/run.sh clean`
force-cleans a leftover harness. Add `REMOVE_IMAGES=1` to also drop the pulled
images.

## Run

```bash
make build                       # or reuse the current stellars/duoptimum-hub:latest
make test-functional             # EVERY regime (signup, gpu, env, signup-open, signup-bootstrap) one by one
tests/functional/run.sh signup   # a SINGLE regime; 'clean' tears down a leftover harness
```

`REMOVE_IMAGES=1 make test-functional` also drops the pulled test images
(`quay.io/jupyterhub/singleuser`, the Playwright runner); by default they are kept
for faster re-runs.

## Setups (initial conditions)

Each setup is a distinct initial condition with its own compose override and
pytest regime; `make test-functional` runs them all in turn (cleaning between
each), or `tests/functional/run.sh <regime>` runs one:

- **signup** (`run.sh signup`) - fresh DB, signup off; the admin is created
  through the bootstrap-signup window. Runs the full SPA UI suite + container policy
- **gpu** (`run.sh gpu`) - GPU autodetect via a mock gpuinfo sidecar (any host); the GPU display tests
- **env** (`run.sh env`) - signup off + `JUPYTERHUB_ADMIN_PASSWORD`;
  restart-to-provision seeds the admin. One focused env-password login test
- **signup-open** (`run.sh signup-open`) - signup enabled; the admin is
  env-provisioned, then a non-admin self-signs-up and the admin authorises via the SPA
- **signup-bootstrap** (`run.sh signup-bootstrap`) - signup enabled, NO env password;
  the admin self-signs-up and is auto-authorised

## Layout

- `compose.functional.yml` + `compose.functional-env.yml` + `compose.functional-signup-open.yml`
- `conftest.py` - fixtures: hub-health wait, admin bootstrap, `admin_api`,
  cookie-injected `admin_page` / `admin_portal` (the SPA driver), `signup_user`,
  `clean_groups`, `docker_client`, and the regime deselection hook
- `test_hub_ui.py` - login shell + per-page SPA render smoke
- `test_scenarios.py` - SPA group lifecycle (create, policy badges, reorder, delete)
- `test_events.py` - event-log render + clear-log flow
- `test_container_policy.py` - group config asserted on the spawned container
- `test_signup_open.py` - signup-open self-signup + admin authorise (regime-gated)
- `test_gpu_detection.py` / `test_auth_env_mode.py` - conditional GPU and env-auth tests

## Acceptance-criteria coverage

Every functional test declares the acceptance criteria it covers with
`@pytest.mark.acc_crit("<doc-slug>::<label>", ...)`, referencing labelled items in
`docs/acc-crit-<doc-slug>.md`. The declaration is mandatory - a collected test with
no `acc_crit` marker aborts the run. At the end of each run the suite prints an
`acceptance criteria coverage` report listing every declared criterion as `MET`
(every covering test that ran passed) or `UNMET` (a covering test failed), so a run
states which criteria it actually met.

## How the SPA is driven

The portal is a React single-page app with no data-testids; tests use visible
text, antd roles (`aria-label`), and placeholders. A direct GET of `/hub/login`
self-redirects, so the browser is authenticated by injecting the API session's hub
cookies; readiness waits on the `.ant-layout` shell, never `networkidle`.

## Coverage boundary

Lab-extension-dependent UI (download-block 403 + toast, favicon CHP proxy,
notification ingest) needs the real `stellars-jupyterlab-ds` image, not the
minimal one, and is out of scope here.
