"""Optimum Hub portal handler - serves the React SPA from the hub itself.

A single ``@web.authenticated`` handler covers the whole ``/hub/portal`` subtree:

* a request that maps to a real bundled file (``assets/*``, ``brand/*``,
  ``favicon.ico``) is served as that file
* anything else (``/hub/portal``, ``/hub/portal/home``, deep links, refresh)
  renders the SPA shell via ``BaseHandler.render_template`` - which injects the
  hub-signed ``xsrf_token``/``base_url``/``user`` that the SPA reads from
  ``window.jhdata`` (see ``optimum-hub-web/src/services/hub/client.ts``)

Auth on the asset path is harmless: assets are only fetched after the shell has
loaded, i.e. once the session cookie is already established.
"""

import json
import logging
import mimetypes
import os

from jupyterhub.handlers import BaseHandler
from tornado import web

_log = logging.getLogger("optimum_hub_web")

_HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(_HERE, "static")
TEMPLATE_DIR = os.path.join(_HERE, "templates")

# Force spec-preferred JS MIME for ES modules (mimetypes is platform-dependent).
_FORCE_MIME = {".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css"}

_entry_cache = None


def static_dir():
    """Absolute path of the bundled SPA static directory."""
    return STATIC_DIR


def template_dir():
    """Absolute path of the package template dir (shell + home/admin stubs)."""
    return TEMPLATE_DIR


def brand_dir():
    """Absolute path of the bundled brand assets (logo/favicon), served publicly
    so the unauthenticated login/signup pages can show the logo."""
    return os.path.join(STATIC_DIR, "brand")


def _entry_assets():
    """(js, css) for the SPA entry, read once from the vite build manifest.

    On any failure (missing/invalid manifest, no entry chunk) the result is NOT
    cached - a transient read error at first hit must be recoverable without a
    hub restart - and a warning is logged so a blank portal is diagnosable rather
    than silent.
    """
    global _entry_cache
    if _entry_cache is not None:
        return _entry_cache
    manifest_path = os.path.join(STATIC_DIR, ".vite", "manifest.json")
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except (OSError, ValueError) as e:
        _log.warning(
            "[OptimumHub] manifest unreadable at %s (%s) - portal shell will be blank until fixed",
            manifest_path, e,
        )
        return ("", "")
    entry = next((v for v in manifest.values() if isinstance(v, dict) and v.get("isEntry")), None)
    if not entry or not entry.get("file"):
        _log.warning(
            "[OptimumHub] no isEntry chunk in %s - portal shell will be blank", manifest_path,
        )
        return ("", "")
    css_list = entry.get("css") or []
    _entry_cache = (entry["file"], css_list[0] if css_list else "")
    return _entry_cache


def entry_assets():
    """Public (js, css) entry pair from the vite manifest, for callers that render
    the shell outside PortalHandler (e.g. the login/signup template vars)."""
    return _entry_assets()


class ImmutableStaticFileHandler(web.StaticFileHandler):
    """StaticFileHandler for the hashed SPA bundle (``/hub/portal/assets``).

    Vite emits content-hashed filenames, so the bytes at a given path never
    change - mark them immutable with a long max-age. StaticFileHandler gives us
    async sendfile, ETag/Range and 304s, so the multi-MB bundle is never read
    blocking on the hub event loop (unlike a plain ``open().read()``).
    """

    def set_extra_headers(self, path):
        self.set_header("Cache-Control", "public, max-age=604800, immutable")


class PortalHandler(BaseHandler):
    """Serve the Optimum Hub SPA: a bundled file if it exists, else the shell."""

    @web.authenticated
    async def get(self, sub=""):
        sub = (sub or "").lstrip("/")
        if sub:
            fpath = os.path.normpath(os.path.join(STATIC_DIR, sub))
            # contain to STATIC_DIR (no path traversal) and only serve real files
            if fpath.startswith(STATIC_DIR + os.sep) and os.path.isfile(fpath):
                ext = os.path.splitext(fpath)[1].lower()
                ctype = _FORCE_MIME.get(ext) or mimetypes.guess_type(fpath)[0] or "application/octet-stream"
                self.set_header("Content-Type", ctype)
                if sub.startswith("assets/"):
                    # hashed bundles are immutable
                    self.set_header("Cache-Control", "public, max-age=604800, immutable")
                with open(fpath, "rb") as f:
                    self.finish(f.read())
                return

        js, css = _entry_assets()
        html = self.render_template(
            "portal.html",
            sync=True,
            entry_js=js,
            entry_css=css,
            admin_access=bool(self.current_user and self.current_user.admin),
        )
        self.finish(html)
