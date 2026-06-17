"""Unit tests for the platform event-log store."""

import pytest

from optimum_hub_services.event_log import EventLogManager, record_event
import optimum_hub_services.event_log as event_log


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
