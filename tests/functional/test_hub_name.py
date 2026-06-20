"""JUPYTERHUB_HUB_NAME branding: the configurable display name must surface as the
portal logo tooltip (title) and as the login/signup screen text.

The functest hub sets JUPYTERHUB_HUB_NAME="Functest Hub Name" (compose.functional.yml);
the shipped default is "DuOptimum Hub" (baked in Dockerfile.jupyterhub). These tests
assert the configured value reaches both surfaces - logged-out (login screen) and
logged-in (logo tooltip).
"""

import pytest
from playwright.sync_api import expect

HUB_NAME = "Functest Hub Name"


@pytest.mark.acc_crit("duoptimumhub::Hub name on the login screen")
def test_hub_name_on_login_screen(page, base_url):
    # logged out: the login screen subtitle shows the configured display name, not the
    # hardcoded default. window.jhdata.hub_name is injected by duoptimum_login.html.
    page.goto(f"{base_url}/hub/login", wait_until="domcontentloaded")
    expect(page.locator(".doh-auth-sub")).to_have_text(HUB_NAME)


@pytest.mark.acc_crit("duoptimumhub::Hub name as the logo tooltip")
def test_hub_name_logo_tooltip(admin_portal):
    # logged in: the portal logo link carries the configured display name as its title
    # (the hover tooltip), driven by hubName() reading window.jhdata.hub_name.
    page = admin_portal.goto("/home")
    expect(page.locator(f'a[title="{HUB_NAME}"]')).to_be_visible()
