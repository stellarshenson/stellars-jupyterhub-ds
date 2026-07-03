"""Functional E2E: the mobile view is a read-only status + own-server-control panel.

Below the 768px useIsMobile breakpoint the portal sheds desktop ceremony and keeps
only what the phone persona needs (the account owner / admin checking in, not doing
data science):

- header is logo + theme + connection pill + stage badge - the language switcher is
  dropped on mobile to make room for the full-text connection pill; the in-flow
  HubConnectionIndicator still carries the down-state detail, and there are no breadcrumbs
- the own-server card carries no Open-Lab (there is nowhere useful to go on a phone)
- the Servers page is a READ-ONLY admin fleet glance: no per-card lifecycle actions,
  no Start-All / Stop-All, plus a compact CPU / Mem / Activity readout

Desktop is unchanged; these assertions just resize the same admin session. The
permission cut (no controlling another user's server from a phone) is the headline:
every lifecycle entry point on the mobile Servers page is gone.
"""

import pytest
from playwright.sync_api import expect

MOBILE = {"width": 375, "height": 720}  # below the 768px useIsMobile breakpoint


@pytest.mark.acc_crit(
    "mobile-scope::Minimal chrome",
    "mobile-scope::No extra header text",
)
def test_mobile_header_minimal(admin_portal):
    page = admin_portal.page
    page.set_viewport_size(MOBILE)
    admin_portal.goto("/home")
    # brand logo is the only topbar content on the left (the sider - and its logo - is
    # dropped on mobile, so the topbar carries the logo as an <img>)
    expect(page.locator(".doh-topbar img").first).to_be_visible()
    # single header only: the brand logo renders exactly once - the old bug stacked
    # ProLayout's own mobile header on top of the content topbar (two headers)
    expect(page.locator("img[src*='jh-logo']")).to_have_count(1)
    # theme switcher stays; the language switcher is dropped on mobile to make room for
    # the full-text connection pill (operator 2026-07-03)
    expect(page.get_by_role("button", name="Theme")).to_be_visible()
    expect(page.get_by_role("button", name="Language")).to_have_count(0)
    # the connection pill now shows on mobile at full text, normal height (level with the
    # stage badge) - "Connected" while the hub answers; the in-flow HubConnectionIndicator
    # still carries the full down-state detail with elapsed
    pill = page.locator(".doh-conn-pill")
    expect(pill).to_have_count(1)
    expect(pill).to_contain_text("Connected")
    # no breadcrumb row stealing vertical space
    expect(page.locator(".doh-topbar .ant-breadcrumb")).to_have_count(0)


@pytest.mark.acc_crit("mobile-scope::No Open-Lab")
def test_mobile_home_has_no_open_lab(admin_portal):
    page = admin_portal.page
    page.set_viewport_size(MOBILE)
    admin_portal.goto("/home")
    # Open-Lab is removed from the mobile surface entirely (any server state)
    expect(page.get_by_role("button", name="Open Lab")).to_have_count(0)


@pytest.mark.acc_crit(
    "mobile-scope::Own-server control only",
    "mobile-scope::Others read-only",
    "mobile-scope::CPU",
    "mobile-scope::Memory",
    "mobile-scope::Volumes",
    "mobile-scope::Activity",
)
def test_mobile_servers_readonly_with_telemetry(admin_portal):
    page = admin_portal.page
    page.set_viewport_size(MOBILE)
    admin_portal.goto("/servers")
    # read-only fleet glance: no fleet-wide controls, no per-card lifecycle actions
    for name in ("Start All", "Stop All", "Restart", "Enter Session"):
        expect(page.get_by_role("button", name=name)).to_have_count(0)
    # compact telemetry readout on the cards, four aligned columns CPU / Mem / Vol / Act
    # (at least the admin's own row exists)
    expect(page.get_by_text("CPU").first).to_be_visible()
    expect(page.get_by_text("Mem").first).to_be_visible()
    expect(page.get_by_text("Vol").first).to_be_visible()
    expect(page.get_by_text("Act").first).to_be_visible()


@pytest.mark.acc_crit("mobile-scope::Version footer plain (no copy/tooltip)")
def test_mobile_version_footer_not_clickable(admin_portal):
    """On mobile the footer version still shows, but the click-to-copy affordance
    (and its build-id hover tooltip) is desktop-only - nothing to hover/copy on a
    touch screen. The .doh-version-copy clickable span is absent on mobile."""
    page = admin_portal.page
    page.set_viewport_size(MOBILE)
    admin_portal.goto("/home")
    expect(page.get_by_text("Duoptimum Hub", exact=False).first).to_be_visible()
    expect(page.locator(".doh-version-copy")).to_have_count(0)
