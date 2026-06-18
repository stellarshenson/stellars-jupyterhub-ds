"""Admin rename-user flow, driven through the SPA Configure-user screen. A stopped
user is renamed via the Username input's attached Rename action (behind a confirm
dialog); the screen lands on the renamed profile and the Events feed shows the
rename attributed to the acting admin (who renamed whom).
"""

import pytest
from playwright.sync_api import expect


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _delete_user(admin_api, base_url, name):
    admin_api.delete(f"{base_url}/hub/api/users/{name}",
                     headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)


@pytest.mark.acc_crit(
    "rename-user::Adjacent to the Username input",
    "rename-user::Enabled only when the server is stopped",
    "rename-user::Confirmation popup",
    "rename-user::Back to the renamed profile",
    "rename-user::Event names the actor (who renamed whom)",
)
def test_rename_user_flow(admin_portal, base_url, admin_api, admin_creds):
    old, new = "rn-old", "rn-new"
    # clean slate (a prior failed run could leave either name)
    _delete_user(admin_api, base_url, old)
    _delete_user(admin_api, base_url, new)
    r = admin_api.post(f"{base_url}/hub/api/users/{old}",
                       headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
    assert r.status_code < 400, f"create user failed: {r.status_code} {r.text}"

    try:
        page = admin_portal.goto(f"/users/{old}")
        # the input adjacent to Rename lives in the "Username" form item
        field = page.locator(".ant-form-item").filter(has_text="Username").get_by_role("textbox")
        rename_btn = page.get_by_role("button", name="Rename")
        # gate: enabled once a DIFFERENT name is typed on a stopped server (the
        # user never spawned -> offline); disabled while the name is unchanged
        expect(rename_btn).to_be_disabled()
        field.fill(new)
        expect(rename_btn).to_be_enabled()
        rename_btn.click()

        # confirmation dialog -> its danger OK (also labelled "Rename")
        modal = page.locator(".ant-modal-confirm")
        expect(modal).to_be_visible()
        modal.locator(".ant-modal-confirm-btns").get_by_role("button", name="Rename").click()

        # lands on the renamed user's Configure screen
        page.wait_for_url(lambda u: f"/users/{new}" in u)

        # the Events feed records who renamed whom: "<admin> renamed <old> to <new>"
        page = admin_portal.goto("/events")
        row = page.locator("tr.ant-table-row").filter(has_text="renamed").filter(has_text=new)
        expect(row.first).to_be_visible()
        expect(row.first).to_contain_text(admin_creds["username"])
        expect(row.first).to_contain_text(old)
    finally:
        _delete_user(admin_api, base_url, old)
        _delete_user(admin_api, base_url, new)
