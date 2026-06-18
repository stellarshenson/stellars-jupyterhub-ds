"""Unit tests for the per-user display-preferences store (opaque JSON blob)."""

import os

import pytest

from duoptimum_hub_services.user_display_preferences import (
    MAX_PREFS_BYTES,
    UserDisplayPreferences,
    UserDisplayPreferencesManager,
)


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """A fresh manager backed by a temp SQLite file (never touches /data)."""
    monkeypatch.setenv('STELLARS_USER_DISPLAY_PREFS_DB_PATH', str(tmp_path / 'prefs.sqlite'))
    UserDisplayPreferencesManager._instance = None
    mgr = UserDisplayPreferencesManager.get_instance()
    yield mgr
    UserDisplayPreferencesManager._instance = None


def test_get_missing_returns_empty(manager):
    assert manager.get_prefs('alice') == {}


def test_save_then_get_roundtrips(manager):
    manager.save_prefs('alice', {'cpuModeServerStatus': 'cores', 'cpuModeHostStatus': 'normalized'})
    assert manager.get_prefs('alice') == {'cpuModeServerStatus': 'cores', 'cpuModeHostStatus': 'normalized'}


def test_partial_merge_keeps_other_keys(manager):
    manager.save_prefs('alice', {'cpuModeServerStatus': 'cores', 'cpuModeHostStatus': 'normalized'})
    manager.save_prefs('alice', {'cpuModeHostStatus': 'cores'})  # only one key changes
    assert manager.get_prefs('alice') == {'cpuModeServerStatus': 'cores', 'cpuModeHostStatus': 'cores'}


def test_save_returns_merged(manager):
    manager.save_prefs('alice', {'a': '1'})
    merged = manager.save_prefs('alice', {'b': '2'})
    assert merged == {'a': '1', 'b': '2'}


def test_save_rejects_non_dict(manager):
    with pytest.raises(ValueError):
        manager.save_prefs('alice', ['not', 'a', 'dict'])


def test_save_rejects_oversize(manager):
    with pytest.raises(ValueError):
        manager.save_prefs('alice', {'big': 'x' * (MAX_PREFS_BYTES + 1)})


def test_rename_moves_prefs(manager):
    manager.save_prefs('alice', {'cpuModeServerStatus': 'cores'})
    manager.rename_user('alice', 'alicia')
    assert manager.get_prefs('alice') == {}
    assert manager.get_prefs('alicia') == {'cpuModeServerStatus': 'cores'}


def test_delete_removes_prefs(manager):
    manager.save_prefs('bob', {'cpuModeServersList': 'normalized'})
    manager.delete_prefs('bob')
    assert manager.get_prefs('bob') == {}


def test_db_uses_overridden_path(manager, tmp_path):
    manager.save_prefs('carol', {'x': '1'})
    assert os.path.exists(str(tmp_path / 'prefs.sqlite'))


def test_corrupt_blob_reads_empty(manager):
    """A corrupt/non-object blob reads as no prefs rather than raising."""
    db = manager._get_db()
    try:
        db.add(UserDisplayPreferences(username='dave', prefs='{not valid json'))
        db.commit()
    finally:
        db.close()
    assert manager.get_prefs('dave') == {}
    # and a subsequent save still works (overwrites the corrupt blob)
    assert manager.save_prefs('dave', {'ok': '1'}) == {'ok': '1'}
