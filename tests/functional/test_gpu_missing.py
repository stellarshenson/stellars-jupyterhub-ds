"""GPU-missing regime (DEF-24): the gpuinfo sidecar cannot start, so GPU must
resolve OFF and labs spawn CPU-only - never with device_requests from a stale
inventory (the regression that crashed every spawn in the nvidia prestart hook).

Run with `tests/functional/run.sh gpu-missing`: GPU autodetect is requested
(FUNCTEST_GPU_ENABLED=1) but the hub points at an absent gpuinfo image, so its
self-start returns "" (sidecar down). These tests assert the hub logs GPU off with
the explicit reason, and a spawned lab carries no GPU device passthrough yet starts.
"""

import os
import re
import time
from urllib.parse import urlparse

import pytest

# hub + lab container names, derived from the same BASE_URL host the harness uses
# (compose names services stellars-functest-<service>), so a rename can't strand them.
_HUB_HOST = urlparse(os.environ.get("BASE_URL", "http://duoptimum-hub:8000/jupyterhub")).hostname or "duoptimum-hub"
HUB_CONTAINER = f"stellars-functest-{_HUB_HOST}"
ADMIN = os.environ.get("ADMIN_USER", "functestadmin")
LAB_CONTAINER = f"jupyterlab-{ADMIN}"


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _wait_container(docker_client, timeout=90):
    import docker
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return docker_client.containers.get(LAB_CONTAINER)
        except docker.errors.NotFound:
            time.sleep(2)
    raise AssertionError(f"container {LAB_CONTAINER} was not created within {timeout}s")


def _stop_server(admin_api, base):
    try:
        admin_api.delete(f"{base}/hub/api/users/{ADMIN}/server",
                         headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=60)
    except Exception:
        pass


@pytest.mark.gpu_missing
@pytest.mark.acc_crit(
    "duoptimumhub::Down sidecar -> off",
    "duoptimumhub::Explicit startup log",
)
def test_hub_logs_gpu_off_with_explicit_reason(docker_client):
    logs = docker_client.containers.get(HUB_CONTAINER).logs().decode("utf-8", "replace")
    m = re.search(r"\[GPU\] enabled=(\d) detected=(\d)", logs)
    assert m, "hub did not log the GPU detection line"
    assert (int(m.group(1)), int(m.group(2))) == (0, 0), \
        "sidecar absent but GPU did not resolve OFF (the DEF-24 stale-on regression)"
    # the explicit operator-facing reason, not just enabled=0
    assert "gpuinfo-nvidia sidecar did not start" in logs, \
        "missing the explicit 'sidecar did not start' WARNING"
    assert "GPU not detected" in logs


@pytest.mark.gpu_missing
@pytest.mark.acc_crit(
    "duoptimumhub::No device_requests when off",
    "duoptimumhub::Runtime: sidecar-missing host spawns CPU-only lab",
)
def test_lab_spawns_cpu_only_without_device_requests(admin_api, docker_client, base_url):
    base = base_url
    try:
        r = admin_api.post(f"{base}/hub/api/users/{ADMIN}/server",
                           headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=60)
        # 201 created / 202 accepted (async spawn) both < 400; >=400 means the hub rejected it
        assert r.status_code < 400, f"spawn request failed: {r.status_code} {r.text}"
        # the lab container is created (CPU-only spawn succeeds, no nvidia prestart 500)
        container = _wait_container(docker_client)
        attrs = container.attrs

        # the regression guard: GPU off -> NO device_requests attached to the lab
        device_requests = attrs["HostConfig"].get("DeviceRequests")
        assert not device_requests, \
            f"GPU off but device_requests attached (DEF-24): {device_requests!r}"

        # GPU support not enabled in the lab env, and no GPU passthrough
        env = dict(e.split("=", 1) for e in attrs["Config"]["Env"] if "=" in e)
        assert env.get("ENABLE_GPU_SUPPORT") != "1", "GPU support enabled despite sidecar down"
        assert env.get("NVIDIA_VISIBLE_DEVICES") in (None, "", "void"), \
            f"unexpected GPU passthrough: NVIDIA_VISIBLE_DEVICES={env.get('NVIDIA_VISIBLE_DEVICES')!r}"
    finally:
        _stop_server(admin_api, base)
