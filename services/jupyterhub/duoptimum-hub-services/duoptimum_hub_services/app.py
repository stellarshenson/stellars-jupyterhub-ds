"""DuoptimumHub - the platform's JupyterHub application subclass.

The platform keeps growing its own behaviour on top of JupyterHub while staying
API-compatible. ``DuoptimumHub`` is the owned extension seam for that drift: a
thin ``JupyterHub`` subclass launched in place of the stock ``jupyterhub`` entry
point (see the ``duoptimum-hub`` console script).

Today it provides ``registered_handlers`` - the supported, non-deprecated
replacement for ``JupyterHub.extra_handlers`` (deprecated in JupyterHub 3.1, its
trait observer logs a warning). Our portal + ``/api/*`` + ``/health`` handlers are
hub-coupled (DB, spawners, ``@web.authenticated``) so they cannot become
out-of-process services. Instead they are spliced into the hub's own
``self.handlers`` list at the exact slot ``extra_handlers`` used - after the
built-ins, immediately before JupyterHub's ``/logo`` (LogoHandler) + ``/api/(.*)``
(API404) handlers - so route resolution is byte-for-byte identical. The deprecated
trait is never touched, so no warning fires and the migration survives its
eventual removal.

(JupyterHub appends three more handlers AFTER ``/api/(.*)`` -
``(user|services)/...`` AddSlash, the ``(?!/hub).*`` PrefixRedirect, and the bare
``(.*)`` Template404 - all outside the ``/hub`` prefix. The splice anchors on the
FIRST ``LogoHandler``/``API404`` occurrence, which precedes all of them, so it lands
in the same slot regardless of what trails the anchors.)
"""

from jupyterhub.apihandlers.base import API404  # trailing /api/(.*) 404 catch-all (anchor)
from jupyterhub.app import JupyterHub
from jupyterhub.handlers.base import UserUrlHandler  # offline /user/... -> portal Starting
from jupyterhub.handlers.static import LogoHandler  # trailing /logo catch-all (anchor)
from traitlets import List

from .handlers.user_url import DuoptimumUserUrlHandler


def splice_before_catch_alls(handlers, custom, hub_prefix, add_url_prefix):
    """Insert hub-prefixed ``custom`` just before the /logo + /api 404 catch-alls.

    Pure - no I/O, no app state - so it is unit-testable without booting a hub.
    The insertion point is the FIRST handler whose class is ``LogoHandler`` or
    ``API404`` (each appears exactly once in a stock build; LogoHandler comes first).
    Located by class identity, never a hardcoded index or pattern string. Raises if
    neither anchor is present: fail loud rather than silently append custom routes
    AFTER the catch-alls (which would let the SPA catch-all shadow built-ins and
    API404 shadow our /api/*).

    ``add_url_prefix`` is ``JupyterHub.add_url_prefix`` (mutates+returns its list);
    each custom tuple is copied first so the caller's list (the trait) is untouched.
    Returns a new list; the input ``handlers`` is not mutated.
    """
    if not custom:
        return list(handlers)
    prefixed = add_url_prefix(hub_prefix, [list(t) for t in custom])  # copy -> no trait mutation
    for i, tup in enumerate(handlers):
        if tup[1] is LogoHandler or tup[1] is API404:
            return list(handlers[:i]) + list(prefixed) + list(handlers[i:])
    raise RuntimeError(
        "DuoptimumHub.init_handlers: no LogoHandler/API404 catch-all in JupyterHub's "
        "handler list - cannot place registered_handlers in their first-match-wins "
        "slot. JupyterHub internals changed; update "
        "duoptimum_hub_services.app.splice_before_catch_alls."
    )


def replace_handler_class(handlers, old_cls, new_cls):
    """Return a new handler list with every tuple whose handler class is ``old_cls``
    rebound to ``new_cls`` (route pattern + kwargs unchanged).

    Pure - no app state - so it is unit-testable without booting a hub. Located by
    class identity, never a pattern string. Raises if ``old_cls`` is absent: fail loud
    rather than silently ship the stock handler when JupyterHub internals move.
    """
    out = []
    replaced = 0
    for tup in handlers:
        if tup[1] is old_cls:
            out.append((tup[0], new_cls, *tup[2:]))
            replaced += 1
        else:
            out.append(tup)
    if not replaced:
        raise RuntimeError(
            f"DuoptimumHub.init_handlers: {old_cls.__name__} not in JupyterHub's handler "
            "list - cannot install the portal cold-start redirect. JupyterHub internals "
            "changed; update duoptimum_hub_services.app.replace_handler_class wiring."
        )
    return out


class DuoptimumHub(JupyterHub):
    """Platform application: JupyterHub plus the platform's owned extensions."""

    registered_handlers = List(
        help="""Extra in-process Tornado request handlers.

        Supported replacement for the deprecated ``JupyterHub.extra_handlers``.
        Same ``(route, Handler)`` / ``(route, Handler, kwargs)`` tuple shape; routes
        are auto-prefixed with the hub base and spliced into ``self.handlers``
        immediately before JupyterHub's trailing ``/logo`` + ``/api/(.*)`` catch-alls,
        so first-match-wins resolution is identical to the old trait.
        """,
    ).tag(config=True)

    def init_handlers(self):
        super().init_handlers()  # build the stock list first (sets self.handlers)
        self.handlers = splice_before_catch_alls(
            self.handlers,
            self.registered_handlers,
            self.hub_prefix,
            self.add_url_prefix,
        )
        # the portal owns cold-start: an offline default server routes into the SPA
        # Starting page instead of JupyterHub's stock not-running page
        self.handlers = replace_handler_class(
            self.handlers, UserUrlHandler, DuoptimumUserUrlHandler
        )


main = DuoptimumHub.launch_instance  # duoptimum-hub console-script entry point
