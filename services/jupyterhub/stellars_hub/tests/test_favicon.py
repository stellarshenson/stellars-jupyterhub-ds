"""Functional tests for FaviconRedirectHandler redirect mapping.

The handler is injected outside the /hub/ prefix and receives the favicon
filename (idle vs kernel-busy frames) from the CHP-proxied request. It maps the
idle frame to the hub's custom favicon and busy frames to the configured busy
target. Tornado's RequestHandler is constructed via __new__ so we can exercise
get() without a live Application/request.
"""

from stellars_hub.handlers.favicon import FaviconRedirectHandler


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
