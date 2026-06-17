"""Unit tests for the user-profile store (first/last name + email persistence)."""

import os

import pytest

from optimum_hub_services.user_profiles import UserProfileManager


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """A fresh manager backed by a temp SQLite file (never touches /data)."""
    monkeypatch.setenv('STELLARS_USER_PROFILES_DB_PATH', str(tmp_path / 'user_profiles.sqlite'))
    UserProfileManager._instance = None
    mgr = UserProfileManager.get_instance()
    yield mgr
    UserProfileManager._instance = None


def test_get_missing_returns_empty(manager):
    p = manager.get_profile('alice')
    assert p == {'username': 'alice', 'first_name': '', 'last_name': '', 'email': '', 'must_change_password': False}


def test_save_then_get_roundtrips(manager):
    manager.save_profile('alice', first_name='Alice', last_name='Nowak', email='alice@example.com')
    p = manager.get_profile('alice')
    assert p['first_name'] == 'Alice'
    assert p['last_name'] == 'Nowak'
    assert p['email'] == 'alice@example.com'


def test_partial_update_keeps_other_fields(manager):
    manager.save_profile('alice', first_name='Alice', last_name='Nowak', email='alice@example.com')
    manager.save_profile('alice', email='alice@lab.example')  # only email changes
    p = manager.get_profile('alice')
    assert p['first_name'] == 'Alice'
    assert p['last_name'] == 'Nowak'
    assert p['email'] == 'alice@lab.example'


def test_rename_moves_profile(manager):
    manager.save_profile('alice', first_name='Alice', last_name='Nowak')
    manager.rename_user('alice', 'alicia')
    assert manager.get_profile('alice')['first_name'] == ''  # old key empty
    assert manager.get_profile('alicia')['first_name'] == 'Alice'


def test_delete_removes_profile(manager):
    manager.save_profile('bob', first_name='Bob')
    manager.delete_profile('bob')
    assert manager.get_profile('bob') == {'username': 'bob', 'first_name': '', 'last_name': '', 'email': '', 'must_change_password': False}


def test_db_uses_overridden_path(manager, tmp_path):
    manager.save_profile('carol', first_name='Carol')
    assert os.path.exists(str(tmp_path / 'user_profiles.sqlite'))


# ── force-password-change flag ───────────────────────────────────────────────
def test_must_change_defaults_false(manager):
    assert manager.get_must_change_password('alice') is False
    manager.save_profile('alice', first_name='Alice')
    assert manager.get_profile('alice')['must_change_password'] is False


def test_set_must_change_creates_row_when_absent(manager):
    manager.set_must_change_password('newuser', True)
    assert manager.get_must_change_password('newuser') is True


def test_set_and_clear_must_change(manager):
    manager.save_profile('alice', first_name='Alice')
    manager.set_must_change_password('alice', True)
    assert manager.get_must_change_password('alice') is True
    assert manager.get_profile('alice')['must_change_password'] is True
    # clearing it leaves the rest of the profile intact
    manager.set_must_change_password('alice', False)
    assert manager.get_must_change_password('alice') is False
    assert manager.get_profile('alice')['first_name'] == 'Alice'


def test_save_profile_preserves_must_change(manager):
    # a profile edit (name/email) must not clobber the force-change flag
    manager.set_must_change_password('alice', True)
    manager.save_profile('alice', first_name='Alice', email='a@x.io')
    assert manager.get_must_change_password('alice') is True


def test_migration_adds_column_to_legacy_db(tmp_path, monkeypatch):
    """A pre-existing DB without the column gets it added (idempotent ALTER)."""
    import sqlalchemy
    db_path = str(tmp_path / 'legacy.sqlite')
    eng = sqlalchemy.create_engine(f'sqlite:///{db_path}')
    with eng.begin() as conn:
        conn.execute(sqlalchemy.text(
            'CREATE TABLE user_profiles (username VARCHAR(255) PRIMARY KEY, '
            'first_name TEXT, last_name TEXT, email TEXT)'))
        conn.execute(sqlalchemy.text(
            "INSERT INTO user_profiles (username, first_name) VALUES ('legacy', 'Old')"))
    eng.dispose()
    monkeypatch.setenv('STELLARS_USER_PROFILES_DB_PATH', db_path)
    UserProfileManager._instance = None
    mgr = UserProfileManager.get_instance()
    try:
        # the legacy row survives and the new column reads False
        assert mgr.get_profile('legacy')['first_name'] == 'Old'
        assert mgr.get_must_change_password('legacy') is False
        mgr.set_must_change_password('legacy', True)
        assert mgr.get_must_change_password('legacy') is True
    finally:
        UserProfileManager._instance = None
