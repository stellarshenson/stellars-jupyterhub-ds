"""Environment-stage header badge (docs/acceptance-criteria/acc-crit-branding-stage.md).

The badge is driven by JUPYTERHUB_BRANDING_STAGE -> window.jhdata.stage and rendered
by StageBadge in the portal header. The default (signup) deployment sets no stage, so
the badge is absent; the env-mode deployment (make test-functional-env) sets
JUPYTERHUB_BRANDING_STAGE=TST in compose.functional-env.yml and the badge shows 'TST'
in the blue/accent tone (--oh-cyan, the design theme's "blue").

Placement: ProLayout renders no top header under layout="side" (its Header returns
null), so the language/theme/stage controls live in the .oh-topbar header row, not in
actionsRender (which would drop them in the sider by the username). They sit top-right,
with the stage badge rightmost.
"""

import pytest
from playwright.sync_api import expect

STAGE_BADGE = ".oh-stage-badge"
HEADER = ".oh-topbar"
LANG = '.oh-topbar [aria-label="Language"]'
THEME = '.oh-topbar [aria-label="Theme"]'


def _x(locator):
    """Left edge of a single matched element."""
    box = locator.bounding_box()
    assert box is not None, "element not laid out"
    return box["x"]


@pytest.mark.acc_crit(
    "branding-stage::None by default",
    "branding-stage::Top-right placement",
)
def test_no_stage_badge_by_default(admin_portal):
    # Default deployment has no JUPYTERHUB_BRANDING_STAGE -> no badge in the header.
    page = admin_portal.goto("/home")
    assert page.locator(STAGE_BADGE).count() == 0
    # The language + theme controls render in the header topbar (top-right), NOT in
    # the sider by the username (the old actionsRender side-layout behaviour).
    expect(page.locator(LANG)).to_be_visible()
    expect(page.locator(THEME)).to_be_visible()
    # Right-aligned: the control cluster sits to the right of the breadcrumb.
    assert _x(page.locator(LANG)) > _x(page.locator(f"{HEADER} .ant-breadcrumb"))


@pytest.mark.envauth
@pytest.mark.acc_crit(
    "branding-stage::Env-driven",
    "branding-stage::Top-right placement",
    "branding-stage::Colour per stage",
)
def test_stage_badge_shows_configured_stage(admin_portal):
    # Env-mode sets JUPYTERHUB_BRANDING_STAGE=TST; the badge renders 'TST' in the
    # blue/accent tone (--oh-cyan).
    page = admin_portal.goto("/home")
    badge = page.locator(STAGE_BADGE)
    expect(badge).to_be_visible()
    assert badge.inner_text().strip().upper() == "TST"
    assert "--oh-cyan" in (badge.get_attribute("style") or "")
    # Placement: the badge is in the header topbar (not the sider) and is the
    # rightmost control - to the right of theme, which is to the right of language.
    assert page.locator(f"{HEADER} {STAGE_BADGE}").count() == 1
    assert _x(badge) > _x(page.locator(THEME)) > _x(page.locator(LANG))
