"""Extending the idle TTL must read 100% against the HIGH-WATER MARK, not ~50%
against the far absolute ceiling (DEF-13), and the extend slider must default to a
stable +4h - not the (shifting) maximum.

Regression: the bar measured banked time against `base + max_extension` (72h live),
so a session extended to 35h read ~48.6% the instant it was extended. The backend
now stores `display_ceiling` (remaining last extended TO) and returns
`display_ceiling_seconds`; the bar measures against it, so a just-extended session
reads ~100%.
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


def _session_info(admin_api, base, user):
    return admin_api.get(f"{base}/hub/api/users/{user}/session-info", timeout=30).json()


def _wait(pred, timeout=120, interval=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return False


@pytest.mark.acc_crit(
    "duoptimumhub::Two-phase pct (high-water mark)",
    "duoptimumhub::Scenario table holds",
)
def test_extend_bar_reads_full_against_high_water_mark(admin_api, base_url):
    user = "ttl-user"
    _delete(admin_api, base_url, f"/hub/api/users/{user}")  # clean slate
    assert _post(admin_api, base_url, f"/hub/api/users/{user}").status_code < 400, "create user failed"
    try:
        _post(admin_api, base_url, f"/hub/api/users/{user}/server")
        assert _wait(lambda: _server_state(admin_api, base_url, user).get("", {}).get("ready")), \
            "server never became ready"

        before = _session_info(admin_api, base_url, user)
        assert before.get("culler_enabled"), f"idle culler must be on for this test: {before}"
        base_sec = before["timeout_seconds"]

        r = _post(admin_api, base_url, f"/hub/api/users/{user}/extend-session", json={"hours": 4})
        assert r.status_code < 400 and r.json().get("success"), f"extend failed: {r.status_code} {r.text}"

        after = _session_info(admin_api, base_url, user)
        remaining = after["time_remaining_seconds"]
        ceiling = after["display_ceiling_seconds"]
        assert remaining > base_sec, f"extend did not bank above base: remaining={remaining} base={base_sec}"
        assert ceiling, f"display_ceiling_seconds missing after extend: {after}"
        # the bar's 100% reference is the high-water mark, so it reads ~100% on extend
        pct = remaining / ceiling * 100
        assert pct >= 95, f"bar should read ~100% against the high-water mark, got {pct:.1f}% (DEF-13 regression?)"
    finally:
        _delete(admin_api, base_url, f"/hub/api/users/{user}/server")
        _delete(admin_api, base_url, f"/hub/api/users/{user}")
        _wait(lambda: not _server_state(admin_api, base_url, user))


@pytest.mark.acc_crit("duoptimumhub::Slider default = stable +4h")
def test_extend_slider_defaults_to_plus_4h(admin_portal, admin_api, base_url):
    me = admin_api.get(f"{base_url}/hub/api/user", timeout=30).json()["name"]
    _post(admin_api, base_url, f"/hub/api/users/{me}/server")
    assert _wait(lambda: _server_state(admin_api, base_url, me).get("", {}).get("ready")), \
        "own server never became ready"
    try:
        page = admin_portal.goto("/home")
        extend = page.get_by_role("button", name="Extend", exact=True)
        expect(extend).to_be_visible()
        extend.click()
        # popover apply button reflects the slider's default value - a stable +4h, not "max"
        expect(page.get_by_role("button", name="Extend +4h", exact=True)).to_be_visible()
    finally:
        _delete(admin_api, base_url, f"/hub/api/users/{me}/server")
        _wait(lambda: not _server_state(admin_api, base_url, me))
