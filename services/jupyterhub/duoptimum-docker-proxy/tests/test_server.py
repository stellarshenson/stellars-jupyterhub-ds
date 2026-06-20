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

from duoptimum_docker_proxy.config import (
    BYTES_PER_GB,
    NANO_PER_CORE,
    OWNER_LABEL,
)
from duoptimum_docker_proxy.filters import COMPOSE_PROJECT_LABEL
from duoptimum_docker_proxy.server import create_app


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
    from duoptimum_docker_proxy.config import ProxyConfig

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


async def test_empty_post_body_not_chunk_encoded_upstream():
    # Regression: POST /containers/<id>/start with empty body. Forwarding
    # request.content as data= used to make aiohttp upgrade to chunked
    # transfer-encoding (terminating 0\r\n\r\n) which dockerd rejects as a
    # "non-empty request body" on endpoints that ban bodies (start removed
    # body support in Docker API v1.24). After the fix, _forward checks
    # request.body_exists and passes None for empty-body requests.
    async with running_proxy(owner="alice") as (client, daemon, _):
        daemon.set("GET", "/containers/c1/json", {"Config": {"Labels": {OWNER_LABEL: "alice"}}})
        daemon.set("POST", "/containers/c1/start", {}, status=204)
        # No json= / data= -> aiohttp client sends Content-Length: 0 and no body.
        resp = await client.post("/containers/c1/start")
        assert resp.status == 204
        rec = daemon.find("POST", "/containers/c1/start")[-1]
        # The upstream call must NOT have a parsed body. (MockDaemon returns
        # body=None on empty/un-decodable payloads; the failure mode would be
        # an empty dict or a chunked body causing JSON parse to differ.)
        assert rec["body"] is None


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


# ---------------------------------------------------------------------------
# Per-flag bypasses and reveal toggles surfaced from ProxyConfig.
# Confirms the server picks up each new field independently and enriches /
# rewrites requests as designed.
# ---------------------------------------------------------------------------


async def test_create_privileged_allowed_when_allow_privileged_true():
    # ProxyConfig.allow_privileged=True opens ONLY the Privileged check.
    # Body must reach the daemon with Privileged=True preserved.
    async with running_proxy(owner="alice", allow_privileged=True) as (client, daemon, _):
        daemon.set("POST", "/containers/create", {"Id": "p"}, status=201)
        resp = await client.post(
            "/containers/create",
            json={"Image": "x", "HostConfig": {"Privileged": True}},
        )
        assert resp.status == 201
        rec = daemon.find("POST", "/containers/create")[0]
        assert rec["body"]["HostConfig"]["Privileged"] is True
        assert rec["body"]["Labels"][OWNER_LABEL] == "alice"


async def test_create_host_bind_still_rejected_when_only_allow_privileged():
    # allow_privileged on its own must NOT also unlock host binds.
    async with running_proxy(owner="alice", allow_privileged=True) as (client, daemon, _):
        resp = await client.post(
            "/containers/create",
            json={"Image": "x", "HostConfig": {"Binds": ["/etc:/etc"]}},
        )
        assert resp.status == 403
        assert daemon.find("POST", "/containers/create") == []


async def test_create_host_bind_allowed_when_allow_dangerous_flags_true():
    # allow_dangerous_flags lets a host bind through.
    async with running_proxy(owner="alice", allow_dangerous_flags=True) as (client, daemon, _):
        daemon.set("POST", "/containers/create", {"Id": "hb"}, status=201)
        resp = await client.post(
            "/containers/create",
            json={"Image": "x", "HostConfig": {"Binds": ["/etc:/etc"]}},
        )
        assert resp.status == 201
        rec = daemon.find("POST", "/containers/create")[0]
        assert rec["body"]["HostConfig"]["Binds"] == ["/etc:/etc"]


async def test_create_privileged_still_rejected_when_only_allow_dangerous_flags():
    # allow_dangerous_flags must NOT also unlock Privileged.
    async with running_proxy(owner="alice", allow_dangerous_flags=True) as (client, daemon, _):
        resp = await client.post(
            "/containers/create",
            json={"Image": "x", "HostConfig": {"Privileged": True}},
        )
        assert resp.status == 403
        assert daemon.find("POST", "/containers/create") == []


async def test_create_both_bypass_flags_open_privileged_and_host_bind_together():
    async with running_proxy(
        owner="alice", allow_privileged=True, allow_dangerous_flags=True,
    ) as (client, daemon, _):
        daemon.set("POST", "/containers/create", {"Id": "b"}, status=201)
        resp = await client.post(
            "/containers/create",
            json={
                "Image": "x",
                "HostConfig": {
                    "Privileged": True,
                    "Binds": ["/etc:/etc"],
                    "CapAdd": ["SYS_ADMIN"],
                },
            },
        )
        assert resp.status == 201
        body = daemon.find("POST", "/containers/create")[0]["body"]
        assert body["HostConfig"]["Privileged"] is True
        assert body["HostConfig"]["Binds"] == ["/etc:/etc"]
        assert body["HostConfig"]["CapAdd"] == ["SYS_ADMIN"]


async def test_create_compose_project_strict_rewrites_user_label():
    # allow_compose_project_override=False forces every container under the
    # configured per-user project, regardless of what the user typed.
    async with running_proxy(
        owner="alice", compose_project="alice-proj", allow_compose_project_override=False,
    ) as (client, daemon, _):
        daemon.set("POST", "/containers/create", {"Id": "s"}, status=201)
        resp = await client.post(
            "/containers/create",
            params={"name": "myproj-web-1"},
            json={"Image": "x", "Labels": {COMPOSE_PROJECT_LABEL: "myproj"}},
        )
        assert resp.status == 201
        body = daemon.find("POST", "/containers/create")[0]["body"]
        assert body["Labels"][COMPOSE_PROJECT_LABEL] == "alice-proj"  # REWRITTEN
        assert body["Labels"][OWNER_LABEL] == "alice"


async def test_create_compose_project_default_override_respects_user_label():
    # allow_compose_project_override=True (default): user-supplied label kept.
    async with running_proxy(
        owner="alice", compose_project="alice-proj",
    ) as (client, daemon, _):
        daemon.set("POST", "/containers/create", {"Id": "s"}, status=201)
        await client.post(
            "/containers/create",
            json={"Image": "x", "Labels": {COMPOSE_PROJECT_LABEL: "myproj"}},
        )
        body = daemon.find("POST", "/containers/create")[0]["body"]
        assert body["Labels"][COMPOSE_PROJECT_LABEL] == "myproj"  # untouched


async def test_create_no_compose_project_means_no_label_stamp():
    # compose_project='' (off-mode) leaves ad-hoc containers free-floating.
    async with running_proxy(owner="alice", compose_project="") as (client, daemon, _):
        daemon.set("POST", "/containers/create", {"Id": "f"}, status=201)
        await client.post("/containers/create", json={"Image": "x"})
        body = daemon.find("POST", "/containers/create")[0]["body"]
        assert COMPOSE_PROJECT_LABEL not in (body.get("Labels") or {})
        assert body["Labels"][OWNER_LABEL] == "alice"  # ownership unchanged


async def test_list_networks_default_owner_scoped_only():
    # Without extra_accessible_networks the path uses the injected-filter branch.
    # Daemon-side filter is applied by upstream; the proxy injects the label.
    async with running_proxy(owner="alice") as (client, daemon, _):
        daemon.set("GET", "/networks", [])
        resp = await client.get("/networks")
        assert resp.status == 200
        rec = daemon.find("GET", "/networks")[-1]
        flt = json.loads(rec["query"]["filters"])
        assert f"{OWNER_LABEL}=alice" in flt["label"]


async def test_list_networks_hub_net_revealed_via_extras():
    # extra_accessible_networks reveals a named network even though it's not owned.
    # Proxy MUST NOT pass an owner label filter to the upstream in this mode
    # (it post-filters in Python to OR ownership with the extras set).
    upstream_networks = [
        {"Name": "alice_net", "Labels": {OWNER_LABEL: "alice"}},
        {"Name": "stellars-tech-ai-lab_network", "Labels": {}},  # hub network
        {"Name": "bob_net", "Labels": {OWNER_LABEL: "bob"}},
        {"Name": "random_external", "Labels": {}},
    ]
    async with running_proxy(
        owner="alice",
        extra_accessible_networks=("stellars-tech-ai-lab_network",),
    ) as (client, daemon, _):
        daemon.set("GET", "/networks", upstream_networks)
        resp = await client.get("/networks")
        assert resp.status == 200
        revealed = await resp.json()
        names = {n["Name"] for n in revealed}
        assert names == {"alice_net", "stellars-tech-ai-lab_network"}
        # And critically: the upstream call carried no owner-label filter.
        rec = daemon.find("GET", "/networks")[-1]
        assert "filters" not in rec["query"] or (
            f"{OWNER_LABEL}=alice" not in json.loads(rec["query"]["filters"]).get("label", [])
        )


async def test_list_networks_extras_set_but_no_match_returns_owned_only():
    # extras configured but the hub network doesn't appear upstream -> owner only.
    upstream_networks = [
        {"Name": "alice_net", "Labels": {OWNER_LABEL: "alice"}},
        {"Name": "bob_net", "Labels": {OWNER_LABEL: "bob"}},
    ]
    async with running_proxy(
        owner="alice", extra_accessible_networks=("missing_network",),
    ) as (client, daemon, _):
        daemon.set("GET", "/networks", upstream_networks)
        resp = await client.get("/networks")
        revealed = await resp.json()
        assert [n["Name"] for n in revealed] == ["alice_net"]


async def test_list_containers_unchanged_by_extra_accessible_networks():
    # extra_accessible_networks must NOT bleed into containers listing.
    async with running_proxy(
        owner="alice", extra_accessible_networks=("stellars-tech-ai-lab_network",),
    ) as (client, daemon, _):
        daemon.set("GET", "/containers/json", [])
        await client.get("/containers/json")
        flt = json.loads(daemon.find("GET", "/containers/json")[-1]["query"]["filters"])
        assert f"{OWNER_LABEL}=alice" in flt["label"]


# ---------------------------------------------------------------------------
# Network-access enforcement on container create + action handler.
# Confirms the rename's new semantic: extra_accessible_networks gates list,
# action, AND create - non-allow-listed non-owned networks are 403 / 404'd.
# ---------------------------------------------------------------------------


async def test_create_passes_with_builtin_network_modes():
    # bridge / none / default / empty / container:* are always allowed,
    # regardless of the access allow-list.
    async with running_proxy(owner="alice") as (client, daemon, _):
        daemon.set("POST", "/containers/create", {"Id": "ok"}, status=201)
        for nm in ("", "default", "bridge", "none", "container:other-id"):
            resp = await client.post(
                "/containers/create",
                json={"Image": "x", "HostConfig": {"NetworkMode": nm}},
            )
            assert resp.status == 201, f"NetworkMode={nm!r} should pass"


async def test_create_rejects_non_owned_non_allow_listed_network_mode():
    # A bare network name that's neither built-in, owned, nor allow-listed
    # is rejected with 403 - no inspect/forward to the daemon for the create.
    async with running_proxy(owner="alice") as (client, daemon, _):
        # Inspect returns 200 with non-owner labels -> not owned.
        daemon.set("GET", "/networks/hub-net", {"Name": "hub-net", "Labels": {}})
        resp = await client.post(
            "/containers/create",
            json={"Image": "x", "HostConfig": {"NetworkMode": "hub-net"}},
        )
        assert resp.status == 403
        assert "network not accessible" in (await resp.json())["message"]
        assert daemon.find("POST", "/containers/create") == []


async def test_create_passes_when_network_in_extra_accessible_networks():
    # Allow-listed network passes without even hitting inspect.
    async with running_proxy(
        owner="alice", extra_accessible_networks=("hub-net",),
    ) as (client, daemon, _):
        daemon.set("POST", "/containers/create", {"Id": "ok"}, status=201)
        resp = await client.post(
            "/containers/create",
            json={"Image": "x", "HostConfig": {"NetworkMode": "hub-net"}},
        )
        assert resp.status == 201
        # No need to inspect because the name is in the allow-list.
        assert daemon.find("GET", "/networks/hub-net") == []


async def test_create_passes_when_network_is_owner_labelled():
    # Owned network passes via inspect.
    async with running_proxy(owner="alice") as (client, daemon, _):
        daemon.set("GET", "/networks/my-net", {
            "Name": "my-net", "Labels": {OWNER_LABEL: "alice"},
        })
        daemon.set("POST", "/containers/create", {"Id": "ok"}, status=201)
        resp = await client.post(
            "/containers/create",
            json={"Image": "x", "HostConfig": {"NetworkMode": "my-net"}},
        )
        assert resp.status == 201


async def test_create_rejects_unauthorized_network_in_endpoints_config():
    # NetworkingConfig.EndpointsConfig keys are checked the same way.
    async with running_proxy(owner="alice") as (client, daemon, _):
        daemon.set("GET", "/networks/hub-net", {"Name": "hub-net", "Labels": {}})
        resp = await client.post(
            "/containers/create",
            json={
                "Image": "x",
                "NetworkingConfig": {"EndpointsConfig": {"hub-net": {}}},
            },
        )
        assert resp.status == 403
        assert daemon.find("POST", "/containers/create") == []


async def test_create_passes_endpoints_config_with_allow_listed_network():
    async with running_proxy(
        owner="alice", extra_accessible_networks=("hub-net",),
    ) as (client, daemon, _):
        daemon.set("POST", "/containers/create", {"Id": "ok"}, status=201)
        resp = await client.post(
            "/containers/create",
            json={
                "Image": "x",
                "NetworkingConfig": {"EndpointsConfig": {"hub-net": {}}},
            },
        )
        assert resp.status == 201


async def test_network_action_allowed_on_allow_listed_network():
    # docker network connect <hub-net> <container> on an allow-listed network
    # must pass even though the network is not owned by alice.
    async with running_proxy(
        owner="alice", extra_accessible_networks=("hub-net",),
    ) as (client, daemon, _):
        daemon.set("GET", "/networks/hub-net", {"Name": "hub-net", "Labels": {}})
        daemon.set("POST", "/networks/hub-net/connect", {}, status=200)
        resp = await client.post(
            "/networks/hub-net/connect", json={"Container": "alice-web"},
        )
        assert resp.status == 200
        assert daemon.find("POST", "/networks/hub-net/connect")


async def test_network_action_404_on_non_owned_non_allow_listed():
    # Same scenario without the toggle -> 404, no forward.
    async with running_proxy(owner="alice") as (client, daemon, _):
        daemon.set("GET", "/networks/hub-net", {"Name": "hub-net", "Labels": {}})
        resp = await client.post(
            "/networks/hub-net/connect", json={"Container": "alice-web"},
        )
        assert resp.status == 404
        assert daemon.find("POST", "/networks/hub-net/connect") == []
