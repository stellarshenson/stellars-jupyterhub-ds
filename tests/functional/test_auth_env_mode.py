"""Auth mode 2 - env-password admin (signup disabled).

Collected only by `make test-functional-env`, which configures the hub with
`JUPYTERHUB_ADMIN_PASSWORD` + signup off and does the restart-to-provision so a
preexisting admin record is seeded. These two quick checks verify that regime;
the rest of the suite is auth-mode-agnostic and is not re-run here.
"""

import requests
import pytest
from playwright.sync_api import expect


@pytest.mark.envauth
@pytest.mark.acc_crit("functional-test-harness::Admin env-password login (mode 2)")
def test_env_password_admin_authenticates(admin_portal):
    # The browser is authenticated from the API session that logged in with the env
    # password; the SPA app shell mounting (not bounced to /login) proves the
    # pre-provisioned env-password admin authenticates.
    page = admin_portal.goto("/dashboard")
    assert "/hub/login" not in page.url
    expect(page.locator(".ant-layout")).to_be_visible()


@pytest.mark.envauth
@pytest.mark.acc_crit("functional-test-harness::Signup enabled/disabled")
def test_signup_is_disabled(base_url):
    # Signup is off and the bootstrap window is closed (an admin already exists),
    # so the signup form must not be served.
    r = requests.get(f"{base_url}/hub/signup", timeout=10, allow_redirects=True)
    assert 'name="signup_password"' not in r.text
