"""Custom NativeAuthenticator with authorization area handler.

`DuoptimumHubAuthenticator` is the platform authenticator: it keeps NativeAuth's
proven credential store + flow and only owns the *presentation* of the login and
signup pages, rendering the Duoptimum Hub antd SPA (the same bundle the portal
serves) instead of the stock/enhanced JupyterHub templates. It does this cleanly
- its login/signup handlers render uniquely-named templates (`duoptimum_login.html`
/ `duoptimum_signup.html`), so there is no template-name collision with the
enhanced stock pages and no jinja-loader wrangling.
"""

from traitlets import default
from jupyterhub.scopes import needs_scope
from nativeauthenticator import NativeAuthenticator
from nativeauthenticator.handlers import AuthorizationAreaHandler as BaseAuthorizationHandler
from nativeauthenticator.handlers import LoginHandler as _NativeLoginHandler
from nativeauthenticator.handlers import SignUpHandler as _NativeSignUpHandler


# NativeAuth renders "native-login.html" (via LoginHandler._render) and
# "signup.html"; remap both to the Duoptimum Hub antd shells. Uniquely named so
# they resolve unambiguously from the portal template dir regardless of the
# enhanced stock templates also on the template path.
_DUOPTIMUM_TEMPLATE_MAP = {
    "native-login.html": "duoptimum_login.html",
    "login.html": "duoptimum_login.html",
    "signup.html": "duoptimum_signup.html",
}


class _DuoptimumAuthTemplatesMixin:
    """Render the Duoptimum Hub auth shells in place of the stock login/signup
    templates. Transparent to NativeAuth's get/post logic - only the template
    name is swapped; sync/async behaviour and all context vars pass through."""

    def render_template(self, name, *args, **kwargs):
        return super().render_template(_DUOPTIMUM_TEMPLATE_MAP.get(name, name), *args, **kwargs)


class DuoptimumLoginHandler(_DuoptimumAuthTemplatesMixin, _NativeLoginHandler):
    """NativeAuth login (unchanged auth + redirect logic) rendered as the antd SPA."""


class DuoptimumSignUpHandler(_DuoptimumAuthTemplatesMixin, _NativeSignUpHandler):
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

    @default("db")
    def _stellars_db_default(self):
        """Provide the authenticator DB session ourselves, silencing JupyterHub's
        `Authenticator.db` deprecation warning (JH issue #3700).

        JupyterHub injects the shared session at construction as
        `_deprecated_db_session` (app.py) and its own `@default("db")` returns it
        *with* a deprecation log on first access (NativeAuth hits it at startup via
        `inspect(self.db.bind)`). We override that default to return the same
        session without the log - so NativeAuth's UserInfo store keeps working
        unchanged, no concurrency change, just no boot noise. A full own-session
        migration is an upstream NativeAuthenticator concern; this owns the default
        until then. Inherited by DuoptimumHub + BootstrapAdmin authenticators.
        """
        return self._deprecated_db_session

    def get_handlers(self, app):
        handlers = super().get_handlers(app)

        new_handlers = []
        for pattern, handler in handlers:
            if handler.__name__ == 'AuthorizationAreaHandler':
                new_handlers.append((pattern, CustomAuthorizationAreaHandler))
            else:
                new_handlers.append((pattern, handler))
        return new_handlers


class DuoptimumHubAuthenticator(StellarsNativeAuthenticator):
    """Platform authenticator: NativeAuth credential logic, Duoptimum Hub antd
    login/signup presentation. Swaps the stock login/signup handlers for ones
    that render the SPA shells; the authorization-area override is inherited."""

    def get_handlers(self, app):
        handlers = super().get_handlers(app)

        new_handlers = []
        for pattern, handler in handlers:
            if handler.__name__ == 'LoginHandler':
                new_handlers.append((pattern, DuoptimumLoginHandler))
            elif handler.__name__ == 'SignUpHandler':
                new_handlers.append((pattern, DuoptimumSignUpHandler))
            else:
                new_handlers.append((pattern, handler))
        return new_handlers

    def change_password(self, username, new_password):
        """Clear the force-password-change flag on a successful change so a flagged
        user can spawn again. Success-gated by NativeAuth's return value. An admin
        re-setting a password also clears it; the admin then re-flags as a separate
        action (the Configure-user toggle), which is applied after the password set."""
        result = super().change_password(username, new_password)
        if result:
            try:
                from .user_profiles import UserProfileManager
                UserProfileManager.get_instance().set_must_change_password(username, False)
            except Exception as e:  # never let flag-clearing break a real password change
                self.log.warning(f"[force-pw] could not clear flag for {username}: {e}")
        return result
