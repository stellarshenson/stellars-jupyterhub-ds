"""Duoptimum Hub native authenticator.

`DuoptimumNativeAuthenticator` is a single self-contained wrapper over
jupyterhub-nativeauthenticator: it keeps NativeAuth's proven credential store +
flow and adds three things on top -

  1. antd presentation of the login / signup / authorization-area pages (renders
     the same Duoptimum Hub SPA shell the portal serves, via uniquely-named
     templates so there is no collision with the stock pages),
  2. force-password-change clearing on a successful password change,
  3. the first-admin bootstrap - env-provision OR the signup-off self-signup
     window OR normal-signup auto-authorise, with fail-fast when no path can
     create the admin.

Selected from the config by dotted-path string, exactly like the spawner:

    c.JupyterHub.authenticator_class = "duoptimum_hub_services.auth.DuoptimumNativeAuthenticator"
    c.DuoptimumNativeAuthenticator.admin_username = ...
    c.DuoptimumNativeAuthenticator.signup_enabled = ...

The INITIAL-ONLY admin password is read straight from os.environ['JUPYTERHUB_ADMIN_PASSWORD']
inside __init__ - deliberately NOT a config=True trait, so the secret never appears in
`jupyterhub --show-config`, `trait_values()` or the Settings page.

Because every native + bootstrap behaviour lives in this one class, selecting a
different authenticator (e.g. "generic-oauth") runs none of it - no conditionals
in the config.
"""

import os

from traitlets import Bool, Unicode, default
from jupyterhub.scopes import needs_scope
from nativeauthenticator import NativeAuthenticator
from nativeauthenticator.handlers import AuthorizationAreaHandler as BaseAuthorizationHandler
from nativeauthenticator.handlers import LoginHandler as _NativeLoginHandler
from nativeauthenticator.handlers import SignUpHandler as _NativeSignUpHandler

from .admin_bootstrap import (
    admin_unreachable,
    bootstrap_window_open,
    first_admin_self_signup_pending,
    provision_admin_userinfo,
    query_admin_state,
)


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
    """NativeAuth signup (unchanged create-user logic) rendered as the antd SPA.
    Base for the bootstrap signup handler."""


class BootstrapAdminSignUpHandler(DuoptimumSignUpHandler):
    """Replace NativeAuth's misleading post-signup messages during the bootstrap window.

    Two upstream branches need correcting:

      * Success branch keys off `username in admin_users`, which we deliberately
        leave empty (populating admin_users triggers an eager User insert and the
        random-password trap in duoptimum_hub_services.events). With create_user
        flagging is_authorized=True the row is correct but the message still drops
        to "Your information has been sent to the admin." Treat is_authorized as
        the success signal here.

      * Generic error branch on `not user` shows "Be sure your username does not
        contain spaces, commas or slashes..." which is misleading when the real
        reason create_user returned None is the bootstrap-window validate_username
        block. Substitute a clearer message in that case.
    """

    def get_result_message(self, user, assume_user_is_human, username_already_taken,
                           confirmation_matches, user_is_admin):
        if user is not None and getattr(user, 'is_authorized', False):
            user_is_admin = True
        alert, message = super().get_result_message(
            user, assume_user_is_human, username_already_taken,
            confirmation_matches, user_is_admin,
        )
        if (
            user is None
            and self.authenticator._bootstrap_admin_pending()
            and assume_user_is_human
            and not username_already_taken
            and confirmation_matches
        ):
            submitted = self.get_body_argument("username", "", strip=False)
            if submitted and submitted != self.authenticator.admin_username:
                alert = "alert-warning"
                message = (
                    "Only the admin user can sign up during the initial "
                    "bootstrap window."
                )
        return alert, message


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


# ── DuoptimumNativeAuthenticator concern mixins ──
# IMPORTANT: these three are PLAIN classes, not HasTraits. The traitlets metaclass only
# scans the composed class's own body, so any TraitType, @default, @observe or @validate
# MUST live on DuoptimumNativeAuthenticator below (the HasTraits subclass) - put one inside
# a mixin and it SILENTLY does not register (no error, a dead trait/handler). Mixins hold
# behaviour (methods) only; config traits + @default("db") stay on the composed class.


class _AntdAuthHandlersMixin:
    """Swap NativeAuth's login/signup/authorization handlers for the antd-rendering
    Duoptimum variants so the portal owns the auth screens."""

    def get_handlers(self, app):
        handlers = super().get_handlers(app)
        new_handlers = []
        for pattern, handler in handlers:
            name = handler.__name__
            if name == 'AuthorizationAreaHandler':
                new_handlers.append((pattern, CustomAuthorizationAreaHandler))
            elif name == 'LoginHandler':
                new_handlers.append((pattern, DuoptimumLoginHandler))
            elif name == 'SignUpHandler':
                new_handlers.append((pattern, BootstrapAdminSignUpHandler))
            else:
                new_handlers.append((pattern, handler))
        return new_handlers


class _AdminPromotionMixin:
    """Promote the configured admin to admin role on every successful auth."""

    async def run_post_auth_hook(self, handler, authentication):
        """Promote the configured admin to admin role on every successful auth.

        Travels with the native authenticator (was a loose c.Authenticator.post_auth_hook
        in the config). admin_users is deliberately NOT set - that makes JupyterHub
        eagerly insert a User row at startup and trips the random-password trap in
        events.py; the role is granted purely at login here. Composes with any
        operator-set post_auth_hook (super runs it first)."""
        authentication = await super().run_post_auth_hook(handler, authentication)
        if authentication and authentication.get('name') == self.admin_username:
            authentication['admin'] = True
        return authentication


class _NativeBootstrapMixin:
    """First-admin bootstrap: env-provision / signup-off self-signup window /
    normal-signup auto-authorise, with fail-fast when the admin can never be created.
    The DECISION logic lives in admin_bootstrap's pure functions; this mixin wires it
    into the native-authenticator lifecycle (__init__ snapshot, enable_signup,
    validate_username, create_user). Native-specific by design - self-signup /
    bootstrap are nonsense over OAuth, so a non-native authenticator would not compose it."""

    # INITIAL-ONLY admin password is read from os.environ in __init__, NOT a config=True
    # trait, so the secret never lands in --show-config / trait_values() / the Settings page.
    #
    # Bootstrap state computed in __init__ (after super() builds users_info). Class-level
    # defaults so the enable_signup property is safe even if read DURING super().__init__()
    # (before the back half of __init__ runs) - it then resolves to "window closed / no
    # provisioning", never AttributeError.
    _bootstrap_window_open = False
    _provisioning_requested = False
    _admin_password = ""

    def __init__(self, *args, **kwargs):
        # super() runs NativeAuthenticator.__init__ -> add_new_table(), so users_info
        # is guaranteed to exist once it returns. Snapshot the bootstrap state HERE,
        # not at config import: on a fresh volume config-import is too early (no table
        # yet -> the env INSERT silently no-ops, the old admin-login bug).
        super().__init__(*args, **kwargs)
        # INITIAL-ONLY secret read straight from env - never a config=True trait (see class body).
        # .strip() preserves the old config's parity: a whitespace-only value -> '' -> no
        # provisioning, and a newline/space-suffixed secret (common from a mounted-file secret)
        # is normalised before hashing so the admin logs in with the bare password and the
        # initial-only is_valid_password(env) no-op check keeps matching an existing volume.
        self._admin_password = os.environ.get("JUPYTERHUB_ADMIN_PASSWORD", "").strip()
        signup = 1 if self.signup_enabled else 0
        self._provisioning_requested = bool(self.admin_username and self._admin_password)
        # Read the startup state from the SAME sqlite file the authenticator's session is
        # bound to. At config-load (the old call site) the ORM was not up, so the path came
        # from an env-captured DEFAULT_DB_PATH; here in __init__ self.db exists, so derive the
        # path from it - the raw read and the ORM stay in lock-step, no import-time coupling.
        db_path = self.db.bind.url.database
        db_empty, admin_present = query_admin_state(self.admin_username, db_path)
        self._bootstrap_window_open = bootstrap_window_open(
            signup, self._provisioning_requested, db_empty, admin_present
        )
        if admin_unreachable(signup, self._provisioning_requested, admin_present, self._bootstrap_window_open):
            raise SystemExit(
                f"[Admin Bootstrap] FATAL: admin '{self.admin_username}' does not exist and "
                "cannot be created - signup is disabled (JUPYTERHUB_SIGNUP_ENABLED=0), the "
                "bootstrap self-signup window is closed (database already contains users), and "
                "no JUPYTERHUB_ADMIN_PASSWORD was set. Provide JUPYTERHUB_ADMIN_PASSWORD to "
                "pre-provision the admin, or set JUPYTERHUB_SIGNUP_ENABLED=1 to allow signup."
            )
        if self._provisioning_requested:
            provision_admin_userinfo(self.db, self.admin_username, self._admin_password)

    # ── First-admin bootstrap window ──
    def _bootstrap_admin_pending(self):
        """The bootstrap window only takes effect while it was open at startup AND
        the admin row has not yet been inserted. Checked at request time so admin
        creation works the moment the admin signs up (no restart to recapture state)."""
        if not self._bootstrap_window_open or not self.admin_username:
            return False
        return self.get_user(self.admin_username) is None

    @property
    def enable_signup(self):
        """Dynamic so the Sign Up link and /hub/signup form disappear the moment the
        bootstrap admin row appears, even though the process started with the window
        open. The operator's signup_enabled still wins if True. Property shadows the
        inherited Bool trait; the no-op setter keeps traitlets config assignment from
        raising."""
        if self.signup_enabled:
            return True
        return self._bootstrap_admin_pending()

    @enable_signup.setter
    def enable_signup(self, value):
        # Computed dynamically; ignore static assignments from config.
        pass

    def validate_username(self, username):
        if not super().validate_username(username):
            return False
        if self._bootstrap_admin_pending() and username and username != self.admin_username:
            return False
        return True

    def create_user(self, username, password, **kwargs):
        # Auto-authorise the FIRST admin's self-signup regardless of the signup flag
        # (was gated on the signup-off window, so the signup-on default left the admin
        # is_authorized=False with no one to authorise them -> locked out). Non-admin
        # signups still land pending. Decision lives in admin_bootstrap; this wires it.
        pending = first_admin_self_signup_pending(self.db, self.admin_username, self._provisioning_requested)
        user_info = super().create_user(username, password, **kwargs)
        if (
            user_info is not None
            and pending
            and self.normalize_username(username) == self.normalize_username(self.admin_username)
        ):
            user_info.is_authorized = True
            self.db.commit()
        return user_info


class DuoptimumNativeAuthenticator(
    _AntdAuthHandlersMixin, _AdminPromotionMixin, _NativeBootstrapMixin, NativeAuthenticator
):
    """Self-contained Duoptimum Hub native authenticator, composed over
    NativeAuthenticator from three single-concern mixins: antd auth handlers
    (_AntdAuthHandlersMixin), admin-role promotion (_AdminPromotionMixin) and the
    first-admin bootstrap (_NativeBootstrapMixin). Configured by trait, selected by
    dotted-path string from the config. The mixins each call super() so the MRO chains
    straight through to NativeAuthenticator; none overrides another's method, so the
    composition is behaviour-identical to the former single class."""

    # ── Bootstrap config (set in the config from its env constants) ──
    admin_username = Unicode(
        "", config=True,
        help="Admin username (already lowercased by the config). Promoted to admin "
             "role at login; the only name allowed to self-register during the "
             "bootstrap window.",
    )
    signup_enabled = Bool(
        True, config=True,
        help="Operator self-registration switch (JUPYTERHUB_SIGNUP_ENABLED). The "
             "effective enable_signup (in _NativeBootstrapMixin) also re-opens for the "
             "admin during the bootstrap window.",
    )

    @default("db")
    def _stellars_db_default(self):
        """Provide the authenticator DB session ourselves, silencing JupyterHub's
        `Authenticator.db` deprecation warning (JH issue #3700).

        JupyterHub injects the shared session at construction as
        `_deprecated_db_session`; its own `@default("db")` returns it *with* a
        deprecation log on first access (NativeAuth hits it at startup via
        `inspect(self.db.bind)`). We return the same session without the log - the
        UserInfo store keeps working unchanged, no concurrency change, just no boot
        noise. A full own-session migration is an upstream NativeAuth concern."""
        return self._deprecated_db_session

    def change_password(self, username, new_password):
        """Clear the force-password-change flag on a successful change so a flagged
        user can spawn again. Success-gated by NativeAuth's return value. An admin
        re-setting a password also clears it; the admin then re-flags as a separate
        action (the Configure-user toggle), applied after the password set."""
        result = super().change_password(username, new_password)
        if result:
            try:
                from .user_profiles import UserProfileManager
                UserProfileManager.get_instance().set_must_change_password(username, False)
            except Exception as e:  # never let flag-clearing break a real password change
                self.log.warning(f"[force-pw] could not clear flag for {username}: {e}")
        return result
