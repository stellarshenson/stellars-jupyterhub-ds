"""Per-user Display Options harness, driven through the SPA Settings page.

acc-crit-duoptimumhub.md -> "Display options (per-user settings harness)":
- the Settings page renders an accordion (antd Collapse) whose first panel,
  Display Options, is collapsed by default and holds the three CPU-mode options
- each CPU option is an exclusive Segmented control (Total normalized vs Core
  aggregate)
- the chosen value persists PER USER server-side and is reflected after a reload

Persistence needs the backend display-preferences endpoint baked, so this runs
against a live stack on rebuild. The test restores the default at the end so it
does not leave the admin's prefs changed for other tests.
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.acc_crit(
    "display-options::Accordion",
    "display-options::Three CPU options",
    "display-options::Control types",
    "display-options::Per-user persistence",
)
def test_display_options_accordion_and_persist(admin_portal):
    page = admin_portal.goto("/settings", ready=".ant-collapse")

    # Display Options is collapsed by default - expand it
    page.get_by_text("Display Options", exact=True).click()
    # the three CPU options are listed
    expect(page.get_by_text("My Server Status CPU", exact=True)).to_be_visible()
    expect(page.get_by_text("Host Status CPU", exact=True)).to_be_visible()
    expect(page.get_by_text("Servers list & widget CPU", exact=True)).to_be_visible()

    # flip "Servers list & widget CPU" (default 'cores') to normalized
    row = page.locator("tr").filter(has_text="Servers list & widget CPU")
    row.get_by_text("Total normalized", exact=False).click()

    # persisted: reload, reopen, the normalized option is the selected segment
    page = admin_portal.goto("/settings", ready=".ant-collapse")
    page.get_by_text("Display Options", exact=True).click()
    row = page.locator("tr").filter(has_text="Servers list & widget CPU")
    expect(row.locator(".ant-segmented-item-selected")).to_contain_text("Total normalized")

    # restore the default so the admin's prefs are unchanged for other tests
    row.get_by_text("Core aggregate", exact=False).click()
    page = admin_portal.goto("/settings", ready=".ant-collapse")
    page.get_by_text("Display Options", exact=True).click()
    row = page.locator("tr").filter(has_text="Servers list & widget CPU")
    expect(row.locator(".ant-segmented-item-selected")).to_contain_text("Core aggregate")
