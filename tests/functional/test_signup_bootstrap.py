"""Signup-on first-admin bootstrap (initial: JUPYTERHUB_SIGNUP_ENABLED=1, no env password).

Collected only by `make test-functional-signup-bootstrap` (FUNCTEST_AUTH_MODE=signupbootstrap).
This is the shipped-default path an adversarial review flagged: signup enabled, no env
password, fresh DB. The configured admin (JUPYTERHUB_ADMIN) self-signs-up via the open
form and must be AUTO-AUTHORISED (first_admin_self_signup_pending) - so they log in
immediately without anyone approving them, not stranded is_authorized=False. The
`_bootstrap_admin` fixture performs the admin self-signup; if the fix were absent the
admin would stay unauthorised and the `admin_api` login would fail, failing these tests.
"""

import pytest
from playwright.sync_api import expect

ADMIN = "functestadmin"


@pytest.mark.signupbootstrap
@pytest.mark.acc_crit("functional-test-harness::Signup-on first admin auto-authorised")
def test_admin_self_signup_is_auto_authorised(admin_api, base_url):
    # signup on + no env password: the admin's own self-signup must self-authorise.
    users = admin_api.get(f"{base_url}/hub/api/native-users", timeout=10).json().get("users", [])
    rec = next((u for u in users if u["username"] == ADMIN), None)
    assert rec and rec["is_authorized"], f"admin not auto-authorised on self-signup: {rec}"


@pytest.mark.signupbootstrap
@pytest.mark.acc_crit("functional-test-harness::Admin reaches the portal")
def test_admin_reaches_portal_after_self_signup(admin_portal):
    # the auto-authorised admin logs in (cookie-injected) and loads the SPA app shell.
    page = admin_portal.goto("/home")
    expect(page.locator(".ant-layout")).to_be_visible()


@pytest.mark.signupbootstrap
@pytest.mark.acc_crit("functional-test-harness::Non-admin needs authorization")
def test_non_admin_self_signup_still_pending(signup_user, admin_api, base_url):
    # the auto-authorise guard is name == admin: a non-admin self-signup stays pending.
    signup_user("functestpending2", "pending-secret")
    users = admin_api.get(f"{base_url}/hub/api/native-users", timeout=10).json().get("users", [])
    rec = next((u for u in users if u["username"] == "functestpending2"), None)
    assert rec and not rec["is_authorized"], f"non-admin should be pending, got: {rec}"
