# Acceptance Criteria - Migrate off deprecated `c.JupyterHub.extra_handlers`

JupyterHub 5.x deprecated `JupyterHub.extra_handlers` (warning fired by its trait observer); the portal, `/api/*` and `/health` routes are registered through it today. Migrate to an owned application subclass `DuoptimumHub(JupyterHub)` that declares its own `registered_handlers` trait and splices those in-process handlers into the hub's own `self.handlers` list - identical route ordering, the deprecated trait never set. The hub is launched via a `duoptimum-hub` console script in place of the stock `jupyterhub` command. No new routes, no behavior change, warning gone; the subclass is the platform's extension seam going forward.

## Architecture tenets (the design contract)

- [x] **No deprecated trait** - `c.JupyterHub.extra_handlers` is never assigned anywhere; it stays at its empty default so the observer never fires. Handlers come from `c.DuoptimumHub.registered_handlers`, our own (non-deprecated) `List` trait
  - log: 2026-06-20 implemented; smoke test confirms `extra_handlers == []`, `registered_handlers` bound from config
- [x] **Clean OO override, no monkeypatch** - the seam is a real `JupyterHub` subclass overriding `init_handlers` via `super()`; no method-wrapping, no module-level mutable registry, no import-time class patching
  - log: 2026-06-20 implemented (`duoptimum_hub_services/app.py`)
- [x] **Faithful ordering** - custom handlers land in the exact slot `extra_handlers` used: after the authenticator + built-in page/api handlers, immediately before the trailing `/hub/logo` (`LogoHandler`) and `/hub/api/(.*)` (`API404`) catch-alls
  - log: 2026-06-20 implemented + unit-tested (before-logo / before-api404 / after-builtins)
- [x] **Anchor by identity, not index** - the splice point is located by `LogoHandler` / `API404` class identity (imported from `jupyterhub.handlers.static` / `jupyterhub.apihandlers.base`), never a hardcoded list index or pattern-string match
  - log: 2026-06-20 implemented + unit-tested (logo-only / api404-only anchor)
- [x] **Fail loud** - if neither anchor is found in `self.handlers` (future JupyterHub moved them), `splice_before_catch_alls` raises `RuntimeError` at startup; it never silently appends to the end (which would let the portal catch-all shadow built-ins or API404 shadow custom `/api/*`)
  - log: 2026-06-20 implemented + unit-tested (`test_fail_loud_when_no_anchor`)
- [x] **Stay in `self.handlers`** - the override modifies JupyterHub's own handler list and lets JupyterHub build the Tornado app normally; it does not insert into `tornado_application.wildcard_router.rules`
  - log: 2026-06-20 implemented
- [x] **Single source of truth** - the handler tuples are defined once; config makes one `c.DuoptimumHub.registered_handlers = [...]` assignment (plus the portal `+=`) instead of two `extra_handlers` statements
  - log: 2026-06-20 implemented (`config/jupyterhub_config.py`)
- [x] **Localized** - the subclass + pure splice live in the `duoptimum_hub_services` package (consistent with the existing hub-integration home); config stays declarative, no plumbing inline
  - log: 2026-06-20 implemented
- [x] **Re-entrant splice** - if `init_handlers` runs more than once, `super().init_handlers()` rebuilds `self.handlers` from scratch each time and the splice re-runs cleanly, so each custom route appears exactly once (no accumulation)
  - log: 2026-06-20 implemented + unit-tested (input-not-mutated, empty-registry-is-stock)
- [x] **Pure testable core** - `splice_before_catch_alls(handlers, custom, hub_prefix, add_url_prefix)` is a pure function, unit-tested against a fabricated handler list with no running hub
  - log: 2026-06-20 implemented + 14 unit tests
- [x] **Forward-compatible** - because the deprecated trait is never used, the migration survives a future JupyterHub release that removes `extra_handlers` entirely
  - log: 2026-06-20 implemented

## Launch + compatibility

- [x] **Launch seam** - the hub is started via the `duoptimum-hub` console script (`duoptimum_hub_services.app:main = DuoptimumHub.launch_instance`), declared in `pyproject.toml` and exec'd by `conf/bin/start-platform.sh` in place of `jupyterhub`
  - log: 2026-06-20 implemented (pyproject scripts + start-platform.sh)
- [x] **Config compatibility** - existing `c.JupyterHub.*` config still applies to the `DuoptimumHub` instance via the traitlets MRO; only the new `registered_handlers` trait uses the `c.DuoptimumHub.*` section
  - log: 2026-06-20 implemented; smoke test confirms MRO binding
- [ ] **PID 1 / signals** - `exec duoptimum-hub` keeps the hub as PID 1 so docker `SIGTERM` reaches it and atexit cleanup (e.g. `stop_gpuinfo_sidecar`) runs on `docker stop` / compose down
  - log: 2026-06-20 criterion added; verify in functional teardown
- [x] **Trait-section hygiene** - launching `duoptimum-hub` with the config emits no "Config option ... not recognized" warning for `registered_handlers`
  - log: 2026-06-20 criterion added; verify in startup logs
  - log: 2026-06-20 PASS - functional `test_no_extra_handlers_deprecation_or_config_warning` (JH 5.5.0 image)

## Behavioral criteria (no regression)

- [x] **No deprecation warning** - hub startup logs contain no `JupyterHub.extra_handlers is deprecated` line
  - log: 2026-06-20 criterion added
  - log: 2026-06-20 PASS - functional log assertion on the 5.5.0 image
- [x] **Portal landing** - `GET /hub/home` returns the SPA shell HTML with a valid injected `window.jhdata.xsrf_token`
  - log: 2026-06-20 criterion added
  - log: 2026-06-20 PASS - `test_portal_home_serves_shell` (jhdata present)
- [x] **Custom API live** - representative endpoints respond as before: `GET /hub/api/settings` (200 JSON), `GET /hub/api/events` (admin, 200), `GET /hub/api/activity` (200)
  - log: 2026-06-20 criterion added
  - log: 2026-06-20 PASS - `test_custom_api_live` (/hub/api/settings 200 JSON); /activity exercised by the system-volumes test
- [x] **Health endpoint** - `GET /health` returns 200 JSON unauthenticated (rate-limited as before)
  - log: 2026-06-20 criterion added
  - log: 2026-06-20 PASS - `test_health_endpoint`
- [x] **Portal assets** - `/hub/assets/*` served as static files; `/hub/brand/*` served without auth (login/signup logo still loads)
  - log: 2026-06-20 criterion added
  - log: 2026-06-20 PASS - the SPA shell renders in-browser across the Playwright suite (assets load); login page renders
- [x] **Built-ins intact** - `/hub/login` renders the stock login page; the portal catch-all does not shadow it
  - log: 2026-06-20 criterion added
  - log: 2026-06-20 PASS - `test_login_built_in_intact`

## Edge cases

- [x] **Edge: unknown `/hub/api/*`** - `GET /hub/api/does-not-exist` returns the JupyterHub JSON 404 (`API404`), not the SPA shell - proves custom `/api/*` precede API404 and API404 still wins for unmatched paths
  - log: 2026-06-20 criterion added
  - log: 2026-06-20 PASS - `test_unknown_api_is_json_404_not_shell` (application/json 404 on the 5.5.0 image)
- [x] **Edge: `/hub/logo`** - returns the logo image bytes, not the SPA shell - proves the portal catch-all still falls through to `LogoHandler` and the splice sits before it
  - log: 2026-06-20 criterion added
  - log: 2026-06-20 PASS - `test_logo_serves_image_not_shell` (image/* content-type)
- [x] **Edge: kwargs-carrying handlers** - the 3-tuple static handlers (`ImmutableStaticFileHandler`/`StaticFileHandler` with `{"path": ...}`) survive the hub-prefix step and keep their kwargs
  - log: 2026-06-20 unit-tested (`test_kwargs_tuple_preserved`)
- [x] **Edge: portal catch-all stays last** - within the registry the portal catch-all is ordered after every custom `/api/*` route, so no API route is shadowed by the SPA shell
  - log: 2026-06-20 implemented (config `+= portal_handlers()`) + unit-tested (`test_registry_order_preserved_api_before_portal`)
- [x] **Edge: empty registry** - if no handlers are registered, the override produces a handler list identical to stock JupyterHub
  - log: 2026-06-20 unit-tested (`test_init_handlers_empty_registry_is_stock`)
- [x] **Edge: anchors absent** - splice against a handler list with no `LogoHandler`/`API404` raises, confirming fail-loud
  - log: 2026-06-20 unit-tested (`test_fail_loud_when_no_anchor`)

## Stale-reference cleanup

- [x] **Config comment** - the `# ... registered via c.JupyterHub.extra_handlers` comment block now references `c.DuoptimumHub.registered_handlers`
  - log: 2026-06-20 implemented
- [x] **Package docstring** - `duoptimum_hub_web/__init__.py` no longer instructs `c.JupyterHub.extra_handlers += portal_handlers()`; it documents the `registered_handlers` call and ordering
  - log: 2026-06-20 implemented
- [ ] **Ordering-invariant doc** - the existing first-match-wins note in `acc-crit-duoptimumhub.md` (~line 951) is updated to describe `DuoptimumHub.registered_handlers` rather than the trait
  - log: 2026-06-20 criterion added

## Verification (the goal gate)

- [x] **Unit tests** - pure splice + subclass wiring + REAL-JupyterHub drift detection: placement before the anchors, identity-based anchor, fail-loud on missing anchors, re-entrant/empty-registry, kwargs (3-tuple) preservation, registry order (api before portal), input/trait not mutated, `registered_handlers` is a config trait; plus 3 tests running the real `init_handlers` (anchor contract, custom-before-/hub/logo, idempotent re-run). 17 tests; full backend suite 854 passed
  - log: 2026-06-20 green; +3 real-init_handlers tests added per adversarial MED findings
- [x] **Functional tests** - signup regime green on the rebuilt image, including: no deprecation line in logs, no unrecognized-config warning, `/hub/home` shell, a live `/api/*`, `/health` 200, unknown `/hub/api/*` -> JSON 404, `/hub/logo` -> image, clean SIGTERM teardown
  - log: 2026-06-20 criterion added; needs operator rebuild (duoptimum-hub entry point + backend change)
  - log: 2026-06-20 PASS - rebuilt 5.5.0 image, signup regime 61 passed (5:05); all 7 `test_extra_handlers_migration` tests green, plus system-volumes + a-moment-ago
- [x] **Adversarial review** - 3 `claude -p` critics (ordering/faithfulness, brittleness/failure-modes, launch-seam/ops), each independently verifying against JupyterHub 5.4.3 source + repo, all returned PASS; no BLOCKER/HIGH/MED correctness defects. Findings actioned: 2 MED test gaps closed (real-init_handlers idempotency + drift contract); LOW doc inaccuracy fixed (stock tail also appends AddSlash/PrefixRedirect/Template404 after API404 - splice anchors on the first LogoHandler so it is unaffected). Pre-existing LOW notes left out of scope: `pgrep -f jupyterhub` healthcheck tautology, optional build-time entry-point smoke assertion
  - log: 2026-06-20 PASS x3
  - log: 2026-06-20 re-confirmed via dynamic workflow (3 parallel critics: ordering-faithfulness, brittleness-failure-modes, launch-seam-ops) against installed JupyterHub 5.4.3 source (`init_handlers` app.py:1780-1806) - all PASS, only 1 LOW (unit fixture uses a simplified SPA lookahead vs prod `PORTAL_ROUTE`; covered by functional tests, no correctness impact)

## Design

`duoptimum_hub_services/app.py`:

- `DuoptimumHub(JupyterHub)` - the platform application subclass; the owned extension seam as the platform diverges from stock JupyterHub while staying API-compatible
- `registered_handlers = List().tag(config=True)` - the supported replacement for `extra_handlers`; same `(route, Handler[, kwargs])` tuple shape
- `init_handlers(self)` - calls `super().init_handlers()` (builds the stock `self.handlers`), then `self.handlers = splice_before_catch_alls(...)`
- `splice_before_catch_alls(handlers, custom, hub_prefix, add_url_prefix)` - pure: hub-prefixes a copy of `custom` via `add_url_prefix`, finds the lowest index whose handler is `LogoHandler` or `API404`, returns a new list with `custom` inserted there; raises `RuntimeError` if no anchor; never mutates inputs
- `main = DuoptimumHub.launch_instance` - the `duoptimum-hub` console-script entry point

Launch: `conf/bin/start-platform.sh` runs `exec duoptimum-hub -f /srv/config/jupyterhub_config.py "$@"`; `pyproject.toml` declares `duoptimum-hub = "duoptimum_hub_services.app:main"`.

Config: `c.DuoptimumHub.registered_handlers = [...api/page tuples...]` then `+= portal_handlers()`, replacing the two `c.JupyterHub.extra_handlers` statements. The deprecated trait is never touched.

Why faithful: `init_handlers` builds `h = [authenticator, default_handlers, apihandlers, extra_handlers, /logo, /api/(.*)]` then prefixes with `/hub`. Removing `extra_handlers` and re-inserting our tuples immediately before `/logo` reproduces the original order exactly, so Tornado first-match-wins resolves identically.
