"""Functional: audit the docker resources the platform creates - names, labels and
characteristics - live over the docker socket. Default regime (always-present resources).

Complements test_role_labels.py (volume role-label discovery) and test_network_roles.py
(gpuinfo net + sidecar, GPU-only) by asserting the resource CONVENTIONS that hold for every
deployment: project-namespaced volume names, the hub container's compose identity, the
hub.volume.description label the Lab Setup system-volumes panel reads, and the hub network
characteristics (bridge driver + the hub attached).
"""

import pytest

PROJECT = "stellars-functest"
HUB = "stellars-functest-duoptimum-hub"
NETWORK = "stellars-functest_network"


def _hub(client):
    return client.containers.get(HUB)


def _hub_volume_mounts(client):
    return [m for m in (_hub(client).attrs.get("Mounts") or []) if m.get("Type") == "volume"]


# --- names ------------------------------------------------------------------

@pytest.mark.acc_crit("duoptimumhub::Hub container identity")
def test_hub_container_name(docker_client):
    # the hub runs under its explicit, project-scoped container name
    assert _hub(docker_client).name == HUB


@pytest.mark.acc_crit("duoptimumhub::Volume names project-namespaced")
def test_hub_volumes_project_prefixed(docker_client):
    # every named volume the hub mounts is namespaced by the compose project - never a bare
    # global name that could collide with another deployment on the same host
    mounts = _hub_volume_mounts(docker_client)
    assert mounts, "hub mounts no named volumes"
    bad = [m["Name"] for m in mounts if not m["Name"].startswith(PROJECT + "_")]
    assert not bad, f"volumes not project-namespaced: {bad}"


# --- labels -----------------------------------------------------------------

@pytest.mark.acc_crit("duoptimumhub::Hub container identity")
def test_hub_compose_project_label(docker_client):
    # the hub container carries the compose project label this namespace is scoped by
    labels = _hub(docker_client).labels or {}
    assert labels.get("com.docker.compose.project") == PROJECT


@pytest.mark.acc_crit("duoptimumhub::Volume description label")
def test_shared_volume_has_description_label(docker_client):
    # the Lab Setup system-volumes panel reads hub.volume.description; assert the shared
    # volume actually carries a non-empty one (the panel falls back to a static phrase if absent)
    for m in _hub_volume_mounts(docker_client):
        labels = docker_client.volumes.get(m["Name"]).attrs.get("Labels") or {}
        if labels.get("hub.volume.role") == "shared":
            assert labels.get("hub.volume.description"), \
                f"shared volume {m['Name']} missing hub.volume.description"
            return
    pytest.fail("no shared-role volume among the hub's mounts")


# --- characteristics --------------------------------------------------------

@pytest.mark.acc_crit("duoptimumhub::Network characteristics")
def test_hub_network_is_bridge(docker_client):
    # the hub<->lab network is a local bridge
    net = docker_client.networks.get(NETWORK)
    assert net.attrs.get("Driver") == "bridge", net.attrs.get("Driver")


@pytest.mark.acc_crit("duoptimumhub::Network characteristics")
def test_hub_attached_to_its_network(docker_client):
    # the hub is a member of the network its spawned labs join (so it can reach them)
    net = docker_client.networks.get(NETWORK)
    net.reload()
    names = [c.name for c in net.containers]
    assert HUB in names, f"hub not attached to {NETWORK}: {names}"
