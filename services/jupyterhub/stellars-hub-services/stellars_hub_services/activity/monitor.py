"""ActivityMonitor singleton - database-backed activity scoring."""

import logging
import math
import os
import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from .model import ActivityBase, ActivitySample

log = logging.getLogger('jupyterhub.custom_handlers')


class ActivityMonitor:
    """Central activity monitoring service with database persistence.

    Usage:
        monitor = ActivityMonitor.get_instance()
        monitor.record_sample(username, last_activity)
        score, count = monitor.get_score(username)
        monitor.rename_user(old_name, new_name)
        monitor.delete_user(username)
    """

    _instance = None
    _lock = threading.Lock()

    DEFAULT_RETENTION_DAYS = 7
    DEFAULT_HALF_LIFE = 72
    DEFAULT_INACTIVE_AFTER = 60
    DEFAULT_ACTIVITY_UPDATE_INTERVAL = 600

    def __init__(self):
        self._db_session = None
        self._engine = None
        self._initialized = False

        self.retention_days = self._get_env_int(
            "JUPYTERHUB_ACTIVITYMON_RETENTION_DAYS", self.DEFAULT_RETENTION_DAYS, 1, 365)
        self.half_life_hours = self._get_env_int(
            "JUPYTERHUB_ACTIVITYMON_HALF_LIFE", self.DEFAULT_HALF_LIFE, 1, 168)
        self.inactive_after_minutes = self._get_env_int(
            "JUPYTERHUB_ACTIVITYMON_INACTIVE_AFTER", self.DEFAULT_INACTIVE_AFTER, 1, 1440)
        self.sample_interval = self._get_env_int(
            "JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL", self.DEFAULT_ACTIVITY_UPDATE_INTERVAL, 60, 86400)

        self.decay_lambda = math.log(2) / self.half_life_hours

        log.info(
            f"[ActivityMonitor] Config: retention={self.retention_days}d, "
            f"half_life={self.half_life_hours}h, inactive_after={self.inactive_after_minutes}m, "
            f"sample_interval={self.sample_interval}s"
        )

    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_env_int(self, name, default, min_val, max_val):
        """Get integer from environment with validation."""
        try:
            value = int(os.environ.get(name, default))
            if value < min_val or value > max_val:
                log.info(f"[ActivityMonitor] {name}={value} out of range ({min_val}-{max_val}), using default {default}")
                return default
            return value
        except (ValueError, TypeError):
            log.info(f"[ActivityMonitor] {name} invalid, using default {default}")
            return default

    def _get_db(self):
        """Get or create database session (separate DB to avoid SQLite locking)."""
        if self._db_session is not None:
            return self._db_session

        db_url = 'sqlite:////data/activity_samples.sqlite'
        try:
            self._engine = create_engine(db_url)
            ActivityBase.metadata.create_all(self._engine)
            Session = sessionmaker(bind=self._engine)
            self._db_session = Session()
            self._initialized = True
            log.info(f"[ActivityMonitor] Database initialized: {db_url}")
            return self._db_session
        except Exception as e:
            log.info(f"[ActivityMonitor] Database init failed: {e}")
            return None

    def record_sample(self, username, last_activity):
        """Record an activity sample. Always inserts - caller controls frequency."""
        db = self._get_db()
        if db is None:
            return False

        try:
            now = datetime.now(timezone.utc)
            active = False
            if last_activity:
                last_activity_utc = last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity
                age_seconds = (now - last_activity_utc).total_seconds()
                active = age_seconds <= (self.inactive_after_minutes * 60)

            db.add(ActivitySample(username=username, timestamp=now, last_activity=last_activity, active=active))
            db.commit()

            cutoff = now - timedelta(days=self.retention_days)
            deleted = db.query(ActivitySample).filter(
                ActivitySample.username == username,
                ActivitySample.timestamp < cutoff,
            ).delete()
            if deleted > 0:
                db.commit()

            return True
        except Exception as e:
            log.info(f"[ActivityMonitor] Error recording sample for {username}: {e}")
            db.rollback()
            return False

    def get_score(self, username):
        """Calculate activity score (0-100). Returns (score, sample_count)."""
        db = self._get_db()
        if db is None:
            return None, 0

        try:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(days=self.retention_days)

            samples = db.query(ActivitySample).filter(
                ActivitySample.username == username,
                ActivitySample.timestamp >= cutoff,
            ).all()

            if not samples:
                return None, 0

            weighted_active = 0.0
            weighted_total = 0.0
            for s in samples:
                ts = s.timestamp.replace(tzinfo=timezone.utc) if s.timestamp.tzinfo is None else s.timestamp
                age_hours = (now - ts).total_seconds() / 3600.0
                weight = math.exp(-self.decay_lambda * age_hours)
                weighted_total += weight
                if s.active:
                    weighted_active += weight

            score = int((weighted_active / weighted_total) * 100) if weighted_total > 0 else 0
            return score, len(samples)
        except Exception as e:
            log.info(f"[ActivityMonitor] Error calculating score for {username}: {e}")
            return None, 0

    def get_status(self):
        """Get overall sampling status."""
        db = self._get_db()
        if db is None:
            return "Database not available"

        try:
            result = db.query(
                func.count(ActivitySample.id),
                func.count(func.distinct(ActivitySample.username)),
            ).first()
            total_samples, total_users = result[0] or 0, result[1] or 0
            return f"{total_samples} samples for {total_users} users" if total_samples > 0 else "No samples yet"
        except Exception as e:
            log.info(f"[ActivityMonitor] Error getting status: {e}")
            return "Status unavailable"

    def rename_user(self, old_username, new_username):
        """Rename user in activity records."""
        db = self._get_db()
        if db is None:
            return False

        try:
            count = db.query(ActivitySample).filter(
                ActivitySample.username == old_username
            ).update({'username': new_username})
            db.commit()
            if count > 0:
                log.info(f"[ActivityMonitor] Renamed {count} samples: {old_username} -> {new_username}")
            return True
        except Exception as e:
            log.info(f"[ActivityMonitor] Error renaming user: {e}")
            db.rollback()
            return False

    def delete_user(self, username):
        """Delete all activity records for a user."""
        db = self._get_db()
        if db is None:
            return False

        try:
            count = db.query(ActivitySample).filter(
                ActivitySample.username == username
            ).delete()
            db.commit()
            if count > 0:
                log.info(f"[ActivityMonitor] Deleted {count} samples for {username}")
            return True
        except Exception as e:
            log.info(f"[ActivityMonitor] Error deleting user: {e}")
            db.rollback()
            return False

    def prune_old_samples(self):
        """Remove all samples older than retention period."""
        db = self._get_db()
        if db is None:
            return 0

        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
            count = db.query(ActivitySample).filter(ActivitySample.timestamp < cutoff).delete()
            db.commit()
            if count > 0:
                log.info(f"[ActivityMonitor] Pruned {count} old samples")
            return count
        except Exception as e:
            log.info(f"[ActivityMonitor] Error pruning samples: {e}")
            db.rollback()
            return 0

    def reset_all(self):
        """Delete all activity samples (reset counters)."""
        db = self._get_db()
        if db is None:
            return 0

        try:
            count = db.query(ActivitySample).delete()
            db.commit()
            log.info(f"[ActivityMonitor] Reset: deleted {count} samples")
            return count
        except Exception as e:
            log.info(f"[ActivityMonitor] Error resetting samples: {e}")
            db.rollback()
            return 0

    def log_activity_tick(self, samples_collected, users_active, users_inactive, users_offline):
        """Log activity tick with activity level breakdown."""
        db = self._get_db()
        if db is None:
            return

        try:
            usernames = [r[0] for r in db.query(func.distinct(ActivitySample.username)).all()]

            levels = {'very-high': 0, 'high': 0, 'normal': 0, 'low': 0, 'very-low': 0, 'none': 0}
            for username in usernames:
                score, _ = self.get_score(username)
                if score is None or score == 0:
                    levels['none'] += 1
                elif score >= 80:
                    levels['very-high'] += 1
                elif score >= 60:
                    levels['high'] += 1
                elif score >= 40:
                    levels['normal'] += 1
                elif score >= 20:
                    levels['low'] += 1
                else:
                    levels['very-low'] += 1

            total_users = users_active + users_inactive + users_offline
            level_str = ', '.join([f"{k}({v})" for k, v in levels.items() if v > 0]) or 'none'

            log.info(
                f"[ActivityMonitor] Tick: {samples_collected} samples collected | "
                f"Users: {total_users} total (active={users_active}, inactive={users_inactive}, offline={users_offline}) | "
                f"Activity levels: {level_str}"
            )
        except Exception as e:
            log.info(f"[ActivityMonitor] Error logging tick: {e}")
