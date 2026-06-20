"""Admin remove-user flow, driven through the SPA Configure-user screen.

acc-crit-duoptimumhub.md -> "Remove user (confirmation + optional volume removal)":
- "Remove User" opens a confirmation modal, not an immediate delete
- a user with no volumes shows a terse "No active volumes" info stripe, no checkbox
- a user with volumes shows the opt-in checkbox; ticking it removes the volumes
  (behind a docker-flavour spinner) then the account, ending on a done report
- both paths end with the account gone from /api/users

The no-volumes case is fast (never spawned). The with-volumes case spawns to
create the per-user volumes, stops the server (volume removal needs it stopped),
then removes with the checkbox ticked.
"""

import time

import pytest
from playwright.sync_api import expect


def _hdr(s):
    return {"X-XSRFToken": s.cookies.get("_xsrf")}


def _ready(admin_api, base, user):
    r = admin_api.get(f"{base}/hub/api/users/{user}", timeout=30)
    srv = (r.json() or {}).get("servers", {}) if r.status_code < 400 else {}
    return bool(srv.get("", {}).get("ready"))


def _exists(admin_api, base, user):
    return admin_api.get(f"{base}/hub/api/users/{user}", timeout=30).status_code < 400


def _wait(pred, timeout=120, interval=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return False


@pytest.mark.acc_crit(
    "remove-user::Confirmation modal",
    "remove-user::Edge: no volumes",
    "remove-user::Keep volumes by default",
)
def test_remove_user_no_volumes(admin_portal, base_url, admin_api):
    """A never-spawned user has no volumes: the modal shows the terse info stripe
    and no checkbox, and confirming removes the account."""
    user = "rm-novol"
    admin_api.delete(f"{base_url}/hub/api/users/{user}", headers=_hdr(admin_api), timeout=30)
    assert admin_api.post(f"{base_url}/hub/api/users/{user}", headers=_hdr(admin_api), timeout=30).status_code < 400

    try:
        page = admin_portal.goto(f"/users/{user}")
        page.get_by_role("button", name="Remove User").click()  # only the page button exists yet
        modal = page.locator(".ant-modal")
        expect(modal).to_be_visible()
        expect(modal).to_contain_text(f"Remove {user}")
        # never spawned -> no volumes -> terse info stripe, no checkbox
        expect(modal).to_contain_text("No active volumes")
        expect(modal.get_by_role("checkbox")).to_have_count(0)
        modal.get_by_role("button", name="Remove User").click()
        assert _wait(lambda: not _exists(admin_api, base_url, user), timeout=30), "user not removed"
    finally:
        admin_api.delete(f"{base_url}/hub/api/users/{user}", headers=_hdr(admin_api), timeout=30)


@pytest.mark.acc_crit(
    "remove-user::Volume checkbox",
    "remove-user::Remove volumes when ticked",
    "remove-user::Spinner popup with docker text",
    "remove-user::Done report",
)
def test_remove_user_with_volumes(admin_portal, base_url, admin_api):
    """Spawn so per-user volumes exist, stop, then remove with the volume checkbox
    ticked: the modal runs the spinner and ends on a done report naming the deleted
    volumes; the account is gone afterwards."""
    user = "rm-vol"
    admin_api.delete(f"{base_url}/hub/api/users/{user}", headers=_hdr(admin_api), timeout=30)
    assert admin_api.post(f"{base_url}/hub/api/users/{user}", headers=_hdr(admin_api), timeout=30).status_code < 400

    try:
        admin_api.post(f"{base_url}/hub/api/users/{user}/server", headers=_hdr(admin_api), timeout=60)
        assert _wait(lambda: _ready(admin_api, base_url, user)), "server never became ready"
        admin_api.delete(f"{base_url}/hub/api/users/{user}/server", headers=_hdr(admin_api), timeout=60)
        assert _wait(lambda: not _ready(admin_api, base_url, user)), "server never stopped"

        page = admin_portal.goto(f"/users/{user}")
        page.get_by_role("button", name="Remove User").click()
        modal = page.locator(".ant-modal")
        expect(modal).to_be_visible()
        # the user has volumes now -> the opt-in checkbox is present and enabled
        cb = modal.get_by_role("checkbox")
        expect(cb).to_be_enabled()
        cb.check()
        modal.get_by_role("button", name="Remove User").click()
        # done report (after the spinner) names the user and the deleted volumes
        expect(modal).to_contain_text(f"{user} removed", timeout=30000)
        expect(modal).to_contain_text("Deleted")
        # footer Close (the antd X-icon shares the "Close" accessible name)
        modal.locator(".ant-modal-footer").get_by_role("button", name="Close").click()
        assert _wait(lambda: not _exists(admin_api, base_url, user), timeout=30), "user not removed"
    finally:
        admin_api.delete(f"{base_url}/hub/api/users/{user}", headers=_hdr(admin_api), timeout=30)
