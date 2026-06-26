"""The Manage-volumes action must be PRESENT but DISABLED for a user with no volumes, in the
admin Servers list - matching the home hero and mobile. The icon keeps its place (a predictable
action row) with an explanatory tooltip ("No volumes to manage") rather than vanishing.

Note: the ENABLED case (has-volumes -> action active) is covered by the `hasVolumes` unit test,
not here - the functest backend lists only docker volumes that exist on disk, and functest's
project-namespaced spawner volumes are not detectable, so no functest user ever reports volumes."""

import pytest
from playwright.sync_api import expect
from test_ttl_extend import _post, _delete


@pytest.mark.acc_crit("duoptimumhub::No volumes disables Manage-volumes action")
def test_manage_volumes_disabled_without_volumes(admin_portal, base_url, admin_api):
    user = "vol-gate-user"
    _delete(admin_api, base_url, f"/hub/api/users/{user}")  # clean slate
    r = _post(admin_api, base_url, f"/hub/api/users/{user}")
    assert r.status_code < 400, f"create user failed: {r.status_code} {r.text}"
    try:
        # never spawned -> no volumes -> the offline row renders the disk action PRESENT but DISABLED
        page = admin_portal.goto("/servers")
        row = page.locator("tr.ant-table-row").filter(has_text=user).first
        expect(row).to_be_visible()
        expect(row.locator(".doh-actions button").first).to_be_visible()  # actions DID render
        # the Manage-volumes (disk) action is present but disabled, named by its explanatory tooltip
        btn = row.get_by_role("button", name="No volumes to manage")
        expect(btn).to_be_visible()
        expect(btn).to_be_disabled()
    finally:
        _delete(admin_api, base_url, f"/hub/api/users/{user}")
