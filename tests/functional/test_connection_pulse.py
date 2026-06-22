"""Connection-status diode pulse - the halo must actually animate (the operator
reported it "did not pulsate" and "too subtle"). The pulse lives on the diode's
::after ring; severity rides BOTH speed and amplitude via two distinct keyframes:
connected = doh-pulse-calm (gentle dip+return) at --doh-status-pulse (3s); down =
doh-pulse-alert (hard fade+expand) 3x faster (calc /3) for urgency. prefers-reduced-
motion stops it. Asserted on the design-language page, which renders both the
connected (good) and down (warning) pills statically so both states are present
regardless of hub health.

Default regime (no special marker), Playwright like test_hub_ui.
"""

import pytest
from playwright.sync_api import expect


def _after_anim(page, selector):
    """Computed animation-name + animation-duration of an element's ::after halo."""
    return page.evaluate(
        """(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const cs = getComputedStyle(el, '::after');
            return { name: cs.animationName, duration: cs.animationDuration };
        }""",
        selector,
    )


def _secs(v):
    v = (v or "").split(",")[0].strip()
    if v.endswith("ms"):
        return float(v[:-2]) / 1000
    if v.endswith("s"):
        return float(v[:-1])
    return float(v or 0)


@pytest.mark.acc_crit(
    "duoptimumhub::Soft pulsing halo (slow connected, 3x faster down)",
    "duoptimumhub::Diode pulse demo on /design-language",
)
def test_connection_diode_pulses_good_and_warning(admin_portal):
    page = admin_portal.goto("/design-language")
    # the design page shows the reference demo: a connected (good) and a down (warning) pill
    expect(page.get_by_text("Diode pulse - good vs warning", exact=False).first).to_be_visible()
    page.emulate_media(reduced_motion="no-preference")

    ok = _after_anim(page, ".doh-conn-pill.ok .doh-conn-dot")
    down = _after_anim(page, ".doh-conn-pill.down .doh-conn-dot")
    # amplitude encodes severity: connected uses the calm keyframe, down the alert keyframe
    assert ok and ok["name"] == "doh-pulse-calm", f"connected diode not calm-pulsing: {ok}"
    assert down and down["name"] == "doh-pulse-alert", f"down diode not alert-pulsing: {down}"

    ok_s, down_s = _secs(ok["duration"]), _secs(down["duration"])
    assert ok_s > 0 and down_s > 0, f"zero pulse duration: ok={ok_s} down={down_s}"
    # down runs 3x faster than connected (urgency); allow rounding slack
    assert down_s < ok_s * 0.6, f"down diode not faster than connected: ok={ok_s}s down={down_s}s"


@pytest.mark.acc_crit("duoptimumhub::Reduced motion")
def test_connection_diode_respects_reduced_motion(admin_portal):
    page = admin_portal.goto("/design-language")
    page.emulate_media(reduced_motion="reduce")
    ok = _after_anim(page, ".doh-conn-pill.ok .doh-conn-dot")
    assert ok and ok["name"] == "none", f"pulse not stopped under reduced-motion: {ok}"
