"""Functional tests for ActivityMonitor - recording, scoring, user management, config."""

import math
import os
from datetime import datetime, timedelta, timezone

import pytest

from stellars_hub.activity.monitor import ActivityMonitor


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

class TestRecording:
    def test_active_sample(self, memory_db_monitor):
        """Recent last_activity marks sample as active."""
        now = datetime.now(timezone.utc)
        assert memory_db_monitor.record_sample("alice", now - timedelta(seconds=10))

        from stellars_hub.activity.model import ActivitySample
        row = memory_db_monitor._db_session.query(ActivitySample).one()
        assert row.username == "alice"
        assert row.active is True

    def test_inactive_sample(self, memory_db_monitor):
        """Stale last_activity marks sample as inactive."""
        stale = datetime.now(timezone.utc) - timedelta(hours=3)
        memory_db_monitor.record_sample("bob", stale)

        from stellars_hub.activity.model import ActivitySample
        row = memory_db_monitor._db_session.query(ActivitySample).one()
        assert row.active is False

    def test_none_last_activity(self, memory_db_monitor):
        """None last_activity marks sample as inactive."""
        memory_db_monitor.record_sample("carol", None)

        from stellars_hub.activity.model import ActivitySample
        row = memory_db_monitor._db_session.query(ActivitySample).one()
        assert row.active is False

    def test_multiple_samples_accumulate(self, memory_db_monitor):
        """Multiple record_sample calls create separate rows."""
        now = datetime.now(timezone.utc)
        memory_db_monitor.record_sample("dave", now)
        memory_db_monitor.record_sample("dave", now)
        memory_db_monitor.record_sample("dave", now)

        from stellars_hub.activity.model import ActivitySample
        count = memory_db_monitor._db_session.query(ActivitySample).filter_by(username="dave").count()
        assert count == 3

    def test_old_samples_pruned_on_record(self, memory_db_monitor):
        """Recording prunes samples older than retention_days for that user."""
        from stellars_hub.activity.model import ActivitySample

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
        """All recent active samples -> score near 100."""
        from stellars_hub.activity.model import ActivitySample

        now = datetime.now(timezone.utc)
        for i in range(5):
            memory_db_monitor._db_session.add(ActivitySample(
                username="alice", timestamp=now - timedelta(minutes=i),
                last_activity=now, active=True,
            ))
        memory_db_monitor._db_session.commit()

        score, count = memory_db_monitor.get_score("alice")
        assert count == 5
        assert score == 100

    def test_all_inactive_score_0(self, memory_db_monitor):
        """All inactive samples -> score 0."""
        from stellars_hub.activity.model import ActivitySample

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
        """Recent active + old inactive -> score between 0 and 100, biased high."""
        from stellars_hub.activity.model import ActivitySample

        now = datetime.now(timezone.utc)
        # Recent sample: active
        memory_db_monitor._db_session.add(ActivitySample(
            username="carol", timestamp=now, last_activity=now, active=True,
        ))
        # Old sample: inactive (but within retention)
        memory_db_monitor._db_session.add(ActivitySample(
            username="carol", timestamp=now - timedelta(days=3),
            last_activity=now - timedelta(days=4), active=False,
        ))
        memory_db_monitor._db_session.commit()

        score, count = memory_db_monitor.get_score("carol")
        assert count == 2
        assert 50 < score <= 100  # recent active sample dominates due to decay


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
        from stellars_hub.activity.model import ActivitySample

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

        from stellars_hub.activity.model import ActivitySample
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
