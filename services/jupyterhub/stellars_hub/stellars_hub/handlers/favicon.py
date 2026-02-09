"""Favicon redirect handler for CHP proxy route."""

from tornado import web


class FaviconRedirectHandler(web.RequestHandler):
    """Redirect user-server favicon requests to hub's static favicon.

    Uses tornado.web.RequestHandler (not BaseHandler) because this handler
    is injected directly into the Tornado app outside the /hub/ prefix,
    serving CHP proxy routes that bypass JupyterHub's handler prefix.
    """

    def get(self):
        base_url = self.application.settings.get('base_url', '/')
        self.redirect(f'{base_url}hub/static/favicon.ico')
