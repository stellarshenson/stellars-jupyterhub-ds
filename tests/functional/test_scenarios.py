"""Multi-step SPA operator scenarios over the group / policy model. These drive
the React portal end-to-end: create a group through the UI, see its
server-rendered policy badges after a config change, reorder priority, and delete
through the UI. Deep policy->container assertions live in test_container_policy.py
(API + docker inspect). Add new UI scenarios here.
"""

import pytest
from playwright.sync_api import expect


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _row(page, name):
    """The Groups table row whose name-link is exactly `name`."""
    return page.locator("tr.ant-table-row").filter(
        has=page.get_by_role("link", name=name, exact=True))


def _create_group_via_ui(admin_portal, name):
    page = admin_portal.goto("/groups")
    page.get_by_role("button", name="Add Group").click()
    page.wait_for_url(lambda u: "/groups/new" in u)
    page.locator("input[placeholder*='vision-lab']").fill(name)
    page.get_by_role("button", name="Create Group").click()
    # create now lands on the new group's config screen; bring the caller back to
    # the list, which is what the downstream scenarios expect to assert against
    page.wait_for_url(lambda u: u.rstrip("/").endswith(f"/groups/{name}"))
    page = admin_portal.goto("/groups")
    expect(_row(page, name)).to_be_visible()
    return page


@pytest.mark.acc_crit(
    "functional-test-harness::Create group",
    "functional-test-harness::Delete group",
    "functional-test-harness::Badges from policy_summary",
    "functional-test-harness::No badges when inactive",
)
def test_group_create_badge_delete(admin_portal, base_url, admin_api):
    name = "scen-grp"
    page = _create_group_via_ui(admin_portal, name)

    # No policy yet -> the Policies cell shows the empty marker, no tags.
    expect(_row(page, name).locator(".ant-tag")).to_have_count(0)

    # Configure a memory cap via the admin API; the SPA must then render a policy
    # badge for it (server policy_summary -> CappedTags).
    r = admin_api.put(f"{base_url}/hub/api/admin/groups/{name}/config",
                      json={"mem_limit_enabled": True, "mem_limit_gb": 4},
                      headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
    assert r.status_code < 400, f"config save failed: {r.status_code} {r.text}"

    page = admin_portal.goto("/groups")
    expect(_row(page, name).locator(".ant-tag").first).to_be_visible()

    # Delete through the UI: the icon opens a danger confirm modal (destructive),
    # only the modal's "Delete" removes the group.
    _row(page, name).get_by_role("button", name="Delete Group").click()
    page.locator(".ant-modal-confirm-btns").get_by_role("button", name="Delete", exact=True).click()
    expect(_row(page, name)).to_have_count(0)


@pytest.mark.acc_crit("functional-test-harness::Multiple badges")
def test_multi_policy_badges(admin_portal, base_url, admin_api):
    name = "scen-multi"
    _create_group_via_ui(admin_portal, name)

    cfg = {
        "sudo_active": True, "sudo_enable": False,
        "downloads_active": True, "downloads_allow": False,
        "mem_limit_enabled": True, "mem_limit_gb": 8,
    }
    r = admin_api.put(f"{base_url}/hub/api/admin/groups/{name}/config", json=cfg,
                      headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
    assert r.status_code < 400, f"config save failed: {r.status_code} {r.text}"

    page = admin_portal.goto("/groups")
    # three active policies -> at least three inline tags (cap=4, so no +N rollup)
    expect(_row(page, name).locator(".ant-tag").nth(2)).to_be_visible()


@pytest.mark.acc_crit("functional-test-harness::Reorder priority")
def test_priority_reorder(admin_portal):
    a, b = "scen-prio-a", "scen-prio-b"
    _create_group_via_ui(admin_portal, a)
    page = _create_group_via_ui(admin_portal, b)

    def order():
        names = page.locator("tr.ant-table-row td:nth-child(3) a").evaluate_all(
            "els => els.map(e => e.textContent)")
        return [n for n in names if n in (a, b)]

    before = order()
    assert len(before) == 2, f"expected both test groups in the list; got {before}"
    lower = before[-1]

    # Move the lower row up; the list reorders optimistically.
    _row(page, lower).get_by_role("button", name="Move up").click()
    expect(page.locator("tr.ant-table-row td:nth-child(3) a").first).to_have_text(lower)
    assert order()[0] == lower


@pytest.mark.acc_crit(
    "duoptimumhub::Land on config after create",
    "duoptimumhub::Config screen usable immediately",
)
def test_group_create_routes_to_config(admin_portal):
    """Creating a group lands on that group's config screen (not the list) so the
    operator can set policy/members right away - the create form only takes name +
    description."""
    name = "scen-cfg-route"
    page = admin_portal.goto("/groups")
    page.get_by_role("button", name="Add Group").click()
    page.wait_for_url(lambda u: "/groups/new" in u)
    page.locator("input[placeholder*='vision-lab']").fill(name)
    page.get_by_role("button", name="Create Group").click()

    # landed on /groups/{name} - the group's config screen (the shared PageHeader
    # renders no title text; the breadcrumb + tabbed form are the page identity)
    page.wait_for_url(lambda u: u.rstrip("/").endswith(f"/groups/{name}"))
    # config screen loaded for THIS group: the read-only General Name field holds the
    # new name (seeded async from its config; to_have_value reads the live DOM value
    # property of the antd controlled input and auto-waits), and it is usable
    expect(page.get_by_label("Name", exact=True)).to_have_value(name)
    # ...with the Policy / Members tabs present, ready to configure
    expect(page.get_by_role("tab", name="Policy")).to_be_visible()
    expect(page.get_by_role("tab", name="Members")).to_be_visible()


@pytest.mark.acc_crit("duoptimumhub::Edge: config API 404 on missing group")
def test_group_config_api_404_on_missing_group(admin_api, base_url):
    """DEF-30: GET/PUT of a group's config for a name with no orm.Group row must 404,
    not silently fabricate a phantom config."""
    ghost = "no-such-group-def30"
    r = admin_api.get(f"{base_url}/hub/api/admin/groups/{ghost}/config",
                      headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
    assert r.status_code == 404, f"GET expected 404, got {r.status_code}: {r.text}"
    r = admin_api.put(f"{base_url}/hub/api/admin/groups/{ghost}/config",
                      json={"description": "x"},
                      headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
    assert r.status_code == 404, f"PUT expected 404, got {r.status_code}: {r.text}"


@pytest.mark.acc_crit("duoptimumhub::Edge: route-colliding username reserved")
def test_reserved_username_rejected(admin_api, base_url):
    """DEF-31: a username that collides with a static /users route (new, bulk) is
    rejected by validate_username on the admin user-create path; a normal name works.
    (Case-insensitivity of the guard is proven in the unit test - JupyterHub lowercases
    the name before validate_username, so this API path always sees the normalised form.)"""
    hdr = {"X-XSRFToken": _xsrf(admin_api)}
    for name in ("new", "bulk"):
        r = admin_api.post(f"{base_url}/hub/api/users/{name}", headers=hdr, timeout=30)
        assert r.status_code == 400, f"expected 400 reject for {name!r}, got {r.status_code}: {r.text}"
        # the reserved name must not have been created (rolled back), else a later run
        # would see a 409 and mask a broken guard
        assert admin_api.get(f"{base_url}/hub/api/users/{name}", timeout=30).status_code == 404, \
            f"reserved user {name!r} should not exist after a rejected create"
    # a non-colliding name still creates fine, then clean up
    r = admin_api.post(f"{base_url}/hub/api/users/def31ok", headers=hdr, timeout=30)
    assert r.status_code < 400, f"normal name should create: {r.status_code} {r.text}"
    admin_api.delete(f"{base_url}/hub/api/users/def31ok", headers=hdr, timeout=30)


@pytest.mark.acc_crit(
    "duoptimumhub::Confirm before delete (config page)",
    "duoptimumhub::Edge: cancel on config page",
)
def test_group_config_page_delete_confirms(admin_portal):
    """The group CONFIG page's Delete Group button gates deletion behind the same
    danger confirm the list uses - a single click must not destroy the group.
    Covers the config-page confirm (deletion only on confirm) and the cancel no-op."""
    name = "scen-cfg-del"
    _create_group_via_ui(admin_portal, name)

    # open the group's config/detail page and click Delete Group
    page = admin_portal.goto(f"/groups/{name}")
    page.get_by_role("button", name="Delete Group").click()
    # a confirm modal naming the group must appear - deletion is gated, not outright
    modal = page.locator(".ant-modal-confirm")
    expect(modal).to_be_visible()
    expect(modal).to_contain_text(name)

    # cancel: the modal closes and the group still exists (no-op)
    modal.get_by_role("button", name="Cancel", exact=True).click()
    expect(page.locator(".ant-modal-confirm")).to_have_count(0)
    page = admin_portal.goto("/groups")
    expect(_row(page, name)).to_be_visible()

    # confirm for real from the config page: back to /groups, the group is gone
    page = admin_portal.goto(f"/groups/{name}")
    page.get_by_role("button", name="Delete Group").click()
    page.locator(".ant-modal-confirm-btns").get_by_role("button", name="Delete", exact=True).click()
    page.wait_for_url(lambda u: u.rstrip("/").endswith("/groups"))
    expect(_row(page, name)).to_have_count(0)
