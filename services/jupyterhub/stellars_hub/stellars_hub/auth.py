"""Custom NativeAuthenticator with authorization area handler."""

from jupyterhub.scopes import needs_scope
from nativeauthenticator import NativeAuthenticator
from nativeauthenticator.handlers import AuthorizationAreaHandler as BaseAuthorizationHandler


class CustomAuthorizationAreaHandler(BaseAuthorizationHandler):
    """Override to pass hub_usernames to template for server-side Discard button logic."""

    @needs_scope('admin:users')
    async def get(self):
        from nativeauthenticator.orm import UserInfo
        from jupyterhub import orm

        hub_usernames = {u.name for u in self.db.query(orm.User).all()}

        html = await self.render_template(
            "authorization-area.html",
            ask_email=self.authenticator.ask_email_on_signup,
            users=self.db.query(UserInfo).all(),
            hub_usernames=hub_usernames,
        )
        self.finish(html)


class StellarsNativeAuthenticator(NativeAuthenticator):
    """Custom authenticator that injects CustomAuthorizationAreaHandler."""

    def get_handlers(self, app):
        handlers = super().get_handlers(app)

        new_handlers = []
        for pattern, handler in handlers:
            if handler.__name__ == 'AuthorizationAreaHandler':
                new_handlers.append((pattern, CustomAuthorizationAreaHandler))
            else:
                new_handlers.append((pattern, handler))
        return new_handlers
