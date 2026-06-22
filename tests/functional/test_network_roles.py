"""Functional: role labels the hub discovers by, verified live over the docker socket.

Gated to the GPU stack (`make test-functional-gpu`) where the gpuinfo_network + the
hub-started gpuinfo sidecar exist. Asserts the net carries hub.network.role=gpuinfo
and the hub-created sidecar carries hub.container.role=gpuinfo - discovery-by-role +
the container role label, end-to-end.
"""

import pytest

GPUINFO_NET = "stellars-functest_gpuinfo_network"  # exact name (suffix match could shadow a stray net)


def _gpuinfo_net(client):
    for n in client.networks.list():
        if n.name == GPUINFO_NET:
            return n
    return None


def _sidecar(client):
    # #405: the hub names the sidecar compose-style <project>-gpuinfo-nvidia-1, not a
    # bare "gpuinfo-nvidia". Find it by the stable name fragment, project-prefix-agnostic.
    for c in client.containers.list(all=True):
        if "gpuinfo-nvidia" in c.name:
            return c
    return None


@pytest.mark.gpu
@pytest.mark.acc_crit("duoptimumhub::Functional: live labels via docker socket")
def test_gpuinfo_network_carries_role_label(docker_client):
    net = _gpuinfo_net(docker_client)
    assert net is not None, f"{GPUINFO_NET} not found in the GPU stack"
    assert (net.attrs.get("Labels") or {}).get("hub.network.role") == "gpuinfo"


@pytest.mark.gpu
@pytest.mark.acc_crit("duoptimumhub::Functional: live labels via docker socket")
def test_sidecar_container_carries_role_label(docker_client):
    # the hub stamps the container role label on the sidecar it creates
    sidecar = _sidecar(docker_client)
    assert sidecar is not None, "hub-created gpuinfo sidecar not found"
    assert (sidecar.labels or {}).get("hub.container.role") == "gpuinfo"


@pytest.mark.gpu
@pytest.mark.acc_crit("duoptimumhub::Functional: live labels via docker socket")
def test_hub_attached_to_gpuinfo_network(docker_client):
    net = _gpuinfo_net(docker_client)
    assert net is not None
    net.reload()
    names = [c.name for c in net.containers]
    assert any("hub" in n for n in names), f"hub not attached to gpuinfo net: {names}"
