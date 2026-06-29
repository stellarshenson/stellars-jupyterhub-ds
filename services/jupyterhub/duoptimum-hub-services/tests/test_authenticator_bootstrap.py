"""Behavioural tests for DuoptimumNativeAuthenticator's first-admin bootstrap.

The pure decision functions are exhaustively covered in test_admin_bootstrap.py.
Here we instantiate the REAL authenticator (against a temp sqlite + a real NativeAuth
UserInfo session) to prove the orchestration that moved from config-load into the
authenticator's __init__ still behaves: env-provision, fail-fast when the admin is
unreachable, and the dynamic enable_signup / validate_username bootstrap window.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from nativeauthenticator.orm import UserInfo

from duoptimum_hub_services.auth import DuoptimumNativeAuthenticator


def _make(tmp_path, monkeypatch, rows=(), **traits):
    """Instantiate the authenticator against a fresh temp DB. `rows` pre-seeds
    UserInfo (username, is_authorized) tuples BEFORE init, so query_admin_state
    (raw sqlite on the same file) and the authenticator's own session agree.

    admin_password is sourced from os.environ['JUPYTERHUB_ADMIN_PASSWORD'] by the
    authenticator (it is NOT a config trait), so route an `admin_password=` test kwarg
    through the env; default-clear it so a leaked outer env never flips provisioning on."""
    db_path = str(tmp_path / "jh.sqlite")
    monkeypatch.setenv("STELLARS_JUPYTERHUB_DB_PATH", db_path)
    monkeypatch.delenv("JUPYTERHUB_ADMIN_PASSWORD", raising=False)
    pw = traits.pop("admin_password", None)
    if pw is not None:
        monkeypatch.setenv("JUPYTERHUB_ADMIN_PASSWORD", pw)
    engine = create_engine(f"sqlite:///{db_path}")
    UserInfo.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    for username, authorized in rows:
        session.add(UserInfo(username=username, password=b"x", is_authorized=authorized))
    session.commit()
    auth = DuoptimumNativeAuthenticator(db=session, **traits)
    return auth, session


def test_env_provision_creates_authorized_admin(tmp_path, monkeypatch):
    # JUPYTERHUB_ADMIN_PASSWORD on a fresh DB -> admin provisioned in __init__
    _, session = _make(tmp_path, monkeypatch, admin_username="admin", admin_password="secret-pw", signup_enabled=False)
    user = UserInfo.find(session, "admin")
    assert user is not None and user.is_authorized is True
    assert user.is_valid_password("secret-pw")  # bcrypt hash matches a normal signup


def test_whitespace_only_admin_password_does_not_provision(tmp_path, monkeypatch):
    # parity with the old stripped config: a whitespace-only secret -> '' -> NOT provisioning;
    # with signup off + empty DB the bootstrap window opens instead (admin self-signs up later)
    auth, session = _make(tmp_path, monkeypatch, admin_username="admin", admin_password="   \n", signup_enabled=False)
    assert UserInfo.find(session, "admin") is None      # not provisioned from whitespace
    assert auth.enable_signup is True                    # fell through to the bootstrap window


def test_fail_fast_when_admin_unreachable(tmp_path, monkeypatch):
    # signup off, no env password, DB already has a non-admin, admin absent -> no path
    with pytest.raises(SystemExit):
        _make(tmp_path, monkeypatch, rows=[("alice", False)], admin_username="admin", signup_enabled=False)


def test_bootstrap_window_enables_signup_until_admin_appears(tmp_path, monkeypatch):
    # signup off, no env password, fresh empty DB -> window open for the admin name only
    auth, session = _make(tmp_path, monkeypatch, admin_username="admin", signup_enabled=False)
    assert auth.enable_signup is True                    # window open, admin still pending
    assert auth.validate_username("admin") is True
    assert auth.validate_username("intruder") is False   # only the admin during the window
    # the admin signs up -> window closes the moment the row exists
    session.add(UserInfo(username="admin", password=b"x", is_authorized=True))
    session.commit()
    assert auth.enable_signup is False
    assert auth.validate_username("intruder") is True     # gate lifts once the admin exists


def test_signup_on_has_no_bootstrap_gate(tmp_path, monkeypatch):
    auth, _ = _make(tmp_path, monkeypatch, admin_username="admin", signup_enabled=True)
    assert auth.enable_signup is True
    assert auth.validate_username("anyone") is True        # no window when signup is on
