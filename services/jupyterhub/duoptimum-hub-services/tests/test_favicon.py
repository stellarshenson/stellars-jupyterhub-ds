"""Functional tests for FaviconRedirectHandler redirect mapping.

The handler is injected outside the /hub/ prefix and receives the favicon
filename (idle vs kernel-busy frames) from the CHP-proxied request. It maps the
idle frame to the hub's custom favicon and busy frames to the configured busy
target. Tornado's RequestHandler is constructed via __new__ so we can exercise
get() without a live Application/request.
"""

from duoptimum_hub_services.handlers.favicon import FaviconRedirectHandler


class _FakeApp:
    def __init__(self, base_url="/jupyterhub/"):
        self.settings = {"base_url": base_url}


def _make_handler(busy_target="", base_url="/jupyterhub/"):
    h = FaviconRedirectHandler.__new__(FaviconRedirectHandler)
    h.application = _FakeApp(base_url)
    h._busy_target = busy_target
    h.redirected_to = None

    def fake_redirect(url):
        h.redirected_to = url

    h.redirect = fake_redirect
    return h


class TestIdleFrame:
    def test_favicon_ico_redirects_to_hub_static(self):
        h = _make_handler()
        h.get("favicon.ico")
        assert h.redirected_to == "/jupyterhub/hub/static/favicon.ico"

    def test_idle_frame_ignores_busy_target(self):
        h = _make_handler(busy_target="hub/static/favicon-busy.ico")
        h.get("favicon.ico")
        assert h.redirected_to == "/jupyterhub/hub/static/favicon.ico"


class TestBusyFrames:
    def test_busy_frame_with_static_target_prepends_base_url(self):
        h = _make_handler(busy_target="hub/static/favicon-busy.ico")
        h.get("favicon-busy-1.ico")
        assert h.redirected_to == "/jupyterhub/hub/static/favicon-busy.ico"

    def test_busy_frame_with_url_target_redirects_to_url(self):
        h = _make_handler(busy_target="https://cdn.example.com/busy.ico")
        h.get("favicon-busy-2.ico")
        assert h.redirected_to == "https://cdn.example.com/busy.ico"

    def test_busy_frame_without_target_falls_back_to_idle(self):
        """If a busy frame reaches the handler but no busy override is set,
        fall back to the idle favicon rather than looping."""
        h = _make_handler(busy_target="")
        h.get("favicon-busy-3.ico")
        assert h.redirected_to == "/jupyterhub/hub/static/favicon.ico"


class TestBaseUrlVariants:
    def test_root_base_url(self):
        h = _make_handler(base_url="/")
        h.get("favicon.ico")
        assert h.redirected_to == "/hub/static/favicon.ico"


# ---------------------------------------------------------------------------
# No-flap regression tests
#
# The per-user favicon override is a CHP route registered in
# `proxy.extra_routes`. JupyterHub's periodic `check_routes()` rebuilds the set
# of expected routes from `extra_routes` keys verbatim and deletes any live CHP
# route whose routespec is not in that set. But `get_all_routes()` (via
# `_routespec_from_chp_path`) ALWAYS appends a trailing slash, so if we store the
# extra_routes key WITHOUT a slash the live route never matches and check_routes
# races to delete it every cycle - the favicon flaps and the lab's stock icon
# leaks through. The fix stores the key in `validate_routespec()` (trailing
# slash) form so the keys match and the route is stable.
# ---------------------------------------------------------------------------

FAVICON_ROUTESPECS = [
    "/user/konrad.jelen/static/favicons/favicon.ico",
    "/user/konrad.jelen/static/favicons/favicon-busy",
    "/jupyterhub/user/alice/static/favicons/favicon.ico",
]


def _new_proxy():
    """Real ConfigurableHTTPProxy instance - exercises the actual normalization
    helpers (validate_routespec / _routespec_to_chp_path / _routespec_from_chp_path)
    without starting the node subprocess."""
    from jupyterhub.proxy import ConfigurableHTTPProxy

    return ConfigurableHTTPProxy()


def _chp_roundtrip(proxy, routespec):
    """The routespec form `get_all_routes()` would return for a route we stored
    under `routespec` - i.e. what check_routes() compares against."""
    return proxy._routespec_from_chp_path(proxy._routespec_to_chp_path(routespec))


def _stale_after_check_routes(proxy, extra_routes_keys):
    """Faithful slice of Proxy.check_routes(): good_routes is built from the
    extra_routes keys verbatim; any live CHP route (the round-tripped form of
    each stored key) not present in good_routes is deleted as stale. Returns the
    set that would be deleted."""
    good_routes = set(extra_routes_keys)
    live_chp_routes = {_chp_roundtrip(proxy, k) for k in extra_routes_keys}
    return {rs for rs in live_chp_routes if rs not in good_routes}


class TestNoFlapInvariant:
    def test_canonical_key_matches_chp_roundtrip(self):
        """validate_routespec() output == the form get_all_routes() returns, so
        check_routes() never considers the route stale."""
        proxy = _new_proxy()
        for rs in FAVICON_ROUTESPECS:
            canonical = proxy.validate_routespec(rs)
            assert canonical == _chp_roundtrip(proxy, canonical)

    def test_unnormalized_key_would_flap(self):
        """Regression guard: the OLD behaviour (storing the raw, slash-less
        routespec) does NOT match the round-trip form, which is exactly what
        caused the flap. If this ever starts passing, the upstream slash
        handling changed and the fix may no longer be needed."""
        proxy = _new_proxy()
        for rs in FAVICON_ROUTESPECS:
            assert rs != _chp_roundtrip(proxy, rs)

    def test_canonical_keys_survive_check_routes(self):
        """With the fix (canonical keys) nothing is flagged stale."""
        proxy = _new_proxy()
        canonical = [proxy.validate_routespec(rs) for rs in FAVICON_ROUTESPECS]
        assert _stale_after_check_routes(proxy, canonical) == set()

    def test_unnormalized_keys_get_deleted_by_check_routes(self):
        """Without the fix every favicon route is deleted on each check_routes
        cycle - this is the flap, asserted explicitly."""
        proxy = _new_proxy()
        stale = _stale_after_check_routes(proxy, FAVICON_ROUTESPECS)
        # every raw key round-trips to a slashed form absent from good_routes
        assert len(stale) == len(FAVICON_ROUTESPECS)

    def test_validate_routespec_is_idempotent(self):
        """Re-normalizing an already-canonical key is a no-op, so repeated
        check_routes cycles keep the same stable key."""
        proxy = _new_proxy()
        for rs in FAVICON_ROUTESPECS:
            once = proxy.validate_routespec(rs)
            assert proxy.validate_routespec(once) == once


class TestHookWritesCanonicalRoutes:
    """Drive the real pre_spawn_hook favicon branch and assert the keys it writes
    into proxy.extra_routes are in canonical (non-flapping) form."""

    def _run_hook(self, monkeypatch, *, favicon_uri, favicon_busy_target, base_url):
        import asyncio
        import logging
        import types

        import jupyterhub.app as jha
        from jupyterhub.proxy import ConfigurableHTTPProxy

        from duoptimum_hub_services.hooks import make_pre_spawn_hook

        real_proxy = ConfigurableHTTPProxy()
        recorded_add = {}

        class _FakeProxy:
            def __init__(self):
                self.extra_routes = {}

            def validate_routespec(self, rs):
                return real_proxy.validate_routespec(rs)

            async def add_route(self, routespec, target, data):
                recorded_add[routespec] = target

        fake_proxy = _FakeProxy()
        fake_app = types.SimpleNamespace(
            base_url=base_url,
            _favicon_handler_injected=True,  # skip Tornado handler injection
            hub=types.SimpleNamespace(url="http://jupyterhub:8080/hub/"),
            proxy=fake_proxy,
        )
        monkeypatch.setattr(jha.JupyterHub, "instance", lambda *a, **k: fake_app)

        branding = {
            "lab_main_icon_static": "",
            "lab_main_icon_url": "",
            "lab_splash_icon_static": "",
            "lab_splash_icon_url": "",
        }
        hook = make_pre_spawn_hook(
            branding,
            favicon_uri=favicon_uri,
            favicon_busy_target=favicon_busy_target,
            gpu_available=False,
            reserved_env_var_names=frozenset(),
            reserved_env_var_prefixes=(),
            compose_project="",
        )
        spawner = types.SimpleNamespace(
            user=types.SimpleNamespace(name="alice", groups=[]),
            volumes={},
            extra_host_config={},
            environment={},
            extra_create_kwargs={},
            mem_limit=None,
            log=logging.getLogger("test_favicon_hook"),
        )
        asyncio.run(hook(spawner))
        return fake_proxy, recorded_add, real_proxy

    def test_favicon_only_route_is_canonical(self, monkeypatch):
        fake_proxy, recorded_add, real_proxy = self._run_hook(
            monkeypatch,
            favicon_uri="file:///srv/branding/favicon.ico",
            favicon_busy_target="",
            base_url="/",
        )
        assert fake_proxy.extra_routes  # a route was registered
        # every stored key is already canonical (idempotent under validate)
        for key in fake_proxy.extra_routes:
            assert key.endswith("/")
            assert key == real_proxy.validate_routespec(key)
        # the favicon.ico override is present in trailing-slash form
        assert "/user/alice/static/favicons/favicon.ico/" in fake_proxy.extra_routes
        # add_route received the same canonical key (so CHP + bookkeeping agree)
        assert set(recorded_add) == set(fake_proxy.extra_routes)

    def test_favicon_and_busy_routes_both_canonical(self, monkeypatch):
        fake_proxy, recorded_add, real_proxy = self._run_hook(
            monkeypatch,
            favicon_uri="file:///srv/branding/favicon.ico",
            favicon_busy_target="hub/static/favicon-busy.ico",
            base_url="/",
        )
        keys = set(fake_proxy.extra_routes)
        assert "/user/alice/static/favicons/favicon.ico/" in keys
        assert "/user/alice/static/favicons/favicon-busy/" in keys
        for key in keys:
            assert key == real_proxy.validate_routespec(key)

    def test_keys_survive_simulated_check_routes(self, monkeypatch):
        """End-to-end: the keys the hook actually wrote are not flagged stale."""
        fake_proxy, _recorded, real_proxy = self._run_hook(
            monkeypatch,
            favicon_uri="file:///srv/branding/favicon.ico",
            favicon_busy_target="hub/static/favicon-busy.ico",
            base_url="/jupyterhub/",
        )
        assert _stale_after_check_routes(real_proxy, fake_proxy.extra_routes) == set()
