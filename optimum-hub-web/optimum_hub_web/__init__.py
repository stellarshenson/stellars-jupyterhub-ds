"""Optimum Hub web portal - hub integration layer.

This package bundles the built React SPA (``optimum_hub_web/static``) together
with the thin JupyterHub glue that serves it: a single ``BaseHandler`` that
renders the SPA shell (so the hub injects a valid ``window.jhdata.xsrf_token``)
and serves the bundled static assets. Wire it into ``jupyterhub_config.py``::

    import optimum_hub_web
    from optimum_hub_web import portal_handlers, PORTAL_URL

    c.JupyterHub.extra_handlers += portal_handlers()
    c.JupyterHub.template_paths = [optimum_hub_web.template_dir(), *c.JupyterHub.template_paths]
    c.JupyterHub.default_url = JUPYTERHUB_BASE_URL_PREFIX + PORTAL_URL

The route is relative to the hub prefix (JupyterHub prepends ``/hub``), so the
portal lives at ``/hub/portal``; ``PORTAL_URL`` is the full hub path for
``default_url``.
"""

import os

from .handlers import ImmutableStaticFileHandler, PortalHandler, static_dir, template_dir

try:
    # Single source of truth: the wheel version from pyproject (set at build).
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("optimum-hub-web")
except Exception:
    __version__ = "0.1.0"  # editable/uninstalled fallback

# Hashed SPA bundle: served by StaticFileHandler (async, ETag/304) and matched
# before the catch-all so it never falls through to the shell renderer.
ASSETS_ROUTE = r"/portal/assets/(.*)"
# Tornado route, relative to the hub prefix. The catch-all serves the shell for
# client-side routes and any other real bundled file (favicon, brand).
PORTAL_ROUTE = r"/portal/?(.*)"
# Full hub path (the caller prefixes the deploy base_url) for default_url.
PORTAL_URL = "/hub/portal"

__all__ = [
    "PortalHandler",
    "portal_handlers",
    "template_dir",
    "static_dir",
    "PORTAL_URL",
    "PORTAL_ROUTE",
    "ASSETS_ROUTE",
    "__version__",
]


def portal_handlers():
    """``extra_handlers`` tuples registering the portal (auto-prefixed with /hub).

    Order matters - Tornado matches first: the hashed-assets static route comes
    before the SPA catch-all so ``/hub/portal/assets/*`` is served as a file.
    """
    return [
        (ASSETS_ROUTE, ImmutableStaticFileHandler, {"path": os.path.join(static_dir(), "assets")}),
        (PORTAL_ROUTE, PortalHandler),
    ]
