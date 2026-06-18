"""Favicon redirect handler for CHP proxy route."""

from tornado import web


class FaviconRedirectHandler(web.RequestHandler):
    """Redirect user-server favicon requests to the hub's custom favicon.

    Uses tornado.web.RequestHandler (not BaseHandler) because this handler
    is injected directly into the Tornado app outside the /hub/ prefix,
    serving CHP proxy routes that bypass JupyterHub's handler prefix.

    The captured filename distinguishes the idle frame (favicon.ico) from the
    kernel-busy animation frames (favicon-busy-1.ico, ...). Busy frames only
    reach this handler when a busy override is configured - otherwise their CHP
    route is never registered and they fall through to the user's own server.
    """

    def initialize(self, busy_target=''):
        # Redirect target for busy frames: hub-relative 'hub/static/...' or an
        # external URL. Empty means no busy override (busy frames shouldn't reach
        # here, but if they do we fall back to the idle favicon).
        self._busy_target = busy_target

    def get(self, filename):
        base_url = self.application.settings.get('base_url', '/')
        if filename.startswith('favicon-busy') and self._busy_target:
            target = self._busy_target
            if '://' not in target:
                target = f'{base_url}{target}'
            self.redirect(target)
            return
        self.redirect(f'{base_url}hub/static/favicon.ico')
