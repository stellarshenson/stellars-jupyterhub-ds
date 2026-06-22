"""Functional: spawned labs + CHP reach the hub by its compose SERVICE NAME - the
stable Docker DNS alias compose registers on every net the hub joins - NOT a
hand-stamped alias, and NOT the hub's ephemeral container id.

The hub is multi-homed (lab net + gpuinfo net). The fix advertises the service name
via c.JupyterHub.hub_connect_ip (advertise-ONLY) and keeps c.JupyterHub.hub_ip
"0.0.0.0" so the API binds ALL interfaces incl. the lab net. The prior bug used
hub_connect_url, which ALSO drives the bind: JupyterHub resolved its host FROM the
multi-homed hub and landed on the gpuinfo IP, binding the API off the lab net so labs
got connection refused. This suite reproduces the multi-homing and guards the bind.

The lab net (stellars-functest_network) is named to sort AFTER the gpuinfo net
(stellars-functest_gpuinfo_network), so the hub's self-name would resolve to the
gpuinfo IP if hub_connect_url were ever reintroduced - the exact bug condition. The
lab-net-IP:8080 reachability assertion is what FAILS on a mis-bind regression.
"""

import os
import socket
import urllib.request
from urllib.parse import urlparse

import pytest

HUB = "stellars-functest-duoptimum-hub"
LAB_NET = "stellars-functest_network"          # role=lab net; labs + test runner live here
HUB_PORT = 8080  # c.JupyterHub.hub_port - the internal API port labs/CHP target
BASE_PREFIX = urlparse(os.environ.get("BASE_URL", "http://duoptimum-hub:8000/jupyterhub")).path.rstrip("/")


def _hub(docker_client):
    return docker_client.containers.get(HUB)


def _service_name(docker_client):
    # the hub advertises THIS (its own compose service name) via hub_connect_ip;
    # it is the DNS name labs/CHP reach the hub by - discover it the way the hub does.
    name = (_hub(docker_client).labels or {}).get("com.docker.compose.service")
    assert name, "hub container has no com.docker.compose.service label"
    return name


def _hub_networks(docker_client):
    return _hub(docker_client).attrs["NetworkSettings"]["Networks"]


def _hub_lab_net_ip(docker_client):
    nets = _hub_networks(docker_client)
    net = nets.get(LAB_NET)
    assert net and net.get("IPAddress"), f"hub has no IP on the lab net {LAB_NET}: {list(nets)}"
    return net["IPAddress"]


@pytest.mark.acc_crit("duoptimumhub::Functional: hub reachable by service name")
def test_hub_is_multi_homed(docker_client):
    # the guard is only meaningful on a multi-homed hub: a single-net hub can never
    # mis-bind off the lab net, so this asserts the bug condition is reproducible.
    nets = _hub_networks(docker_client)
    assert len(nets) > 1, f"hub is not multi-homed (mis-bind cannot happen): {list(nets)}"


@pytest.mark.acc_crit("duoptimumhub::Functional: hub reachable by service name")
def test_hub_has_no_handstamped_alias(docker_client):
    # the fix dropped the hand-stamped 'hub' alias: reachability must ride the service
    # name's DNS, not an alias. Docker auto-registers the service name, the container id
    # (full + short) and the explicit container_name as aliases; nothing hand-stamped
    # (specifically 'hub') should be present.
    hub = _hub(docker_client)
    service = (hub.labels or {}).get("com.docker.compose.service")
    cid_short = hub.id[:12]
    allowed = {service, hub.id, cid_short, HUB}
    for net_name, net in _hub_networks(docker_client).items():
        aliases = set(net.get("Aliases") or [])
        assert "hub" not in aliases, f"hand-stamped 'hub' alias still on {net_name}: {aliases}"
        extra = aliases - allowed
        assert not extra, f"unexpected aliases on {net_name}: {extra} (only service name + id allowed)"


@pytest.mark.acc_crit("duoptimumhub::Functional: hub reachable by service name")
def test_service_name_resolves_to_lab_net_ip(docker_client):
    # the runner is on the lab net; resolving the service name must hit the hub's
    # LAB-net IP specifically (not merely any hub IP) - else labs on the lab net would
    # reach the hub at an address that may be off their net.
    service = _service_name(docker_client)
    resolved = socket.gethostbyname(service)
    lab_ip = _hub_lab_net_ip(docker_client)
    assert resolved == lab_ip, f"service '{service}' -> {resolved}, not the hub's lab-net IP {lab_ip}"


@pytest.mark.acc_crit("duoptimumhub::Functional: hub reachable by service name")
def test_api_binds_the_lab_interface(docker_client):
    # the bind assertion: hit the hub's LAB-net IP directly (not the name). 200 proves
    # the API is listening on the lab interface. If someone reintroduces hub_connect_url
    # and the API mis-binds off the lab net, this connection is refused.
    lab_ip = _hub_lab_net_ip(docker_client)
    url = f"http://{lab_ip}:{HUB_PORT}{BASE_PREFIX}/hub/api"
    with urllib.request.urlopen(url, timeout=5) as r:
        assert r.status == 200, f"{url} -> {r.status}"


@pytest.mark.acc_crit("duoptimumhub::Functional: hub reachable by service name")
def test_api_reachable_via_service_name(docker_client):
    # the exact host:port spawned labs/CHP use (service name = hub_connect_ip) must
    # answer unauthenticated.
    service = _service_name(docker_client)
    url = f"http://{service}:{HUB_PORT}{BASE_PREFIX}/hub/api"
    with urllib.request.urlopen(url, timeout=5) as r:
        assert r.status == 200, f"{url} -> {r.status}"
