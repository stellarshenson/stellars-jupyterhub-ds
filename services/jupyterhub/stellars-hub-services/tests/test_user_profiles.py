"""Unit tests for the user-profile store (first/last name + email persistence)."""

import os

import pytest

from stellars_hub_services.user_profiles import UserProfileManager


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
    assert p == {'username': 'alice', 'first_name': '', 'last_name': '', 'email': ''}


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
    assert manager.get_profile('bob') == {'username': 'bob', 'first_name': '', 'last_name': '', 'email': ''}


def test_db_uses_overridden_path(manager, tmp_path):
    manager.save_profile('carol', first_name='Carol')
    assert os.path.exists(str(tmp_path / 'user_profiles.sqlite'))
