"""Integration tests: real proxy in front of a mock Docker daemon.

The mock daemon listens on a unix socket, records every request it receives,
and returns canned responses. The proxy is served over TCP via aiohttp's
TestServer so requests are easy to drive. Asserts the labeling / filtering /
quota / cap contract end to end.
"""

import contextlib
import json
import os
import tempfile

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from stellars_docker_proxy.config import (
    BYTES_PER_GB,
    MANAGED_LABEL,
    NANO_PER_CORE,
    OWNER_LABEL,
)
from stellars_docker_proxy.filters import COMPOSE_PROJECT_LABEL
from stellars_docker_proxy.server import create_app


class MockDaemon:
    """Records requests; returns configured or default responses."""

    def __init__(self):
        self.requests = []
        self.responses = {}  # (method, path) -> (status, payload)
        self._runner = None
        self.sockpath = None

    async def _handler(self, request):
        raw = await request.read()
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = None
        self.requests.append({
            "method": request.method,
            "path": request.path,
            "query": dict(request.rel_url.query),
            "body": body,
        })
        status, payload = self.responses.get((request.method, request.path), (200, {"ok": True}))
        return web.json_response(payload, status=status)

    def set(self, method, path, payload, status=200):
        self.responses[(method, path)] = (status, payload)

    def find(self, method, path):
        return [r for r in self.requests if r["method"] == method and r["path"] == path]

    async def start(self):
        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", self._handler)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self.sockpath = os.path.join(tempfile.mkdtemp(), "docker.sock")
        await web.UnixSite(self._runner, self.sockpath).start()

    async def stop(self):
        if self._runner:
            await self._runner.cleanup()


@contextlib.asynccontextmanager
async def running_proxy(owner="alice", **cfg_kwargs):
    from stellars_docker_proxy.config import ProxyConfig

    daemon = MockDaemon()
    await daemon.start()
    config = ProxyConfig(
        owner=owner,
        listen_socket="/tmp/_proxy_test_unused.sock",
        upstream_socket=daemon.sockpath,
        **cfg_kwargs,
    )
    app = await create_app(config)
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        yield client, daemon, config
    finally:
        await client.close()
        await daemon.stop()


async def test_create_injects_labels_caps_name_and_project():
    async with running_proxy(owner="alice", compose_project="jhub") as (client, daemon, _):
        daemon.set("POST", "/containers/create", {"Id": "abc"}, status=201)
        resp = await client.post("/containers/create", params={"name": "web"},
                                 json={"Image": "python:3.12"})
        assert resp.status == 201
        rec = daemon.find("POST", "/containers/create")[0]
        body = rec["body"]
        assert body["Labels"][OWNER_LABEL] == "alice"
        assert body["Labels"][MANAGED_LABEL] == "true"
        assert body["Labels"][COMPOSE_PROJECT_LABEL] == "jhub"
        assert body["HostConfig"]["NanoCpus"] == int(2.0 * NANO_PER_CORE)
        assert body["HostConfig"]["Memory"] == int(8.0 * BYTES_PER_GB)
        assert rec["query"]["name"] == "user-alice-web"


async def test_create_respects_user_compose():
    async with running_proxy(owner="alice", compose_project="jhub") as (client, daemon, _):
        daemon.set("POST", "/containers/create", {"Id": "x"}, status=201)
        await client.post(
            "/containers/create",
            params={"name": "myproj-web-1"},
            json={"Image": "x", "Labels": {COMPOSE_PROJECT_LABEL: "myproj"}},
        )
        rec = daemon.find("POST", "/containers/create")[0]
        assert rec["body"]["Labels"][COMPOSE_PROJECT_LABEL] == "myproj"  # preserved
        assert rec["body"]["Labels"][OWNER_LABEL] == "alice"            # still owned
        assert rec["query"]["name"] == "myproj-web-1"                   # not prefixed


async def test_create_privileged_rejected():
    async with running_proxy(owner="alice") as (client, daemon, _):
        resp = await client.post("/containers/create",
                                 json={"Image": "x", "HostConfig": {"Privileged": True}})
        assert resp.status == 403
        assert daemon.find("POST", "/containers/create") == []  # never forwarded


async def test_create_over_cpu_cap_rejected():
    async with running_proxy(owner="alice") as (client, daemon, _):
        resp = await client.post(
            "/containers/create",
            json={"Image": "x", "HostConfig": {"NanoCpus": 4 * NANO_PER_CORE}},
        )
        assert resp.status == 403
        assert daemon.find("POST", "/containers/create") == []


async def test_create_quota_reached_rejected():
    async with running_proxy(owner="alice", max_containers=2) as (client, daemon, _):
        daemon.set("GET", "/containers/json", [{"Id": "1"}, {"Id": "2"}])
        resp = await client.post("/containers/create", json={"Image": "x"})
        assert resp.status == 403
        assert daemon.find("POST", "/containers/create") == []


async def test_list_injects_owner_filter():
    async with running_proxy(owner="alice") as (client, daemon, _):
        daemon.set("GET", "/containers/json", [])
        resp = await client.get("/containers/json",
                                params={"filters": json.dumps({"status": ["running"]})})
        assert resp.status == 200
        flt = json.loads(daemon.find("GET", "/containers/json")[-1]["query"]["filters"])
        assert f"{OWNER_LABEL}=alice" in flt["label"]
        assert flt["status"] == ["running"]


async def test_action_on_foreign_container_404():
    async with running_proxy(owner="alice") as (client, daemon, _):
        daemon.set("GET", "/containers/c1/json", {"Config": {"Labels": {OWNER_LABEL: "bob"}}})
        resp = await client.post("/containers/c1/stop")
        assert resp.status == 404
        assert daemon.find("POST", "/containers/c1/stop") == []  # not forwarded


async def test_action_on_owned_container_forwarded():
    async with running_proxy(owner="alice") as (client, daemon, _):
        daemon.set("GET", "/containers/c1/json", {"Config": {"Labels": {OWNER_LABEL: "alice"}}})
        daemon.set("POST", "/containers/c1/stop", {}, status=200)
        resp = await client.post("/containers/c1/stop")
        assert resp.status == 200
        assert daemon.find("POST", "/containers/c1/stop")


async def test_prune_scoped_to_owner():
    async with running_proxy(owner="alice") as (client, daemon, _):
        daemon.set("POST", "/containers/prune", {"ContainersDeleted": []})
        resp = await client.post("/containers/prune")
        assert resp.status == 200
        flt = json.loads(daemon.find("POST", "/containers/prune")[-1]["query"]["filters"])
        assert f"{OWNER_LABEL}=alice" in flt["label"]


async def test_passthrough_untouched():
    async with running_proxy(owner="alice") as (client, daemon, _):
        daemon.set("GET", "/version", {"Version": "99"})
        resp = await client.get("/version")
        assert resp.status == 200
        assert (await resp.json())["Version"] == "99"
        assert "filters" not in daemon.find("GET", "/version")[-1]["query"]
