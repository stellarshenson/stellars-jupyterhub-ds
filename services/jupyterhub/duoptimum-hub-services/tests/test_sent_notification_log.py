"""Unit tests for the portal sent-notification history store (incl. boot self-heal)."""

import logging

import pytest
from sqlalchemy import create_engine, text

from duoptimum_hub_services.sent_notification_log import (
    SentNotificationLogManager,
    record_sent_notification,
)
import duoptimum_hub_services.sent_notification_log as snl


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setenv('STELLARS_SENT_NOTIFICATION_LOG_DB_PATH', str(tmp_path / 'sent.sqlite'))
    SentNotificationLogManager._instance = None
    mgr = SentNotificationLogManager.get_instance()
    yield mgr
    SentNotificationLogManager._instance = None


def test_record_then_recent_newest_first_portal_shape(manager):
    manager.record('first broadcast', 'info', 5, 6)
    manager.record('second broadcast', 'warning', 18, 18)
    rows = manager.recent()
    assert len(rows) == 2
    assert rows[0]['message'] == 'second broadcast'  # newest first
    assert rows[0]['type'] == 'warning'
    assert rows[0]['delivered'] == 18 and rows[0]['total'] == 18
    # portal row shape: id + sentISO (not raw ts), delivered/total ints
    assert all({'id', 'message', 'type', 'sentISO', 'delivered', 'total'} == set(r) for r in rows)


def test_recent_respects_limit(manager):
    for i in range(10):
        manager.record(f'b{i}', 'info', 1, 1)
    assert len(manager.recent(limit=3)) == 3


def test_clear_removes_all_rows_and_returns_count(manager):
    manager.record('a', 'info', 1, 1)
    manager.record('b', 'warning', 2, 2)
    assert manager.clear() == 2  # returns the count removed
    assert manager.recent() == []  # history emptied
    # the store is still usable after a clear (records append fresh)
    manager.record('c', 'success', 3, 3)
    assert [r['message'] for r in manager.recent()] == ['c']


def test_clear_on_empty_returns_zero(manager):
    assert manager.clear() == 0


def test_record_helper_never_raises(monkeypatch):
    # unwritable path: the manager would fail; the helper must swallow it
    monkeypatch.setenv('STELLARS_SENT_NOTIFICATION_LOG_DB_PATH', '/proc/nonexistent/cannot.sqlite')
    SentNotificationLogManager._instance = None
    record_sent_notification('should not raise', 'info', 0, 0)  # no exception escapes
    SentNotificationLogManager._instance = None


def test_table_is_pruned_to_max_rows(manager, monkeypatch):
    monkeypatch.setattr(snl, '_MAX_ROWS', 5)
    for i in range(12):
        manager.record(f'b{i}', 'info', 1, 1)
    rows = manager.recent(limit=100)
    assert len(rows) == 5
    assert rows[0]['message'] == 'b11'  # newest retained


def test_prepare_creates_table_when_absent(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv('STELLARS_SENT_NOTIFICATION_LOG_DB_PATH', str(tmp_path / 'fresh.sqlite'))
    SentNotificationLogManager._instance = None
    mgr = SentNotificationLogManager.get_instance()
    with caplog.at_level(logging.INFO, logger='jupyterhub.sent_notification_log'):
        mgr.prepare()
    # heal is logged, and the table is usable afterwards
    assert any('created' in r.message for r in caplog.records)
    mgr.record('hi', 'info', 3, 3)
    assert manager_first_message(mgr) == 'hi'
    SentNotificationLogManager._instance = None


def test_prepare_rebuilds_stale_inherited_table(tmp_path, monkeypatch, caplog):
    # simulate a /data DB inherited from an older deploy: a same-named table with a
    # stale schema missing our columns
    path = tmp_path / 'inherited.sqlite'
    eng = create_engine(f'sqlite:///{path}')
    with eng.begin() as conn:
        conn.execute(text('CREATE TABLE sent_notifications (id INTEGER PRIMARY KEY, legacy TEXT)'))
        conn.execute(text("INSERT INTO sent_notifications (legacy) VALUES ('old row')"))
    eng.dispose()

    monkeypatch.setenv('STELLARS_SENT_NOTIFICATION_LOG_DB_PATH', str(path))
    SentNotificationLogManager._instance = None
    mgr = SentNotificationLogManager.get_instance()
    with caplog.at_level(logging.WARNING, logger='jupyterhub.sent_notification_log'):
        mgr.prepare()
    # the repair is logged
    assert any('stale schema' in r.message for r in caplog.records)
    # rebuilt: stale data gone, new schema usable with all columns
    mgr.record('fresh', 'success', 1, 2)
    rows = mgr.recent()
    assert [r['message'] for r in rows] == ['fresh']
    assert rows[0]['delivered'] == 1 and rows[0]['total'] == 2
    SentNotificationLogManager._instance = None


def test_notification_types_canonical_set():
    # the types we send: info/success/warning/error/in-progress, and 'default' retired
    from duoptimum_hub_services.handlers.notifications import NOTIFICATION_TYPES
    assert set(NOTIFICATION_TYPES) == {'info', 'success', 'warning', 'error', 'in-progress'}
    assert 'default' not in NOTIFICATION_TYPES


def test_store_round_trips_every_sent_type(manager):
    # every type we broadcast must persist and read back unchanged
    from duoptimum_hub_services.handlers.notifications import NOTIFICATION_TYPES
    for t in NOTIFICATION_TYPES:
        manager.record(f'msg {t}', t, 1, 1)
    rows = manager.recent(limit=100)
    assert {r['type'] for r in rows} == set(NOTIFICATION_TYPES)


def test_prepare_preserves_good_schema(manager, caplog):
    manager.record('keep me', 'info', 1, 1)
    with caplog.at_level(logging.WARNING, logger='jupyterhub.sent_notification_log'):
        manager.prepare()  # schema already correct -> no rebuild, data preserved
    assert not any('rebuild' in r.message.lower() for r in caplog.records)
    assert [r['message'] for r in manager.recent()] == ['keep me']


def manager_first_message(mgr):
    rows = mgr.recent()
    return rows[0]['message'] if rows else None
