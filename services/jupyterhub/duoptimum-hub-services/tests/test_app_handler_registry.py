"""Tests for the DuoptimumHub handler-registration seam (duoptimum_hub_services.app).

DuoptimumHub replaces the deprecated c.JupyterHub.extra_handlers with its own
registered_handlers trait, spliced into the hub's handler list in the exact
first-match-wins slot extra_handlers used: after the built-ins, immediately before
JupyterHub's trailing /logo (LogoHandler) + /api/(.*) (API404) catch-alls. The
splice is a pure function so it is testable without booting a hub; it locates the
insertion point by class identity and fails loud if the anchors are gone.
"""

import pytest
from jupyterhub.apihandlers.base import API404
from jupyterhub.app import JupyterHub
from jupyterhub.auth import Authenticator
from jupyterhub.handlers.base import UserUrlHandler
from jupyterhub.handlers.static import LogoHandler

from duoptimum_hub_services.app import (
    DuoptimumHub,
    replace_handler_class,
    splice_before_catch_alls,
)
from duoptimum_hub_services.handlers.user_url import DuoptimumUserUrlHandler


class _StubAuth(Authenticator):
    """Authenticator with no DB-backed handlers - lets the REAL init_handlers run
    in-process (the default authenticator needs self.db, which needs a booted hub)."""

    def get_handlers(self, app):
        return []


def _real_hub(registered=None):
    hub = DuoptimumHub()
    hub.authenticator = _StubAuth()
    if registered is not None:
        hub.registered_handlers = registered
    return hub

PREFIX = "/hub/"
add_prefix = JupyterHub.add_url_prefix


class _Dummy:
    """Stand-in handler class for built-in / custom routes."""


def _stock_handlers():
    """A JupyterHub-like, already /hub-prefixed handler list with the real anchors."""
    return add_prefix(
        PREFIX,
        [
            (r"/login", _Dummy),
            (r"/home", _Dummy),
            # the /user route the CLOSE-GAP wiring rebinds to the portal subclass
            (r"/user/(?P<user_name>[^/]+)(?P<user_path>/.*)?", UserUrlHandler),
            (r"/api/users", _Dummy),       # a built-in /api route precedes API404
            (r"/logo", LogoHandler, {"path": "/x.png"}),
            (r"/api/(.*)", API404),
        ],
    )


def _patterns(handlers):
    return [h[0] for h in handlers]


# ── pure splice ────────────────────────────────────────────────────────────

def test_custom_inserted_before_logo_and_api404():
    out = splice_before_catch_alls(
        _stock_handlers(), [(r"/api/settings", _Dummy)], PREFIX, add_prefix
    )
    pats = _patterns(out)
    assert "/hub/api/settings" in pats
    assert pats.index("/hub/api/settings") < pats.index("/hub/logo")
    assert pats.index("/hub/api/settings") < pats.index("/hub/api/(.*)")


def test_custom_after_builtins():
    out = splice_before_catch_alls(
        _stock_handlers(), [(r"/api/settings", _Dummy)], PREFIX, add_prefix
    )
    pats = _patterns(out)
    # built-in /hub/login keeps priority over any custom route
    assert pats.index("/hub/login") < pats.index("/hub/api/settings")


def test_routes_get_hub_prefix():
    out = splice_before_catch_alls(
        _stock_handlers(), [(r"/health", _Dummy)], PREFIX, add_prefix
    )
    assert "/hub/health" in _patterns(out)


def test_registry_order_preserved_api_before_portal():
    custom = [(r"/api/events", _Dummy), (r"/(?!logo|api/)(.*)", _Dummy)]
    out = splice_before_catch_alls(_stock_handlers(), custom, PREFIX, add_prefix)
    pats = _patterns(out)
    assert pats.index("/hub/api/events") < pats.index("/hub/(?!logo|api/)(.*)")


def test_kwargs_tuple_preserved():
    custom = [(r"/assets/(.*)", _Dummy, {"path": "/srv/assets"})]
    out = splice_before_catch_alls(_stock_handlers(), custom, PREFIX, add_prefix)
    spliced = [h for h in out if h[0] == "/hub/assets/(.*)"][0]
    assert spliced[1] is _Dummy
    assert spliced[2] == {"path": "/srv/assets"}


def test_anchor_by_identity_logo_only():
    handlers = add_prefix(PREFIX, [(r"/home", _Dummy), (r"/logo", LogoHandler, {"path": "/x"})])
    out = splice_before_catch_alls(handlers, [(r"/health", _Dummy)], PREFIX, add_prefix)
    pats = _patterns(out)
    assert pats.index("/hub/health") < pats.index("/hub/logo")


def test_anchor_by_identity_api404_only():
    handlers = add_prefix(PREFIX, [(r"/home", _Dummy), (r"/api/(.*)", API404)])
    out = splice_before_catch_alls(handlers, [(r"/health", _Dummy)], PREFIX, add_prefix)
    pats = _patterns(out)
    assert pats.index("/hub/health") < pats.index("/hub/api/(.*)")


def test_fail_loud_when_no_anchor():
    handlers = add_prefix(PREFIX, [(r"/login", _Dummy), (r"/home", _Dummy)])
    with pytest.raises(RuntimeError, match="LogoHandler/API404"):
        splice_before_catch_alls(handlers, [(r"/health", _Dummy)], PREFIX, add_prefix)


def test_empty_custom_returns_unchanged_copy():
    stock = _stock_handlers()
    out = splice_before_catch_alls(stock, [], PREFIX, add_prefix)
    assert _patterns(out) == _patterns(stock)
    assert out is not stock  # a copy, not the same object


def test_input_handlers_not_mutated():
    stock = _stock_handlers()
    before = list(stock)
    splice_before_catch_alls(stock, [(r"/health", _Dummy)], PREFIX, add_prefix)
    assert stock == before  # caller's list untouched


def test_custom_trait_list_not_mutated():
    custom = [(r"/health", _Dummy)]
    snapshot = [tuple(t) for t in custom]
    splice_before_catch_alls(_stock_handlers(), custom, PREFIX, add_prefix)
    assert [tuple(t) for t in custom] == snapshot  # no /hub prefix bled into the trait


# ── pure class-replace (CLOSE-GAP cold-start redirect) ───────────────────────

class _OldUserUrl:
    """Stand-in for the stock handler class to be replaced."""


class _NewUserUrl:
    """Stand-in for the Duoptimum override class."""


def _user_url_handlers():
    return add_prefix(
        PREFIX,
        [
            (r"/login", _Dummy),
            (r"/user/(?P<user_name>[^/]+)(?P<user_path>/.*)?", _OldUserUrl),
            (r"/logo", LogoHandler, {"path": "/x.png"}),
        ],
    )


def test_replace_rebinds_matching_class():
    out = replace_handler_class(_user_url_handlers(), _OldUserUrl, _NewUserUrl)
    classes = [t[1] for t in out]
    assert _NewUserUrl in classes
    assert _OldUserUrl not in classes


def test_replace_keeps_route_and_kwargs():
    handlers = add_prefix(PREFIX, [(r"/user/(.*)", _OldUserUrl, {"k": 1})])
    out = replace_handler_class(handlers, _OldUserUrl, _NewUserUrl)
    assert out[0][0] == "/hub/user/(.*)"
    assert out[0][1] is _NewUserUrl
    assert out[0][2] == {"k": 1}


def test_replace_leaves_other_handlers_untouched():
    out = replace_handler_class(_user_url_handlers(), _OldUserUrl, _NewUserUrl)
    pats = _patterns(out)
    assert "/hub/login" in pats
    assert "/hub/logo" in pats


def test_replace_fail_loud_when_class_absent():
    handlers = add_prefix(PREFIX, [(r"/login", _Dummy), (r"/home", _Dummy)])
    with pytest.raises(RuntimeError, match=_OldUserUrl.__name__):
        replace_handler_class(handlers, _OldUserUrl, _NewUserUrl)


def test_replace_input_not_mutated():
    handlers = _user_url_handlers()
    before = [tuple(t) for t in handlers]
    replace_handler_class(handlers, _OldUserUrl, _NewUserUrl)
    assert [tuple(t) for t in handlers] == before


# ── subclass wiring ────────────────────────────────────────────────────────

def test_registered_handlers_is_config_trait():
    trait = DuoptimumHub.class_traits()["registered_handlers"]
    assert trait.metadata.get("config") is True


def test_init_handlers_splices_registered(monkeypatch):
    """init_handlers calls super (stock list) then splices registered_handlers."""
    hub = DuoptimumHub()
    hub.registered_handlers = [(r"/api/settings", _Dummy)]

    def fake_super(self):
        self.handlers = _stock_handlers()

    monkeypatch.setattr(JupyterHub, "init_handlers", fake_super)
    hub.init_handlers()
    pats = _patterns(hub.handlers)
    assert pats.index("/hub/api/settings") < pats.index("/hub/logo")


def test_init_handlers_empty_registry_is_stock(monkeypatch):
    hub = DuoptimumHub()
    hub.registered_handlers = []

    def fake_super(self):
        self.handlers = _stock_handlers()

    monkeypatch.setattr(JupyterHub, "init_handlers", fake_super)
    hub.init_handlers()
    assert _patterns(hub.handlers) == _patterns(_stock_handlers())


# ── against the REAL JupyterHub.init_handlers (drift detection) ───────────────
# These exercise stock JupyterHub end-to-end (real default_handlers + real /logo
# and API404 appends), so they catch the exact internal drift the fail-loud guard
# exists for - which the monkeypatched-super tests above structurally cannot.

def test_real_anchor_contract():
    """Stock init_handlers still emits LogoHandler + API404 exactly once each, as
    the anchors the splice depends on (caught here, not only in production)."""
    hub = _real_hub()
    hub.init_handlers()  # real super().init_handlers() + empty splice (no-op)
    classes = [t[1] for t in hub.handlers]
    assert classes.count(LogoHandler) == 1
    assert classes.count(API404) == 1
    # both sit at the tail (everything before them is a built-in or a custom route)
    logo_i = classes.index(LogoHandler)
    assert logo_i >= len(classes) - 5


def test_real_custom_lands_before_logo():
    """End-to-end: a registered route is spliced ahead of /hub/logo in the REAL
    handler list - the same first-match-wins slot extra_handlers occupied."""
    hub = _real_hub(registered=[(r"/api/zzz", _Dummy)])
    hub.init_handlers()
    pats = _patterns(hub.handlers)
    assert "/hub/api/zzz" in pats
    logo_i = next(i for i, t in enumerate(hub.handlers) if t[1] is LogoHandler)
    assert pats.index("/hub/api/zzz") < logo_i


def test_real_init_handlers_idempotent():
    """Re-running init_handlers (reload) yields the identical list - no duplicate
    accumulation - because super() rebuilds self.handlers from scratch each call."""
    hub = _real_hub(registered=[(r"/api/zzz", _Dummy)])
    hub.init_handlers()
    first = _patterns(hub.handlers)
    hub.init_handlers()
    second = _patterns(hub.handlers)
    assert first == second
    assert second.count("/hub/api/zzz") == 1


def test_real_user_url_handler_replaced():
    """End-to-end: stock init_handlers registers UserUrlHandler exactly once, and
    DuoptimumHub rebinds it to the portal cold-start subclass (the /user route keeps
    its pattern). Catches upstream drift in the UserUrlHandler registration."""
    hub = _real_hub()
    hub.init_handlers()
    classes = [t[1] for t in hub.handlers]
    assert UserUrlHandler not in classes
    assert classes.count(DuoptimumUserUrlHandler) == 1
    # DuoptimumUserUrlHandler is a subclass, so the route still resolves the same way
    assert issubclass(DuoptimumUserUrlHandler, UserUrlHandler)
