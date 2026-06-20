"""Notifications "Past Notifications" history controls, driven through the SPA: a
broadcast records a sent-history row; the page shows it within the default 24h range;
the danger-toned Clear button (behind a confirm modal) empties the persistent store
and the table. Mirrors the Events page range+clear (test_events.py)."""

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


@pytest.mark.acc_crit(
    "duoptimumhub::Range filter",
    "duoptimumhub::24h default",
    "duoptimumhub::Clear",
    "duoptimumhub::Parity with Events",
)
def test_notifications_history_range_and_clear(admin_portal, base_url, admin_api):
    me = admin_api.get(f"{base_url}/hub/api/user", timeout=30).json()["name"]
    # a broadcast only records a sent-history row when there is an active recipient,
    # so start the admin's own lab, then broadcast to it
    admin_api.post(f"{base_url}/hub/api/users/{me}/server",
                   headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=60)
    assert _wait(lambda: _server_state(admin_api, base_url, me).get("", {}).get("ready")), \
        "own server never became ready"
    try:
        r = admin_api.post(f"{base_url}/hub/api/notifications/broadcast",
                           json={"message": "functest history row", "variant": "info"},
                           headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
        assert r.status_code < 400, f"broadcast failed: {r.status_code} {r.text}"

        page = admin_portal.goto("/notifications")
        # the default range is 24h and the just-sent broadcast is within it -> a row shows.
        # scope to the card header (the Send card has its own auto-close Segmented too)
        expect(page.locator(".ant-card-extra .ant-segmented-item-selected")).to_have_text("Last 24h")
        expect(page.locator("tr.ant-table-row").first).to_be_visible()

        clear = page.get_by_role("button", name="Clear", exact=True)
        expect(clear).to_be_enabled()
        clear.click()
        # confirm modal -> its danger OK button (labelled "Clear")
        page.locator(".ant-modal-confirm-btns").get_by_role("button", name="Clear", exact=True).click()
        expect(page.locator(".ant-modal-confirm")).to_have_count(0)
        # the history empties and the toolbar button disables (nothing left to clear)
        expect(page.locator("tr.ant-table-row")).to_have_count(0)
        expect(page.get_by_role("button", name="Clear", exact=True)).to_be_disabled()
    finally:
        admin_api.delete(f"{base_url}/hub/api/users/{me}/server",
                         headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=60)
        _wait(lambda: not _server_state(admin_api, base_url, me))
