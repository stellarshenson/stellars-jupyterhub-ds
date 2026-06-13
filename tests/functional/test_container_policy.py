"""End-to-end: a group's configured policies land on the spawned container.

The resolved policy *is* the container's create-time config (Env / Mounts /
HostConfig), set by DockerSpawner before the lab app starts - so we assert it via
`docker inspect` as soon as the container exists, regardless of whether the
minimal singleuser image fully boots. One group carries several policies; the
admin is added to it and spawned; every effect is checked on the one container.
"""

import time

CONTAINER = "jupyterlab-functestadmin"
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


def test_policies_applied_to_container(admin_api, docker_client, base_url):
    base = base_url
    # 1. Create the group and configure several policies.
    _post(admin_api, base, "/hub/api/admin/groups/create", json={"name": GROUP})
    cfg = {
        "sudo_active": True, "sudo_enable": False,
        "env_vars_active": True, "env_vars": [{"name": "FOO", "value": "bar"}],
        "mem_limit_enabled": True, "mem_limit_gb": 2,
        "volume_mounts_active": True,
        "volume_mounts": [{"volume": "functest-data", "mountpoint": "/mnt/functest"}],
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

        assert attrs["HostConfig"]["Memory"] == 2 * 1024 ** 3, "memory cap not applied"

        mounts = {m["Destination"]: m for m in attrs.get("Mounts", [])}
        assert "/mnt/functest" in mounts, f"group volume not mounted; mounts={list(mounts)}"
        assert mounts["/mnt/functest"]["Name"] == "functest-data"

        # compose-project label so teardown reaps the spawned lab
        labels = attrs["Config"].get("Labels", {})
        assert labels.get("com.docker.compose.project") == "stellars-functest"
    finally:
        _stop_server(admin_api, base)
