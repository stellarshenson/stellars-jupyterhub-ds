"""Custom NativeAuthenticator with authorization area handler.

`OptimumHubAuthenticator` is the platform authenticator: it keeps NativeAuth's
proven credential store + flow and only owns the *presentation* of the login and
signup pages, rendering the Optimum Hub antd SPA (the same bundle the portal
serves) instead of the stock/enhanced JupyterHub templates. It does this cleanly
- its login/signup handlers render uniquely-named templates (`optimum_login.html`
/ `optimum_signup.html`), so there is no template-name collision with the
enhanced stock pages and no jinja-loader wrangling.
"""

from jupyterhub.scopes import needs_scope
from nativeauthenticator import NativeAuthenticator
from nativeauthenticator.handlers import AuthorizationAreaHandler as BaseAuthorizationHandler
from nativeauthenticator.handlers import LoginHandler as _NativeLoginHandler
from nativeauthenticator.handlers import SignUpHandler as _NativeSignUpHandler


# NativeAuth renders "native-login.html" (via LoginHandler._render) and
# "signup.html"; remap both to the Optimum Hub antd shells. Uniquely named so
# they resolve unambiguously from the portal template dir regardless of the
# enhanced stock templates also on the template path.
_OPTIMUM_TEMPLATE_MAP = {
    "native-login.html": "optimum_login.html",
    "login.html": "optimum_login.html",
    "signup.html": "optimum_signup.html",
}


class _OptimumAuthTemplatesMixin:
    """Render the Optimum Hub auth shells in place of the stock login/signup
    templates. Transparent to NativeAuth's get/post logic - only the template
    name is swapped; sync/async behaviour and all context vars pass through."""

    def render_template(self, name, *args, **kwargs):
        return super().render_template(_OPTIMUM_TEMPLATE_MAP.get(name, name), *args, **kwargs)


class OptimumLoginHandler(_OptimumAuthTemplatesMixin, _NativeLoginHandler):
    """NativeAuth login (unchanged auth + redirect logic) rendered as the antd SPA."""


class OptimumSignUpHandler(_OptimumAuthTemplatesMixin, _NativeSignUpHandler):
    """NativeAuth signup (unchanged create-user logic) rendered as the antd SPA."""


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


class OptimumHubAuthenticator(StellarsNativeAuthenticator):
    """Platform authenticator: NativeAuth credential logic, Optimum Hub antd
    login/signup presentation. Swaps the stock login/signup handlers for ones
    that render the SPA shells; the authorization-area override is inherited."""

    def get_handlers(self, app):
        handlers = super().get_handlers(app)

        new_handlers = []
        for pattern, handler in handlers:
            if handler.__name__ == 'LoginHandler':
                new_handlers.append((pattern, OptimumLoginHandler))
            elif handler.__name__ == 'SignUpHandler':
                new_handlers.append((pattern, OptimumSignUpHandler))
            else:
                new_handlers.append((pattern, handler))
        return new_handlers
