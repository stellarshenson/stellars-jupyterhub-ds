"""Environment-stage header badge (docs/acc-crit-branding-stage.md).

The badge is driven by JUPYTERHUB_BRANDING_STAGE -> window.jhdata.stage and rendered
by StageBadge in the portal header. The default (signup) deployment sets no stage, so
the badge is absent; the env-mode deployment (make test-functional-env) sets
JUPYTERHUB_BRANDING_STAGE=TST in compose.functional-env.yml and the badge shows 'TST'
in the blue/accent tone (--oh-cyan, the design theme's "blue").
"""

import pytest
from playwright.sync_api import expect

STAGE_BADGE = ".oh-stage-badge"


@pytest.mark.acc_crit("branding-stage::None by default")
def test_no_stage_badge_by_default(admin_portal):
    # Default deployment has no JUPYTERHUB_BRANDING_STAGE -> no badge in the header.
    page = admin_portal.goto("/dashboard")
    assert page.locator(STAGE_BADGE).count() == 0


@pytest.mark.envauth
@pytest.mark.acc_crit(
    "branding-stage::Env-driven",
    "branding-stage::Top-right placement",
    "branding-stage::Colour per stage",
)
def test_stage_badge_shows_configured_stage(admin_portal):
    # Env-mode sets JUPYTERHUB_BRANDING_STAGE=TST; the badge renders 'TST' in the
    # blue/accent tone (--oh-cyan).
    page = admin_portal.goto("/dashboard")
    badge = page.locator(STAGE_BADGE)
    expect(badge).to_be_visible()
    assert badge.inner_text().strip().upper() == "TST"
    assert "--oh-cyan" in (badge.get_attribute("style") or "")
