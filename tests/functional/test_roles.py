"""Roles reference page - the admin-only /roles screen renders the role
definition cards and the capability x role access matrix with per-cell access
levels (not a bare yes/no).
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.acc_crit(
    "roles-reference::One row per capability",
    "roles-reference::A column per role",
    "roles-reference::Access level per cell, not just yes/no",
    "roles-reference::Admin definition (page)",
)
def test_roles_page_renders(admin_portal):
    page = admin_portal.goto("/roles")
    # role definition cards (Admin + User)
    titles = page.locator(".ant-card-head-title")
    expect(titles.filter(has_text="Admin").first).to_be_visible()
    expect(titles.filter(has_text="User").first).to_be_visible()
    # capability rows from the access matrix (a page row + an action row)
    expect(page.get_by_text("Rename user", exact=False).first).to_be_visible()
    expect(page.get_by_text("Broadcast notifications", exact=False).first).to_be_visible()
    # per-cell access levels render as pills, not a bare yes/no
    expect(page.get_by_text("Full", exact=True).first).to_be_visible()
    expect(page.get_by_text("Denied", exact=True).first).to_be_visible()
