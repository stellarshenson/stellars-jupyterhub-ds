"""A user with EXACTLY zero 7-day activity must light ZERO meter bars - not the
floored single pale-red bar the meter used to render (DEF-26). activity_score is
mapped `?? 0`, so a fresh/never-active user is a real 0 (a meter), not null (a dash)."""

import pytest
from playwright.sync_api import expect
from test_ttl_extend import _post, _delete


@pytest.mark.acc_crit("duoptimumhub::Zero activity lights zero bars")
def test_zero_activity_lights_no_bars(admin_portal, base_url, admin_api):
    user = "zero-act-user"
    _delete(admin_api, base_url, f"/hub/api/users/{user}")  # clean slate
    r = _post(admin_api, base_url, f"/hub/api/users/{user}")
    assert r.status_code < 400, f"create user failed: {r.status_code} {r.text}"
    try:
        page = admin_portal.goto("/users")
        row = page.locator("tr.ant-table-row").filter(has_text=user).first
        expect(row).to_be_visible()
        meter = row.locator(".doh-meter").first
        expect(meter).to_be_visible()  # a real meter: activity 0 is a number, never the muted dash
        # exactly zero activity -> ZERO lit segments (regression floored it to one pale-red bar)
        expect(meter.locator("i.on")).to_have_count(0)
    finally:
        _delete(admin_api, base_url, f"/hub/api/users/{user}")
