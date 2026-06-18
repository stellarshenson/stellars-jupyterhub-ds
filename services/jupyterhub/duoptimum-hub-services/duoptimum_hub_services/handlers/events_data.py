"""Handler for the platform event log (admin-only, read-only JSON)."""

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..event_log import EventLogManager


class EventsDataHandler(BaseHandler):
    """The platform event log: GET the recent feed, DELETE to clear it (admin-only)."""

    @web.authenticated
    async def get(self):
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this endpoint")

        events = EventLogManager.get_instance().recent(limit=100)
        self.finish({"events": events})

    @web.authenticated
    async def delete(self):
        """Clear the entire event log (the Events panel "Clear" action)."""
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this endpoint")

        cleared = EventLogManager.get_instance().clear()
        self.finish({"cleared": cleared})
