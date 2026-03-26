"""Tests for session extension calculation logic."""

from stellars_hub.handlers.session import (
    calc_available_hours,
    calc_ceiling,
    calc_effective_timeout,
    calc_new_extensions,
    calc_time_remaining,
)

# Constants matching typical config: 24h base, 48h max extension, 72h ceiling
BASE = 86400       # 24h
MAX_EXT = 48       # hours
CEILING = BASE + MAX_EXT * 3600  # 259200s = 72h


class TestCalcEffectiveTimeout:
    def test_no_extensions(self):
        assert calc_effective_timeout(BASE, 0) == BASE

    def test_with_extensions(self):
        assert calc_effective_timeout(BASE, 10) == BASE + 36000

    def test_full_extensions(self):
        assert calc_effective_timeout(BASE, MAX_EXT) == CEILING


class TestCalcCeiling:
    def test_standard(self):
        assert calc_ceiling(BASE, MAX_EXT) == CEILING

    def test_no_extensions_allowed(self):
        assert calc_ceiling(BASE, 0) == BASE


class TestCalcTimeRemaining:
    def test_no_elapsed(self):
        assert calc_time_remaining(CEILING, 0) == CEILING

    def test_partial_elapsed(self):
        assert calc_time_remaining(CEILING, 3600) == CEILING - 3600

    def test_fully_elapsed(self):
        assert calc_time_remaining(CEILING, CEILING + 1000) == 0

    def test_never_negative(self):
        assert calc_time_remaining(BASE, BASE * 2) == 0


class TestCalcAvailableHours:
    def test_at_ceiling(self):
        """No hours available when remaining equals ceiling."""
        assert calc_available_hours(CEILING, CEILING) == 0

    def test_fresh_server_no_extensions(self):
        """Fresh 24h server: 72h ceiling - 24h remaining = 48h available."""
        assert calc_available_hours(CEILING, BASE) == MAX_EXT

    def test_one_hour_elapsed(self):
        """After 1h elapsed from ceiling: 1h available."""
        remaining = CEILING - 3600
        assert calc_available_hours(CEILING, remaining) == 1

    def test_five_minutes_elapsed(self):
        """After 5min elapsed: 0h available (whole hours only)."""
        remaining = CEILING - 300
        assert calc_available_hours(CEILING, remaining) == 0

    def test_partial_hour(self):
        """1h30m elapsed: only 1h available (floor)."""
        remaining = CEILING - 5400
        assert calc_available_hours(CEILING, remaining) == 1

    def test_ten_hours_elapsed(self):
        """10h elapsed from ceiling: 10h available."""
        remaining = CEILING - 36000
        assert calc_available_hours(CEILING, remaining) == 10

    def test_remaining_zero(self):
        """Server expired: full max available."""
        assert calc_available_hours(CEILING, 0) == int(CEILING / 3600)

    def test_remaining_exceeds_ceiling(self):
        """Edge case: remaining somehow above ceiling."""
        assert calc_available_hours(CEILING, CEILING + 3600) == 0


class TestCalcNewExtensions:
    def test_max_extend_snaps_to_max(self):
        """Extending by full available snaps to max_extension_hours."""
        assert calc_new_extensions(0, 48, 48, MAX_EXT) == MAX_EXT

    def test_partial_extend_adds_hours(self):
        """Partial extension adds to current."""
        assert calc_new_extensions(10, 5, 38, MAX_EXT) == 15

    def test_max_extend_after_prior_extensions(self):
        """Max extend with prior extensions still snaps to max."""
        assert calc_new_extensions(40, 8, 8, MAX_EXT) == MAX_EXT

    def test_truncated_to_available_snaps(self):
        """When hours >= available (truncated), snaps to max."""
        assert calc_new_extensions(45, 3, 3, MAX_EXT) == MAX_EXT

    def test_single_hour(self):
        """Extending by 1h out of many available."""
        assert calc_new_extensions(0, 1, 48, MAX_EXT) == 1


class TestExtensionScenarios:
    """End-to-end scenarios combining all functions."""

    def test_fresh_server_full_extend(self):
        """Fresh server, extend to max: remaining = ceiling - 0 elapsed."""
        used = 0
        elapsed = 0
        effective = calc_effective_timeout(BASE, used)
        remaining = calc_time_remaining(effective, elapsed)
        ceiling = calc_ceiling(BASE, MAX_EXT)
        available = calc_available_hours(ceiling, remaining)

        assert remaining == BASE  # 24h
        assert available == MAX_EXT  # 48h

        new_ext = calc_new_extensions(used, available, available, MAX_EXT)
        assert new_ext == MAX_EXT

        new_effective = calc_effective_timeout(BASE, new_ext)
        new_remaining = calc_time_remaining(new_effective, elapsed)
        assert new_remaining == CEILING  # 72h

    def test_ten_hours_elapsed_extend_back(self):
        """Already at ceiling, 10h pass, extend by 10h back to ceiling."""
        used = MAX_EXT
        elapsed = 10 * 3600
        effective = calc_effective_timeout(BASE, used)
        remaining = calc_time_remaining(effective, elapsed)
        ceiling = calc_ceiling(BASE, MAX_EXT)
        available = calc_available_hours(ceiling, remaining)

        assert remaining == CEILING - elapsed  # 62h
        assert available == 10

        new_ext = calc_new_extensions(used, available, available, MAX_EXT)
        # Snaps to max since hours >= available
        assert new_ext == MAX_EXT

        new_effective = calc_effective_timeout(BASE, new_ext)
        new_remaining = calc_time_remaining(new_effective, elapsed)
        # Back to ceiling - elapsed = 72h - 10h = 62h
        # (same as before because extensions_used was already at max)
        assert new_remaining == CEILING - elapsed

    def test_partial_extend_then_time_passes(self):
        """Extend by 5h, then 5h passes, extend by 5h more."""
        # Step 1: fresh server, extend by 5h
        used = 0
        elapsed = 0
        ceiling = calc_ceiling(BASE, MAX_EXT)

        new_ext = calc_new_extensions(used, 5, 48, MAX_EXT)
        assert new_ext == 5

        # Step 2: 5h passes
        elapsed = 5 * 3600
        effective = calc_effective_timeout(BASE, new_ext)
        remaining = calc_time_remaining(effective, elapsed)
        available = calc_available_hours(ceiling, remaining)

        assert remaining == (BASE + 5 * 3600) - elapsed  # 24h
        assert available == MAX_EXT  # 72h - 24h = 48h

        # Step 3: extend by 5h more
        new_ext2 = calc_new_extensions(new_ext, 5, available, MAX_EXT)
        assert new_ext2 == 10

    def test_no_extension_allowed(self):
        """Max extension = 0: never available."""
        ceiling = calc_ceiling(BASE, 0)
        remaining = calc_time_remaining(BASE, 0)
        available = calc_available_hours(ceiling, remaining)
        assert available == 0

    def test_whole_hours_only(self):
        """Available hours are always whole - no fractional extensions."""
        ceiling = calc_ceiling(BASE, MAX_EXT)
        # 30 minutes elapsed from ceiling
        remaining = CEILING - 1800
        available = calc_available_hours(ceiling, remaining)
        assert available == 0  # not enough for 1 full hour
