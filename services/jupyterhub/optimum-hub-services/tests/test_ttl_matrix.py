"""TTL progress-bar + extension behaviour matrix (idle_culler pure math).

These are the source-of-truth functions the front-end TtlGadget mirrors: the
bar fills against the BASE timeout (not the ceiling), banked time pins at 100%,
the extend offer is the gap up to the ceiling, and "max means max" lands exactly
on the ceiling.
"""

import pytest

from optimum_hub_services.idle_culler import (
    calc_ceiling,
    calc_remaining,
    calc_available_hours,
    calc_progress_pct,
    calc_extended_remaining,
    should_cull,
)

H = 3600
BASE = 24 * H            # 24h base timeout
MAXEXT = 24             # up to +24h
CEIL = BASE + MAXEXT * H  # ceiling = base + max extension


# ---- progress bar: base-relative, caps at 100, floors at 0 ---------------

@pytest.mark.parametrize("remaining, base, expected", [
    (BASE, BASE, 100.0),        # full / fresh -> 100%
    (BASE // 2, BASE, 50.0),    # half drained -> 50%
    (0, BASE, 0.0),             # culled -> 0%
    (BASE * 2, BASE, 100.0),    # extended above base -> pinned at 100%
    (-10, BASE, 0.0),           # past deadline -> floored at 0
    (BASE, 0, 0.0),             # no base -> 0 (guard)
])
def test_progress_pct_matrix(remaining, base, expected):
    assert calc_progress_pct(remaining, base) == expected


# ---- ceiling --------------------------------------------------------------

def test_ceiling_is_base_plus_max_extension():
    assert calc_ceiling(BASE, MAXEXT) == CEIL
    assert calc_ceiling(BASE, 0) == BASE


# ---- extend offer (available hours = gap up to ceiling, floored) ----------

@pytest.mark.parametrize("remaining, ceiling, expected_hours", [
    (BASE, CEIL, MAXEXT),            # fresh at base -> full 24h offer
    (CEIL, CEIL, 0),                 # already at ceiling -> nothing to add
    (CEIL - 90 * 60, CEIL, 1),       # 90m gap -> floored to 1h
    (CEIL + H, CEIL, 0),             # above ceiling (defensive) -> 0
])
def test_available_hours_matrix(remaining, ceiling, expected_hours):
    assert calc_available_hours(remaining, ceiling) == expected_hours


# ---- applying an extension, capped at ceiling -----------------------------

def test_extend_adds_hours_capped():
    # add 2h to a session 4h from the deadline -> 6h, under the ceiling
    assert calc_extended_remaining(4 * H, 2, CEIL, maxed=False) == 6 * H


def test_extend_caps_at_ceiling():
    # adding more than the headroom never exceeds the ceiling
    assert calc_extended_remaining(CEIL - H, 5, CEIL, maxed=False) == CEIL


def test_extend_maxed_lands_exactly_on_ceiling():
    # "max means max" - taking the full whole-hour offer lands on the ceiling,
    # not up to 59m short from the flooring
    assert calc_extended_remaining(BASE, MAXEXT, CEIL, maxed=True) == CEIL


# ---- remaining: activity floor + ceiling clamp + floor at 0 ---------------

def test_remaining_keeps_active_server_at_base():
    # fresh activity (0s since) -> at least base, even with a passed deadline
    assert calc_remaining(-100, 0, BASE, CEIL) == BASE


def test_remaining_clamped_to_ceiling():
    assert calc_remaining(CEIL * 2, 0, BASE, CEIL) == CEIL


def test_remaining_floored_at_zero():
    # long idle, deadline passed -> 0
    assert calc_remaining(-100, BASE + 100, BASE, CEIL) == 0


# ---- replenish laws: no auto-replenish above base; drains to base then tops up

def test_remaining_extended_not_inflated_by_activity():
    # extended above base (deadline 1.5x base) and freshly active (0s idle):
    # activity floor is only `base`, so remaining stays the extended deadline -
    # activity does NOT replenish above base; the banked time just drains.
    assert calc_remaining(int(1.5 * BASE), 0, BASE, CEIL) == int(1.5 * BASE)


def test_remaining_below_base_active_replenishes_to_base():
    # deadline drained below base but the server is active (0s idle): the activity
    # floor tops remaining back up to exactly base ("max becomes base again"),
    # resuming the normal replenish law once back in the base window.
    assert calc_remaining(BASE // 3, 0, BASE, CEIL) == BASE


# ---- cull decision --------------------------------------------------------

@pytest.mark.parametrize("remaining, age, max_age, culled", [
    (0, 0, 0, True),            # remaining gone -> cull
    (-5, 0, 0, True),           # negative remaining -> cull
    (H, 0, 0, False),           # time left, no max-age -> keep
    (H, 100, 50, True),         # max-age reached -> cull regardless of remaining
    (H, 10, 50, False),         # under max-age -> keep
    (H, None, 50, False),       # unknown age -> not culled by age
])
def test_should_cull_matrix(remaining, age, max_age, culled):
    assert should_cull(remaining, age, max_age) is culled
