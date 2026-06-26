"""Admin tables progressively drop lower-priority columns at tablet widths while
identity / state / actions always survive. antd `responsive: ['xl']` hides a column
below 1200px, `['lg']` below 992px; the mobile swap (<768) is a separate concern
(test_mobile_scope.py) and is left intact.

antd evaluates `responsive` via matchMedia at MOUNT, so the viewport is set BEFORE
each navigation (a programmatic resize of an already-mounted table does not reliably
re-trigger the breakpoint observer in headless Chromium). `not_to_be_visible` is robust
whether antd removes the column from the DOM or merely hides it."""

import pytest
from playwright.sync_api import expect


def _col(page, name):
    return page.locator(".ant-table-thead th").filter(has_text=name)


@pytest.mark.acc_crit("duoptimumhub::Responsive columns drop progressively on tablet")
def test_users_columns_drop_progressively(admin_portal):
    # desktop (>=1200): every column present
    admin_portal.page.set_viewport_size({"width": 1300, "height": 900})
    page = admin_portal.goto("/users")
    expect(_col(page, "User")).to_be_visible()
    expect(_col(page, "Created")).to_be_visible()
    expect(_col(page, "Last Seen")).to_be_visible()
    expect(_col(page, "Activity")).to_be_visible()
    expect(_col(page, "Groups")).to_be_visible()

    # tablet wide (>=992, <1200): the 'xl' time/metadata columns drop, 'lg' stay
    admin_portal.page.set_viewport_size({"width": 1100, "height": 900})
    page = admin_portal.goto("/users")
    expect(_col(page, "User")).to_be_visible()
    expect(_col(page, "Activity")).to_be_visible()
    expect(_col(page, "Created")).not_to_be_visible()
    expect(_col(page, "Last Seen")).not_to_be_visible()

    # tablet narrow (>=768, <992): the 'lg' secondary columns also drop; identity + state remain
    # (the Users table has no Actions column - the username cell links to Configure user)
    admin_portal.page.set_viewport_size({"width": 900, "height": 900})
    page = admin_portal.goto("/users")
    expect(_col(page, "User")).to_be_visible()
    expect(_col(page, "Authorised")).to_be_visible()
    expect(_col(page, "Activity")).not_to_be_visible()
    expect(_col(page, "Groups")).not_to_be_visible()


@pytest.mark.acc_crit("duoptimumhub::Responsive columns drop progressively on tablet")
def test_groups_columns_drop_on_tablet(admin_portal):
    # desktop (>=1200): all group columns present
    admin_portal.page.set_viewport_size({"width": 1300, "height": 900})
    page = admin_portal.goto("/groups")
    expect(_col(page, "Group")).to_be_visible()
    expect(_col(page, "Description")).to_be_visible()
    expect(_col(page, "Members")).to_be_visible()
    expect(_col(page, "Policies")).to_be_visible()

    # tablet wide (>=992, <1200): 'xl' Members drops; 'lg' Description/Policies stay
    admin_portal.page.set_viewport_size({"width": 1100, "height": 900})
    page = admin_portal.goto("/groups")
    expect(_col(page, "Description")).to_be_visible()
    expect(_col(page, "Members")).not_to_be_visible()

    # tablet narrow (>=768, <992): 'lg' Description/Policies also drop; #/Group/Actions remain
    admin_portal.page.set_viewport_size({"width": 900, "height": 900})
    page = admin_portal.goto("/groups")
    expect(_col(page, "Group")).to_be_visible()
    expect(_col(page, "Actions")).to_be_visible()
    expect(_col(page, "Description")).not_to_be_visible()
    expect(_col(page, "Policies")).not_to_be_visible()
