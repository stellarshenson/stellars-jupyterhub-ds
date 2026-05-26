"""Tests for the central-mode Manager: per-user listener lifecycle.

These tests don't need a real Docker daemon; they use a stub upstream socket
inside a temp dir. We only verify the lifecycle - listener spins up, the
socket file appears with the expected mode, idempotent re-register replaces,
and unregister tears it down.
"""

import os
import stat

import pytest

from stellars_docker_proxy.manager import Manager


@pytest.fixture
def socket_dir(tmp_path):
    return str(tmp_path / "sockets")


@pytest.fixture
def upstream(tmp_path):
    # An empty file is fine; the manager never connects upstream from these
    # tests (no requests flow through the per-user app).
    p = tmp_path / "upstream.sock"
    p.write_bytes(b"")
    return str(p)


@pytest.mark.asyncio
async def test_register_creates_socket_with_expected_mode(socket_dir, upstream):
    mgr = Manager(socket_dir=socket_dir, upstream_socket=upstream)
    try:
        path = await mgr.register("alice")
        assert path == os.path.join(socket_dir, "alice.sock")
        assert os.path.exists(path)
        # default socket_mode is 0o666 (world rw)
        mode = stat.S_IMODE(os.stat(path).st_mode)
        assert mode == 0o666
        assert mgr.is_registered("alice")
    finally:
        await mgr.close()


@pytest.mark.asyncio
async def test_register_uses_overrides(socket_dir, upstream):
    mgr = Manager(socket_dir=socket_dir, upstream_socket=upstream)
    try:
        await mgr.register("alice", overrides={
            "max_containers": 3, "max_volumes": 2, "compose_project": "demo",
        })
        info = mgr.registered()
        assert len(info) == 1
        cfg = info[0]["config"]
        assert cfg["max_containers"] == 3
        assert cfg["max_volumes"] == 2
        assert cfg["compose_project"] == "demo"
    finally:
        await mgr.close()


@pytest.mark.asyncio
async def test_register_is_idempotent_replace(socket_dir, upstream):
    mgr = Manager(socket_dir=socket_dir, upstream_socket=upstream)
    try:
        await mgr.register("alice", overrides={"max_containers": 3})
        await mgr.register("alice", overrides={"max_containers": 5})
        info = mgr.registered()
        assert len(info) == 1
        assert info[0]["config"]["max_containers"] == 5
        assert os.path.exists(os.path.join(socket_dir, "alice.sock"))
    finally:
        await mgr.close()


@pytest.mark.asyncio
async def test_unregister_removes_socket(socket_dir, upstream):
    mgr = Manager(socket_dir=socket_dir, upstream_socket=upstream)
    try:
        await mgr.register("alice")
        path = os.path.join(socket_dir, "alice.sock")
        assert os.path.exists(path)
        removed = await mgr.unregister("alice")
        assert removed is True
        assert not os.path.exists(path)
        assert not mgr.is_registered("alice")
    finally:
        await mgr.close()


@pytest.mark.asyncio
async def test_unregister_unknown_is_noop(socket_dir, upstream):
    mgr = Manager(socket_dir=socket_dir, upstream_socket=upstream)
    try:
        removed = await mgr.unregister("nobody")
        assert removed is False
    finally:
        await mgr.close()


@pytest.mark.asyncio
async def test_multiple_users_independent(socket_dir, upstream):
    mgr = Manager(socket_dir=socket_dir, upstream_socket=upstream)
    try:
        await mgr.register("alice", overrides={"max_containers": 1})
        await mgr.register("bob", overrides={"max_containers": 9})
        info = {r["user"]: r for r in mgr.registered()}
        assert info["alice"]["config"]["max_containers"] == 1
        assert info["bob"]["config"]["max_containers"] == 9
        assert os.path.exists(os.path.join(socket_dir, "alice.sock"))
        assert os.path.exists(os.path.join(socket_dir, "bob.sock"))
        await mgr.unregister("alice")
        assert mgr.is_registered("bob")
        assert not mgr.is_registered("alice")
    finally:
        await mgr.close()


@pytest.mark.asyncio
async def test_close_tears_everything_down(socket_dir, upstream):
    mgr = Manager(socket_dir=socket_dir, upstream_socket=upstream)
    await mgr.register("alice")
    await mgr.register("bob")
    assert len(mgr.registered()) == 2
    await mgr.close()
    assert mgr.registered() == []
    assert not os.path.exists(os.path.join(socket_dir, "alice.sock"))
    assert not os.path.exists(os.path.join(socket_dir, "bob.sock"))


@pytest.mark.asyncio
async def test_register_rejects_empty_user(socket_dir, upstream):
    mgr = Manager(socket_dir=socket_dir, upstream_socket=upstream)
    try:
        with pytest.raises(ValueError):
            await mgr.register("")
    finally:
        await mgr.close()
