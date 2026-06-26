"""Tests for make_post_stop_hook (duoptimum_hub_services.hooks).

The post-stop cleanup was moved out of jupyterhub_config.py into a factory beside
its pre-spawn twin. It must: pass the configured socket_dir to unregister_user,
release the api-key reservation, record a stop event - and be fully best-effort
(a failure in any step must never propagate and block a server stop).
"""

import asyncio

from duoptimum_hub_services import hooks
from duoptimum_hub_services.hooks import make_post_stop_hook


class _FakeUser:
    def __init__(self, name):
        self.name = name


class _FakeLog:
    def __init__(self):
        self.warnings = []

    def warning(self, *a, **k):
        self.warnings.append((a, k))


class _FakeSpawner:
    def __init__(self, name="alice"):
        self.user = _FakeUser(name)
        self.log = _FakeLog()


def test_returns_async_callable():
    assert asyncio.iscoroutinefunction(make_post_stop_hook(socket_dir="/run/x"))


def test_happy_path_calls_all_three(monkeypatch):
    calls = {}

    async def fake_unregister(name, socket_dir=None):
        calls['unregister'] = (name, socket_dir)

    class _Pool:
        @staticmethod
        def get_instance():
            class _Inst:
                def release_tentative(self, name):
                    calls['release'] = name
            return _Inst()

    def fake_record(kind, msg, icon=None):
        calls['event'] = (kind, msg, icon)

    monkeypatch.setattr(hooks, "unregister_user", fake_unregister)
    monkeypatch.setattr(hooks, "PoolManager", _Pool)
    monkeypatch.setattr(hooks, "record_event", fake_record)

    sp = _FakeSpawner("alice")
    asyncio.run(make_post_stop_hook(socket_dir="/run/sockets")(sp))

    assert calls['unregister'] == ("alice", "/run/sockets")  # configured socket_dir threaded through
    assert calls['release'] == "alice"
    assert calls['event'][0] == 'server' and 'alice' in calls['event'][1]
    assert calls['event'][2] == 'stop'  # per-event glyph: a stop reads as a stop, not the type-default play
    assert sp.log.warnings == []  # no warnings on the happy path


def test_best_effort_swallows_all_failures(monkeypatch):
    async def boom_unregister(name, socket_dir=None):
        raise RuntimeError("proxy down")

    class _Pool:
        @staticmethod
        def get_instance():
            raise RuntimeError("pool down")

    def boom_record(kind, msg, icon=None):
        raise RuntimeError("db down")

    monkeypatch.setattr(hooks, "unregister_user", boom_unregister)
    monkeypatch.setattr(hooks, "PoolManager", _Pool)
    monkeypatch.setattr(hooks, "record_event", boom_record)

    sp = _FakeSpawner("bob")
    # must not raise even though every dependency fails
    asyncio.run(make_post_stop_hook(socket_dir="/run/sockets")(sp))
    # unregister + api-key failures log a warning each; the event failure is silent
    assert len(sp.log.warnings) == 2
