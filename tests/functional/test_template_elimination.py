"""End-to-end checks for the html_templates_enhanced elimination (#419).

Run against the LIVE stack AFTER the relic-free image is redeployed. They prove the
portal SPA owns every user/admin journey (the deleted custom templates are never landed
on), that the old assets are gone, and that the few framework pages JupyterHub still
renders fall back to plain stock JupyterHub/NativeAuth - unbranded, no old chrome.
"""
import time

import pytest
import requests
from playwright.sync_api import expect

# the three static assets the deleted page.html chrome used to load; their presence in
# any served page means the old Bootstrap chrome (or its template) survived
RELIC_ASSETS = ("custom.css", "session-timer.js", "mobile.js")


def _ensure_server_stopped(session, base_url, user, timeout=90):
    """Stop the user's default server and wait until it is neither active nor pending,
    so a following /user/{user}/ request hits the clean offline branch (not the
    spawn-pending redirect). Idempotent - a not-running server just returns fast."""
    tok = session.cookies.get("_xsrf")
    session.delete(f"{base_url}/hub/api/users/{user}/server",
                   headers={"X-XSRFToken": tok}, timeout=30)
    deadline = time.time() + timeout
    while time.time() < deadline:
        info = session.get(f"{base_url}/hub/api/users/{user}", timeout=10).json()
        default = info.get("servers", {}).get("")  # "" == default server
        if not default or not (default.get("active") or default.get("pending")):
            return
        time.sleep(2)


@pytest.mark.acc_crit(
    "duoptimumhub::No old-asset 404",
    "duoptimumhub::Functional (e2e)",
)
def test_spa_journey_requests_no_old_assets(admin_portal):
    """Browsing the whole portal never requests custom.css/session-timer.js/mobile.js."""
    seen = []
    admin_portal.page.on("response", lambda r: seen.append(r.url))
    for route in ("/home", "/servers", "/users", "/activity", "/settings", "/groups"):
        admin_portal.goto(route)
    offenders = [u for u in seen if any(a in u for a in RELIC_ASSETS)]
    assert not offenders, f"portal requested removed assets: {offenders}"


@pytest.mark.acc_crit("duoptimumhub::No old-asset 404")
def test_old_assets_are_gone(base_url):
    """The removed static assets 404 when requested directly (cp lines dropped)."""
    for path in (
        "/hub/static/css/custom.css",
        "/hub/static/js/session-timer.js",
        "/hub/static/js/mobile.js",
    ):
        r = requests.get(f"{base_url}{path}", timeout=30)
        assert r.status_code == 404, f"{path} still served: {r.status_code}"


@pytest.mark.acc_crit("duoptimumhub::DELETE - unreachable")
def test_unknown_hub_route_served_by_spa(admin_portal):
    """An unknown /hub route is caught by the portal catch-all and renders the SPA
    shell, not the old 404.html (which has no antd layout)."""
    page = admin_portal.goto("/this-route-does-not-exist")
    expect(page.locator(".ant-layout")).to_be_visible()


@pytest.mark.acc_crit("duoptimumhub::DELETE - unreachable")
def test_logout_redirects_not_rendered(base_url):
    """/hub/logout redirects (auto_login=False) instead of rendering logout.html."""
    r = requests.get(f"{base_url}/hub/logout", allow_redirects=False, timeout=30)
    assert r.status_code in (301, 302, 303, 307, 308), f"logout did not redirect: {r.status_code}"
    assert not any(a in r.text for a in RELIC_ASSETS), "old chrome served on logout"


@pytest.mark.acc_crit("duoptimumhub::DELETE - vestigial (SPA owns journey)")
def test_change_password_page_has_no_old_chrome(admin_api, base_url):
    """The SPA owns password change (Profile); a direct GET to the legacy route now
    falls back to stock NativeAuth - no custom.css/session-timer.js chrome."""
    r = admin_api.get(f"{base_url}/hub/change-password", timeout=30)
    assert r.status_code < 500, f"change-password errored: {r.status_code}"
    assert not any(a in r.text for a in RELIC_ASSETS), "old chrome served on change-password"


@pytest.mark.acc_crit("duoptimumhub::DELETE - vestigial (SPA owns journey)")
def test_authorization_area_has_no_old_chrome(admin_api, base_url):
    """The SPA Users page owns pending-user authorization; a direct GET to /hub/authorize
    now falls back to stock NativeAuth - no old chrome."""
    r = admin_api.get(f"{base_url}/hub/authorize", timeout=30)
    assert r.status_code < 500, f"authorize errored: {r.status_code}"
    assert not any(a in r.text for a in RELIC_ASSETS), "old chrome served on authorize"


@pytest.mark.acc_crit("duoptimumhub::KEEP as plain JupyterHub")
def test_my_message_renders_stock(base_url):
    """my_message is irreducible NativeAuth plumbing (the email-confirm landing); it
    persists as plain stock NativeAuth after the custom dir is gone - renders, no old chrome."""
    r = requests.get(f"{base_url}/hub/confirm/invalid-slug", timeout=30)
    assert r.status_code == 200, f"confirm page status {r.status_code}"
    assert not any(a in r.text for a in RELIC_ASSETS), "old chrome served on my_message"


@pytest.mark.acc_crit(
    "duoptimumhub::CLOSE-GAP cold-start redirect",
    "duoptimumhub::Functional (e2e)",
)
def test_offline_default_server_redirects_to_spa_starting(admin_api, admin_creds, base_url):
    """Cold start: opening /user/{admin}/ while the default server is offline 303-redirects
    into the SPA Starting page instead of rendering the stock not_running.html. Proves the
    portal owns the cold-start journey (DuoptimumUserUrlHandler). Accept: text/html is
    required - JSON/api requests take JupyterHub's 503 branch before the render."""
    user = admin_creds["username"]
    _ensure_server_stopped(admin_api, base_url, user)
    r = admin_api.get(
        f"{base_url}/hub/user/{user}/",
        headers={"Accept": "text/html"},
        allow_redirects=False,
        timeout=30,
    )
    assert r.status_code == 303, f"expected 303 redirect, got {r.status_code}: {r.text[:200]}"
    loc = r.headers.get("Location", "")
    assert loc.endswith(f"/servers/{user}/starting"), f"unexpected redirect target: {loc}"
    assert not any(a in r.text for a in RELIC_ASSETS), "old chrome served on cold-start redirect"
