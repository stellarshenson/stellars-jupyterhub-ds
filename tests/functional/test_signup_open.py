"""Signup-open regime (initial condition: JUPYTERHUB_SIGNUP_ENABLED=1).

Collected only by `make test-functional-signup-open` (FUNCTEST_AUTH_MODE=signupopen).
Verifies the open-signup flow that the default signup-bootstrap run cannot reach:
the signup form is served, a non-admin self-signs-up into the pending queue, and
the admin authorises them through the SPA Users page.
"""

import requests
import pytest
from playwright.sync_api import expect

PENDING_USER = "functestpending"


@pytest.mark.signupopen
@pytest.mark.acc_crit("functional-test-harness::Signup enabled/disabled")
def test_signup_form_served(base_url):
    # signup enabled -> the NativeAuth signup form is served to anyone.
    r = requests.get(f"{base_url}/hub/signup", timeout=10)
    assert 'name="signup_password"' in r.text


@pytest.mark.signupopen
@pytest.mark.acc_crit(
    "functional-test-harness::Non-admin needs authorization",
    "functional-test-harness::Admin authorizes user",
)
def test_self_signup_then_admin_authorises(admin_portal, signup_user, admin_api, base_url):
    # A non-admin self-signs-up; not matching the admin self-approval, they land in
    # the pending queue (authorised=False).
    signup_user(PENDING_USER, "pending-secret")

    page = admin_portal.goto("/users")
    expect(page.get_by_text("Pending authorisation", exact=False)).to_be_visible()
    row = page.locator(".oh-pending-table tr").filter(
        has=page.get_by_role("link", name=PENDING_USER, exact=True))
    expect(row).to_be_visible()

    # Authorise through the SPA; the pending queue then empties (only user pending).
    row.get_by_role("button", name="Authorize").click()
    expect(page.locator(".oh-pending-table")).to_have_count(0)

    # and the backend now reports the user authorised (deterministic, no refetch race).
    users = admin_api.get(f"{base_url}/hub/api/native-users", timeout=10).json().get("users", [])
    rec = next((u for u in users if u["username"] == PENDING_USER), None)
    assert rec and rec["is_authorized"], f"{PENDING_USER} not authorised after SPA action: {rec}"
