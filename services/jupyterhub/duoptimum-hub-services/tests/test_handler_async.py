"""The Docker-touching handlers must not block the hub event loop.

RestartServerHandler.post, ServerLogsHandler.get and ManageVolumesHandler.delete
call blocking docker-py operations (container.restart blocks up to 10s+). These
run on the shared executor so one user's operation can't freeze the hub for every
other user. Each test records the thread the blocking call ran on and asserts it
is NOT the event-loop thread - that is the proof the offload actually happened.

Handlers are built via __new__ (skips RequestHandler.__init__, mirrors
test_user_url_redirect.py); only the attributes each method touches are stubbed.
"""

import asyncio
import json
import logging
import threading
from types import SimpleNamespace

import docker
import pytest
from tornado import web

from duoptimum_hub_services.handlers import server as server_mod
from duoptimum_hub_services.handlers import volumes as volumes_mod
from duoptimum_hub_services.handlers.server import RestartServerHandler, ServerLogsHandler
from duoptimum_hub_services.handlers.volumes import ManageVolumesHandler

_LOG = logging.getLogger("test_handler_async")


# ── fakes ────────────────────────────────────────────────────────────────────

class _FakeClient:
    """Fake docker client; records close() and raises the seeded error on get."""

    def __init__(self, container=None, volume=None, raise_on_get=None):
        self.closed = False
        self._raise = raise_on_get
        self.containers = SimpleNamespace(get=self._get_container)
        self.volumes = SimpleNamespace(get=self._get_volume)
        self._container = container
        self._volume = volume

    def _get_container(self, name):
        if self._raise:
            raise self._raise
        return self._container

    def _get_volume(self, name):
        if self._raise:
            raise self._raise
        return self._volume

    def close(self):
        self.closed = True


class _FakeContainer:
    def __init__(self, holder):
        self._h = holder

    def restart(self, timeout=None):
        self._h["thread"] = threading.get_ident()
        self._h["timeout"] = timeout

    def logs(self, tail=None, **kw):
        self._h["thread"] = threading.get_ident()
        return b"line-a\nline-b\nline-c"


class _FakeVolume:
    def __init__(self, holder):
        self._h = holder

    def remove(self):
        self._h["thread"] = threading.get_ident()


# ── restart ──────────────────────────────────────────────────────────────────

def _restart_handler():
    h = RestartServerHandler.__new__(RestartServerHandler)
    h.application = SimpleNamespace(settings={"log": _LOG})  # settings -> application.settings
    h._jupyterhub_user = SimpleNamespace(admin=True, name="admin")  # current_user reads this
    h.find_user = lambda u: SimpleNamespace(spawner=SimpleNamespace(active=True))
    cap = {}
    h.set_status = lambda code: cap.__setitem__("status", code)
    h.finish = lambda body=None: cap.__setitem__("body", body)
    return h, cap


def test_restart_offloads_blocking_call(monkeypatch):
    holder = {}
    client = _FakeClient(container=_FakeContainer(holder))
    monkeypatch.setattr(server_mod, "get_docker_client", lambda: client)
    h, cap = _restart_handler()

    asyncio.run(h.post("alice"))

    assert cap["status"] == 200
    assert "successfully restarted" in cap["body"]["message"]
    assert holder["timeout"] == 10  # restart(timeout=10) preserved
    assert client.closed is True
    # the fix: the blocking restart ran on an executor thread, not this one
    assert holder["thread"] != threading.get_ident()


def test_restart_not_found_maps_404_and_closes(monkeypatch):
    client = _FakeClient(raise_on_get=docker.errors.NotFound("nope"))
    monkeypatch.setattr(server_mod, "get_docker_client", lambda: client)
    h, _ = _restart_handler()

    with pytest.raises(web.HTTPError) as ei:
        asyncio.run(h.post("alice"))

    assert ei.value.status_code == 404
    assert client.closed is True  # finally ran on the error path


def test_restart_api_error_maps_500(monkeypatch):
    client = _FakeClient(raise_on_get=docker.errors.APIError("boom"))
    monkeypatch.setattr(server_mod, "get_docker_client", lambda: client)
    h, _ = _restart_handler()

    with pytest.raises(web.HTTPError) as ei:
        asyncio.run(h.post("alice"))

    assert ei.value.status_code == 500
    assert client.closed is True


# ── logs ─────────────────────────────────────────────────────────────────────

def _logs_handler():
    h = ServerLogsHandler.__new__(ServerLogsHandler)
    h.application = SimpleNamespace(settings={"log": _LOG})  # settings -> application.settings
    h._jupyterhub_user = SimpleNamespace(admin=True, name="admin")  # current_user reads this
    h.request = SimpleNamespace(method="GET")
    h.get_argument = lambda name, default=None: default
    cap = {}
    h.finish = lambda body=None: cap.__setitem__("body", body)
    return h, cap


def test_logs_offloads_and_returns_tail(monkeypatch):
    holder = {}
    client = _FakeClient(container=_FakeContainer(holder))
    monkeypatch.setattr(server_mod, "get_docker_client", lambda: client)
    h, cap = _logs_handler()

    asyncio.run(h.get("alice"))

    assert cap["body"] == {"lines": ["line-a", "line-b", "line-c"]}
    assert client.closed is True
    assert holder["thread"] != threading.get_ident()


def test_logs_not_found_maps_404(monkeypatch):
    client = _FakeClient(raise_on_get=docker.errors.NotFound("nope"))
    monkeypatch.setattr(server_mod, "get_docker_client", lambda: client)
    h, _ = _logs_handler()

    with pytest.raises(web.HTTPError) as ei:
        asyncio.run(h.get("alice"))

    assert ei.value.status_code == 404
    assert client.closed is True


# ── volume delete ────────────────────────────────────────────────────────────

def _delete_handler(body):
    h = ManageVolumesHandler.__new__(ManageVolumesHandler)
    h._jupyterhub_user = SimpleNamespace(admin=True, name="admin")  # current_user reads this
    h.find_user = lambda u: SimpleNamespace(spawner=SimpleNamespace(active=False))
    h.request = SimpleNamespace(body=json.dumps(body).encode())
    h.application = SimpleNamespace(settings={  # settings -> application.settings
        "log": _LOG,
        "stellars_config": {
            "user_volume_suffixes": ["home", "cache"],
            "user_volume_name_templates": {
                "home": "jupyterlab-{username}_home",
                "cache": "jupyterlab-{username}_cache",
            },
        },
    })
    cap = {}
    h.set_status = lambda code: cap.__setitem__("status", code)
    h.finish = lambda body=None: cap.__setitem__("body", body)
    return h, cap


def test_delete_offloads_removal(monkeypatch):
    holder = {}
    client = _FakeClient(volume=_FakeVolume(holder))
    monkeypatch.setattr(volumes_mod, "get_docker_client", lambda: client)
    monkeypatch.setattr(volumes_mod, "record_event", lambda *a, **k: None)
    h, cap = _delete_handler({"volumes": ["home"]})

    asyncio.run(h.delete("alice"))

    assert cap["status"] == 200
    assert cap["body"]["reset_volumes"] == ["home"]
    assert cap["body"]["failed_volumes"] == []
    assert client.closed is True
    assert holder["thread"] != threading.get_ident()


def test_delete_missing_volume_reported_not_raised(monkeypatch):
    client = _FakeClient(raise_on_get=docker.errors.NotFound("gone"))
    monkeypatch.setattr(volumes_mod, "get_docker_client", lambda: client)
    monkeypatch.setattr(volumes_mod, "record_event", lambda *a, **k: None)
    h, cap = _delete_handler({"volumes": ["home"]})

    asyncio.run(h.delete("alice"))

    assert cap["status"] == 200
    assert cap["body"]["reset_volumes"] == []
    assert cap["body"]["failed_volumes"] == [{"volume": "home", "reason": "not found"}]
    assert client.closed is True
