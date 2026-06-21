"""Functional: spawned labs + CHP reach the hub by a STABLE network alias, not the
hub's ephemeral container id, so a hub redeploy (new id) does not strand running labs.

Default regime. The hub config sets hub_connect_url host = JUPYTERHUB_LABEL_CONTAINER_ROLE_HUB
('hub'); compose stamps that value as a hub_network alias AND as the hub's hub.container.role
label. This test proves the label, the alias, and live DNS + reachability from a peer on the
same network (the test runner itself) at the exact host:port hub_connect_url uses. Regression
guard for DEF-22 (socket.gethostname() baked an unstable id into JUPYTERHUB_API_URL).
"""

import os
import socket
import urllib.request
from urllib.parse import urlparse

import pytest

HUB = "stellars-functest-duoptimum-hub"
ALIAS = "hub"
HUB_PORT = 8080  # c.JupyterHub.hub_port - the internal API port hub_connect_url targets
BASE_PREFIX = urlparse(os.environ.get("BASE_URL", "http://duoptimum-hub:8000/jupyterhub")).path.rstrip("/")


def _hub_network_ips(docker_client):
    hub = docker_client.containers.get(HUB)
    nets = hub.attrs["NetworkSettings"]["Networks"]
    return {n["IPAddress"] for n in nets.values() if n.get("IPAddress")}


@pytest.mark.acc_crit("duoptimumhub::Functional: hub reachable by stable alias")
def test_hub_carries_container_role_label(docker_client):
    # compose stamps the hub's own role label, parallel to the gpuinfo sidecar's
    hub = docker_client.containers.get(HUB)
    assert (hub.labels or {}).get("hub.container.role") == ALIAS


@pytest.mark.acc_crit("duoptimumhub::Functional: hub reachable by stable alias")
def test_hub_network_alias_present(docker_client):
    # the stable alias must be on a hub network, else hub_connect_url cannot resolve
    hub = docker_client.containers.get(HUB)
    aliases = []
    for n in hub.attrs["NetworkSettings"]["Networks"].values():
        aliases += (n.get("Aliases") or [])
    assert ALIAS in aliases, f"stable hub alias '{ALIAS}' on no hub network: {aliases}"


@pytest.mark.acc_crit("duoptimumhub::Functional: hub reachable by stable alias")
def test_hub_alias_resolves_to_hub_ip(docker_client):
    # the runner is on the test network; resolving the alias must hit the hub container
    resolved = socket.gethostbyname(ALIAS)
    hub_ips = _hub_network_ips(docker_client)
    assert resolved in hub_ips, f"alias '{ALIAS}' -> {resolved}, not a hub IP {hub_ips}"


@pytest.mark.acc_crit("duoptimumhub::Functional: hub reachable by stable alias")
def test_hub_api_reachable_via_alias():
    # the exact host:port spawned labs/CHP use (hub_connect_url) must answer unauthenticated
    url = f"http://{ALIAS}:{HUB_PORT}{BASE_PREFIX}/hub/api"
    with urllib.request.urlopen(url, timeout=5) as r:
        assert r.status == 200, f"{url} -> {r.status}"
