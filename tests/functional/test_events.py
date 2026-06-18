"""Event-log persistence + clear, driven through the SPA Events page. An admin
action records an event; the Events page shows it; the danger-toned Clear-log
button (behind a confirm modal) empties the persistent store and the feed.
"""

from playwright.sync_api import expect


def _xsrf(s):
    return s.cookies.get("_xsrf")


def test_events_render_and_clear(admin_portal, base_url, admin_api):
    # Guarantee at least one event exists: creating a group records a 'group' event.
    r = admin_api.post(f"{base_url}/hub/api/admin/groups/create",
                       json={"name": "evt-grp"},
                       headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
    assert r.status_code < 400, f"group create failed: {r.status_code} {r.text}"

    page = admin_portal.goto("/events")
    # the feed shows at least the group event
    expect(page.locator("tr.ant-table-row").first).to_be_visible()
    clear = page.get_by_role("button", name="Clear log")
    expect(clear).to_be_enabled()

    # Clear log -> confirm modal -> its danger OK button (also labelled "Clear log").
    clear.click()
    page.locator(".ant-modal-confirm-btns").get_by_role("button", name="Clear log").click()

    # Wait for the confirm modal to close (else two "Clear log" buttons match), then
    # the feed empties and the toolbar button disables (nothing left to clear).
    expect(page.locator(".ant-modal-confirm")).to_have_count(0)
    expect(page.locator("tr.ant-table-row")).to_have_count(0)
    expect(page.get_by_role("button", name="Clear log")).to_be_disabled()
