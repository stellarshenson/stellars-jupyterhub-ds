"""Starting your OWN server from the Servers list backgrounds it (inline spinner,
no navigation) - identical to starting another user's server. Only the home
ServerHero keeps the foreground navigation to the dedicated Start-server page.

Regression (#346): the Servers list/widget play button used to navigate the
current user to /servers/<me>/starting; now it runs the inline background start.
The row's play action is shared by the list and the Home widget (rowActions), so
covering the list covers both surfaces.
"""

import time

import pytest
from playwright.sync_api import expect


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _server_state(admin_api, base, user):
    r = admin_api.get(f"{base}/hub/api/users/{user}", timeout=30)
    return (r.json() or {}).get("servers", {}) if r.status_code < 400 else {}


def _wait(pred, timeout=120, interval=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return False


@pytest.mark.acc_crit("duoptimumhub::List/widget own start = background")
def test_own_server_starts_in_background_from_servers_list(admin_portal, admin_api, base_url):
    me = admin_api.get(f"{base_url}/hub/api/user", timeout=30).json()["name"]
    hdr = {"X-XSRFToken": _xsrf(admin_api)}
    # own server must be OFFLINE so the row shows the play (start) action
    admin_api.delete(f"{base_url}/hub/api/users/{me}/server", headers=hdr, timeout=60)
    assert _wait(lambda: not _server_state(admin_api, base_url, me)), "own server never stopped"

    try:
        page = admin_portal.goto("/servers", ready=".ant-table")
        # own row's play is labelled exactly "Start server" (others read "Start <user>'s server");
        # IconAction sets aria-label=title, so match by accessible role/name, not a DOM title attr
        start = page.get_by_role("button", name="Start server", exact=True)
        expect(start).to_be_visible()
        start.click()
        # #346: background start - must NOT navigate to the dedicated foreground start page
        page.wait_for_timeout(1000)
        assert "/starting" not in page.url, f"navigated to the foreground start page: {page.url}"
        assert "/servers" in page.url, f"unexpectedly left the servers list: {page.url}"
        # the start actually fired: the row shows the inline busy spinner (no modal, no nav)
        expect(page.locator(".doh-actions .ant-spin").first).to_be_visible()
    finally:
        admin_api.delete(f"{base_url}/hub/api/users/{me}/server", headers=hdr, timeout=60)
        _wait(lambda: not _server_state(admin_api, base_url, me))
