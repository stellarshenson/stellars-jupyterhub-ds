"""Roles reference page - the admin-only /roles screen renders a single
role-definitions panel (one table: role, description, how assigned, who) and the
capability x role access matrix where every row carries a terse description and
each cell shows an access LEVEL (not a bare yes/no).
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.acc_crit(
    "roles-reference::Role definitions single panel",
    "roles-reference::Role table columns",
    "roles-reference::One row per capability",
    "roles-reference::Per-capability description",
    "roles-reference::Access level per cell, not just yes/no",
)
def test_roles_page_renders(admin_portal):
    page = admin_portal.goto("/roles")

    # ONE role-definitions panel, holding a single table with the four columns
    defs = page.locator(".ant-card").filter(has_text="Role definitions")
    expect(defs).to_be_visible()
    for col in ("Role", "Description", "How assigned", "Who"):
        expect(defs.locator("th.ant-table-cell").filter(has_text=col).first).to_be_visible()
    # one row per role (admin + user)
    expect(defs.locator("tbody tr").filter(has_text="Admin").first).to_be_visible()
    expect(defs.locator("tbody tr").filter(has_text="User").first).to_be_visible()

    # access matrix: capability rows, each with a terse CRUD-worded description
    expect(page.get_by_text("Rename user", exact=False).first).to_be_visible()
    expect(page.get_by_text("Broadcast notifications", exact=False).first).to_be_visible()
    expect(page.get_by_text("List, create, read, write and remove any account", exact=False).first).to_be_visible()
    # per-cell access levels render as pills, not a bare yes/no
    expect(page.get_by_text("Full", exact=True).first).to_be_visible()
    expect(page.get_by_text("Denied", exact=True).first).to_be_visible()
