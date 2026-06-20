"""Functional tests for ActivityMonitor - recording, scoring, user management, config."""

import math
import os
from datetime import datetime, timedelta, timezone

import pytest

from duoptimum_hub_services.activity.monitor import ActivityMonitor


def _seed_window(monitor, username, active_every):
    """Fill EVERY slot of a full retention window at sample_interval spacing, marking
    a slot active when its index % active_every == 0. Represents an ESTABLISHED user
    whose window is already fully sampled (the sampler records every user every
    interval). Uniform interleave spreads active slots across the decay curve, so the
    decay-weighted active fraction is ~= 1/active_every: 1 -> all active (24h/day),
    2 -> ~12h, 3 -> ~8h, 6 -> ~4h."""
    from duoptimum_hub_services.activity.model import ActivitySample
    now = datetime.now(timezone.utc)
    dt = timedelta(seconds=monitor.sample_interval)
    n_slots = int(round(monitor.retention_days * 24 * 3600 / monitor.sample_interval))
    rows = []
    for k in range(n_slots):
        active = (k % active_every == 0)
        ts = now - k * dt
        rows.append(ActivitySample(
            username=username, timestamp=ts,
            last_activity=(ts if active else ts - timedelta(hours=3)), active=active))
    monitor._db_session.add_all(rows)
    monitor._db_session.commit()


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

class TestRecording:
    def test_active_sample(self, memory_db_monitor):
        """Recent last_activity marks sample as active."""
        now = datetime.now(timezone.utc)
        assert memory_db_monitor.record_sample("alice", now - timedelta(seconds=10))

        from duoptimum_hub_services.activity.model import ActivitySample
        row = memory_db_monitor._db_session.query(ActivitySample).one()
        assert row.username == "alice"
        assert row.active is True

    def test_inactive_sample(self, memory_db_monitor):
        """Stale last_activity marks sample as inactive."""
        stale = datetime.now(timezone.utc) - timedelta(hours=3)
        memory_db_monitor.record_sample("bob", stale)

        from duoptimum_hub_services.activity.model import ActivitySample
        row = memory_db_monitor._db_session.query(ActivitySample).one()
        assert row.active is False

    def test_none_last_activity(self, memory_db_monitor):
        """None last_activity marks sample as inactive."""
        memory_db_monitor.record_sample("carol", None)

        from duoptimum_hub_services.activity.model import ActivitySample
        row = memory_db_monitor._db_session.query(ActivitySample).one()
        assert row.active is False

    def test_multiple_samples_accumulate(self, memory_db_monitor):
        """Multiple record_sample calls create separate rows."""
        now = datetime.now(timezone.utc)
        memory_db_monitor.record_sample("dave", now)
        memory_db_monitor.record_sample("dave", now)
        memory_db_monitor.record_sample("dave", now)

        from duoptimum_hub_services.activity.model import ActivitySample
        count = memory_db_monitor._db_session.query(ActivitySample).filter_by(username="dave").count()
        assert count == 3

    def test_old_samples_pruned_on_record(self, memory_db_monitor):
        """Recording prunes samples older than retention_days for that user."""
        from duoptimum_hub_services.activity.model import ActivitySample

        old_ts = datetime.now(timezone.utc) - timedelta(days=memory_db_monitor.retention_days + 1)
        memory_db_monitor._db_session.add(ActivitySample(
            username="eve", timestamp=old_ts, last_activity=old_ts, active=True,
        ))
        memory_db_monitor._db_session.commit()

        now = datetime.now(timezone.utc)
        memory_db_monitor.record_sample("eve", now)

        count = memory_db_monitor._db_session.query(ActivitySample).filter_by(username="eve").count()
        assert count == 1  # old sample pruned, only new one remains


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

class TestScoring:
    def test_no_samples_returns_none(self, memory_db_monitor):
        """No samples -> (None, 0)."""
        score, count = memory_db_monitor.get_score("nobody")
        assert score is None
        assert count == 0

    def test_all_active_score_100(self, memory_db_monitor):
        """A full window of active samples (active all the time) -> score 100."""
        _seed_window(memory_db_monitor, "alice", active_every=1)
        score, count = memory_db_monitor.get_score("alice")
        assert count > 0
        assert score == 100

    def test_all_inactive_score_0(self, memory_db_monitor):
        """All inactive samples -> score 0."""
        from duoptimum_hub_services.activity.model import ActivitySample

        now = datetime.now(timezone.utc)
        for i in range(5):
            memory_db_monitor._db_session.add(ActivitySample(
                username="bob", timestamp=now - timedelta(minutes=i),
                last_activity=now - timedelta(hours=3), active=False,
            ))
        memory_db_monitor._db_session.commit()

        score, count = memory_db_monitor.get_score("bob")
        assert count == 5
        assert score == 0

    def test_decay_weights_recent_more(self, memory_db_monitor):
        """The same amount of active time scores higher when it is recent."""
        from duoptimum_hub_services.activity.model import ActivitySample

        now = datetime.now(timezone.utc)
        dt = timedelta(seconds=memory_db_monitor.sample_interval)
        # 48 active samples (~8h) placed recently for "fresh", the same 48 placed
        # ~6 days back for "stale" - both within the 7-day window, same active time.
        for k in range(48):
            memory_db_monitor._db_session.add(ActivitySample(
                username="fresh", timestamp=now - k * dt, last_activity=now, active=True))
        for k in range(48):
            old_ts = now - timedelta(days=6) - k * dt
            memory_db_monitor._db_session.add(ActivitySample(
                username="stale", timestamp=old_ts, last_activity=old_ts, active=True))
        memory_db_monitor._db_session.commit()

        fresh_score, _ = memory_db_monitor.get_score("fresh")
        stale_score, _ = memory_db_monitor.get_score("stale")
        assert fresh_score > stale_score  # recent active time dominates due to decay


# ---------------------------------------------------------------------------
# Target-hours normalisation (the under-reporting fix)
# ---------------------------------------------------------------------------

class TestTargetNormalisation:
    def test_target_hours_default(self, reset_activity_monitor):
        """target_hours defaults to 8 (daily hours that count as 100%)."""
        monitor = ActivityMonitor.get_instance()
        assert monitor.target_hours == ActivityMonitor.DEFAULT_TARGET_HOURS == 8

    def test_target_hours_env(self, reset_activity_monitor, monkeypatch):
        monkeypatch.setenv("JUPYTERHUB_ACTIVITYMON_TARGET_HOURS", "6")
        assert ActivityMonitor.get_instance().target_hours == 6

    def test_eight_hours_a_day_scores_100_not_33(self, memory_db_monitor):
        """The fix: a user active 8/24 of the time scores 100, not 33%.

        Pre-fix the score was the raw active fraction (8/24 = 33%); now it is the
        active hours measured against the 8h target, so a full-time user reads 100."""
        _seed_window(memory_db_monitor, "natalia", active_every=3)  # ~1/3 -> 8h/day
        score, _ = memory_db_monitor.get_score("natalia")
        assert score == 100

    def test_half_target_scores_about_50(self, memory_db_monitor):
        """~4h/day (half the 8h target) scores ~50."""
        _seed_window(memory_db_monitor, "halfday", active_every=6)  # ~1/6 -> 4h/day
        score, _ = memory_db_monitor.get_score("halfday")
        assert 45 <= score <= 55

    def test_avg_active_hours_is_real_and_uncapped(self, memory_db_monitor):
        """get_avg_active_hours returns the real hours/day, uncapped above target."""
        # ~1/2 of a full window active -> ~12h/day; score caps at 100 but hours stays 12
        _seed_window(memory_db_monitor, "heavy", active_every=2)
        hours = memory_db_monitor.get_avg_active_hours("heavy")
        score, _ = memory_db_monitor.get_score("heavy")
        assert 11.0 <= hours <= 13.0
        assert score == 100  # capped

    def test_avg_active_hours_none_without_samples(self, memory_db_monitor):
        assert memory_db_monitor.get_avg_active_hours("ghost") is None


# ---------------------------------------------------------------------------
# New-user ramp (DEF-6): active fraction measured against a FULL window, so a
# brand-new mostly-active account ramps from zero instead of spiking to ~300%.
# ---------------------------------------------------------------------------

class TestNewUserRamp:
    def _add_active(self, monitor, username, n):
        """n recent active samples on a brand-new account (rest of window empty)."""
        from duoptimum_hub_services.activity.model import ActivitySample
        now = datetime.now(timezone.utc)
        dt = timedelta(seconds=monitor.sample_interval)
        monitor._db_session.add_all([
            ActivitySample(username=username, timestamp=now - k * dt,
                           last_activity=now, active=True) for k in range(n)])
        monitor._db_session.commit()

    def test_new_active_user_does_not_spike(self, memory_db_monitor):
        """~1h of solid activity on a new account reads low, not the old 100/300%."""
        self._add_active(memory_db_monitor, "newbie", 6)
        score, count = memory_db_monitor.get_score("newbie")
        hours = memory_db_monitor.get_avg_active_hours("newbie")
        assert count == 6
        assert score < 10                       # not the old ~100 spike
        assert hours is not None and hours < 2.0  # not the old 24h (300% of 8h target)

    def test_ramp_grows_as_active_time_accumulates(self, memory_db_monitor):
        """More accumulated active time -> higher score (progressive ramp)."""
        self._add_active(memory_db_monitor, "early", 6)
        self._add_active(memory_db_monitor, "later", 60)
        early, _ = memory_db_monitor.get_score("early")
        later, _ = memory_db_monitor.get_score("later")
        assert later > early

    def test_avg_active_hours_never_exceeds_24(self, memory_db_monitor):
        """Active fraction caps at 1.0 - hours can never exceed 24 (sampler jitter)."""
        from duoptimum_hub_services.activity.model import ActivitySample
        now = datetime.now(timezone.utc)
        n_slots = int(round(
            memory_db_monitor.retention_days * 24 * 3600 / memory_db_monitor.sample_interval))
        memory_db_monitor._db_session.add_all([
            ActivitySample(username="jitter", timestamp=now, last_activity=now, active=True)
            for _ in range(n_slots + 200)])  # more active samples than expected slots
        memory_db_monitor._db_session.commit()
        assert memory_db_monitor.get_avg_active_hours("jitter") == 24.0


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

class TestUserManagement:
    def test_rename_user_transfers_samples(self, memory_db_monitor):
        now = datetime.now(timezone.utc)
        memory_db_monitor.record_sample("old_name", now)

        assert memory_db_monitor.rename_user("old_name", "new_name")

        _, old_count = memory_db_monitor.get_score("old_name")
        _, new_count = memory_db_monitor.get_score("new_name")
        assert old_count == 0
        assert new_count == 1

    def test_delete_user_removes_samples(self, memory_db_monitor):
        now = datetime.now(timezone.utc)
        memory_db_monitor.record_sample("doomed", now)

        assert memory_db_monitor.delete_user("doomed")

        _, count = memory_db_monitor.get_score("doomed")
        assert count == 0

    def test_prune_old_samples(self, memory_db_monitor):
        """prune_old_samples removes expired samples for all users."""
        from duoptimum_hub_services.activity.model import ActivitySample

        old_ts = datetime.now(timezone.utc) - timedelta(days=memory_db_monitor.retention_days + 1)
        memory_db_monitor._db_session.add(ActivitySample(
            username="stale", timestamp=old_ts, last_activity=old_ts, active=True,
        ))
        memory_db_monitor._db_session.commit()

        pruned = memory_db_monitor.prune_old_samples()
        assert pruned == 1

    def test_reset_all_clears_everything(self, memory_db_monitor):
        now = datetime.now(timezone.utc)
        memory_db_monitor.record_sample("user1", now)
        memory_db_monitor.record_sample("user2", now)

        deleted = memory_db_monitor.reset_all()
        assert deleted == 2

        from duoptimum_hub_services.activity.model import ActivitySample
        assert memory_db_monitor._db_session.query(ActivitySample).count() == 0


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:
    def test_default_values(self, reset_activity_monitor):
        """Without env vars, defaults apply."""
        monitor = ActivityMonitor.get_instance()
        assert monitor.retention_days == ActivityMonitor.DEFAULT_RETENTION_DAYS
        assert monitor.half_life_hours == ActivityMonitor.DEFAULT_HALF_LIFE
        assert monitor.inactive_after_minutes == ActivityMonitor.DEFAULT_INACTIVE_AFTER
        assert monitor.sample_interval == ActivityMonitor.DEFAULT_ACTIVITY_UPDATE_INTERVAL

    def test_custom_env_values(self, reset_activity_monitor, monkeypatch):
        """Custom env values are respected."""
        monkeypatch.setenv("JUPYTERHUB_ACTIVITYMON_RETENTION_DAYS", "14")
        monkeypatch.setenv("JUPYTERHUB_ACTIVITYMON_HALF_LIFE", "48")
        monkeypatch.setenv("JUPYTERHUB_ACTIVITYMON_INACTIVE_AFTER", "30")
        monkeypatch.setenv("JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL", "120")

        monitor = ActivityMonitor.get_instance()
        assert monitor.retention_days == 14
        assert monitor.half_life_hours == 48
        assert monitor.inactive_after_minutes == 30
        assert monitor.sample_interval == 120

    def test_out_of_range_falls_back(self, reset_activity_monitor, monkeypatch):
        """Out-of-range values fall back to defaults."""
        monkeypatch.setenv("JUPYTERHUB_ACTIVITYMON_RETENTION_DAYS", "999")

        monitor = ActivityMonitor.get_instance()
        assert monitor.retention_days == ActivityMonitor.DEFAULT_RETENTION_DAYS

    def test_decay_lambda_matches_half_life(self, reset_activity_monitor):
        """decay_lambda = ln(2) / half_life_hours."""
        monitor = ActivityMonitor.get_instance()
        expected = math.log(2) / monitor.half_life_hours
        assert abs(monitor.decay_lambda - expected) < 1e-10
