"""Tests for the central-mode admin HTTP API.

Black-box: build the admin app against a real Manager, drive it via aiohttp's
TestClient. Verifies auth, register-replace, unregister-noop, and the listing
endpoint shape.
"""

import os

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from stellars_docker_proxy.admin import create_admin_app
from stellars_docker_proxy.manager import Manager


TOKEN = "test-secret"


@pytest.fixture
def upstream(tmp_path):
    p = tmp_path / "upstream.sock"
    p.write_bytes(b"")
    return str(p)


@pytest.fixture
async def client(tmp_path, upstream):
    mgr = Manager(socket_dir=str(tmp_path / "sockets"), upstream_socket=upstream)
    app = create_admin_app(mgr, TOKEN)
    server = TestServer(app)
    async with TestClient(server) as c:
        yield c
    await mgr.close()


def _auth(token=TOKEN):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_requires_auth(client):
    resp = await client.post("/admin/registered/alice")
    assert resp.status == 401
    body = await resp.json()
    assert body == {"error": "unauthorized"}


@pytest.mark.asyncio
async def test_register_wrong_token_rejected(client):
    resp = await client.post("/admin/registered/alice", headers=_auth("nope"))
    assert resp.status == 401


@pytest.mark.asyncio
async def test_register_then_list(client, tmp_path):
    resp = await client.post(
        "/admin/registered/alice",
        json={"overrides": {"max_containers": 3}},
        headers=_auth(),
    )
    assert resp.status == 200
    body = await resp.json()
    assert body["user"] == "alice"
    assert body["socket_path"].endswith("alice.sock")
    assert os.path.exists(body["socket_path"])

    resp = await client.get("/admin/registered", headers=_auth())
    assert resp.status == 200
    listing = await resp.json()
    assert len(listing["users"]) == 1
    assert listing["users"][0]["user"] == "alice"
    assert listing["users"][0]["config"]["max_containers"] == 3


@pytest.mark.asyncio
async def test_register_replace_updates_quotas(client):
    await client.post(
        "/admin/registered/alice",
        json={"overrides": {"max_containers": 3}},
        headers=_auth(),
    )
    resp = await client.post(
        "/admin/registered/alice",
        json={"overrides": {"max_containers": 7}},
        headers=_auth(),
    )
    assert resp.status == 200

    listing = await (await client.get("/admin/registered", headers=_auth())).json()
    assert len(listing["users"]) == 1
    assert listing["users"][0]["config"]["max_containers"] == 7


@pytest.mark.asyncio
async def test_unregister_removes(client):
    body = await (
        await client.post("/admin/registered/alice", json={}, headers=_auth())
    ).json()
    sock = body["socket_path"]
    assert os.path.exists(sock)

    resp = await client.delete("/admin/registered/alice", headers=_auth())
    assert resp.status == 200
    assert (await resp.json()) == {"removed": True}
    assert not os.path.exists(sock)


@pytest.mark.asyncio
async def test_unregister_unknown_is_noop(client):
    resp = await client.delete("/admin/registered/ghost", headers=_auth())
    assert resp.status == 200
    assert (await resp.json()) == {"removed": False}


@pytest.mark.asyncio
async def test_register_invalid_overrides_returns_400(client):
    resp = await client.post(
        "/admin/registered/alice",
        json={"overrides": {"unknown_field": 1}},
        headers=_auth(),
    )
    assert resp.status == 400


@pytest.mark.asyncio
async def test_register_empty_body_uses_defaults(client):
    resp = await client.post("/admin/registered/alice", headers=_auth())
    assert resp.status == 200
    listing = await (await client.get("/admin/registered", headers=_auth())).json()
    cfg = listing["users"][0]["config"]
    assert cfg["max_containers"] == 10  # ProxyConfig default
    assert cfg["max_volumes"] == 10
    assert cfg["max_networks"] == 3


@pytest.mark.asyncio
async def test_create_admin_app_requires_token():
    mgr = Manager(socket_dir="/tmp/_should_not_be_used", upstream_socket="/var/run/docker.sock")
    with pytest.raises(ValueError):
        create_admin_app(mgr, "")
    await mgr.close()
