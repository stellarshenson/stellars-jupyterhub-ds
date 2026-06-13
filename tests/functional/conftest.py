"""Shared fixtures for the UI test suite.

The suite runs inside the Playwright runner container (see compose.functional.yml),
reaching the hub by service name on the test network. Lifecycle (compose up/down)
is owned by ``make test-ui``; this conftest only waits for hub health and provides
a logged-in admin page.
"""

import os
import re
import time

import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "http://jupyterhub:8000/jupyterhub").rstrip("/")
ADMIN_USER = os.environ.get("ADMIN_USER", "functestadmin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "functest-secret")
# "signup" (default): first admin created via the bootstrap-signup window.
# "env": signup disabled + JUPYTERHUB_ADMIN_PASSWORD; the admin is pre-provisioned
# by the make target's restart-to-provision, so no signup is performed here.
AUTH_MODE = os.environ.get("FUNCTEST_AUTH_MODE", "signup")


def pytest_collection_modifyitems(config, items):
    """Deselect (not skip) tests that do not apply to this run's regime, so the
    suite never reports noise skips:
    - env mode runs ONLY the env-auth test (everything else is auth-mode-agnostic
      and already covered by the default signup run);
    - signup mode drops the env-auth tests;
    - gpu tests are collected only when GPU auto-detect is on (dropped on CPU hosts).
    """
    gpu_on = os.environ.get("FUNCTEST_GPU_ENABLED", "0") == "2"
    if AUTH_MODE == "env":
        items[:] = [i for i in items if "envauth" in i.keywords]
        return
    items[:] = [
        i for i in items
        if "envauth" not in i.keywords and ("gpu" not in i.keywords or gpu_on)
    ]


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def admin_creds():
    return {"username": ADMIN_USER, "password": ADMIN_PASSWORD}


@pytest.fixture(scope="session", autouse=True)
def _wait_for_hub():
    """Block until the hub health endpoint returns 200 (depends_on already gates
    on the compose healthcheck; this is a belt-and-braces guard)."""
    health = f"{BASE_URL}/hub/health"
    deadline = time.time() + 180
    last = None
    while time.time() < deadline:
        try:
            r = requests.get(health, timeout=5)
            if r.status_code == 200:
                return
            last = r.status_code
        except Exception as e:  # connection refused while CHP comes up
            last = repr(e)
        time.sleep(2)
    raise RuntimeError(f"JupyterHub never became healthy at {health} (last={last})")


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_admin(_wait_for_hub):
    """Create the first admin on a fresh hub (bootstrap-by-signup window).

    On a single fresh boot the env-password path cannot seed the admin (the
    users_info table is created after the config runs), so the documented flow is
    to sign up the admin during the one-shot bootstrap window. Idempotent - a
    second attempt (user exists) is harmless.

    In env-password mode the admin is pre-provisioned (signup disabled +
    restart-to-provision), so skip signup entirely.
    """
    if AUTH_MODE != "signup":
        yield
        return
    s = requests.Session()
    r = s.get(f"{BASE_URL}/hub/signup", timeout=10)
    m = re.search(r'name="_xsrf"[^>]*value="([^"]+)"', r.text)
    data = {
        "username": ADMIN_USER,
        "email": f"{ADMIN_USER}@functest.local",
        "signup_password": ADMIN_PASSWORD,
        "signup_password_confirmation": ADMIN_PASSWORD,
    }
    if m:
        data["_xsrf"] = m.group(1)
    s.post(f"{BASE_URL}/hub/signup", data=data, timeout=10)
    yield


@pytest.fixture(scope="session")
def admin_api(_bootstrap_admin):
    """A requests session logged in as the admin, for API-level setup/teardown."""
    s = requests.Session()
    r = s.get(f"{BASE_URL}/hub/login", timeout=10)
    m = re.search(r'name="_xsrf"[^>]*value="([^"]+)"', r.text)
    s.post(f"{BASE_URL}/hub/login",
           data={"username": ADMIN_USER, "password": ADMIN_PASSWORD,
                 "_xsrf": m.group(1) if m else ""}, timeout=10)
    return s


@pytest.fixture(autouse=True)
def clean_groups(admin_api):
    """Wipe all groups before and after each test so tests are independent (no
    cross-test pollution from a test that failed before its own cleanup)."""
    def wipe():
        try:
            tok = admin_api.cookies.get("_xsrf")
            groups = admin_api.get(f"{BASE_URL}/hub/api/admin/groups", timeout=10).json().get("groups", [])
            for g in groups:
                admin_api.delete(
                    f"{BASE_URL}/hub/api/admin/groups/{g['name']}/delete",
                    headers={"X-XSRFToken": tok}, timeout=10)
        except Exception:
            pass
    wipe()
    yield
    wipe()


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # The runner container is root; Chromium needs no-sandbox there.
    return {**browser_type_launch_args, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}


def _login(page, username, password):
    page.goto(f"{BASE_URL}/hub/login")
    page.fill("input[name='username']", username)
    page.fill("input[name='password']", password)
    # Submit by pressing Enter (robust to input-vs-button submit markup).
    page.press("input[name='password']", "Enter")
    page.wait_for_load_state("networkidle")
    if "/hub/login" in page.url:
        # Surface the NativeAuthenticator error so failures are diagnosable.
        try:
            msg = page.inner_text("body")[:400]
        except Exception:
            msg = "<no body>"
        raise RuntimeError(f"login failed for {username!r}; still on /hub/login. page: {msg!r}")


@pytest.fixture
def admin_page(page, admin_creds):
    """A Playwright page logged in as the bootstrap admin."""
    _login(page, admin_creds["username"], admin_creds["password"])
    return page


@pytest.fixture(scope="session")
def docker_client():
    """Docker client (the runner mounts the host socket) for end-to-end checks on
    the spawned lab container - env vars, mounts, memory/cpu limits, network,
    privileged and labels are all set by DockerSpawner from the resolved policy at
    container create, so they are inspectable regardless of the lab image."""
    import docker
    return docker.from_env()


def spawned_container_name(username):
    """DockerSpawner names spawned labs jupyterlab-<username>."""
    return f"jupyterlab-{username}"
