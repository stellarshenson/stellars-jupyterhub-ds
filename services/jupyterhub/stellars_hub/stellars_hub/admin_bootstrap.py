"""Admin bootstrap subsystem.

Two operating modes share this code:

  1. Bootstrap-by-signup (default): operator sets only ``JUPYTERHUB_ADMIN``. On a
     fresh deployment the signup form is silently re-opened just for the admin
     name (``BootstrapAdminAuthenticator.validate_username`` rejects every other
     username). The admin signs up with their own password and our ``create_user``
     override flips ``is_authorized=True`` directly on the new ``UserInfo`` row
     (no email, no SMTP, no approval URL). They log in, the post-auth hook
     promotes them to admin role. Once their ``UserInfo`` is in the DB the
     bootstrap window closes and signup falls back to the operator's setting.

  2. Bootstrap-by-env: operator also sets ``JUPYTERHUB_ADMIN_PASSWORD``. The hub
     pre-creates the admin ``UserInfo`` with that password on startup. The env
     value is INITIAL ONLY: ``bcrypt.checkpw`` decides whether the stored hash
     was generated from the env value; the moment the admin changes their
     password verification fails and env is permanently ignored.

``c.Authenticator.admin_users`` is intentionally NOT set by callers: setting it
makes JupyterHub eagerly insert a ``User`` row at startup, which fires the
``after_insert`` listener in :mod:`stellars_hub.events` and creates a
``UserInfo`` with a random xkcd password the operator cannot retrieve. Admin
role is granted purely at login time via :func:`make_admin_post_auth_hook`.
"""

from __future__ import annotations

import os
import sqlite3

import bcrypt
from nativeauthenticator.handlers import SignUpHandler as _NativeSignUpHandler
from traitlets import Bool, Unicode

from .auth import StellarsNativeAuthenticator


# ── Pure helpers ─────────────────────────────────────────────────────────────


def query_admin_state(admin_username, db_path):
    """Return ``(db_empty, admin_present)`` at the time of the call.

    ``db_empty`` is ``True`` iff ``users_info`` has zero rows or doesn't exist
    yet (including the very-first-boot case where the DB file itself is absent).
    ``admin_present`` is ``True`` iff a ``UserInfo`` row for ``admin_username``
    exists.
    """
    if not admin_username or not os.path.exists(db_path):
        return True, False
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users_info'")
        if not cur.fetchone():
            return True, False
        cur.execute("SELECT COUNT(*) FROM users_info")
        empty = cur.fetchone()[0] == 0
        cur.execute("SELECT 1 FROM users_info WHERE username = ?", (admin_username,))
        present = cur.fetchone() is not None
        return empty, present
    finally:
        conn.close()


def provision_admin_userinfo(admin_username, admin_password, db_path):
    """Bootstrap-by-env: seed admin ``UserInfo`` from ``JUPYTERHUB_ADMIN_PASSWORD``.

    Initial-only semantics:
      - missing UserInfo                        -> INSERT bcrypt(env), is_authorized=1
      - exists, env still verifies against hash -> no-op (still initial)
      - exists, env does NOT verify             -> leave alone (admin rotated it)
    """
    if not admin_username or not admin_password or not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users_info'")
        if not cur.fetchone():
            return
        cur.execute("SELECT password FROM users_info WHERE username = ?", (admin_username,))
        row = cur.fetchone()
        if row is None:
            hashed = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt())
            cur.execute(
                "INSERT INTO users_info (username, password, is_authorized) VALUES (?, ?, 1)",
                (admin_username, hashed),
            )
            conn.commit()
            print(
                f"[Admin Bootstrap] Provisioned '{admin_username}' from JUPYTERHUB_ADMIN_PASSWORD",
                flush=True,
            )
            return
        stored = row[0].encode("utf-8") if isinstance(row[0], str) else row[0]
        try:
            still_initial = bcrypt.checkpw(admin_password.encode("utf-8"), stored)
        except Exception:
            still_initial = False
        if not still_initial:
            print(
                f"[Admin Bootstrap] '{admin_username}' has changed their password; "
                "JUPYTERHUB_ADMIN_PASSWORD ignored",
                flush=True,
            )
    finally:
        conn.close()


def compute_bootstrap_window_open(signup_enabled, admin_password, db_empty, admin_present):
    """Decide whether the bootstrap-by-signup window is open at startup.

    The window opens iff: signup is operator-disabled AND no env-provisioning
    is requested AND the database is empty AND the admin row is not present.
    """
    return (
        not signup_enabled
        and not admin_password
        and db_empty
        and not admin_present
    )


def make_admin_post_auth_hook(admin_username):
    """Return an async post_auth_hook closure that promotes ``admin_username``."""

    async def _hook(authenticator, handler, authentication):
        if authentication and authentication.get("name") == admin_username:
            authentication["admin"] = True
        return authentication

    return _hook


# ── Signup handler ───────────────────────────────────────────────────────────


class BootstrapAdminSignUpHandler(_NativeSignUpHandler):
    """Replace NativeAuth's misleading post-signup messages during the bootstrap window.

    Two upstream branches need correcting:

      * Success branch keys off ``username in admin_users``, which we deliberately
        leave empty. With our ``create_user`` override flagging ``is_authorized=True``,
        the row is correct but the message would still drop to "Your information
        has been sent to the admin." Treat ``is_authorized`` as the success signal.

      * Generic error branch on ``not user`` shows "Be sure your username does
        not contain spaces, commas or slashes..." which is misleading when the
        real reason ``create_user`` returned ``None`` is our bootstrap-window
        ``validate_username`` block. Substitute a clearer message in that case.
    """

    def get_result_message(
        self,
        user,
        assume_user_is_human,
        username_already_taken,
        confirmation_matches,
        user_is_admin,
    ):
        if user is not None and getattr(user, "is_authorized", False):
            user_is_admin = True
        alert, message = super().get_result_message(
            user,
            assume_user_is_human,
            username_already_taken,
            confirmation_matches,
            user_is_admin,
        )
        if (
            user is None
            and getattr(self.authenticator, "_bootstrap_admin_pending", lambda: False)()
            and assume_user_is_human
            and not username_already_taken
            and confirmation_matches
        ):
            submitted = self.get_body_argument("username", "", strip=False)
            admin_username = getattr(self.authenticator, "bootstrap_admin_username", "")
            if submitted and submitted != admin_username:
                alert = "alert-warning"
                message = (
                    "Only the admin user can sign up during the initial "
                    "bootstrap window."
                )
        return alert, message


# ── Authenticator ────────────────────────────────────────────────────────────


class BootstrapAdminAuthenticator(StellarsNativeAuthenticator):
    """During the bootstrap window, only the admin username may self-sign-up.

    Outside the window this class is a transparent passthrough to
    :class:`StellarsNativeAuthenticator`. The window state is supplied by the
    operator via the ``bootstrap_window_open`` traitlet (computed once at
    startup); the admin-row check is re-evaluated against the database on
    every ``validate_username`` call so admin user creation works as soon as
    the admin signs up - no hub restart needed.

    Why we override ``create_user`` instead of using NativeAuth's
    ``allow_self_approval_for``: that path forces ``ask_email_on_signup=True``,
    matches the regex against the email field (not the username), generates a
    signed approval URL and tries to send it via SMTP. Hub containers have no
    MTA, so the admin signup ends up pending without any way to confirm it.
    """

    bootstrap_window_open = Bool(
        False,
        config=True,
        help="True iff the deployment booted into a bootstrap window.",
    )
    bootstrap_admin_username = Unicode(
        "",
        config=True,
        help="Username scoped during the bootstrap window (typically JUPYTERHUB_ADMIN).",
    )

    def _bootstrap_admin_pending(self):
        """True only while the window was open at startup AND the admin row is
        not yet present. Re-checked at request time via ``self.get_user``.
        """
        if not self.bootstrap_window_open or not self.bootstrap_admin_username:
            return False
        return self.get_user(self.bootstrap_admin_username) is None

    def validate_username(self, username):
        if not super().validate_username(username):
            return False
        if (
            self._bootstrap_admin_pending()
            and username
            and username != self.bootstrap_admin_username
        ):
            return False
        return True

    def get_handlers(self, app):
        return [
            (path, BootstrapAdminSignUpHandler if path == r"/signup" else handler)
            for path, handler in super().get_handlers(app)
        ]

    def create_user(self, username, password, **kwargs):
        pending = self._bootstrap_admin_pending()
        user_info = super().create_user(username, password, **kwargs)
        if (
            user_info is not None
            and pending
            and self.bootstrap_admin_username
            and self.normalize_username(username)
            == self.normalize_username(self.bootstrap_admin_username)
        ):
            user_info.is_authorized = True
            self.db.commit()
        return user_info
