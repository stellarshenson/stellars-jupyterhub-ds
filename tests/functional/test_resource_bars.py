"""Resource-bar colour ramp (docs/acceptance-criteria/acc-crit-resource-bars.md).

A near-full CPU/memory bar must read as the strong danger red - the same
--color-danger token as the server-controls Stop button (antd colorError) - not a
pale orange. The /design-language reference page renders a 90% bar through the same
ResourceBars/barColor path used by the Server Status and Host Status widgets, so it
is the deterministic surface to assert the >=90% colour (live bars need real >=90%
metrics, which a test cannot force).
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.acc_crit("resource-bars::Gradual ramp past 50%")
def test_bar_at_90pct_uses_danger_token(admin_portal):
    page = admin_portal.goto("/design-language", ready=".oh-res-row")
    # the demo ResourceBars row labelled "90%" - its fill must use the danger token
    # (barColor saturates to var(--color-danger) at >=90%, == the Stop-button red).
    row = page.locator(".oh-res-row").filter(
        has=page.locator(".oh-res-label", has_text="90%")
    ).first
    expect(row).to_be_visible()
    fill = row.locator(".oh-res-bar > i")
    style = fill.get_attribute("style") or ""
    assert "var(--color-danger)" in style, f"90% bar is not the danger red: {style!r}"
