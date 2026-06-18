"""Shared fixtures for the functional test suite.

The suite runs inside the Playwright runner container (see compose.functional.yml),
reaching the hub by service name on the test network. Lifecycle (compose up/down)
is owned by the ``make test-functional*`` targets; this conftest only waits for hub
health, bootstraps the admin, and drives the React SPA portal.

The portal is a React single-page app served at ``{BASE_URL}/hub/<route>`` (default
landing ``/hub/dashboard``); login is the server-rendered NativeAuthenticator page
at ``/hub/login`` (``input[name=username|password|_xsrf]``). There are NO
data-testid attributes - selectors use visible text, antd roles, breadcrumbs and
button labels. ``networkidle`` is unusable (the SPA polls in the background), so
readiness is a per-page DOM signal instead.
"""

import os
import re
import time
from urllib.parse import urlparse

import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "http://jupyterhub:8000/jupyterhub").rstrip("/")
HUB_HOST = urlparse(BASE_URL).hostname or "jupyterhub"
ADMIN_USER = os.environ.get("ADMIN_USER", "functestadmin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "functest-secret")
# Auth regime for this run (one initial-condition "setup" per value):
#   "signup"     (default): first admin created via the bootstrap-signup window.
#   "env"                 : signup disabled + JUPYTERHUB_ADMIN_PASSWORD; the admin
#                           is pre-provisioned by the target's restart-to-provision.
#   "signupopen"          : signup ENABLED; admin self-signs-up + self-approves, a
#                           second user self-signs-up (pending) and admin authorises.
AUTH_MODE = os.environ.get("FUNCTEST_AUTH_MODE", "signup")

# Generous timeout: the SPA bundle (~2.4 MB) boots after the post-login redirect.
SPA_TIMEOUT = 30000


def pytest_collection_modifyitems(config, items):
    """Deselect (not skip) tests that do not apply to this run's regime, so the
    suite never reports noise skips. Each regime runs only the tests it owns plus
    the regime-agnostic ones; gpu tests are collected only when auto-detect is on.
    """
    gpu_on = os.environ.get("FUNCTEST_GPU_ENABLED", "0") == "2"
    if AUTH_MODE == "env":
        items[:] = [i for i in items if "envauth" in i.keywords]
        return
    if AUTH_MODE == "signupopen":
        items[:] = [i for i in items if "signupopen" in i.keywords]
        return
    items[:] = [
        i for i in items
        if "envauth" not in i.keywords
        and "signupopen" not in i.keywords
        and ("gpu" not in i.keywords or gpu_on)
    ]


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def admin_creds():
    return {"username": ADMIN_USER, "password": ADMIN_PASSWORD}


# ── hub lifecycle / bootstrap ───────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _wait_for_hub():
    """Block until the hub health endpoint returns 200 (depends_on already gates on
    the compose healthcheck; this is a belt-and-braces guard)."""
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


def _signup(base_url, username, password, email=None):
    """POST the NativeAuthenticator signup form for `username`. Idempotent - a
    repeat signup (user exists) is harmless. Returns the response."""
    s = requests.Session()
    r = s.get(f"{base_url}/hub/signup", timeout=10)
    m = re.search(r'name="_xsrf"[^>]*value="([^"]+)"', r.text)
    data = {
        "username": username,
        "email": email or f"{username}@functest.local",
        "signup_password": password,
        "signup_password_confirmation": password,
    }
    if m:
        data["_xsrf"] = m.group(1)
    return s.post(f"{base_url}/hub/signup", data=data, timeout=10)


@pytest.fixture(scope="session")
def signup_user():
    """Factory: self-sign-up an arbitrary user via the NativeAuth signup form.
    Used by the signup-open regime to create a pending (unauthorised) user."""
    def _make(username, password):
        return _signup(BASE_URL, username, password)
    return _make


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_admin(_wait_for_hub):
    """Create the first admin on a fresh hub.

    signup mode: sign up `ADMIN_USER`; the bootstrap window flips is_authorized and
    the first login grants the admin role. env / signupopen modes: the admin is
    env-provisioned (restart-to-provision; is_authorized=1), so skip signup - the
    bootstrap window is closed there (env password set / signup enabled).
    """
    if AUTH_MODE in ("env", "signupopen"):
        yield
        return
    _signup(BASE_URL, ADMIN_USER, ADMIN_PASSWORD)
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


# ── Playwright / SPA driving ─────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # The runner container is root; Chromium needs no-sandbox there.
    return {**browser_type_launch_args, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}


def _pw_cookies(session):
    """Convert a logged-in requests session's cookies to Playwright cookie dicts.

    We authenticate the browser by injecting the API session's hub cookies rather
    than driving the login form: a direct GET of ``/hub/login`` self-redirects in a
    loop (the SPA auth shell appends ``?next=<self>``), so cookie injection is the
    reliable way to reach the authenticated portal.
    """
    return [
        {"name": c.name, "value": c.value, "domain": HUB_HOST, "path": c.path or "/"}
        for c in session.cookies
    ]


class Portal:
    """Thin wrapper over a logged-in Playwright page that drives the SPA portal by
    full navigation (re-mounts the app per route; robust vs SPA-internal nav races).
    """

    def __init__(self, page, base_url):
        self.page = page
        self.base = base_url

    def goto(self, route, ready=None):
        """Navigate to an SPA route (e.g. ``/servers``) and wait for the app shell,
        plus an optional page-specific ready selector."""
        self.page.goto(f"{self.base}/hub{route}")
        self.page.wait_for_selector(".ant-layout", timeout=SPA_TIMEOUT)
        if ready:
            self.page.wait_for_selector(ready, timeout=SPA_TIMEOUT)
        return self.page


@pytest.fixture
def admin_page(page, context, admin_api):
    """A Playwright page authenticated as the bootstrap admin (session cookies
    injected from the API session, so the SPA loads already logged in)."""
    context.add_cookies(_pw_cookies(admin_api))
    return page


@pytest.fixture
def admin_portal(admin_page, base_url):
    """The logged-in admin page wrapped with SPA navigation helpers."""
    return Portal(admin_page, base_url)


# ── docker (end-to-end container inspection) ─────────────────────────────────────

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
