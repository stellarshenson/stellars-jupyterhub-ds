"""Tests for TimingDockerSpawner's failed-start event recording.

super().start() is stubbed (no real Docker) so we exercise only the wrapper:
a raised spawn records exactly one 'error' event and re-raises; a successful
spawn records nothing; the username is HTML-escaped (event text is pre-escaped).
"""

import asyncio

import pytest
from dockerspawner import DockerSpawner

from duoptimum_hub_services import timing_spawner
from duoptimum_hub_services.timing_spawner import TimingDockerSpawner


class _FakeUser:
    def __init__(self, name="alice"):
        self.name = name


class _FakeLog:
    def info(self, *a, **k):
        pass


def _make_spawner(name="alice"):
    # skip DockerSpawner's heavy __init__ - we only drive the start() wrapper
    sp = TimingDockerSpawner.__new__(TimingDockerSpawner)
    sp.user = _FakeUser(name)
    sp.log = _FakeLog()
    return sp


def _capture_events(monkeypatch):
    calls = []
    monkeypatch.setattr(timing_spawner, "record_event", lambda et, text: calls.append((et, text)))
    return calls


def test_failed_start_records_one_error_event_and_reraises(monkeypatch):
    sp = _make_spawner()
    calls = _capture_events(monkeypatch)

    async def boom(self, *a, **k):
        raise RuntimeError("nvidia prestart 500")

    monkeypatch.setattr(DockerSpawner, "start", boom)
    with pytest.raises(RuntimeError):
        asyncio.run(sp.start())
    assert len(calls) == 1
    assert calls[0][0] == "error"
    assert "alice" in calls[0][1]
    assert "failed to start" in calls[0][1]


def test_successful_start_records_no_event(monkeypatch):
    sp = _make_spawner()
    calls = _capture_events(monkeypatch)

    async def ok(self, *a, **k):
        return ("1.2.3.4", 8888)

    monkeypatch.setattr(DockerSpawner, "start", ok)
    assert asyncio.run(sp.start()) == ("1.2.3.4", 8888)
    assert calls == []


def test_failed_start_escapes_username(monkeypatch):
    sp = _make_spawner(name="<script>")
    calls = _capture_events(monkeypatch)

    async def boom(self, *a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(DockerSpawner, "start", boom)
    with pytest.raises(RuntimeError):
        asyncio.run(sp.start())
    assert "&lt;script&gt;" in calls[0][1]
    assert "<script>" not in calls[0][1]
