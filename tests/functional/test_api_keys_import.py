"""Functional: the API Keys Pool credential editor imports keys from a file - one per
non-blank line, validated, appended to the list. Import only, no export. Default regime.

Drives the SPA: open a group's Configure -> Policy tab, enable the API Keys Pool, pick
single mode, open the Import popup, upload an in-memory text file, confirm, and assert the
success toast + the parsed rows land in the credential table. #411, popup rework #418.
"""

import pytest
from playwright.sync_api import expect

GROUP = "apikey-import"


def _xsrf(s):
    return s.cookies.get("_xsrf")


@pytest.mark.acc_crit("duoptimumhub::AC-4a")
def test_import_single_keys_from_file(admin_portal, admin_api, base_url):
    # the group only needs to exist so the Configure page loads; the import is a
    # client-side edit before Save, so policy persistence is not exercised here
    admin_api.delete(f"{base_url}/hub/api/groups/{GROUP}",
                     headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
    r = admin_api.post(f"{base_url}/hub/api/groups/{GROUP}",
                       headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
    assert r.status_code < 400, f"create group failed: {r.status_code} {r.text}"
    try:
        page = admin_portal.goto(f"/groups/{GROUP}")
        page.get_by_role("tab", name="Policy").click()

        # enable the API Keys Pool section, then pick single mode
        page.locator(".doh-pol-head").filter(has_text="API Keys Pool").get_by_role("switch").click()
        sec = page.locator(".doh-pol-sec").filter(has=page.get_by_text("API Keys Pool", exact=True))
        sec.locator(".ant-select").first.click()
        # antd renders options in a body-level portal as .ant-select-item-option
        page.locator(".ant-select-item-option", has_text="Single API Key").click()

        # open the import popup; the file input lives in a body-level antd Modal, not in sec
        sec.get_by_role("button", name="Import Keys").click()
        dialog = page.get_by_role("dialog", name="Import API keys")
        # import three keys (one per line); the blank line is skipped silently
        dialog.locator("input[type=file]").set_input_files(files=[{
            "name": "keys.txt", "mimeType": "text/plain",
            "buffer": b"sk-aaa\nsk-bbb\n\nsk-ccc\n",
        }])
        # validation parses the file; the OK button reports the count - confirm to append
        dialog.get_by_role("button", name="Import 3 keys").click()

        # success toast reports the count, and the parsed rows land in the table
        expect(page.get_by_text("Imported 3 keys")).to_be_visible()
        expect(sec.locator(".ant-table-tbody tr.ant-table-row")).to_have_count(3)
        expect(sec.locator(".ant-table-tbody input").first).to_have_value("sk-aaa")
    finally:
        admin_api.delete(f"{base_url}/hub/api/groups/{GROUP}",
                         headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
