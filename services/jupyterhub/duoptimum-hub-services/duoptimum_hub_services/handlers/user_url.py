"""Cold-start interception: send an offline default server into the portal SPA.

When a user navigates to ``/user/{name}/...`` while their default server is not running,
JupyterHub's ``UserUrlHandler`` renders the stock ``not_running.html`` (a dead-end page
with a Launch button into the stock spawn flow). The Duoptimum Hub portal owns the
cold-start journey, so this subclass intercepts exactly that one render and 303-redirects
to the SPA Starting page (``/hub/servers/{name}/starting``), which spawns the server with
live progress and enters the lab once it genuinely answers. Every other branch - the
access-scope check, the ready/pending/API paths - is inherited from ``UserUrlHandler``
unchanged; only the offline-render outcome differs.

Default server only: the SPA Starting route is per-user with no named-server variant, so
an offline *named* server keeps JupyterHub's stock not-running page.
"""
from jupyterhub.handlers.base import UserUrlHandler
from jupyterhub.utils import url_path_join
from tornado import web


def should_redirect_to_starting(template_name, server_name):
    """True when a ``render_template`` call is the offline default-server not-running
    page - the one case the portal Starting page should own. Pure for unit tests."""
    return template_name == "not_running.html" and not server_name


def spa_starting_url(hub_base_url, escaped_name):
    """The portal SPA Starting route for a user's default server. Pure for unit tests."""
    return url_path_join(hub_base_url, "servers", escaped_name, "starting")


class DuoptimumUserUrlHandler(UserUrlHandler):
    """``UserUrlHandler`` that routes an offline default server into the portal Starting page."""

    def render_template(self, name, sync=False, **ns):
        if should_redirect_to_starting(name, ns.get("server_name")):
            # 303 so the browser re-GETs the SPA route; raise Finish so the parent
            # get() stops before it writes the stock not-running body (redirect already
            # finished the response).
            self.redirect(spa_starting_url(self.hub.base_url, ns["user"].escaped_name), status=303)
            raise web.Finish()
        return super().render_template(name, sync=sync, **ns)
