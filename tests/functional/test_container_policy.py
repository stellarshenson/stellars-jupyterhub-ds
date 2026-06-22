"""End-to-end: a group's configured policies land on the spawned container.

The resolved policy *is* the container's create-time config (Env / Mounts /
HostConfig), set by DockerSpawner before the lab app starts - so we assert it via
`docker inspect` as soon as the container exists, regardless of whether the
minimal singleuser image fully boots. One group carries several policies; the
admin is added to it and spawned; every effect is checked on the one container.
"""

import time
from urllib.parse import urlparse

import pytest

CONTAINER = "jupyterlab-functestadmin"
HUB = "stellars-functest-duoptimum-hub"
GROUP = "ctr-policy"


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _post(s, base, path, json=None):
    return s.post(f"{base}{path}", json=json, headers={"X-XSRFToken": _xsrf(s)}, timeout=30)


def _wait_container(docker_client, timeout=90):
    import docker
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return docker_client.containers.get(CONTAINER)
        except docker.errors.NotFound:
            time.sleep(2)
    raise AssertionError(f"container {CONTAINER} was not created within {timeout}s")


def _stop_server(admin_api, base):
    """Stop the admin's server (DockerSpawner stops + removes the container)."""
    try:
        admin_api.delete(f"{base}/hub/api/users/functestadmin/server",
                         headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=60)
    except Exception:
        pass


@pytest.mark.acc_crit(
    "functional-test-harness::Spawn creates the container",
    "functional-test-harness::Container created",
    "functional-test-harness::Env: sudo",
    "functional-test-harness::Env: group vars",
    "functional-test-harness::Mounts: group volume",
    "functional-test-harness::Limit: memory",
    "functional-test-harness::Labels: compose project",
    "functional-test-harness::sudo off",
    "functional-test-harness::mem 4G",
    "functional-test-harness::env FOO=bar",
    "functional-test-harness::volume vol->/mnt/x",
    "duoptimumhub::Access level per volume",
    "duoptimumhub::Standard resolved by label, not by saved name",
)
def test_policies_applied_to_container(admin_api, docker_client, base_url):
    base = base_url
    # 1. Create the group and configure several policies, incl. a read-write and a
    #    read-only custom mount and the standard shared mount (read-only).
    _post(admin_api, base, "/hub/api/admin/groups/create", json={"name": GROUP})
    cfg = {
        "sudo_active": True, "sudo_enable": False,
        "env_vars_active": True, "env_vars": [{"name": "FOO", "value": "bar"}],
        "mem_limit_enabled": True, "mem_limit_gb": 2,
        "volume_mounts_active": True,
        "shared_mount_allow": True, "shared_mount_mode": "ro",
        "volume_mounts": [
            {"volume": "functest-data", "mountpoint": "/mnt/functest", "mode": "rw"},
            {"volume": "functest-ro", "mountpoint": "/mnt/functest-ro", "mode": "ro"},
        ],
    }
    r = admin_api.put(f"{base}/hub/api/admin/groups/{GROUP}/config", json=cfg,
                      headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
    assert r.status_code < 400, f"config save failed: {r.status_code} {r.text}"

    # 2. Add the admin to the group (native JupyterHub group API), then spawn.
    _post(admin_api, base, f"/hub/api/groups/{GROUP}/users", json={"users": ["functestadmin"]})
    try:
        _post(admin_api, base, "/hub/api/users/functestadmin/server")
        container = _wait_container(docker_client)
        attrs = container.attrs

        # 3. Assert the resolved policy on the container.
        env = dict(e.split("=", 1) for e in attrs["Config"]["Env"] if "=" in e)
        assert env.get("JUPYTERLAB_SUDO_ENABLE") == "0", "sudo policy not applied"
        assert env.get("FOO") == "bar", "group env var not injected"
        # DEF-22: the lab's JUPYTERHUB_API_URL host must equal the hub's discovered compose
        # service name (the hub_connect_ip the fix advertises), not the hub's ephemeral
        # container id - so a hub redeploy does not strand the lab. Reverting it to
        # gethostname() would bake the hub's short id here and fail this assertion.
        hub_service = (docker_client.containers.get(HUB).labels or {}).get("com.docker.compose.service")
        api_url = env.get("JUPYTERHUB_API_URL", "")
        assert urlparse(api_url).hostname == hub_service, \
            f"lab API URL host {urlparse(api_url).hostname!r} != hub service name {hub_service!r}: {api_url!r}"

        assert attrs["HostConfig"]["Memory"] == 2 * 1024 ** 3, "memory cap not applied"

        mounts = {m["Destination"]: m for m in attrs.get("Mounts", [])}
        # read-write custom mount
        assert "/mnt/functest" in mounts, f"group volume not mounted; mounts={list(mounts)}"
        assert mounts["/mnt/functest"]["Name"] == "functest-data"
        assert mounts["/mnt/functest"]["RW"] is True, "rw custom mount must be writable"
        # read-only custom mount (access level ro)
        assert "/mnt/functest-ro" in mounts, f"ro group volume not mounted; mounts={list(mounts)}"
        assert mounts["/mnt/functest-ro"]["RW"] is False, "ro custom mount must be read-only"
        # standard shared mount: resolved by label (role=shared), read-only. The name
        # is the docker-resolved volume, NOT a literal saved in the group config.
        assert "/mnt/shared" in mounts, f"standard shared mount not applied; mounts={list(mounts)}"
        assert mounts["/mnt/shared"]["RW"] is False, "shared mount must be read-only here"
        assert "shared" in mounts["/mnt/shared"]["Name"], "shared mount must resolve the role=shared volume by label"

        # compose-project label so teardown reaps the spawned lab
        labels = attrs["Config"].get("Labels", {})
        assert labels.get("com.docker.compose.project") == "stellars-functest"
        # role label so labs are discoverable like the hub + gpuinfo sidecar
        assert labels.get("hub.container.role") == "lab", "spawned lab missing hub.container.role=lab"
    finally:
        _stop_server(admin_api, base)
