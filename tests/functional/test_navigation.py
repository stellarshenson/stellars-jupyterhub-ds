"""Navigation patterns - form/sub screens return to their parent and the
breadcrumb names that parent. Driven through the SPA: open an edit screen, assert
the breadcrumb parent link, then Cancel and assert it returns to the parent list.
"""

import pytest
from playwright.sync_api import expect


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _ends_with(suffix):
    return lambda u: u.rstrip("/").endswith(suffix)


@pytest.mark.acc_crit(
    "navigation-patterns::Origin round-trip",
    "navigation-patterns::Parent crumb is a link",
    "edit-returns-to-origin::From Users -> Users",
)
def test_configure_user_returns_to_users(admin_portal, base_url, admin_api):
    name = "nav-user"
    admin_api.delete(f"{base_url}/hub/api/users/{name}",
                     headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
    r = admin_api.post(f"{base_url}/hub/api/users/{name}",
                       headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)
    assert r.status_code < 400, f"create user failed: {r.status_code} {r.text}"
    try:
        # open Configure user from the Users list (the username link)
        page = admin_portal.goto("/users")
        page.get_by_role("link", name=name, exact=True).click()
        page.wait_for_url(_ends_with(f"/users/{name}"))
        # breadcrumb parent links back to Users
        expect(page.locator(".ant-breadcrumb").get_by_role("link", name="Users")).to_be_visible()
        # Cancel returns to the Users list (not still on /users/{name})
        page.get_by_role("button", name="Cancel").click()
        page.wait_for_url(_ends_with("/users"))
    finally:
        admin_api.delete(f"{base_url}/hub/api/users/{name}",
                         headers={"X-XSRFToken": _xsrf(admin_api)}, timeout=30)


@pytest.mark.acc_crit(
    "navigation-patterns::Single-parent round-trip",
    "navigation-patterns::Parent crumb is a link",
)
def test_new_user_returns_to_users(admin_portal):
    page = admin_portal.goto("/users")
    page.get_by_role("button", name="Add User").click()
    page.wait_for_url(_ends_with("/users/new"))
    expect(page.locator(".ant-breadcrumb").get_by_role("link", name="Users")).to_be_visible()
    page.get_by_role("button", name="Cancel").click()
    page.wait_for_url(_ends_with("/users"))


@pytest.mark.acc_crit(
    "navigation-patterns::Single-parent round-trip",
    "navigation-patterns::Parent crumb is a link",
)
def test_new_group_returns_to_groups(admin_portal):
    page = admin_portal.goto("/groups")
    page.get_by_role("button", name="Add Group").click()
    page.wait_for_url(_ends_with("/groups/new"))
    expect(page.locator(".ant-breadcrumb").get_by_role("link", name="Groups")).to_be_visible()
    page.get_by_role("button", name="Cancel").click()
    page.wait_for_url(_ends_with("/groups"))
