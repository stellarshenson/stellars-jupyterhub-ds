"""Tests for admin_bootstrap.py - first-admin bootstrap DB queries (raw sqlite3)."""

import sqlite3

import bcrypt

from duoptimum_hub_services.admin_bootstrap import (
    provision_admin_userinfo,
    query_admin_state,
)


def _make_db(path, rows=None):
    """Create a minimal users_info table; rows = [(username, password, is_authorized)]."""
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "CREATE TABLE users_info (username TEXT, password BLOB, is_authorized INTEGER)"
        )
        for r in rows or []:
            conn.execute("INSERT INTO users_info VALUES (?, ?, ?)", r)
        conn.commit()
    finally:
        conn.close()


def _password_of(path, username):
    conn = sqlite3.connect(path)
    try:
        cur = conn.execute("SELECT password FROM users_info WHERE username = ?", (username,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


class TestQueryAdminState:
    def test_no_db_file_opens_window(self, tmp_path):
        missing = str(tmp_path / "nope.sqlite")
        assert query_admin_state("admin", missing) == (True, False)

    def test_no_users_info_table_opens_window(self, tmp_path):
        path = str(tmp_path / "jh.sqlite")
        sqlite3.connect(path).close()  # file exists, no table
        assert query_admin_state("admin", path) == (True, False)

    def test_empty_table_is_empty_no_admin(self, tmp_path):
        path = str(tmp_path / "jh.sqlite")
        _make_db(path)
        assert query_admin_state("admin", path) == (True, False)

    def test_admin_present(self, tmp_path):
        path = str(tmp_path / "jh.sqlite")
        _make_db(path, [("admin", b"x", 1)])
        assert query_admin_state("admin", path) == (False, True)

    def test_other_user_no_admin(self, tmp_path):
        path = str(tmp_path / "jh.sqlite")
        _make_db(path, [("alice", b"x", 1)])
        assert query_admin_state("admin", path) == (False, False)

    def test_empty_username_opens_window(self, tmp_path):
        path = str(tmp_path / "jh.sqlite")
        _make_db(path, [("alice", b"x", 1)])
        assert query_admin_state("", path) == (True, False)


class TestProvisionAdminUserinfo:
    def test_no_db_is_noop(self, tmp_path):
        missing = str(tmp_path / "nope.sqlite")
        provision_admin_userinfo("admin", "pw", missing)  # must not raise

    def test_no_table_is_noop(self, tmp_path):
        path = str(tmp_path / "jh.sqlite")
        sqlite3.connect(path).close()
        provision_admin_userinfo("admin", "pw", path)  # must not raise

    def test_missing_admin_is_inserted_and_authorized(self, tmp_path):
        path = str(tmp_path / "jh.sqlite")
        _make_db(path)
        provision_admin_userinfo("admin", "secret-pw", path)
        stored = _password_of(path, "admin")
        assert stored is not None
        blob = stored.encode() if isinstance(stored, str) else stored
        assert bcrypt.checkpw(b"secret-pw", blob)
        conn = sqlite3.connect(path)
        try:
            auth = conn.execute(
                "SELECT is_authorized FROM users_info WHERE username = 'admin'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert auth == 1

    def test_existing_initial_password_is_noop(self, tmp_path):
        path = str(tmp_path / "jh.sqlite")
        hashed = bcrypt.hashpw(b"secret-pw", bcrypt.gensalt())
        _make_db(path, [("admin", hashed, 1)])
        provision_admin_userinfo("admin", "secret-pw", path)
        assert _password_of(path, "admin") == hashed  # unchanged

    def test_admin_changed_password_is_left_alone(self, tmp_path):
        path = str(tmp_path / "jh.sqlite")
        changed = bcrypt.hashpw(b"new-user-chosen-pw", bcrypt.gensalt())
        _make_db(path, [("admin", changed, 1)])
        provision_admin_userinfo("admin", "secret-pw", path)  # env no longer matches
        assert _password_of(path, "admin") == changed  # not overwritten

    def test_empty_password_is_noop(self, tmp_path):
        path = str(tmp_path / "jh.sqlite")
        _make_db(path)
        provision_admin_userinfo("admin", "", path)
        assert _password_of(path, "admin") is None
