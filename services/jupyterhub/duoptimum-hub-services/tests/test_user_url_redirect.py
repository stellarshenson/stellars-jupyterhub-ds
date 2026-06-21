"""Tests for the cold-start redirect helpers (duoptimum_hub_services.handlers.user_url).

When a user opens /user/{name}/... while their default server is offline, JupyterHub
renders the stock not_running.html. The portal owns that journey, so
DuoptimumUserUrlHandler intercepts exactly that one render and 303-redirects to the SPA
Starting page. The decision and URL construction are pure functions, tested here without
booting a hub.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from jupyterhub.handlers.base import UserUrlHandler
from tornado import web

from duoptimum_hub_services.handlers.user_url import (
    DuoptimumUserUrlHandler,
    should_redirect_to_starting,
    spa_starting_url,
)


# ── should_redirect_to_starting ──────────────────────────────────────────────

def test_redirect_for_offline_default_server():
    # default server -> server_name is the empty string
    assert should_redirect_to_starting("not_running.html", "") is True


def test_redirect_for_offline_default_server_none():
    # some call sites pass no server_name at all
    assert should_redirect_to_starting("not_running.html", None) is True


def test_no_redirect_for_named_server():
    # named server has no SPA Starting variant -> keep stock page
    assert should_redirect_to_starting("not_running.html", "gpu") is False


def test_no_redirect_for_other_templates():
    assert should_redirect_to_starting("spawn_pending.html", "") is False
    assert should_redirect_to_starting("page.html", "") is False


# ── spa_starting_url ─────────────────────────────────────────────────────────

def test_starting_url_shape():
    assert spa_starting_url("/hub/", "alice") == "/hub/servers/alice/starting"


def test_starting_url_handles_no_trailing_slash():
    assert spa_starting_url("/hub", "alice") == "/hub/servers/alice/starting"


def test_starting_url_uses_escaped_name():
    # escaped_name is already URL-safe; the helper just joins it
    assert spa_starting_url("/hub/", "bob-x") == "/hub/servers/bob-x/starting"


# ── render_template override (the side-effecting branch) ─────────────────────
# Built without booting a hub: __new__ skips RequestHandler.__init__, and we stub
# only the two attributes the override touches (self.hub.base_url, self.redirect).

def _stub_handler(base_url="/hub/"):
    h = DuoptimumUserUrlHandler.__new__(DuoptimumUserUrlHandler)
    # .hub -> self.settings['hub']; .settings -> self.application.settings (both read-only)
    h.application = SimpleNamespace(settings={"hub": SimpleNamespace(base_url=base_url)})
    h.redirect = MagicMock()
    return h


def test_offline_default_server_redirects_and_finishes():
    h = _stub_handler()
    with pytest.raises(web.Finish):
        h.render_template("not_running.html", user=SimpleNamespace(escaped_name="alice"), server_name="")
    h.redirect.assert_called_once_with("/hub/servers/alice/starting", status=303)


def test_offline_redirect_respects_base_url():
    h = _stub_handler(base_url="/jupyterhub/hub/")
    with pytest.raises(web.Finish):
        h.render_template("not_running.html", user=SimpleNamespace(escaped_name="alice"), server_name="")
    h.redirect.assert_called_once_with("/jupyterhub/hub/servers/alice/starting", status=303)


def test_named_server_delegates_to_super(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(UserUrlHandler, "render_template", lambda self, name, sync=False, **ns: sentinel)
    h = _stub_handler()
    out = h.render_template("not_running.html", user=SimpleNamespace(escaped_name="alice"), server_name="gpu")
    assert out is sentinel
    h.redirect.assert_not_called()


def test_other_template_delegates_to_super(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(UserUrlHandler, "render_template", lambda self, name, sync=False, **ns: sentinel)
    h = _stub_handler()
    out = h.render_template("spawn_pending.html", user=SimpleNamespace(escaped_name="alice"), server_name="")
    assert out is sentinel
    h.redirect.assert_not_called()
