"""Duoptimum Hub web portal - hub integration layer.

This package bundles the built React SPA (``duoptimum_hub_web/static``) together
with the thin JupyterHub glue that serves it: a single ``BaseHandler`` that
renders the SPA shell (so the hub injects a valid ``window.jhdata.xsrf_token``)
and serves the bundled static assets. Wire it into ``jupyterhub_config.py``::

    import duoptimum_hub_web
    from duoptimum_hub_web import portal_handlers, PORTAL_URL

    c.JupyterHub.extra_handlers += portal_handlers()
    c.JupyterHub.template_paths = [duoptimum_hub_web.template_dir(), *c.JupyterHub.template_paths]
    c.JupyterHub.default_url = JUPYTERHUB_BASE_URL_PREFIX + PORTAL_URL

The route is relative to the hub prefix (JupyterHub prepends ``/hub``), so the
portal lives at the hub root ``/hub/...`` (no ``portal`` segment); ``PORTAL_URL``
is the full hub path (``/hub/home``) for ``default_url``.
"""

import os

from tornado import web

from .handlers import (
    ImmutableStaticFileHandler,
    PortalHandler,
    brand_dir,
    entry_assets,
    static_dir,
    template_dir,
)

try:
    # Single source of truth: the wheel version from pyproject (set at build).
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("duoptimum-hub-web")
except Exception:
    __version__ = "0.1.0"  # editable/uninstalled fallback

# Hashed SPA bundle: served by StaticFileHandler (async, ETag/304) and matched
# before the catch-all so it never falls through to the shell renderer.
ASSETS_ROUTE = r"/assets/(.*)"
# Brand assets (logo/favicon) served publicly (no auth) so the unauthenticated
# login/signup pages can show the logo; matched before the @authenticated catch-all.
BRAND_ROUTE = r"/brand/(.*)"
# Tornado catch-all, relative to the hub prefix -> serves the SPA shell for every
# /hub/<path> not already claimed by a JupyterHub built-in. extra_handlers run
# AFTER the built-ins (app.py registers default_handlers first, first-match-wins),
# so /hub/login, /hub/logout, /hub/static/*, /hub/spawn*, /hub/token etc. are
# served by the hub; only leftover SPA routes (/servers, /users, ...) fall through
# here. /hub/home and /hub/admin are also stock built-ins, but their templates are
# shadowed by this package's template_dir: home.html renders the SPA shell (so the
# portal OWNS the /home landing route) and admin.html redirects into it. The legacy
# server-page handlers (/notifications, /settings, /activity, /groups) were
# unregistered so they no longer shadow the matching SPA routes.
#
# The negative lookahead is load-bearing: TWO built-ins are appended AFTER
# extra_handlers (jupyterhub/app.py: `/logo` -> LogoHandler and `/api/(.*)` ->
# API404), so a bare /(.*) shadowed both - the lab logo (<img src=.../hub/logo>)
# rendered the SPA HTML instead of the PNG, and an unknown /hub/api/* returned the
# shell instead of a JSON 404. Excluding `logo` and `api/` lets them fall through
# to those late built-ins (the custom /api/* data handlers register earlier in
# extra_handlers, so they still win).
PORTAL_ROUTE = r"/(?!logo(?:/|$)|api/)(.*)"
# Full hub path (the caller prefixes the deploy base_url) for default_url. The SPA
# landing is /home: the stock /hub/home built-in renders this package's home.html,
# which is the SPA shell (template_dir shadows the stock template).
PORTAL_URL = "/hub/home"

__all__ = [
    "PortalHandler",
    "portal_handlers",
    "template_dir",
    "static_dir",
    "brand_dir",
    "entry_assets",
    "PORTAL_URL",
    "PORTAL_ROUTE",
    "ASSETS_ROUTE",
    "BRAND_ROUTE",
    "__version__",
]


def portal_handlers():
    """``extra_handlers`` tuples registering the portal (auto-prefixed with /hub).

    Order matters - Tornado matches first: the hashed-assets and public brand
    routes come before the SPA catch-all so ``/hub/assets/*`` and
    ``/hub/brand/*`` are served as files (brand without auth, so the
    login/signup pages can load the logo).
    """
    return [
        (ASSETS_ROUTE, ImmutableStaticFileHandler, {"path": os.path.join(static_dir(), "assets")}),
        (BRAND_ROUTE, web.StaticFileHandler, {"path": brand_dir()}),
        (PORTAL_ROUTE, PortalHandler),
    ]
