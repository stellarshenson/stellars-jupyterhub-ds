"""Scenario-matrix tests for the ceiling-bounded deadline idle-culler.

The pure functions and the `remaining_seconds_for` helper back the home-page
countdown, the extend handler, the admin dashboard, and the in-hub culler, so
these scenarios pin the single source of truth. The matrices exercise the full
lifecycle: fresh -> active -> idle -> extend/replenish -> cull, plus the legacy
`extension_hours_used` migration and the hard ceiling cap.
"""

import types
from datetime import datetime, timedelta, timezone

import pytest

from optimum_hub_services.idle_culler import (
    calc_available_hours,
    calc_ceiling,
    calc_extended_remaining,
    calc_progress_pct,
    calc_remaining,
    remaining_seconds_for,
    should_cull,
)

# Live config: 24h base, 48h max extension, 72h ceiling.
BASE = 86400                      # 24h, seconds
MAX_EXT = 48                      # hours
CEILING = BASE + MAX_EXT * 3600   # 259200s = 72h
H = 3600

NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _ago(seconds):
    return NOW - timedelta(seconds=seconds)


def _spawner(state=None, last_activity=None, started=None):
    """Minimal stand-in for orm_spawner (only the attrs the helper reads)."""
    return types.SimpleNamespace(
        state=state or {},
        last_activity=last_activity,
        started=started,
    )


def _cull_at_iso(seconds_from_now):
    return (NOW + timedelta(seconds=seconds_from_now)).isoformat()


# ── calc_ceiling ────────────────────────────────────────────────────────────

class TestCalcCeiling:
    def test_standard(self):
        assert calc_ceiling(BASE, MAX_EXT) == CEILING

    def test_no_extension_allowed(self):
        assert calc_ceiling(BASE, 0) == BASE


# ── calc_remaining: deadline vs activity floor, clamped to [0, ceiling] ──────

@pytest.mark.parametrize("to_deadline, since_activity, expected", [
    # deadline dominates
    (50 * H, 10 * H, 50 * H),
    # activity floor dominates (recently active, deadline already low)
    (2 * H, 0, BASE),                       # active -> floor base
    (2 * H, 5 * H, 19 * H),                 # idle 5h, floor base-5h beats 2h deadline
    # clamp to ceiling (deadline absurdly far)
    (200 * H, 0, CEILING),
    # floored at zero (past deadline AND idle beyond base)
    (-8 * H, 80 * H, 0),
    (-1, 100 * H, 0),
    # exactly zero
    (0, BASE, 0),
])
def test_calc_remaining_matrix(to_deadline, since_activity, expected):
    assert calc_remaining(to_deadline, since_activity, BASE, CEILING) == expected


# ── calc_available_hours: whole-hour replenish offer (floored) ──────────────

@pytest.mark.parametrize("remaining, expected", [
    (CEILING, 0),                  # at ceiling -> nothing to add
    (CEILING - H, 1),
    (CEILING - 5400, 1),           # 1h30m gap -> 1h (floored)
    (CEILING - 300, 0),            # 5m gap -> 0
    (BASE, MAX_EXT),               # fresh 24h -> 48h headroom
    (0, CEILING // H),             # empty -> full 72h offer
    (CEILING + H, 0),              # never negative
])
def test_calc_available_hours_matrix(remaining, expected):
    assert calc_available_hours(remaining, CEILING) == expected


# ── calc_progress_pct: bar fill on the normal-TTL (base) scale, clamped ─────

@pytest.mark.parametrize("remaining, expected", [
    (BASE, 100.0),                 # fresh/active -> full
    (CEILING, 100.0),              # extended to ceiling (72h) -> clamped full
    (BASE + 1, 100.0),             # just over base -> clamped full
    (BASE // 2, 50.0),             # 12h of a 24h base -> half
    (6 * H, 25.0),                 # 6h -> quarter
    (int(BASE * 0.1), 10.0),       # 10% of base
    (0, 0.0),                      # empty
    (-5, 0.0),                     # defensive: never negative
])
def test_calc_progress_pct_matrix(remaining, expected):
    assert calc_progress_pct(remaining, BASE) == expected


def test_calc_progress_pct_zero_base():
    assert calc_progress_pct(BASE, 0) == 0.0


def test_calc_progress_pct_pinned_full_while_extended():
    # Drains from ceiling (72h) down to base (24h): bar stays pinned at 100%.
    for remaining in range(BASE, CEILING + 1, 6 * H):
        assert calc_progress_pct(remaining, BASE) == 100.0


# ── calc_extended_remaining: add hours, cap at ceiling, "max means max" ─────

@pytest.mark.parametrize("remaining, hours, maxed, expected", [
    (59 * H, 13, True, CEILING),                    # take full offer -> exact ceiling
    (59 * H, 5, False, 64 * H),                     # partial add
    (CEILING - 1800, 0, True, CEILING),             # 30m short, maxed -> exact ceiling (no shortfall)
    (BASE, MAX_EXT, True, CEILING),                 # fresh, full offer -> ceiling
    (BASE, 10, False, BASE + 10 * H),               # fresh, partial
    (0, CEILING // H, True, CEILING),               # empty, full offer -> ceiling
    (CEILING - H, 5, False, CEILING),               # partial overshoots -> capped
])
def test_calc_extended_remaining_matrix(remaining, hours, maxed, expected):
    assert calc_extended_remaining(remaining, hours, CEILING, maxed) == expected

def test_extended_remaining_never_exceeds_ceiling():
    # hard-cap regression: no (remaining, hours) combination banks past the ceiling
    for remaining in range(0, CEILING + 1, 6 * H):
        for hours in range(0, 200, 7):
            assert calc_extended_remaining(remaining, hours, CEILING, False) <= CEILING
            assert calc_extended_remaining(remaining, hours, CEILING, True) == CEILING


# ── should_cull ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("remaining, age, max_age, expected", [
    (0, 1 * H, 0, True),               # out of time
    (-5, 1 * H, 0, True),              # defensive: non-positive
    (1, 100 * H, 72 * H, True),        # alive on time but past max_age
    (100 * H, 10 * H, 72 * H, False),  # within both
    (5 * H, 200 * H, 0, False),        # old but max_age disabled and time remains
    (1, 71 * H, 72 * H, False),        # just under max_age, time remains
])
def test_should_cull_matrix(remaining, age, max_age, expected):
    assert should_cull(remaining, age, max_age) is expected


# ── remaining_seconds_for: full lifecycle matrix over real spawner state ────

@pytest.mark.parametrize("label, state, last_activity, started, expected", [
    # fresh server (no extension state)
    ("fresh-active",        {},               NOW,           _ago(0),        BASE),
    ("fresh-idle-5h",       {},               _ago(5 * H),   _ago(5 * H),    19 * H),
    ("fresh-idle-past",     {},               _ago(30 * H),  _ago(30 * H),   0),
    ("never-active-idle-5h", {},              None,          _ago(5 * H),    19 * H),
    ("no-reference",        {},               None,          None,           BASE),
    # legacy extension_hours_used (derive-on-read, ceiling-capped)
    ("legacy-ext0-idle-5h", {"extension_hours_used": 0},  _ago(5 * H),  _ago(5 * H),  19 * H),
    ("legacy-ext48-active", {"extension_hours_used": 48}, NOW,          _ago(0),      CEILING),
    ("legacy-ext48-idle-10h", {"extension_hours_used": 48}, _ago(10 * H), _ago(50 * H), 62 * H),
    ("legacy-konrad-90-idle-13h", {"extension_hours_used": 90}, _ago(13 * H), _ago(60 * H), 59 * H),
    ("legacy-konrad-capped-at-72h", {"extension_hours_used": 90}, _ago(80 * H), _ago(120 * H), 0),
    # new model: stored cull_at deadline
    ("deadline-idle-10h",   {"cull_at": _cull_at_iso(50 * H)}, _ago(10 * H), _ago(60 * H), 50 * H),
    ("deadline-active-floor", {"cull_at": _cull_at_iso(2 * H)}, NOW,        _ago(0),       BASE),
    ("deadline-past",       {"cull_at": _cull_at_iso(-1 * H)}, _ago(30 * H), _ago(30 * H), 0),
    ("deadline-clamped-ceiling", {"cull_at": _cull_at_iso(500 * H)}, _ago(0), _ago(0),     CEILING),
    ("deadline-garbage-falls-back", {"cull_at": "not-a-date"}, _ago(5 * H), _ago(5 * H),  19 * H),
])
def test_remaining_seconds_for_matrix(label, state, last_activity, started, expected):
    sp = _spawner(state=state, last_activity=last_activity, started=started)
    assert remaining_seconds_for(sp, BASE, CEILING, NOW) == expected


# ── Integration: extend lands exactly, never banks past ceiling ─────────────

def _extend(remaining):
    """Mirror the handler: offer, maxed, new remaining, new cull_at deadline."""
    available = calc_available_hours(remaining, CEILING)
    maxed = available > 0  # taking the full offer
    new_remaining = calc_extended_remaining(remaining, available, CEILING, maxed)
    return available, new_remaining


class TestExtendLifecycle:
    def test_konrad_idle_then_max_extend_hits_ceiling(self):
        sp = _spawner(state={"extension_hours_used": 90}, last_activity=_ago(13 * H), started=_ago(60 * H))
        remaining = remaining_seconds_for(sp, BASE, CEILING, NOW)
        assert remaining == 59 * H            # counts down (was pinned at 72h before)
        available, new_remaining = _extend(remaining)
        assert available == 13
        assert new_remaining == CEILING       # max means max - exactly 72h

    def test_repeated_idle_extend_cycles_never_exceed_ceiling(self):
        # The old model banked effective past the ceiling; the deadline model cannot.
        remaining = BASE
        for _ in range(20):
            _, remaining = _extend(remaining)
            assert remaining <= CEILING
            # simulate 6h of idle before the next refill
            remaining = max(0, remaining - 6 * H)
        # after many cycles, a final max extend still tops out at exactly the ceiling
        _, final = _extend(remaining)
        assert final == CEILING

    def test_at_ceiling_offers_nothing(self):
        sp = _spawner(state={"cull_at": _cull_at_iso(CEILING)}, last_activity=NOW, started=_ago(0))
        remaining = remaining_seconds_for(sp, BASE, CEILING, NOW)
        assert remaining == CEILING
        assert calc_available_hours(remaining, CEILING) == 0


# ── Cull decision wired through the helper ──────────────────────────────────

class TestCullDecision:
    def test_idle_past_ceiling_is_culled(self):
        sp = _spawner(state={"extension_hours_used": 90}, last_activity=_ago(80 * H), started=_ago(120 * H))
        remaining = remaining_seconds_for(sp, BASE, CEILING, NOW)
        assert remaining == 0
        assert should_cull(remaining, 120 * H, 0) is True

    def test_active_extended_server_not_culled(self):
        sp = _spawner(state={"cull_at": _cull_at_iso(40 * H)}, last_activity=NOW, started=_ago(2 * H))
        remaining = remaining_seconds_for(sp, BASE, CEILING, NOW)
        assert remaining == 40 * H
        assert should_cull(remaining, 2 * H, 72 * H) is False

    def test_max_age_forces_cull_even_with_time_left(self):
        sp = _spawner(state={"cull_at": _cull_at_iso(40 * H)}, last_activity=NOW, started=_ago(100 * H))
        remaining = remaining_seconds_for(sp, BASE, CEILING, NOW)
        assert should_cull(remaining, 100 * H, 72 * H) is True
