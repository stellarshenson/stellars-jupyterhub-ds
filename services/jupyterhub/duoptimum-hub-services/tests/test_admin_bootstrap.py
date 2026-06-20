"""Tests for admin_bootstrap.py.

query_admin_state: config-load state read (raw sqlite3, no ORM yet).
provision_admin_userinfo: authenticator-init provisioning (real ORM session +
NativeAuth UserInfo, the exact path the hub takes).
"""

import sqlite3

import bcrypt

import itertools

from duoptimum_hub_services.admin_bootstrap import (
    admin_unreachable,
    bootstrap_window_open,
    first_admin_self_signup_pending,
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


def _orm_session(path):
    """Real SQLAlchemy session with NativeAuth's users_info table - the init-time path
    (NativeAuthenticator.add_new_table() creates this table before provisioning runs)."""
    from nativeauthenticator.orm import UserInfo
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(f"sqlite:///{path}")
    UserInfo.__table__.create(engine)
    return sessionmaker(bind=engine)()


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
    def test_missing_admin_is_inserted_and_authorized(self, tmp_path):
        from nativeauthenticator.orm import UserInfo
        db = _orm_session(str(tmp_path / "jh.sqlite"))
        provision_admin_userinfo(db, "admin", "secret-pw")
        user = UserInfo.find(db, "admin")
        assert user is not None
        assert user.is_authorized is True
        assert user.is_valid_password("secret-pw")  # bcrypt hash matches a normal signup

    def test_existing_initial_password_is_noop(self, tmp_path):
        from nativeauthenticator.orm import UserInfo
        db = _orm_session(str(tmp_path / "jh.sqlite"))
        hashed = bcrypt.hashpw(b"secret-pw", bcrypt.gensalt())
        db.add(UserInfo(username="admin", password=hashed, is_authorized=True))
        db.commit()
        provision_admin_userinfo(db, "admin", "secret-pw")
        assert UserInfo.find(db, "admin").password == hashed  # unchanged

    def test_admin_changed_password_is_left_alone(self, tmp_path):
        from nativeauthenticator.orm import UserInfo
        db = _orm_session(str(tmp_path / "jh.sqlite"))
        changed = bcrypt.hashpw(b"new-user-chosen-pw", bcrypt.gensalt())
        db.add(UserInfo(username="admin", password=changed, is_authorized=True))
        db.commit()
        provision_admin_userinfo(db, "admin", "secret-pw")  # env no longer matches
        assert UserInfo.find(db, "admin").password == changed  # not overwritten

    def test_empty_password_is_noop(self, tmp_path):
        from nativeauthenticator.orm import UserInfo
        db = _orm_session(str(tmp_path / "jh.sqlite"))
        provision_admin_userinfo(db, "admin", "")
        assert UserInfo.find(db, "admin") is None

    def test_empty_username_is_noop(self, tmp_path):
        from nativeauthenticator.orm import UserInfo
        db = _orm_session(str(tmp_path / "jh.sqlite"))
        provision_admin_userinfo(db, "", "secret-pw")
        assert UserInfo.all_users(db) == []


class TestFirstAdminSelfSignupPending:
    def test_no_admin_row_pending(self, tmp_path):
        # fresh DB, no env provisioning -> the admin's self-signup must self-authorise
        db = _orm_session(str(tmp_path / "jh.sqlite"))
        assert first_admin_self_signup_pending(db, "admin", provisioning_requested=False) is True

    def test_admin_present_not_pending(self, tmp_path):
        from nativeauthenticator.orm import UserInfo
        db = _orm_session(str(tmp_path / "jh.sqlite"))
        db.add(UserInfo(username="admin", password=b"x", is_authorized=True))
        db.commit()
        assert first_admin_self_signup_pending(db, "admin", provisioning_requested=False) is False

    def test_env_provisioning_takes_precedence(self, tmp_path):
        # env-password path owns provisioning -> self-signup auto-authorise stays off
        db = _orm_session(str(tmp_path / "jh.sqlite"))
        assert first_admin_self_signup_pending(db, "admin", provisioning_requested=True) is False

    def test_no_admin_username_not_pending(self, tmp_path):
        db = _orm_session(str(tmp_path / "jh.sqlite"))
        assert first_admin_self_signup_pending(db, "", provisioning_requested=False) is False

    def test_other_users_present_admin_absent_still_pending(self, tmp_path):
        # signup-on default with existing non-admin users but no admin yet -> still pending
        from nativeauthenticator.orm import UserInfo
        db = _orm_session(str(tmp_path / "jh.sqlite"))
        db.add(UserInfo(username="alice", password=b"x", is_authorized=False))
        db.commit()
        assert first_admin_self_signup_pending(db, "admin", provisioning_requested=False) is True


def _creation_path(signup, prov, db_empty, admin_present):
    """How a first admin comes to exist in a given startup state - the model the policy
    functions must agree with. Exactly one of: admin already there, env provision, the
    signup-off bootstrap window, normal signup, or FAIL (no path)."""
    window = bootstrap_window_open(signup, prov, db_empty, admin_present)
    fail = admin_unreachable(signup, prov, admin_present, window)
    if admin_present:
        return "present"
    if fail:
        return "fail"
    if prov:
        return "env"
    if window:
        return "window"
    if signup == 1:
        return "signup"
    return "HOLE"  # must never happen


class TestBootstrapPolicyMatrix:
    """Exhaustive policy proof over signup x provisioning x db_empty x admin_present.
    Covers both fresh (db_empty) and existing-users (not db_empty) deployments."""

    STATES = list(itertools.product((0, 1), (False, True), (True, False), (True, False)))

    def test_every_state_has_exactly_one_outcome_no_holes(self):
        for signup, prov, db_empty, admin_present in self.STATES:
            path = _creation_path(signup, prov, db_empty, admin_present)
            assert path != "HOLE", (signup, prov, db_empty, admin_present)

    def test_window_only_when_signup_off_fresh_no_env_no_admin(self):
        for signup, prov, db_empty, admin_present in self.STATES:
            expected = (signup == 0 and not prov and db_empty and not admin_present)
            assert bootstrap_window_open(signup, prov, db_empty, admin_present) is expected

    def test_failfast_exactly_when_no_admin_and_no_path(self):
        # fail iff: signup off, no env, no admin, DB not empty (window can't open)
        for signup, prov, db_empty, admin_present in self.STATES:
            window = bootstrap_window_open(signup, prov, db_empty, admin_present)
            expected = (signup == 0 and not prov and not admin_present and not db_empty)
            assert admin_unreachable(signup, prov, admin_present, window) is expected

    def test_failfast_never_when_admin_present(self):
        for signup, prov, db_empty in itertools.product((0, 1), (False, True), (True, False)):
            window = bootstrap_window_open(signup, prov, db_empty, admin_present=True)
            assert admin_unreachable(signup, prov, True, window) is False

    def test_signup_on_always_has_a_path(self):
        # the shipped default (signup on) never fails and never leaves the admin uncreatable
        for prov, db_empty, admin_present in itertools.product((False, True), (True, False), (True, False)):
            assert _creation_path(1, prov, db_empty, admin_present) != "fail"

    def test_existing_users_no_admin_signup_off_no_env_fails(self):
        # the recovery footgun: DB has users, admin row deleted, signup off, no env pw
        assert _creation_path(0, False, db_empty=False, admin_present=False) == "fail"

    def test_fresh_signup_off_no_env_opens_window(self):
        assert _creation_path(0, False, db_empty=True, admin_present=False) == "window"

    def test_env_password_provisions_regardless_of_signup(self):
        for signup, db_empty in itertools.product((0, 1), (True, False)):
            assert _creation_path(signup, True, db_empty, admin_present=False) == "env"
