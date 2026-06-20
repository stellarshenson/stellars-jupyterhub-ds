"""Functional: role labels the hub discovers by, verified live over the docker socket.

Gated to the GPU stack (`make test-functional-gpu`) where hub_gpuinfo_network + the
hub-started gpuinfo sidecar exist. Asserts the net carries hub.network.role=gpuinfo
and the hub-created sidecar carries hub.container.role=gpuinfo - discovery-by-role +
the container role label, end-to-end.
"""

import pytest


def _net_by_suffix(client, suffix):
    for n in client.networks.list():
        if n.name.endswith(suffix):
            return n
    return None


@pytest.mark.gpu
@pytest.mark.acc_crit("duoptimumhub::Functional: live labels via docker socket")
def test_gpuinfo_network_carries_role_label(docker_client):
    net = _net_by_suffix(docker_client, "_hub_gpuinfo_network")
    assert net is not None, "hub_gpuinfo_network not found in the GPU stack"
    assert (net.attrs.get("Labels") or {}).get("hub.network.role") == "gpuinfo"


@pytest.mark.gpu
@pytest.mark.acc_crit("duoptimumhub::Functional: live labels via docker socket")
def test_sidecar_container_carries_role_label(docker_client):
    # the hub stamps the container role label on the sidecar it creates
    sidecar = docker_client.containers.get("gpuinfo-nvidia")
    assert (sidecar.labels or {}).get("hub.container.role") == "gpuinfo"


@pytest.mark.gpu
@pytest.mark.acc_crit("duoptimumhub::Functional: live labels via docker socket")
def test_hub_attached_to_gpuinfo_network(docker_client):
    net = _net_by_suffix(docker_client, "_hub_gpuinfo_network")
    assert net is not None
    net.reload()
    names = [c.name for c in net.containers]
    assert any("hub" in n for n in names), f"hub not attached to gpuinfo net: {names}"
