"""Extending the idle TTL must read 100% against the HIGH-WATER MARK, not ~50%
against the far absolute ceiling (DEF-13), and the extend slider must default to a
stable +4h - not the (shifting) maximum.

Regression: the bar measured banked time against `base + max_extension` (72h live),
so a session extended to 35h read ~48.6% the instant it was extended. The backend
now stores `display_ceiling` (remaining last extended TO) and returns
`display_ceiling_seconds`; the bar measures against it, so a just-extended session
reads ~100%.
"""

import re
import time

import pytest
from playwright.sync_api import expect


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _post(s, base, path, json=None):
    return s.post(f"{base}{path}", json=json, headers={"X-XSRFToken": _xsrf(s)}, timeout=60)


def _delete(s, base, path):
    return s.delete(f"{base}{path}", headers={"X-XSRFToken": _xsrf(s)}, timeout=60)


def _server_state(admin_api, base, user):
    r = admin_api.get(f"{base}/hub/api/users/{user}", timeout=30)
    return (r.json() or {}).get("servers", {}) if r.status_code < 400 else {}


def _session_info(admin_api, base, user):
    return admin_api.get(f"{base}/hub/api/users/{user}/session-info", timeout=30).json()


def _wait(pred, timeout=120, interval=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return False


@pytest.mark.acc_crit(
    "duoptimumhub::Two-phase pct (high-water mark)",
    "duoptimumhub::Scenario table holds",
)
def test_extend_bar_reads_full_against_high_water_mark(admin_api, base_url):
    user = "ttl-user"
    _delete(admin_api, base_url, f"/hub/api/users/{user}")  # clean slate
    assert _post(admin_api, base_url, f"/hub/api/users/{user}").status_code < 400, "create user failed"
    try:
        _post(admin_api, base_url, f"/hub/api/users/{user}/server")
        assert _wait(lambda: _server_state(admin_api, base_url, user).get("", {}).get("ready")), \
            "server never became ready"

        before = _session_info(admin_api, base_url, user)
        assert before.get("culler_enabled"), f"idle culler must be on for this test: {before}"
        base_sec = before["timeout_seconds"]

        r = _post(admin_api, base_url, f"/hub/api/users/{user}/extend-session", json={"hours": 4})
        assert r.status_code < 400 and r.json().get("success"), f"extend failed: {r.status_code} {r.text}"

        after = _session_info(admin_api, base_url, user)
        remaining = after["time_remaining_seconds"]
        ceiling = after["display_ceiling_seconds"]
        assert remaining > base_sec, f"extend did not bank above base: remaining={remaining} base={base_sec}"
        assert ceiling, f"display_ceiling_seconds missing after extend: {after}"
        # the bar's 100% reference is the high-water mark, so it reads ~100% on extend
        pct = remaining / ceiling * 100
        assert pct >= 95, f"bar should read ~100% against the high-water mark, got {pct:.1f}% (DEF-13 regression?)"
    finally:
        _delete(admin_api, base_url, f"/hub/api/users/{user}/server")
        _delete(admin_api, base_url, f"/hub/api/users/{user}")
        _wait(lambda: not _server_state(admin_api, base_url, user))


@pytest.mark.acc_crit("duoptimumhub::Session extend is audited")
def test_extend_records_event(admin_api, base_url):
    """Extending a session records a 'server' audit event naming the user + amount,
    so the Events feed shows who bought more idle time."""
    user = "ttl-evt-user"
    _delete(admin_api, base_url, f"/hub/api/users/{user}")  # clean slate
    assert _post(admin_api, base_url, f"/hub/api/users/{user}").status_code < 400, "create user failed"
    try:
        _post(admin_api, base_url, f"/hub/api/users/{user}/server")
        assert _wait(lambda: _server_state(admin_api, base_url, user).get("", {}).get("ready")), \
            "server never became ready"
        r = _post(admin_api, base_url, f"/hub/api/users/{user}/extend-session", json={"hours": 2})
        assert r.status_code < 400 and r.json().get("success"), f"extend failed: {r.status_code} {r.text}"

        # the extend is recorded synchronously before the POST returns -> the feed has it now
        events = admin_api.get(f"{base_url}/hub/api/events", timeout=30).json().get("events", [])
        texts = [e.get("text", "") for e in events]
        assert any(user in t and "session extended" in t for t in texts), \
            f"extend must record an audit event naming the user; recent events={texts[:5]}"
    finally:
        _delete(admin_api, base_url, f"/hub/api/users/{user}/server")
        _delete(admin_api, base_url, f"/hub/api/users/{user}")
        _wait(lambda: not _server_state(admin_api, base_url, user))


@pytest.mark.acc_crit("duoptimumhub::Slider default = stable +4h")
def test_extend_slider_defaults_to_plus_4h(admin_portal, admin_api, base_url):
    me = admin_api.get(f"{base_url}/hub/api/user", timeout=30).json()["name"]
    _post(admin_api, base_url, f"/hub/api/users/{me}/server")
    assert _wait(lambda: _server_state(admin_api, base_url, me).get("", {}).get("ready")), \
        "own server never became ready"
    try:
        page = admin_portal.goto("/home")
        extend = page.get_by_role("button", name="Extend", exact=True)
        expect(extend).to_be_visible()
        extend.click()
        # popover apply button reflects the slider's default value - a stable +4h, not "max"
        expect(page.get_by_role("button", name="Extend +4h", exact=True)).to_be_visible()
    finally:
        _delete(admin_api, base_url, f"/hub/api/users/{me}/server")
        _wait(lambda: not _server_state(admin_api, base_url, me))


@pytest.mark.acc_crit(
    "duoptimumhub::Boost bar glow + fill brightness",
    "duoptimumhub::Boost counter blur + clock glow",
    "duoptimumhub::Boost counter shows absolute time + disabled trigger",
    "duoptimumhub::Boosted gadget recolours to accent (glow on the same hue)",
)
def test_extend_boost_motion(admin_portal, admin_api, base_url):
    """The extend boost is a pure-CSS flourish (no JS animation loop), CONTAINED inside the
    track so it never bleeds onto the controls (DEF-29): the FILL runs `doh-ttl-fill-boost`
    (brightness/saturation lift on the accent hue + an inner inset bloom), a bright sheen sweeps
    the whole track once (`doh-ttl-sweep` on `.doh-ttl-track::after`), the counter number blurs
    (`doh-ttl-boost-num`), the clock glyph glows (`doh-ttl-clock-boost` -> `doh-ttl-boost-clock`),
    the readout shows the absolute remaining time (never a static +delta), and the trigger is
    disabled (label stays "Extend"). The whole gadget recolours to the accent hue while boosting. Animation-name is
    stable while the boost class is on, so the checks are race-free."""
    me = admin_api.get(f"{base_url}/hub/api/user", timeout=30).json()["name"]
    _post(admin_api, base_url, f"/hub/api/users/{me}/server")
    assert _wait(lambda: _server_state(admin_api, base_url, me).get("", {}).get("ready")), \
        "own server never became ready"
    try:
        page = admin_portal.goto("/home")
        page.get_by_role("button", name="Extend", exact=True).click()
        page.get_by_role("button", name="Extend +4h", exact=True).click()
        # the boost holds for the fill window; the bar carries the boost class, the FILL runs the motion
        bar = page.locator(".doh-ttl-bar").first
        expect(bar).to_have_class(re.compile(r"doh-ttl-boost"))
        # the fill lifts brightness/saturation on the accent hue + an inner inset bloom (fill-boost)
        fill = bar.locator(".doh-ttl-fill").first
        assert "doh-ttl-fill-boost" in fill.evaluate("el => getComputedStyle(el).animationName"), "fill must run the fill-boost brightness lift + inner bloom"
        # a bright sheen sweeps the WHOLE track once (doh-ttl-sweep on the track ::after), CLIPPED by the
        # track overflow:hidden so the bar glows as a whole yet never bleeds onto the controls (DEF-29)
        track = bar.locator(".doh-ttl-track").first
        assert "doh-ttl-sweep" in track.evaluate("el => getComputedStyle(el, '::after').animationName"), "track ::after must run the clipped sheen sweep"
        assert track.evaluate("el => getComputedStyle(el).overflow").startswith(("hidden", "clip")), "track must clip (overflow:hidden) so the glow is contained, never a bleeding wrapper box-shadow"
        fill_bg, accent_rgb = bar.evaluate(
            "el => {"
            " const f = el.querySelector('.doh-ttl-fill');"
            " const probe = document.createElement('span');"
            " probe.style.color = 'var(--color-accent)';"
            " document.body.appendChild(probe);"
            " const a = getComputedStyle(probe).color;"
            " probe.remove();"
            " return [f ? getComputedStyle(f).backgroundColor : '', a];"
            "}"
        )
        assert fill_bg and fill_bg == accent_rgb, \
            f"boosted fill must be the accent hue (glow = brightness on that hue): fill={fill_bg!r} accent={accent_rgb!r}"
        # the counter number blurs (boost-num)
        num = page.locator(".doh-ttl-val.doh-ttl-boost b").first
        assert "doh-ttl-boost-num" in num.evaluate("el => getComputedStyle(el).animationName"), "counter must run the blur boost"
        # the readout is the absolute remaining duration (design "Label" spec), blurred but
        # never a static "+delta" - so it matches a duration and carries no leading '+'
        txt = num.inner_text()
        assert re.search(r"\d+\s*[hm]", txt), f"counter must show an absolute duration, got {txt!r}"
        assert "+" not in txt, f"counter must NOT show a +delta, got {txt!r}"
        # the clock glyph glows during the boost
        clock = page.locator(".doh-ttl-clock-boost").first
        assert "doh-ttl-boost-clock" in clock.evaluate("el => getComputedStyle(el).animationName"), "clock must run the boost glow"
        # the trigger is disabled during the in-flight extend (label stays "Extend")
        expect(page.get_by_role("button", name="Extend", exact=True)).to_be_disabled()
    finally:
        _delete(admin_api, base_url, f"/hub/api/users/{me}/server")
        _wait(lambda: not _server_state(admin_api, base_url, me))


@pytest.mark.acc_crit(
    "duoptimumhub::Stopped-ago text",
    "duoptimumhub::Running unchanged",
)
def test_stopped_server_shows_stopped_ago_readout(admin_portal, admin_api, base_url):
    """A stopped server shows plain "stopped Xh ago" / "never started" text in the TTL
    slot, never a live idle-timer bar. Starts then stops the admin's own server so the
    Server Control hero renders the stopped state."""
    me = admin_api.get(f"{base_url}/hub/api/user", timeout=30).json()["name"]
    # ensure stopped (clean state) - the readout replaces the bar only when not running.
    # default ready=False so a fully-removed server entry ({}) reads as stopped, not running.
    _delete(admin_api, base_url, f"/hub/api/users/{me}/server")
    assert _wait(lambda: not _server_state(admin_api, base_url, me).get("", {}).get("ready", False)), \
        "own server never stopped"
    page = admin_portal.goto("/home")
    # the Server Control card shows Start Server (stopped) and no live TTL bar
    expect(page.get_by_role("button", name="Start Server", exact=True)).to_be_visible()
    expect(page.locator(".doh-ttl-bar")).to_have_count(0)
    # the TTL slot reads "stopped ... ago" or "never started", never a bar
    expect(page.get_by_text(re.compile(r"(stopped .+ ago|never started)"))).to_be_visible()


@pytest.mark.acc_crit(
    "duoptimumhub::Stopped sub-minute reads 'a moment ago' (DEF-16)",
)
def test_stopped_server_reads_a_moment_ago(admin_portal, admin_api, base_url):
    """DEF-16: a server stopped within the last minute reads "stopped a moment ago",
    never the ungrammatical "stopped now ago". Start then immediately stop the admin's
    own server so the last activity is sub-minute, then assert the Server Control
    readout. The "now ago" guard is timing-independent (it must never render)."""
    me = admin_api.get(f"{base_url}/hub/api/user", timeout=30).json()["name"]
    # fresh recent activity: start -> ready -> stop, so lastActivity is sub-minute
    _post(admin_api, base_url, f"/hub/api/users/{me}/server")
    assert _wait(lambda: _server_state(admin_api, base_url, me).get("", {}).get("ready")), \
        "own server never became ready"
    _delete(admin_api, base_url, f"/hub/api/users/{me}/server")
    assert _wait(lambda: not _server_state(admin_api, base_url, me).get("", {}).get("ready", False)), \
        "own server never stopped"
    page = admin_portal.goto("/home")
    # the DEF-16 fix: sub-minute reads "a moment ago", and "now ago" never renders
    expect(page.get_by_text("stopped a moment ago", exact=False)).to_be_visible()
    expect(page.get_by_text(re.compile(r"now ago"))).to_have_count(0)
