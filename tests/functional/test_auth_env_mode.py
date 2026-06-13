"""Auth mode 2 - env-password admin (signup disabled).

Collected only by `make test-functional-env`, which configures the hub with
`JUPYTERHUB_ADMIN_PASSWORD` + signup off and does the restart-to-provision so a
preexisting admin record is seeded. These two quick checks verify that regime;
the rest of the suite is auth-mode-agnostic and is not re-run here.
"""

import requests
import pytest


@pytest.mark.envauth
def test_env_password_admin_authenticates(admin_page):
    # admin_page logged in with the env password; reaching the hub (not bounced
    # to /login) proves the pre-provisioned env-password admin authenticates.
    assert "/hub/login" not in admin_page.url


@pytest.mark.envauth
def test_signup_is_disabled(base_url):
    # Signup is off and the bootstrap window is closed (an admin already exists),
    # so the signup form must not be served.
    r = requests.get(f"{base_url}/hub/signup", timeout=10, allow_redirects=True)
    assert 'name="signup_password"' not in r.text
