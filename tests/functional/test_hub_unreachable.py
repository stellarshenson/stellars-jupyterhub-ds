"""Functional E2E: the SPA raises a hub-unreachable indicator when the hub stops
responding and clears it on recovery.

Stops the real hub container over the docker socket, asserts the portal's offline
indicator in both forms (desktop header connection-status pill, mobile top panel), then
restarts the hub and asserts the indicator clears. A stop/start (not down/up)
preserves /data (cookie secret + db) inside the container, so the session admin
cookies stay valid; the hub is always restored in `finally` so later tests run
against a healthy stack.

The redesign (#399/#414) replaced the old corner diode + full-screen modal with a
calm header pill on desktop (`.doh-conn-pill.ok` -> `.doh-conn-pill.down`) and a pale
in-flow panel on mobile (`.doh-hub-warn-panel`); there is no dialog any more.

Detection is intentionally debounced (the hook needs a couple of failed 15s polls),
so the waits are generous.
"""

import time

import pytest
import requests
from playwright.sync_api import expect

HUB_CONTAINER = "stellars-functest-duoptimum-hub"
DESKTOP = {"width": 1280, "height": 800}
MOBILE = {"width": 375, "height": 720}  # below the 768px useIsMobile breakpoint
DETECT_TIMEOUT = 70_000  # ms: 2 failed 15s polls (~30s) + margin
CLEAR_TIMEOUT = 45_000   # ms: one successful poll after recovery (<=15s) + margin


def _wait_health(base_url, up, deadline_s=120):
    """Block until GET /hub/health is reachable (up=True) or refused (up=False)."""
    end = time.time() + deadline_s
    while time.time() < end:
        try:
            ok = requests.get(f"{base_url}/hub/health", timeout=5).status_code == 200
        except Exception:
            ok = False
        if ok == up:
            return
        time.sleep(2)
    raise RuntimeError(f"hub /hub/health never reached up={up}")


@pytest.mark.acc_crit(
    "duoptimumhub::E2E: hub stop raises indicator",
    "duoptimumhub::E2E: hub restart clears indicator",
    "duoptimumhub::E2E: both viewports",
    "duoptimumhub::E2E: no false trigger while healthy",
)
def test_hub_unreachable_indicator(admin_portal, docker_client, base_url):
    page = admin_portal.page
    page.set_viewport_size(DESKTOP)
    admin_portal.goto("/home")

    # healthy: no DOWN indicator in any form (the desktop pill shows the calm "ok"
    # state; only the down forms must be absent)
    expect(page.locator(".doh-conn-pill.down")).to_have_count(0)
    expect(page.locator(".doh-hub-warn-panel")).to_have_count(0)

    hub = docker_client.containers.get(HUB_CONTAINER)
    try:
        hub.stop(timeout=10)
        _wait_health(base_url, up=False)

        # desktop: the header pill flips to the down state (no modal/dialog any more)
        down_pill = page.locator(".doh-conn-pill.down")
        expect(down_pill).to_be_visible(timeout=DETECT_TIMEOUT)
        expect(down_pill).to_contain_text("Not responding")
        expect(page.get_by_role("dialog")).to_have_count(0)

        # mobile: the in-flow panel carries the elapsed detail, and the header keeps the
        # FULL-TEXT "Not responding" pill (design: full-text mobile pill, panel owns the
        # pulse - see global.css max-width:767px block + journal 436/437). Both show for
        # one outage; only the pill's ticking elapsed suffix is dropped on a phone.
        page.set_viewport_size(MOBILE)
        panel = page.locator(".doh-hub-warn-panel")
        expect(panel).to_be_visible(timeout=DETECT_TIMEOUT)
        expect(panel).to_contain_text("Hub not responding")
        expect(page.locator(".doh-conn-pill.down")).to_contain_text("Not responding")
        page.set_viewport_size(DESKTOP)
    finally:
        hub.start()
        _wait_health(base_url, up=True)

    # recovery: the down indicator clears on the next successful poll
    expect(page.locator(".doh-conn-pill.down")).to_have_count(0, timeout=CLEAR_TIMEOUT)
    expect(page.locator(".doh-hub-warn-panel")).to_have_count(0, timeout=CLEAR_TIMEOUT)
