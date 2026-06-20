"""Traefik dashboard route (/traefik on 443) - traefik regime only.

Runs against the Traefik + TLS overlay (compose.functional-traefik.yml): Traefik
fronts the hub on :443, the dashboard is exposed at /traefik via --api.basePath
(no stripprefix). These tests reach `traefik` by service name over HTTPS with a
self-signed cert. The UI check renders the dashboard in a real browser so the
harness actually SEES it render (a bare 200 would pass on a white page).
"""

import os
import re
import time

import pytest
import requests
import urllib3
from playwright.sync_api import expect

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TRAEFIK_BASE = os.environ.get("TRAEFIK_BASE", "https://traefik").rstrip("/")
API_OVERVIEW = f"{TRAEFIK_BASE}/traefik/api/overview"


@pytest.fixture(scope="module", autouse=True)
def _wait_for_traefik():
    """Traefik starts after the hub (depends_on) and the harness only waits on hub
    health, so poll the dashboard API until it answers before the tests run."""
    deadline = time.time() + 60
    last = None
    while time.time() < deadline:
        try:
            r = requests.get(API_OVERVIEW, verify=False, timeout=5)
            if r.status_code == 200:
                return
            last = f"HTTP {r.status_code}"
        except Exception as e:  # connection refused while traefik boots
            last = repr(e)
        time.sleep(2)
    pytest.fail(f"traefik dashboard never came up at {API_OVERVIEW}: {last}")


@pytest.mark.traefik
@pytest.mark.acc_crit("duoptimumhub::Dashboard API on /traefik")
def test_dashboard_api_open():
    # /traefik/api/overview -> the built-in api@internal, served over TLS on 443.
    r = requests.get(API_OVERVIEW, verify=False, timeout=10)
    assert r.status_code == 200, r.text[:200]
    body = r.json()  # parses -> it is the Traefik API, not an error page
    assert isinstance(body, dict) and ("http" in body or "features" in body), body


@pytest.mark.traefik
@pytest.mark.acc_crit("duoptimumhub::Dashboard UI on /traefik")
def test_dashboard_ui_renders(page):
    # Render the dashboard in-browser: proves --api.basePath serves the SPA assets
    # under /traefik (no white page). A white page would leave #app empty.
    page.goto(f"{TRAEFIK_BASE}/traefik/dashboard/", wait_until="domcontentloaded")
    expect(page).to_have_title(re.compile("Traefik", re.I))
    # content only present once the SPA mounts (i.e. assets resolved under /traefik)
    expect(page.get_by_text(re.compile("Routers", re.I)).first).to_be_visible(timeout=30000)


@pytest.mark.traefik
@pytest.mark.acc_crit("duoptimumhub::Insecure :8080 removed")
def test_insecure_8080_absent():
    # The insecure dashboard port is gone - nothing listens on :8080.
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get("http://traefik:8080/dashboard/", timeout=5)
