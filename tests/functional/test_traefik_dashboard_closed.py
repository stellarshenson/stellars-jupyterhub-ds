"""Traefik dashboard CLOSED toggle - traefik-closed regime only.

Same Traefik + TLS overlay as the open regime, but run.sh exports
TRAEFIK_DASHBOARD_ENABLED=false so the dashboard router (traefik.enable) is never
created by the docker provider. The built-in api@internal then has NO entrypoint,
so /traefik is unreachable - UI and API both gone.

This is the regression test for the corrected toggle: an adversarial review + an
isolated empirical probe showed `--api.dashboard=false` hides ONLY the UI and
leaves /traefik/api/* answering 200, so the toggle gates the ROUTE, not that flag.
Separate module from test_traefik_dashboard.py on purpose: that module's autouse
fixture waits for the dashboard API to return 200, which never happens when closed.
"""

import os
import time

import pytest
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TRAEFIK_BASE = os.environ.get("TRAEFIK_BASE", "https://traefik").rstrip("/")
API_OVERVIEW = f"{TRAEFIK_BASE}/traefik/api/overview"
API_RAWDATA = f"{TRAEFIK_BASE}/traefik/api/rawdata"


def _is_traefik_api(r):
    """True only for a genuine Traefik API response (200 + the overview/rawdata JSON
    shape), so a fall-through 404/redirect or an HTML error page reads as closed."""
    if r.status_code != 200:
        return False
    try:
        body = r.json()
    except ValueError:
        return False
    return isinstance(body, dict) and ("http" in body or "features" in body or "routers" in body)


@pytest.fixture(scope="module", autouse=True)
def _wait_for_traefik_up():
    """Closed mode: the dashboard API never answers, so wait until traefik is merely
    REACHABLE on 443 (any HTTP status = up; only ConnectionError means not yet)."""
    deadline = time.time() + 60
    last = None
    while time.time() < deadline:
        try:
            requests.get(f"{TRAEFIK_BASE}/", verify=False, timeout=5)
            return  # any HTTP-level response (even 404) means traefik is listening
        except requests.exceptions.ConnectionError as e:
            last = repr(e)
        time.sleep(2)
    pytest.fail(f"traefik never came up on 443: {last}")


@pytest.mark.traefikclosed
@pytest.mark.acc_crit("duoptimumhub::Closeable")
def test_dashboard_closed_api_unreachable():
    # Toggle off -> dashboard router dropped -> api@internal has no entrypoint.
    # Both the overview and the config-dumping rawdata endpoint must be closed.
    ov = requests.get(API_OVERVIEW, verify=False, timeout=10)
    raw = requests.get(API_RAWDATA, verify=False, timeout=10)
    assert not _is_traefik_api(ov), f"/traefik/api/overview still exposed when closed: {ov.status_code} {ov.text[:200]}"
    assert not _is_traefik_api(raw), f"/traefik/api/rawdata still exposed when closed: {raw.status_code} {raw.text[:200]}"
