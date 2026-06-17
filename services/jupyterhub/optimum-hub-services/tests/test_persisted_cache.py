"""Tests for the shared last-known persisted cache helper.

Covers the round-trip, the TTL gate (JUPYTERHUB_CACHED_DATA_TTL_MINUTES, in
minutes), atomic write, and the best-effort failure paths (missing / corrupt
file return None, never raise).
"""

import json
from datetime import datetime, timezone, timedelta

import pytest

from optimum_hub_services import persisted_cache as pc


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("JUPYTERHUB_CACHED_DATA_TTL_MINUTES", raising=False)
    return tmp_path


def test_round_trip_seeds(_data_dir):
    data = {"alice": {"total": 12.3, "volumes": {"home": 12.3}}}
    pc.save_cached("widget", data)
    assert (_data_dir / "widget.json").exists()
    loaded = pc.load_cached("widget")
    assert loaded is not None
    got, ts = loaded
    assert got == data
    assert isinstance(ts, datetime)


def test_atomic_write_leaves_no_temp(_data_dir):
    pc.save_cached("widget", {"a": 1})
    leftovers = [p.name for p in _data_dir.iterdir() if p.name.startswith(".widget-")]
    assert leftovers == []


def test_missing_file_returns_none(_data_dir):
    assert pc.load_cached("never-written") is None


def test_corrupt_file_returns_none(_data_dir):
    (_data_dir / "broken.json").write_text("{not json")
    assert pc.load_cached("broken") is None


def test_ttl_gate_minutes(_data_dir, monkeypatch):
    path = _data_dir / "widget.json"
    # 90 minutes old, TTL 60 minutes -> too stale -> None
    monkeypatch.setenv("JUPYTERHUB_CACHED_DATA_TTL_MINUTES", "60")
    old = datetime.now(timezone.utc) - timedelta(minutes=90)
    path.write_text(json.dumps({"timestamp": old.isoformat(), "data": {"a": 1}}))
    assert pc.load_cached("widget") is None
    # 30 minutes old, same TTL -> still good
    recent = datetime.now(timezone.utc) - timedelta(minutes=30)
    path.write_text(json.dumps({"timestamp": recent.isoformat(), "data": {"a": 1}}))
    loaded = pc.load_cached("widget")
    assert loaded is not None and loaded[0] == {"a": 1}


def test_default_ttl_is_24h(_data_dir):
    path = _data_dir / "widget.json"
    # 23h old is within the default 1440-minute TTL
    ok = datetime.now(timezone.utc) - timedelta(hours=23)
    path.write_text(json.dumps({"timestamp": ok.isoformat(), "data": {"a": 1}}))
    assert pc.load_cached("widget") is not None
    # 25h old is past it
    stale = datetime.now(timezone.utc) - timedelta(hours=25)
    path.write_text(json.dumps({"timestamp": stale.isoformat(), "data": {"a": 1}}))
    assert pc.load_cached("widget") is None


def test_save_never_raises_on_bad_dir(monkeypatch):
    # an unwritable data dir degrades silently (best-effort), never raises
    monkeypatch.setenv("JUPYTERHUB_DATA_DIR", "/nonexistent/path/should/not/exist")
    pc.save_cached("widget", {"a": 1})  # must not raise
    assert pc.load_cached("widget") is None
