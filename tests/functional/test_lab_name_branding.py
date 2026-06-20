"""Lab-name branding env rename (acc-crit-lab-name-branding-env.md).

The hub knob JUPYTERHUB_BRANDING_LAB_NAME is injected into every spawned lab as
JUPYTERLAB_SYSTEM_NAME (the var the lab image consumes for header/welcome/MOTD).
The old JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME / JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR
envs were dropped and must NOT appear on the spawned container.

End-to-end: spawn the admin lab, inspect its create-time Config.Env (set by
DockerSpawner from the resolved config, regardless of the lab image).
"""

import time

import pytest

CONTAINER = "jupyterlab-functestadmin"
LAB_NAME = "Functest Lab Name"  # = JUPYTERHUB_BRANDING_LAB_NAME in compose.functional.yml


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _wait_container(docker_client, timeout=90):
    import docker
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return docker_client.containers.get(CONTAINER)
        except docker.errors.NotFound:
            time.sleep(2)
    raise AssertionError(f"container {CONTAINER} was not created within {timeout}s")


@pytest.mark.acc_crit(
    "lab-name-branding-env::Injected as JUPYTERLAB_SYSTEM_NAME",
    "lab-name-branding-env::Edge: not on the container",
)
def test_lab_name_injected_and_dropped_absent(admin_api, docker_client, base_url):
    me = "functestadmin"
    try:
        admin_api.post(f"{base_url}/hub/api/users/{me}/server",
                       headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
        container = _wait_container(docker_client)
        env = dict(e.split("=", 1) for e in container.attrs["Config"]["Env"] if "=" in e)
        # renamed hub knob -> injected into the lab as JUPYTERLAB_SYSTEM_NAME
        assert env.get("JUPYTERLAB_SYSTEM_NAME") == LAB_NAME, \
            f"JUPYTERLAB_SYSTEM_NAME not injected from JUPYTERHUB_BRANDING_LAB_NAME: {env.get('JUPYTERLAB_SYSTEM_NAME')!r}"
        # dropped envs must not be set on the container
        assert "JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME" not in env, "dropped capitalize env still set on the lab"
        assert "JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR" not in env, "dropped color env still set on the lab"
    finally:
        admin_api.delete(f"{base_url}/hub/api/users/{me}/server",
                         headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=60)
