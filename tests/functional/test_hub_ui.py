"""Portal page-render smoke - every major SPA screen mounts and shows its
signature control. These need no successful lab spawn, so they run against the
minimal singleuser image. Selectors use visible text / antd roles / placeholders
(there are no data-testid attributes in the SPA).
"""

import re

import pytest
import requests
from playwright.sync_api import expect


# ── unauthenticated ────────────────────────────────────────────────────────────

@pytest.mark.acc_crit("functional-test-harness::Health endpoint")
def test_health_endpoint(base_url):
    r = requests.get(f"{base_url}/hub/health", timeout=10)
    assert r.status_code == 200


@pytest.mark.acc_crit("functional-test-harness::Login shell served")
def test_login_shell_served(base_url):
    # The hub serves the SPA auth shell at /hub/login (window.jhdata.authPage =
    # "login" makes the SPA render the antd sign-in screen); assert the shell + its
    # bundle are served, not the deep JS-rendered form (which is covered by login
    # working end-to-end in the admin_api fixture).
    r = requests.get(f"{base_url}/hub/login", timeout=10)
    assert r.status_code == 200
    assert re.search(r'authPage:\s*"login"', r.text), "login auth shell not served"


# ── authenticated: portal lands on the dashboard ─────────────────────────────────

@pytest.mark.acc_crit(
    "functional-test-harness::Admin reaches the portal",
    "functional-test-harness::Signup bootstrap window",
)
def test_admin_reaches_portal(admin_portal):
    # The injected session cookies authenticate the browser; the SPA app shell
    # (not the auth shell) mounts, proving the admin session is valid.
    page = admin_portal.goto("/home")
    assert "/hub/login" not in page.url
    expect(page.locator(".ant-layout")).to_be_visible()


# ── per-page render smoke (signature control proves the page mounted) ────────────

@pytest.mark.acc_crit("functional-test-harness::SPA page-render smoke")
def test_dashboard_renders(admin_portal):
    page = admin_portal.goto("/home")
    # the admin dashboard always shows the "Active Servers" widget card
    expect(page.get_by_text("Active Servers", exact=False).first).to_be_visible()


@pytest.mark.acc_crit("functional-test-harness::SPA page-render smoke")
def test_servers_page_renders(admin_portal):
    page = admin_portal.goto("/servers")
    expect(page.locator("input[placeholder*='Filter by user']")).to_be_visible()


@pytest.mark.acc_crit("functional-test-harness::SPA page-render smoke")
def test_users_page_renders(admin_portal):
    page = admin_portal.goto("/users")
    # the "Inactive" scope pill is unique to the Users screen
    expect(page.get_by_text("Inactive", exact=False).first).to_be_visible()


@pytest.mark.acc_crit(
    "functional-test-harness::SPA page-render smoke",
    "functional-test-harness::Groups page renders",
)
def test_groups_page_renders(admin_portal):
    page = admin_portal.goto("/groups")
    expect(page.get_by_role("button", name="Add Group")).to_be_visible()


@pytest.mark.acc_crit("functional-test-harness::SPA page-render smoke")
def test_events_page_renders(admin_portal):
    page = admin_portal.goto("/events")
    expect(page.get_by_role("button", name="Clear", exact=True)).to_be_visible()


@pytest.mark.acc_crit(
    "functional-test-harness::SPA page-render smoke",
    "functional-test-harness::Settings / Notifications render",
)
def test_notifications_page_renders(admin_portal):
    page = admin_portal.goto("/notifications")
    expect(page.get_by_role("button", name="Send Broadcast")).to_be_visible()


@pytest.mark.acc_crit(
    "functional-test-harness::SPA page-render smoke",
    "functional-test-harness::Settings / Notifications render",
)
def test_settings_page_renders(admin_portal):
    page = admin_portal.goto("/settings")
    expect(page.get_by_text("Full Reference", exact=False).first).to_be_visible()


@pytest.mark.acc_crit("functional-test-harness::SPA page-render smoke")
def test_lab_setup_page_renders(admin_portal):
    page = admin_portal.goto("/lab-container")
    expect(page.get_by_text("Lab image", exact=False).first).to_be_visible()


@pytest.mark.acc_crit("functional-test-harness::SPA page-render smoke")
def test_design_language_page_renders(admin_portal):
    page = admin_portal.goto("/design-language")
    expect(page.get_by_text("Design language", exact=False).first).to_be_visible()
