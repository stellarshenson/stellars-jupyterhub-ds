"""Handler for the portal sent-notification history (admin-only, read-only JSON)."""

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..sent_notification_log import SentNotificationLogManager


class SentNotificationsDataHandler(BaseHandler):
    """The portal "Past Notifications" feed: GET the recent sent-broadcast history."""

    @web.authenticated
    async def get(self):
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this endpoint")

        notifications = SentNotificationLogManager.get_instance().recent(limit=100)
        self.finish({"notifications": notifications})
