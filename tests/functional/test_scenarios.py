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
    page.get_by_role("button", name="Add group").click()
    page.wait_for_url(lambda u: "/groups/new" in u)
    page.locator("input[placeholder*='vision-lab']").fill(name)
    page.get_by_role("button", name="Create group").click()
    page.wait_for_url(lambda u: u.rstrip("/").endswith("/groups"))
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

    # Delete through the UI (the icon deletes directly - no confirm modal).
    _row(page, name).get_by_role("button", name="Delete group").click()
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
        names = page.locator("tr.ant-table-row td:nth-child(2) a").evaluate_all(
            "els => els.map(e => e.textContent)")
        return [n for n in names if n in (a, b)]

    before = order()
    assert len(before) == 2, f"expected both test groups in the list; got {before}"
    lower = before[-1]

    # Move the lower row up; the list reorders optimistically.
    _row(page, lower).get_by_role("button", name="Move up").click()
    expect(page.locator("tr.ant-table-row td:nth-child(2) a").first).to_have_text(lower)
    assert order()[0] == lower
