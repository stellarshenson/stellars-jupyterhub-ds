"""End-to-end: per-user environment variables reach the spawned container, the
reserved blacklist is enforced on save, and an admin can manage another user's set.

The per-user env vars are injected by the pre-spawn hook into the container's
create-time Env, so we assert them via `docker inspect` as soon as the container
exists - same approach as test_container_policy.
"""

import time

import pytest

ADMIN = "functestadmin"
OTHER = "functestenvuser"


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _post(s, base, path, json=None):
    return s.post(f"{base}{path}", json=json, headers={"X-XSRFToken": _xsrf(s)}, timeout=30)


def _put(s, base, path, json=None):
    return s.put(f"{base}{path}", json=json, headers={"X-XSRFToken": _xsrf(s)}, timeout=30)


def _delete(s, base, path):
    return s.delete(f"{base}{path}", headers={"X-XSRFToken": _xsrf(s)}, timeout=60)


def _wait_container(docker_client, name, timeout=90):
    import docker
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return docker_client.containers.get(name)
        except docker.errors.NotFound:
            time.sleep(2)
    raise AssertionError(f"container {name} was not created within {timeout}s")


@pytest.mark.acc_crit(
    "user-env-vars::Inject on spawn",
    "user-env-vars::Description not injected",
)
def test_user_env_var_injected_on_spawn(admin_api, docker_client, base_url):
    base = base_url
    # save a user env var (with a description) for the admin's own account
    r = _put(admin_api, base, f"/hub/api/users/{ADMIN}/env-vars",
             json={"env_vars": [{"name": "LAB_TEST_VAR", "value": "hello", "description": "a note"}]})
    assert r.status_code < 400, f"env-vars PUT failed: {r.status_code} {r.text}"
    try:
        _post(admin_api, base, f"/hub/api/users/{ADMIN}/server")
        container = _wait_container(docker_client, f"jupyterlab-{ADMIN}")
        env = dict(e.split("=", 1) for e in container.attrs["Config"]["Env"] if "=" in e)
        # the value is injected
        assert env.get("LAB_TEST_VAR") == "hello", "user env var not injected into the container"
        # the description is UI metadata only - it must NEVER become an env var
        assert "a note" not in env.values(), "description leaked into the container environment"
    finally:
        _delete(admin_api, base, f"/hub/api/users/{ADMIN}/server")
        _put(admin_api, base, f"/hub/api/users/{ADMIN}/env-vars", json={"env_vars": []})  # clear


@pytest.mark.acc_crit("user-env-vars::Reserved rejected on save")
def test_reserved_env_var_rejected(admin_api, base_url):
    base = base_url
    r = _put(admin_api, base, f"/hub/api/users/{ADMIN}/env-vars",
             json={"env_vars": [{"name": "JUPYTERHUB_HACK", "value": "x", "description": ""}]})
    assert r.status_code == 400, f"reserved name must be rejected, got {r.status_code}"
    body = r.json()
    assert body.get("code") == "reserved_env_var_names", f"unexpected error body: {body}"
    assert "JUPYTERHUB_HACK" in body.get("rejected", []), f"rejected list missing the name: {body}"
    # nothing was persisted
    g = admin_api.get(f"{base}/hub/api/users/{ADMIN}/env-vars", timeout=30).json()
    assert all(e["name"] != "JUPYTERHUB_HACK" for e in g.get("env_vars", [])), "reserved var was persisted"


@pytest.mark.acc_crit("user-env-vars::Admin edits another user")
def test_admin_sets_env_for_another_user(admin_api, base_url):
    base = base_url
    # create a second user, then the admin manages THEIR env vars (not the admin's own)
    _post(admin_api, base, f"/hub/api/users/{OTHER}")
    try:
        r = _put(admin_api, base, f"/hub/api/users/{OTHER}/env-vars",
                 json={"env_vars": [{"name": "OTHER_VAR", "value": "xyz", "description": ""}]})
        assert r.status_code < 400, f"admin PUT for another user failed: {r.status_code} {r.text}"
        g = admin_api.get(f"{base}/hub/api/users/{OTHER}/env-vars", timeout=30).json()
        names = {e["name"]: e["value"] for e in g.get("env_vars", [])}
        assert names.get("OTHER_VAR") == "xyz", f"admin-set env var not stored for {OTHER}: {g}"
    finally:
        # deleting the user also removes their env-vars row (delete-sync listener)
        _delete(admin_api, base, f"/hub/api/users/{OTHER}")
