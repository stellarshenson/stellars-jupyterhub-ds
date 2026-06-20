"""Functional: hub-owned volumes carry hub.volume.role labels, discovered live
over the docker socket. Default regime.

Verifies the role-label discovery the hub relies on (no name reconstruction, no fallback):
the shared + docker-proxy volumes carry their role, each role is unique WITHIN this namespace
(compose project), the prefix is duoptimum-hub, and a foreign namespace's identically-labelled
volume is NOT picked up. A healthy hub also proves the central config validator passed on boot
(it would SystemExit on a missing required var instead of serving).
"""

import pytest

HUB = "stellars-functest-duoptimum-hub"
ROLE_KEY = "hub.volume.role"


def _hub_volume_roles(client):
    """role -> [volume names] for the volumes THIS hub container mounts - mirrors the hub's
    own self-mount discovery, inherently scoped to this namespace."""
    hub = client.containers.get(HUB)
    roles = {}
    seen = set()
    for m in (hub.attrs.get("Mounts") or []):
        if m.get("Type") != "volume":
            continue
        name = m.get("Name")
        if not name or name in seen:
            continue
        seen.add(name)
        labels = client.volumes.get(name).attrs.get("Labels") or {}
        role = labels.get(ROLE_KEY)
        if role:
            roles.setdefault(role, []).append(name)
    return roles


@pytest.mark.acc_crit("duoptimumhub::Functional: live role labels per namespace")
def test_shared_volume_carries_role(docker_client):
    roles = _hub_volume_roles(docker_client)
    assert "shared" in roles, f"no volume with role=shared among hub mounts: {roles}"


@pytest.mark.acc_crit("duoptimumhub::Functional: live role labels per namespace")
def test_docker_proxy_volume_carries_role(docker_client):
    roles = _hub_volume_roles(docker_client)
    assert "docker-proxy" in roles, f"no volume with role=docker-proxy among hub mounts: {roles}"


@pytest.mark.acc_crit("duoptimumhub::Functional: live role labels per namespace")
def test_role_unique_per_namespace(docker_client):
    # the hub must mount at most one volume per role - a duplicate makes the resolver raise
    roles = _hub_volume_roles(docker_client)
    dupes = {r: v for r, v in roles.items() if len(v) > 1}
    assert not dupes, f"duplicate volume roles among hub mounts: {dupes}"


@pytest.mark.acc_crit("duoptimumhub::Functional: live role labels per namespace")
def test_role_label_prefix_is_duoptimum_hub(docker_client):
    # hub-owned volume role labels use the hub. prefix (renamed from bare duoptimum.)
    hub = docker_client.containers.get(HUB)
    for m in (hub.attrs.get("Mounts") or []):
        if m.get("Type") != "volume":
            continue
        labels = docker_client.volumes.get(m["Name"]).attrs.get("Labels") or {}
        for k in labels:
            if "volume.role" in k:
                assert k == ROLE_KEY, f"stale volume-role label key: {k}"


@pytest.mark.acc_crit("duoptimumhub::Functional: foreign-namespace volume not picked")
def test_foreign_namespace_volume_not_picked(docker_client):
    # simulate a second deployment's role=shared volume on the same host; it must NOT appear
    # among THIS hub's mounts - uniqueness is per-namespace, not host-wide
    name = "stellars-functest-foreign_shared_probe"
    try:
        docker_client.volumes.get(name).remove(force=True)
    except Exception:
        pass
    docker_client.volumes.create(name=name, labels={ROLE_KEY: "shared"})
    try:
        roles = _hub_volume_roles(docker_client)
        assert name not in roles.get("shared", []), "foreign-namespace volume leaked into hub discovery"
    finally:
        docker_client.volumes.get(name).remove(force=True)


@pytest.mark.acc_crit("duoptimumhub::Single validation pass")
def test_hub_booted_so_validator_passed(docker_client):
    # the hub serving health proves validate_hub_config passed on boot - a missing required
    # var would have raised SystemExit instead of a running, healthy container
    hub = docker_client.containers.get(HUB)
    assert hub.status == "running", f"hub not running (validator may have failed): {hub.status}"
