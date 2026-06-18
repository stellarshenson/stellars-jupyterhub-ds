"""Activity is a 7-day engagement metric and must read the SAME on every surface
that reports it - the Home servers widget, the Servers screen and the Users
screen - whether or not the server is running right now.

Scenario (operator's): launch a user's lab, leave it ~10s, stop it, then observe
the user's Activity across all three pages. The regression: an offline-but-active
user showed a real meter on Users but a muted dash ("none") on Servers/Home,
because the server-row builder gated the 7-day meter on the server being running.
"""

import time

import pytest
from playwright.sync_api import expect


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _post(s, base, path, json=None):
    return s.post(f"{base}{path}", json=json, headers={"X-XSRFToken": _xsrf(s)}, timeout=60)


def _delete(s, base, path):
    return s.delete(f"{base}{path}", headers={"X-XSRFToken": _xsrf(s)}, timeout=60)


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


def _meter_title(admin_portal, route, user):
    """Open a page, find the user's row, and return the Activity meter title.
    Asserts a real meter is rendered (the regression rendered a muted dash)."""
    page = admin_portal.goto(route)
    row = page.locator("tr.ant-table-row").filter(has_text=user)
    expect(row.first).to_be_visible()
    meter = row.first.locator(".oh-meter")
    expect(meter.first).to_be_visible()  # bug: '-' dash (oh-muted), no meter
    return meter.first.get_attribute("title")


@pytest.mark.acc_crit(
    "activity-consistency::Reported on every surface",
    "activity-consistency::Same value on Servers and Users",
    "activity-consistency::Shown when the server is stopped",
    "activity-consistency::7-day metric, not gated on run state",
)
def test_activity_consistent_across_pages(admin_portal, base_url, admin_api):
    user = "act-user"
    _delete(admin_api, base_url, f"/hub/api/users/{user}")  # clean slate
    r = _post(admin_api, base_url, f"/hub/api/users/{user}")
    assert r.status_code < 400, f"create user failed: {r.status_code} {r.text}"

    try:
        # launch the user's lab, leave it running ~10s, sample while active so the
        # 7-day score is non-zero, then stop it -> offline but with activity
        _post(admin_api, base_url, f"/hub/api/users/{user}/server")
        assert _wait(lambda: _server_state(admin_api, base_url, user).get("", {}).get("ready")), \
            "server never became ready"
        time.sleep(10)
        _post(admin_api, base_url, "/hub/api/activity/sample")  # record an active sample
        _delete(admin_api, base_url, f"/hub/api/users/{user}/server")
        assert _wait(lambda: not _server_state(admin_api, base_url, user)), "server never stopped"

        # the Activity meter must be present (not a dash) on every surface...
        servers = _meter_title(admin_portal, "/servers", user)
        users = _meter_title(admin_portal, "/users", user)
        home = _meter_title(admin_portal, "/dashboard", user)

        # ...and report the SAME 7-day engagement on each (the meter title carries
        # the percent + avg hours); Servers and Users come from different builders
        assert servers == users == home, \
            f"activity inconsistent: servers={servers!r} users={users!r} home={home!r}"
    finally:
        _delete(admin_api, base_url, f"/hub/api/users/{user}/server")
        _delete(admin_api, base_url, f"/hub/api/users/{user}")
