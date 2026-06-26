"""Unit tests for the platform event-log store."""

import sqlite3

import pytest

from duoptimum_hub_services.event_log import EventLogManager, record_event
import duoptimum_hub_services.event_log as event_log


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setenv('STELLARS_EVENT_LOG_DB_PATH', str(tmp_path / 'event_log.sqlite'))
    EventLogManager._instance = None
    mgr = EventLogManager.get_instance()
    yield mgr
    EventLogManager._instance = None


def test_record_then_recent_newest_first(manager):
    manager.record('user', '<b>alice</b> was created')
    manager.record('group', 'Group <b>research</b> created')
    rows = manager.recent()
    assert len(rows) == 2
    assert rows[0]['text'] == 'Group <b>research</b> created'  # newest first
    assert rows[0]['type'] == 'group'
    assert rows[1]['type'] == 'user'
    assert all('ts' in r and 'id' in r for r in rows)


def test_recent_respects_limit(manager):
    for i in range(10):
        manager.record('user', f'event {i}')
    assert len(manager.recent(limit=3)) == 3


def test_record_event_helper_never_raises(monkeypatch):
    # point at an unwritable path so the manager would fail; helper must swallow it
    monkeypatch.setenv('STELLARS_EVENT_LOG_DB_PATH', '/proc/nonexistent/cannot.sqlite')
    EventLogManager._instance = None
    record_event('user', 'should not raise')  # no exception escapes
    EventLogManager._instance = None


def test_table_is_pruned_to_max_rows(manager, monkeypatch):
    monkeypatch.setattr(event_log, '_MAX_ROWS', 5)
    for i in range(12):
        manager.record('user', f'event {i}')
    rows = manager.recent(limit=100)
    assert len(rows) == 5
    assert rows[0]['text'] == 'event 11'  # newest retained


def test_clear_empties_the_log(manager):
    manager.record('user', 'one')
    manager.record('group', 'two')
    removed = manager.clear()
    assert removed == 2
    assert manager.recent() == []
    # log keeps working after a clear
    manager.record('user', 'three')
    assert [r['text'] for r in manager.recent()] == ['three']


def test_clear_empty_log_is_noop(manager):
    assert manager.clear() == 0
    assert manager.recent() == []


def test_record_persists_optional_icon(manager):
    # a per-event glyph override (e.g. a server STOP) round-trips; absent one, icon is ''
    manager.record('user', '<b>bob</b> was created')  # no icon -> type default on the client
    manager.record('server', '<b>alice</b> server stopped', icon='stop')  # newest
    rows = manager.recent()
    assert rows[0]['icon'] == 'stop'  # newest first
    assert rows[1]['icon'] == ''


def test_legacy_table_without_icon_is_migrated(tmp_path, monkeypatch):
    # an `events` table created before the icon column existed must be migrated in place
    # (create_all never adds columns); new rows then carry an icon, old rows read ''
    db = tmp_path / 'event_log.sqlite'
    conn = sqlite3.connect(str(db))
    conn.execute('CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts VARCHAR(40) NOT NULL, type VARCHAR(40) NOT NULL, text TEXT)')
    conn.execute("INSERT INTO events (ts, type, text) VALUES ('2026-01-01T00:00:00+00:00', 'user', 'legacy row')")
    conn.commit()
    conn.close()
    monkeypatch.setenv('STELLARS_EVENT_LOG_DB_PATH', str(db))
    EventLogManager._instance = None
    try:
        mgr = EventLogManager.get_instance()
        mgr.record('server', '<b>alice</b> server stopped', icon='stop')
        rows = mgr.recent()
        newest = rows[0]
        assert newest['text'] == '<b>alice</b> server stopped'
        assert newest['icon'] == 'stop'
        legacy = next(r for r in rows if r['text'] == 'legacy row')
        assert legacy['icon'] == ''  # migrated column is NULL for the pre-existing row
    finally:
        EventLogManager._instance = None
