"""First-admin bootstrap helpers against NativeAuthenticator's ``users_info`` table.

Two phases, two DB access styles by necessity:

- ``query_admin_state`` runs at *config-load*, before the hub's SQLAlchemy engine
  exists, so it reads the sqlite file directly with stdlib ``sqlite3``.
- ``provision_admin_userinfo`` runs at *authenticator-init*, where the ORM and the
  ``users_info`` table both exist (``NativeAuthenticator.__init__`` creates it), so it
  uses the authenticator's own session + UserInfo model.

The config orchestrates bootstrap *policy* (which mode, window open, when to fail
fast); this module is the data layer.

``query_admin_state``'s DB path defaults to ``/data/jupyterhub.sqlite``; override with
``STELLARS_JUPYTERHUB_DB_PATH`` (tests point it at a temp file).
"""

import os
import sqlite3

DEFAULT_DB_PATH = os.environ.get('STELLARS_JUPYTERHUB_DB_PATH', '/data/jupyterhub.sqlite')


def query_admin_state(admin_username, db_path=DEFAULT_DB_PATH):
    """Return ``(db_empty, admin_present)`` at startup.

    ``db_empty`` is True iff ``users_info`` has zero rows (or doesn't exist yet).
    ``admin_present`` is True iff a UserInfo row for ``admin_username`` exists.
    First-ever boot (no DB file) reports ``(True, False)`` so the bootstrap window opens.
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


def provision_admin_userinfo(db, admin_username, admin_password):
    """Bootstrap-by-env: seed admin UserInfo from ``JUPYTERHUB_ADMIN_PASSWORD``.

    Runs at authenticator-init, not config-load: ``NativeAuthenticator.__init__`` runs
    ``add_new_table()`` first -> ``users_info`` guaranteed to exist (no table-creation
    race). Uses the authenticator's own session + UserInfo model so the stored bcrypt
    hash matches a normal signup byte-for-byte.

    Initial-only:
      - no row            -> INSERT bcrypt(env), is_authorized=1, log the creation
      - row, env verifies -> no-op (still the initial password)
      - row, env differs  -> leave alone (admin changed it; env permanently ignored)

    Never logs the password. Creation line fires only when the admin row is absent.
    """
    import bcrypt
    from nativeauthenticator.orm import UserInfo
    if not admin_username or not admin_password:
        return
    user = UserInfo.find(db, admin_username)
    if user is None:
        print(
            f"[Admin Bootstrap] JUPYTERHUB_ADMIN_PASSWORD provided; "
            f"creating admin '{admin_username}' (initial password)",
            flush=True,
        )
        hashed = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
        db.add(UserInfo(username=admin_username, password=hashed, is_authorized=True))
        db.commit()
        return
    if not user.is_valid_password(admin_password):
        print(
            f"[Admin Bootstrap] '{admin_username}' has changed their password; "
            f"JUPYTERHUB_ADMIN_PASSWORD ignored",
            flush=True,
        )


def bootstrap_window_open(signup_enabled, provisioning_requested, db_empty, admin_present):
    """Is the one-shot signup-off bootstrap window open?

    When signup is off and no env password is set, a fresh empty DB with no admin
    re-opens signup scoped to the admin name so the first admin can self-register.
    Pure policy - no DB access (state is read once by query_admin_state at config-load).
    """
    return (
        signup_enabled == 0
        and not provisioning_requested
        and db_empty
        and not admin_present
    )


def admin_unreachable(signup_enabled, provisioning_requested, admin_present, window_open):
    """Is there NO way to obtain a first admin (-> fail fast)?

    signup off (no normal signup) AND no env password (no pre-provision) AND no admin
    row AND the bootstrap window can't open (DB already has users). Booting in this state
    yields a locked-out, adminless hub - worse than refusing to boot. Pure policy.
    """
    return (
        signup_enabled == 0
        and not provisioning_requested
        and not admin_present
        and not window_open
    )


def first_admin_self_signup_pending(db, admin_username, provisioning_requested):
    """Should the admin's OWN self-signup be auto-authorised right now?

    True when the configured admin has no row yet and env-password provisioning is not
    in use - no other admin exists to authorise them, so the self-signup must
    self-authorise or the first admin is locked out (is_authorized=False, NativeAuth
    refuses login). Deliberately independent of JUPYTERHUB_SIGNUP_ENABLED: it covers
    BOTH normal signup (on) and the re-opened bootstrap window (off). Signup
    availability is gated upstream by enable_signup, so reaching create_user means
    signup was allowed. Mutually exclusive with the env path via provisioning_requested.

    Runs at request-time (ORM up); checked live so it flips off the moment the admin
    row appears.
    """
    from nativeauthenticator.orm import UserInfo
    if not admin_username or provisioning_requested:
        return False
    return UserInfo.find(db, admin_username) is None
