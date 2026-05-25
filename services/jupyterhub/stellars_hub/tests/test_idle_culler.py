"""Scenario tests for the idle-culler submodule.

Covers the session-extension math (effective budget, ceiling-clamped remaining,
replenish offer, extend application) and the cull decision (`should_cull`),
including end-to-end timelines. The same pure functions back the home-page
countdown, the extend handler, the admin dashboard, and the in-hub culler, so
these scenarios pin the single source of truth.
"""

from datetime import datetime, timedelta, timezone

from stellars_hub.idle_culler import (
    calc_available_hours,
    calc_ceiling,
    calc_effective_timeout,
    calc_new_extensions,
    calc_time_remaining,
    should_cull,
)

# Typical config: 24h base, 48h max extension, 72h ceiling
BASE = 86400          # 24h, seconds
MAX_EXT = 48          # hours
CEILING = BASE + MAX_EXT * 3600   # 259200s = 72h
H = 3600              # one hour in seconds

NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _ago(seconds):
    return NOW - timedelta(seconds=seconds)


class TestCalcEffectiveTimeout:
    def test_no_extensions(self):
        assert calc_effective_timeout(BASE, 0) == BASE

    def test_with_extensions(self):
        assert calc_effective_timeout(BASE, 10) == BASE + 10 * H

    def test_full_extensions(self):
        assert calc_effective_timeout(BASE, MAX_EXT) == CEILING

    def test_beyond_max_for_replenish(self):
        # extension may exceed max_extension - that is how idle time is replenished
        assert calc_effective_timeout(BASE, 56) == BASE + 56 * H  # 80h, > ceiling


class TestCalcCeiling:
    def test_standard(self):
        assert calc_ceiling(BASE, MAX_EXT) == CEILING

    def test_no_extension_allowed(self):
        assert calc_ceiling(BASE, 0) == BASE


class TestCalcTimeRemaining:
    def test_no_elapsed_unclamped(self):
        assert calc_time_remaining(CEILING, 0) == CEILING

    def test_partial_elapsed(self):
        assert calc_time_remaining(CEILING, H) == CEILING - H

    def test_fully_elapsed(self):
        assert calc_time_remaining(CEILING, CEILING + 1000) == 0

    def test_never_negative(self):
        assert calc_time_remaining(BASE, BASE * 2) == 0

    def test_clamped_to_ceiling(self):
        # effective 80h, no elapsed -> clamped to the 72h ceiling
        assert calc_time_remaining(BASE + 56 * H, 0, CEILING) == CEILING

    def test_below_ceiling_not_clamped(self):
        assert calc_time_remaining(CEILING, H, CEILING) == CEILING - H

    def test_no_ceiling_arg_means_no_clamp(self):
        assert calc_time_remaining(BASE + 56 * H, 0) == BASE + 56 * H


class TestCalcAvailableHours:
    def test_at_ceiling(self):
        assert calc_available_hours(CEILING, CEILING) == 0

    def test_fresh_server(self):
        # 72h ceiling - 24h remaining = 48h offer
        assert calc_available_hours(CEILING, BASE) == MAX_EXT

    def test_one_hour(self):
        assert calc_available_hours(CEILING, CEILING - H) == 1

    def test_five_minutes_floors_to_zero(self):
        assert calc_available_hours(CEILING, CEILING - 300) == 0

    def test_partial_hour_floors(self):
        assert calc_available_hours(CEILING, CEILING - 5400) == 1  # 1h30m -> 1h

    def test_idle_8h_offers_replenish_plus_headroom(self):
        remaining = BASE - 8 * H  # 16h
        assert calc_available_hours(CEILING, remaining) == 56  # 48 headroom + 8 idle

    def test_remaining_zero(self):
        assert calc_available_hours(CEILING, 0) == int(CEILING / H)  # 72

    def test_remaining_above_ceiling(self):
        assert calc_available_hours(CEILING, CEILING + H) == 0


class TestCalcNewExtensions:
    def test_single_hour(self):
        assert calc_new_extensions(0, 1) == 1

    def test_partial_adds(self):
        assert calc_new_extensions(10, 5) == 15

    def test_can_exceed_max(self):
        assert calc_new_extensions(0, 56) == 56  # > MAX_EXT, intended for replenish

    def test_accumulates_beyond_max(self):
        assert calc_new_extensions(48, 8) == 56


class TestShouldCull:
    def test_idle_past_effective_culls(self):
        assert should_cull(NOW, _ago(BASE + 10), _ago(BASE + 10), BASE) is True

    def test_within_budget_keeps(self):
        assert should_cull(NOW, _ago(BASE - 10), _ago(BASE - 10), BASE) is False

    def test_extension_pushes_cull_out(self):
        # base 24h + 12h extension = 36h budget; idle 30h -> still alive
        effective = calc_effective_timeout(BASE, 12)
        assert should_cull(NOW, _ago(30 * H), _ago(30 * H), effective) is False

    def test_without_extension_would_cull(self):
        # same 30h idle, no extension (24h budget) -> culled
        assert should_cull(NOW, _ago(30 * H), _ago(30 * H), BASE) is True

    def test_max_age_forces_cull_even_when_active(self):
        # active now, but server is 100h old and max_age is 72h
        assert should_cull(NOW, NOW, _ago(100 * H), BASE, max_age_seconds=72 * H) is True

    def test_max_age_zero_disables_age_check(self):
        assert should_cull(NOW, NOW, _ago(100 * H), BASE, max_age_seconds=0) is False

    def test_last_activity_none_falls_back_to_started(self):
        assert should_cull(NOW, None, _ago(BASE + 10), BASE) is True

    def test_last_activity_none_started_within_budget(self):
        assert should_cull(NOW, None, _ago(BASE - 10), BASE) is False

    def test_no_reference_never_culls(self):
        assert should_cull(NOW, None, None, BASE) is False

    def test_naive_datetime_treated_as_utc(self):
        naive = (NOW - timedelta(seconds=BASE + 10)).replace(tzinfo=None)
        assert should_cull(NOW, naive, naive, BASE) is True


class TestReplenishScenarios:
    """End-to-end extend flows built from the pure functions."""

    def test_fresh_server_full_extend_reaches_ceiling(self):
        used, elapsed = 0, 0
        ceiling = calc_ceiling(BASE, MAX_EXT)
        remaining = calc_time_remaining(calc_effective_timeout(BASE, used), elapsed, ceiling)
        assert remaining == BASE
        available = calc_available_hours(ceiling, remaining)
        assert available == MAX_EXT
        new_used = calc_new_extensions(used, available)
        new_remaining = calc_time_remaining(calc_effective_timeout(BASE, new_used), elapsed, ceiling)
        assert new_remaining == CEILING

    def test_idle_8h_replenish_to_ceiling(self):
        used, elapsed = 0, 8 * H
        ceiling = calc_ceiling(BASE, MAX_EXT)
        remaining = calc_time_remaining(calc_effective_timeout(BASE, used), elapsed, ceiling)
        assert remaining == 16 * H
        available = calc_available_hours(ceiling, remaining)
        assert available == 56  # the worked example: 48 + 8
        new_used = calc_new_extensions(used, available)
        assert new_used == 56 and new_used > MAX_EXT  # exceeds max - replenished idle
        new_remaining = calc_time_remaining(calc_effective_timeout(BASE, new_used), elapsed, ceiling)
        assert new_remaining == CEILING  # full 72h restored

    def test_partial_extend_adds_exactly_chosen_hours(self):
        used, elapsed = 0, 8 * H
        ceiling = calc_ceiling(BASE, MAX_EXT)
        remaining = calc_time_remaining(calc_effective_timeout(BASE, used), elapsed, ceiling)
        new_used = calc_new_extensions(used, 10)  # user opts for 10 of 56 available
        new_remaining = calc_time_remaining(calc_effective_timeout(BASE, new_used), elapsed, ceiling)
        assert new_remaining == remaining + 10 * H  # 16h -> 26h

    def test_offer_is_zero_at_ceiling(self):
        ceiling = calc_ceiling(BASE, MAX_EXT)
        # remaining already at the ceiling
        assert calc_available_hours(ceiling, ceiling) == 0

    def test_activity_reset_clamps_display(self):
        # extended to 80h effective, then activity resets elapsed to 0
        ceiling = calc_ceiling(BASE, MAX_EXT)
        effective = calc_effective_timeout(BASE, 56)  # 80h
        assert calc_time_remaining(effective, 0, ceiling) == CEILING  # shows 72h, not 80h

    def test_repeated_extend_never_shows_more_than_ceiling(self):
        ceiling = calc_ceiling(BASE, MAX_EXT)
        used = 0
        # extend fully on a fresh server
        used = calc_new_extensions(used, calc_available_hours(
            ceiling, calc_time_remaining(calc_effective_timeout(BASE, used), 0, ceiling)))
        for elapsed in (0, 10 * H, 30 * H):
            remaining = calc_time_remaining(calc_effective_timeout(BASE, used), elapsed, ceiling)
            assert remaining <= CEILING
            avail = calc_available_hours(ceiling, remaining)
            used = calc_new_extensions(used, avail)  # top back up each time
            topped = calc_time_remaining(calc_effective_timeout(BASE, used), elapsed, ceiling)
            assert topped <= CEILING


class TestModuleSurface:
    def test_session_handler_reexports_same_objects(self):
        from stellars_hub.handlers import session as s
        from stellars_hub import idle_culler as ic
        for name in (
            "calc_available_hours", "calc_ceiling", "calc_effective_timeout",
            "calc_new_extensions", "calc_time_remaining",
        ):
            assert getattr(s, name) is getattr(ic, name)

    def test_runtime_entrypoints_present(self):
        from stellars_hub import idle_culler as ic
        assert callable(ic.run_cull_pass) and callable(ic.schedule_idle_culler)
