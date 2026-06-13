"""Hub-side UI tests - exercise the JupyterHub admin pages we own, foremost the
group / policy management page. These need no successful lab spawn, so they run
against the minimal singleuser image without depending on it.
"""

import requests
from playwright.sync_api import expect


# ── unauthenticated ────────────────────────────────────────────────────────────

def test_health_endpoint(base_url):
    r = requests.get(f"{base_url}/hub/health", timeout=10)
    assert r.status_code == 200


def test_login_page_renders(page, base_url):
    page.goto(f"{base_url}/hub/login")
    expect(page.locator("input[name='username']")).to_be_visible()
    expect(page.locator("input[name='password']")).to_be_visible()


# ── authenticated admin pages ──────────────────────────────────────────────────

def test_admin_login_reaches_hub(admin_page, base_url):
    assert "/hub/login" not in admin_page.url


def test_groups_page_renders(admin_page, base_url):
    admin_page.goto(f"{base_url}/hub/groups")
    expect(admin_page.locator("h1")).to_contain_text("Groups")
    expect(admin_page.get_by_role("button", name="Add Group")).to_be_visible()


def test_settings_page_renders(admin_page, base_url):
    resp = admin_page.goto(f"{base_url}/hub/settings")
    assert resp.status < 400


def test_activity_page_renders(admin_page, base_url):
    resp = admin_page.goto(f"{base_url}/hub/activity")
    assert resp.status < 400


def test_notifications_page_renders(admin_page, base_url):
    resp = admin_page.goto(f"{base_url}/hub/notifications")
    assert resp.status < 400


# ── group / policy lifecycle (the feature under test) ──────────────────────────

def test_group_policy_lifecycle(admin_page, base_url):
    name = "functestgrp"
    page = admin_page
    page.goto(f"{base_url}/hub/groups")

    # Create a group via the Add Group modal.
    page.get_by_role("button", name="Add Group").click()
    expect(page.locator("#add-group-modal")).to_be_visible()
    page.fill("#new-group-name", name)
    page.click("#create-group-btn")
    row = page.locator(f"#groups-table-body tr[data-name='{name}']")
    expect(row).to_be_visible()

    # Clicking the group name opens its configuration (the cog button was dropped).
    page.locator(f"#groups-table-body a.btn-config[data-name='{name}']").click()
    expect(page.locator("#config-group-modal")).to_be_visible()
    expect(page.locator("#config-group-name-badge")).to_contain_text(name)

    # Enable the Sudo Access policy section and save.
    page.check("#config-sudo-active")
    page.click("#save-config-btn")
    expect(page.locator("#config-group-modal")).to_be_hidden()

    # The group row now shows a Sudo badge (rendered from server policy_summary).
    expect(row).to_contain_text("Sudo")

    # Reopen the config - the Sudo switch persisted as on.
    page.locator(f"#groups-table-body a.btn-config[data-name='{name}']").click()
    expect(page.locator("#config-group-modal")).to_be_visible()
    expect(page.locator("#config-sudo-active")).to_be_checked()
    # close the modal via its dismiss control
    page.locator("#config-group-modal [data-bs-dismiss='modal']").first.click()
    expect(page.locator("#config-group-modal")).to_be_hidden()

    # Delete the group (JS confirm() dialog -> accept; AJAX DELETE). Reload to
    # assert the UI reflects the server-side delete (the in-place re-render lags).
    page.once("dialog", lambda d: d.accept())
    page.locator(f"#groups-table-body tr[data-name='{name}'] .btn-delete").click()
    page.wait_for_timeout(1000)
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.locator(f"#groups-table-body tr[data-name='{name}']")).to_have_count(0, timeout=10000)
