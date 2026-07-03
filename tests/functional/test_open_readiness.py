"""DEF-25: the Open control activates only once the lab truly serves.

After a start/restart the hub flips 'running' ~1s before the lab serves HTTP, so
the portal Open controls used to navigate straight into the hub spawn-pending /
503 page. The server-lifecycle now gates entry on the shared lab-ready probe: a
just-restarted server shows "Starting" (disabled) until the lab answers, then
the Enter action activates.

This drives a REAL restart of the admin's own server and intercepts the lab-ready
probe so the becoming-ready window is deterministic: while the probe is forced
not-ready the active Enter action never appears; flipping it to ready opens the
gate. The shared gate is also used by the cold-start Starting page and the
ServerHero "Open Lab" button (same isServing path).
"""

import json
import time

import pytest
from playwright.sync_api import expect


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _running(admin_api, base, user):
    r = admin_api.get(f"{base}/hub/api/users/{user}", timeout=30)
    servers = (r.json() or {}).get("servers", {}) if r.status_code < 400 else {}
    return servers.get("", {}).get("ready") is True


def _wait(pred, timeout=180, interval=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return False


@pytest.mark.acc_crit(
    "open-server-readiness::Functional",
    "open-server-readiness::After restart",
    "open-server-readiness::Active only when serving",
)
def test_open_gated_until_lab_ready_after_restart(admin_portal, admin_api, base_url):
    me = admin_api.get(f"{base_url}/hub/api/user", timeout=30).json()["name"]
    hdr = {"X-XSRFToken": _xsrf(admin_api)}
    # own server must be running so the row shows the enter/restart actions
    if not _running(admin_api, base_url, me):
        admin_api.post(f"{base_url}/hub/api/users/{me}/server", headers=hdr, timeout=180)
        assert _wait(lambda: _running(admin_api, base_url, me)), "own server never started"

    page = admin_portal.page
    ready = {"v": False}

    def handler(route):
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"ready": ready["v"]}))

    page.route("**/lab-ready", handler)
    try:
        admin_portal.goto("/servers", ready=".ant-table")
        # restart own server from the row -> opens the becoming-ready gate
        page.get_by_role("button", name="Restart", exact=True).first.click()
        # gated: the Open/Enter action shows "Starting" (disabled) ...
        expect(page.get_by_role("button", name="Starting").first).to_be_visible(timeout=180_000)
        # ... and the active Enter action does NOT appear while lab-ready is false
        page.wait_for_timeout(8_000)
        expect(page.get_by_role("button", name="Enter session")).to_have_count(0)
        # lab now serves -> the gate opens, the Enter action activates
        ready["v"] = True
        expect(page.get_by_role("button", name="Enter session").first).to_be_visible(timeout=60_000)
    finally:
        page.unroute("**/lab-ready")
