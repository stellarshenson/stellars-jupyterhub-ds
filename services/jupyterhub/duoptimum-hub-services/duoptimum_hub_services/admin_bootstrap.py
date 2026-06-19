"""First-admin bootstrap DB queries against NativeAuthenticator's ``users_info`` table.

Extracted from ``jupyterhub_config.py``: the config orchestrates bootstrap *policy*
(which mode, when the window is open), but the raw SQL belongs in the service layer.
These run at config-load time - before the hub's SQLAlchemy engine exists - so they
use stdlib ``sqlite3`` directly rather than the ORM.

The DB path defaults to ``/data/jupyterhub.sqlite``; override with the
``STELLARS_JUPYTERHUB_DB_PATH`` env var (tests point it at a temp file).
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


def provision_admin_userinfo(admin_username, admin_password, db_path=DEFAULT_DB_PATH):
    """Bootstrap-by-env: seed admin UserInfo from ``JUPYTERHUB_ADMIN_PASSWORD``.

    Initial-only semantics:
      - missing UserInfo                        -> INSERT bcrypt(env), is_authorized=1
      - exists, env still verifies against hash -> no-op (already initial)
      - exists, env does NOT verify             -> leave alone (admin has changed it)
    """
    import bcrypt
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
            hashed = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
            cur.execute(
                "INSERT INTO users_info (username, password, is_authorized) VALUES (?, ?, 1)",
                (admin_username, hashed),
            )
            conn.commit()
            print(f"[Admin Bootstrap] Provisioned '{admin_username}' from JUPYTERHUB_ADMIN_PASSWORD", flush=True)
            return
        stored = row[0].encode('utf-8') if isinstance(row[0], str) else row[0]
        try:
            still_initial = bcrypt.checkpw(admin_password.encode('utf-8'), stored)
        except Exception:
            still_initial = False
        if not still_initial:
            print(f"[Admin Bootstrap] '{admin_username}' has changed their password; JUPYTERHUB_ADMIN_PASSWORD ignored", flush=True)
    finally:
        conn.close()
