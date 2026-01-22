#!/usr/bin/env python3
"""
Custom JupyterHub API handlers for volume management, server control, and notifications
"""

from jupyterhub.handlers import BaseHandler
from tornado import web
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
import docker
import json
import asyncio
import time
import os
import logging
import threading
from datetime import datetime, timedelta, timezone

# Module-level logger
log = logging.getLogger('jupyterhub.custom_handlers')


# =============================================================================
# Password Cache for Admin User Creation
# =============================================================================

# Temporary password cache - stores {username: (password, timestamp)}
_password_cache = {}
_CACHE_EXPIRY_SECONDS = 300  # 5 minutes


def cache_password(username, password):
    """Store a password in the cache with timestamp"""
    _password_cache[username] = (password, time.time())


def get_cached_password(username):
    """Get a password from cache if not expired"""
    if username in _password_cache:
        password, timestamp = _password_cache[username]
        if time.time() - timestamp < _CACHE_EXPIRY_SECONDS:
            return password
        else:
            del _password_cache[username]
    return None


def clear_cached_password(username):
    """Remove a password from cache"""
    _password_cache.pop(username, None)


# =============================================================================
# Activity Sampling for User Engagement Tracking (Database-backed)
# =============================================================================

import math
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLAlchemy model for activity samples
ActivityBase = declarative_base()


class ActivitySample(ActivityBase):
    """Database model for storing user activity samples"""
    __tablename__ = 'activity_samples'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, nullable=True)
    active = Column(Boolean, default=False)

    __table_args__ = (
        Index('ix_activity_user_time', 'username', 'timestamp'),
    )


class ActivityMonitor:
    """
    Central activity monitoring service with database persistence.

    Usage:
        monitor = ActivityMonitor.get_instance()
        monitor.record_sample(username, last_activity)
        score, count = monitor.get_score(username)
        monitor.rename_user(old_name, new_name)
        monitor.delete_user(username)
    """

    _instance = None
    _lock = threading.Lock()

    # Default configuration
    DEFAULT_RETENTION_DAYS = 7       # 7 days
    DEFAULT_HALF_LIFE = 24           # 24 hours
    DEFAULT_INACTIVE_AFTER = 60      # 60 minutes
    DEFAULT_ACTIVITY_UPDATE_INTERVAL = 600  # 10 minutes

    def __init__(self):
        self._db_session = None
        self._engine = None
        self._initialized = False

        # Load configuration from environment
        self.retention_days = self._get_env_int("JUPYTERHUB_ACTIVITYMON_RETENTION_DAYS", self.DEFAULT_RETENTION_DAYS, 1, 365)
        self.half_life_hours = self._get_env_int("JUPYTERHUB_ACTIVITYMON_HALF_LIFE", self.DEFAULT_HALF_LIFE, 1, 168)
        self.inactive_after_minutes = self._get_env_int("JUPYTERHUB_ACTIVITYMON_INACTIVE_AFTER", self.DEFAULT_INACTIVE_AFTER, 1, 1440)
        self.activity_update_interval = self._get_env_int("JUPYTERHUB_ACTIVITYMON_ACTIVITY_UPDATE_INTERVAL", self.DEFAULT_ACTIVITY_UPDATE_INTERVAL, 60, 86400)

        # Calculate decay constant
        self.decay_lambda = math.log(2) / self.half_life_hours

        log.info(f"[ActivityMonitor] Config: retention={self.retention_days}d, half_life={self.half_life_hours}h, inactive_after={self.inactive_after_minutes}m, activity_update={self.activity_update_interval}s")

    @classmethod
    def get_instance(cls):
        """Get singleton instance of ActivityMonitor"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_env_int(self, name, default, min_val, max_val):
        """Get integer from environment with validation"""
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
        """Get or create database session.

        Uses a SEPARATE database file to avoid SQLite locking conflicts
        with JupyterHub's main database.
        """
        if self._db_session is not None:
            return self._db_session

        # Use separate database file to avoid locking conflicts with JupyterHub
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
        """Record an activity sample for a user.

        Always inserts a new sample - caller controls sampling frequency.
        """
        db = self._get_db()
        if db is None:
            return False

        try:
            now = datetime.now(timezone.utc)

            # User is "active" if last_activity is within INACTIVE_AFTER minutes
            active = False
            if last_activity:
                last_activity_utc = last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity
                age_seconds = (now - last_activity_utc).total_seconds()
                active = age_seconds <= (self.inactive_after_minutes * 60)

            # Insert new sample
            db.add(ActivitySample(username=username, timestamp=now, last_activity=last_activity, active=active))
            db.commit()

            # Prune old samples
            cutoff = now - timedelta(days=self.retention_days)
            deleted = db.query(ActivitySample).filter(
                ActivitySample.username == username,
                ActivitySample.timestamp < cutoff
            ).delete()
            if deleted > 0:
                db.commit()

            return True
        except Exception as e:
            log.info(f"[ActivityMonitor] Error recording sample for {username}: {e}")
            db.rollback()
            return False

    def get_score(self, username):
        """Calculate activity score (0-100) for a user. Returns (score, sample_count)."""
        db = self._get_db()
        if db is None:
            return None, 0

        try:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(days=self.retention_days)

            samples = db.query(ActivitySample).filter(
                ActivitySample.username == username,
                ActivitySample.timestamp >= cutoff
            ).all()

            if not samples:
                return None, 0

            # Calculate weighted sums with exponential decay
            # Score is based on measured samples only (not theoretical max)
            weighted_active = 0.0
            weighted_total = 0.0
            for s in samples:
                ts = s.timestamp.replace(tzinfo=timezone.utc) if s.timestamp.tzinfo is None else s.timestamp
                age_hours = (now - ts).total_seconds() / 3600.0
                weight = math.exp(-self.decay_lambda * age_hours)
                weighted_total += weight
                if s.active:
                    weighted_active += weight

            # Score = ratio of weighted active to weighted total samples
            score = int((weighted_active / weighted_total) * 100) if weighted_total > 0 else 0

            return score, len(samples)
        except Exception as e:
            log.info(f"[ActivityMonitor] Error calculating score for {username}: {e}")
            return None, 0

    def get_status(self):
        """Get overall sampling status"""
        db = self._get_db()
        if db is None:
            return "Database not available"

        try:
            result = db.query(func.count(ActivitySample.id), func.count(func.distinct(ActivitySample.username))).first()
            total_samples, total_users = result[0] or 0, result[1] or 0
            return f"{total_samples} samples for {total_users} users" if total_samples > 0 else "No samples yet"
        except Exception as e:
            log.info(f"[ActivityMonitor] Error getting status: {e}")
            return "Status unavailable"

    def rename_user(self, old_username, new_username):
        """Rename user in activity records"""
        db = self._get_db()
        if db is None:
            return False

        try:
            count = db.query(ActivitySample).filter(ActivitySample.username == old_username).update({'username': new_username})
            db.commit()
            if count > 0:
                log.info(f"[ActivityMonitor] Renamed {count} samples: {old_username} -> {new_username}")
            return True
        except Exception as e:
            log.info(f"[ActivityMonitor] Error renaming user: {e}")
            db.rollback()
            return False

    def delete_user(self, username):
        """Delete all activity records for a user"""
        db = self._get_db()
        if db is None:
            return False

        try:
            count = db.query(ActivitySample).filter(ActivitySample.username == username).delete()
            db.commit()
            if count > 0:
                log.info(f"[ActivityMonitor] Deleted {count} samples for {username}")
            return True
        except Exception as e:
            log.info(f"[ActivityMonitor] Error deleting user: {e}")
            db.rollback()
            return False

    def prune_old_samples(self):
        """Remove all samples older than retention period"""
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
        """Delete all activity samples (reset counters)"""
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
        """Log activity tick statistics with activity level breakdown.

        Activity levels based on score:
        - very-high: 80-100%
        - high: 60-79%
        - normal: 40-59%
        - low: 20-39%
        - very-low: 1-19%
        - none: 0%
        """
        db = self._get_db()
        if db is None:
            return

        try:
            # Get all unique usernames with samples
            usernames = [r[0] for r in db.query(func.distinct(ActivitySample.username)).all()]

            # Calculate activity levels
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

            log.info(f"[ActivityMonitor] Tick: {samples_collected} samples collected | "
                  f"Users: {total_users} total (active={users_active}, inactive={users_inactive}, offline={users_offline}) | "
                  f"Activity levels: {level_str}")
        except Exception as e:
            log.info(f"[ActivityMonitor] Error logging tick: {e}")


# Convenience functions that use the singleton instance
def record_activity_sample(username, last_activity):
    return ActivityMonitor.get_instance().record_sample(username, last_activity)

def calculate_activity_score(username):
    return ActivityMonitor.get_instance().get_score(username)

def get_activity_sampling_status():
    return ActivityMonitor.get_instance().get_status()

def get_inactive_after_seconds():
    """Get the inactive threshold in seconds"""
    return ActivityMonitor.get_instance().inactive_after_minutes * 60

def rename_activity_user(old_username, new_username):
    return ActivityMonitor.get_instance().rename_user(old_username, new_username)

def delete_activity_user(username):
    return ActivityMonitor.get_instance().delete_user(username)

def reset_all_activity_data():
    """Reset all activity data (delete all samples)"""
    return ActivityMonitor.get_instance().reset_all()


def record_samples_for_all_users(db, find_user_func):
    """
    Record activity samples for ALL users (active and offline).

    Call this from a scheduled task or background process.
    - Active users with recent activity → sample marked as active
    - Active users without recent activity (idle) → sample marked as inactive
    - Offline users → sample marked as inactive (last_activity from last session)

    Args:
        db: JupyterHub database session (handler.db)
        find_user_func: Function to find user by name (handler.find_user)

    Returns:
        dict with counts: {'total': N, 'active': N, 'inactive': N, 'offline': N}
    """
    from jupyterhub import orm
    from datetime import datetime, timezone

    monitor = ActivityMonitor.get_instance()
    inactive_threshold = monitor.inactive_after_minutes * 60
    now = datetime.now(timezone.utc)

    counts = {'total': 0, 'active': 0, 'inactive': 0, 'offline': 0}

    for orm_user in db.query(orm.User).all():
        user = find_user_func(orm_user.name)
        if not user:
            continue

        spawner = user.spawner
        server_active = spawner.active if spawner else False

        # Get last_activity from spawner
        last_activity = None
        if spawner and spawner.orm_spawner:
            last_activity = spawner.orm_spawner.last_activity
            if last_activity and last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)

        # Record sample for this user
        monitor.record_sample(user.name, last_activity)
        counts['total'] += 1

        # Count by status
        if server_active:
            if last_activity:
                elapsed = (now - last_activity).total_seconds()
                if elapsed <= inactive_threshold:
                    counts['active'] += 1
                else:
                    counts['inactive'] += 1
            else:
                counts['inactive'] += 1
        else:
            counts['offline'] += 1

    # Log the tick with statistics
    monitor.log_activity_tick(
        counts['total'],
        counts['active'],
        counts['inactive'],
        counts['offline']
    )


# =============================================================================
# Background Activity Sampler (automatic periodic sampling)
# =============================================================================

_activity_sampler = None

class ActivitySampler:
    """
    Background scheduler that periodically samples activity for ALL users.
    Uses Tornado's PeriodicCallback for non-blocking execution.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        from tornado.ioloop import PeriodicCallback
        self.periodic_callback = None
        self.db = None
        self.find_user = None
        self.interval_seconds = int(os.environ.get('JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL', 600))
        log.info(f"[ActivitySampler] Initialized with interval={self.interval_seconds}s")

    def start(self, db, find_user):
        """Start the periodic sampler. Call with handler's db and find_user."""
        from tornado.ioloop import PeriodicCallback
        self.db = db
        self.find_user = find_user

        if self.periodic_callback is not None:
            log.info("[ActivitySampler] Already running")
            return

        # Convert seconds to milliseconds for PeriodicCallback
        interval_ms = self.interval_seconds * 1000

        self.periodic_callback = PeriodicCallback(self._sample_tick, interval_ms)
        self.periodic_callback.start()
        log.info(f"[ActivitySampler] Started - sampling every {self.interval_seconds}s")

        # Run first sample immediately
        asyncio.get_event_loop().call_soon(lambda: asyncio.ensure_future(self._sample_tick_async()))

    def stop(self):
        """Stop the periodic sampler."""
        if self.periodic_callback is not None:
            self.periodic_callback.stop()
            self.periodic_callback = None
            log.info("[ActivitySampler] Stopped")

    def _sample_tick(self):
        """Called by PeriodicCallback - wraps async call."""
        asyncio.ensure_future(self._sample_tick_async())

    async def _sample_tick_async(self):
        """Async tick - records samples for all users."""
        if self.db is None or self.find_user is None:
            log.info("[ActivitySampler] No db/find_user reference, skipping")
            return

        try:
            from jupyterhub import orm

            monitor = ActivityMonitor.get_instance()
            inactive_threshold = monitor.inactive_after_minutes * 60
            now = datetime.now(timezone.utc)

            counts = {'total': 0, 'active': 0, 'inactive': 0, 'offline': 0}

            for orm_user in self.db.query(orm.User).all():
                user = self.find_user(orm_user.name)
                if not user:
                    continue

                spawner = user.spawner
                server_active = spawner.active if spawner else False

                # Get last_activity from spawner
                last_activity = None
                if spawner and spawner.orm_spawner:
                    last_activity = spawner.orm_spawner.last_activity
                    if last_activity and last_activity.tzinfo is None:
                        last_activity = last_activity.replace(tzinfo=timezone.utc)

                # Record sample for this user
                monitor.record_sample(user.name, last_activity)
                counts['total'] += 1

                # Count by status
                if server_active:
                    if last_activity:
                        elapsed = (now - last_activity).total_seconds()
                        if elapsed <= inactive_threshold:
                            counts['active'] += 1
                        else:
                            counts['inactive'] += 1
                    else:
                        counts['inactive'] += 1
                else:
                    counts['offline'] += 1

            # Log the tick with statistics
            monitor.log_activity_tick(
                counts['total'],
                counts['active'],
                counts['inactive'],
                counts['offline']
            )

        except Exception as e:
            log.info(f"[ActivitySampler] Error during sampling: {e}")


def start_activity_sampler(db, find_user):
    """Start the background activity sampler. Pass db session and find_user function."""
    sampler = ActivitySampler.get_instance()
    sampler.start(db, find_user)


# Thread pool for blocking Docker operations (prevents event loop blocking)
from concurrent.futures import ThreadPoolExecutor
_docker_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="docker-stats")


def get_container_stats(username):
    """Get CPU and memory stats for a user's container (blocking - use async wrapper)"""
    try:
        docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        container_name = f'jupyterlab-{encode_username_for_docker(username)}'

        try:
            container = docker_client.containers.get(container_name)
            stats = container.stats(stream=False)

            # Calculate CPU percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                        stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                           stats['precpu_stats']['system_cpu_usage']

            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                online_cpus = stats['cpu_stats'].get('online_cpus', 1)
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100

            # Memory stats
            memory_usage = stats['memory_stats'].get('usage', 0)
            memory_limit = stats['memory_stats'].get('limit', 1)
            memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0

            return {
                'cpu_percent': round(cpu_percent, 1),
                'memory_mb': round(memory_usage / (1024 * 1024), 1),
                'memory_percent': round(memory_percent, 1)
            }
        finally:
            docker_client.close()

    except Exception as e:
        return None


async def get_container_stats_async(username):
    """Async wrapper for get_container_stats - runs in thread pool to avoid blocking"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_docker_executor, get_container_stats, username)


# =============================================================================
# Volume Sizes Cache (background refresh to avoid blocking page load)
# =============================================================================

# Cache for volume sizes: {'data': {encoded_username: size_mb}, 'timestamp': datetime}
_volume_sizes_cache = {'data': {}, 'timestamp': None, 'refreshing': False}

def _get_volumes_update_interval():
    """Get volume sizes update interval in seconds (default 3600 = 1 hour)"""
    return int(os.environ.get('JUPYTERHUB_ACTIVITYMON_VOLUMES_UPDATE_INTERVAL', 3600))

def _fetch_volume_sizes():
    """
    Fetch sizes of all user volumes (blocking).
    Returns dict: {encoded_username: total_size_mb}
    Uses 'docker system df -v' equivalent via Docker SDK.
    """
    try:
        docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        try:
            # Use df() to get disk usage including volume sizes
            # This is equivalent to 'docker system df -v'
            df_data = docker_client.df()
            volumes_data = df_data.get('Volumes', []) or []

            # Build dict of volume sizes by encoded username
            user_sizes = {}
            for vol in volumes_data:
                name = vol.get('Name', '')
                # Match pattern: jupyterlab-{encoded_username}_{suffix}
                if name.startswith('jupyterlab-') and '_' in name:
                    # Extract encoded username (between 'jupyterlab-' and last '_')
                    parts = name[len('jupyterlab-'):].rsplit('_', 1)
                    if len(parts) == 2:
                        encoded_username = parts[0]
                        # UsageData.Size contains actual bytes used
                        usage_data = vol.get('UsageData', {}) or {}
                        size_bytes = usage_data.get('Size', 0) or 0

                        if encoded_username not in user_sizes:
                            user_sizes[encoded_username] = 0
                        user_sizes[encoded_username] += size_bytes

            # Convert to MB
            result = {user: round(size / (1024 * 1024), 1) for user, size in user_sizes.items()}
            log.info(f"[Volume Sizes] Refreshed: {len(result)} users, total {sum(result.values()):.1f} MB")
            return result
        finally:
            docker_client.close()
    except Exception as e:
        log.info(f"[Volume Sizes] Error: {e}")
        return {}

def _refresh_volume_sizes_sync():
    """Synchronous refresh of volume sizes cache"""
    global _volume_sizes_cache
    if _volume_sizes_cache['refreshing']:
        return  # Already refreshing

    _volume_sizes_cache['refreshing'] = True
    try:
        data = _fetch_volume_sizes()
        _volume_sizes_cache['data'] = data
        _volume_sizes_cache['timestamp'] = datetime.now(timezone.utc)
    finally:
        _volume_sizes_cache['refreshing'] = False

async def _refresh_volume_sizes_background():
    """Trigger background refresh of volume sizes (non-blocking)"""
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_docker_executor, _refresh_volume_sizes_sync)

def get_cached_volume_sizes():
    """
    Get cached volume sizes (non-blocking).
    Returns immediately with cached data. Triggers background refresh if stale.
    Returns dict: {encoded_username: size_mb}
    """
    global _volume_sizes_cache
    now = datetime.now(timezone.utc)
    interval = _get_volumes_update_interval()

    # Check if cache needs refresh
    needs_refresh = (
        _volume_sizes_cache['timestamp'] is None or
        (now - _volume_sizes_cache['timestamp']).total_seconds() > interval
    )

    return _volume_sizes_cache['data'], needs_refresh

async def get_volume_sizes_with_refresh():
    """
    Get volume sizes, triggering background refresh if needed.
    Returns immediately with cached data (may be empty on first call).
    """
    data, needs_refresh = get_cached_volume_sizes()
    if needs_refresh:
        log.info(f"[Volume Sizes] Cache stale, triggering background refresh")
        await _refresh_volume_sizes_background()
    return data


# =============================================================================
# Volume Size Refresher (independent background refresh)
# =============================================================================

class VolumeSizeRefresher:
    """
    Background scheduler that periodically refreshes volume sizes.
    Uses Tornado's PeriodicCallback for non-blocking execution.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.periodic_callback = None
        self.interval_seconds = _get_volumes_update_interval()
        log.info(f"[VolumeSizeRefresher] Initialized with interval={self.interval_seconds}s")

    def start(self):
        """Start the periodic refresher."""
        from tornado.ioloop import PeriodicCallback

        if self.periodic_callback is not None:
            log.info("[VolumeSizeRefresher] Already running")
            return

        # Convert seconds to milliseconds for PeriodicCallback
        interval_ms = self.interval_seconds * 1000

        self.periodic_callback = PeriodicCallback(self._refresh_tick, interval_ms)
        self.periodic_callback.start()
        log.info(f"[VolumeSizeRefresher] Started - refreshing every {self.interval_seconds}s")

        # Run first refresh immediately
        asyncio.get_event_loop().call_soon(lambda: asyncio.ensure_future(self._refresh_tick_async()))

    def stop(self):
        """Stop the periodic refresher."""
        if self.periodic_callback is not None:
            self.periodic_callback.stop()
            self.periodic_callback = None
            log.info("[VolumeSizeRefresher] Stopped")

    def _refresh_tick(self):
        """Called by PeriodicCallback - wraps async call."""
        asyncio.ensure_future(self._refresh_tick_async())

    async def _refresh_tick_async(self):
        """Async tick - refreshes volume sizes in background."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(_docker_executor, _refresh_volume_sizes_sync)
        except Exception as e:
            log.error(f"[VolumeSizeRefresher] Error during refresh: {e}")


def start_volume_size_refresher():
    """Start the background volume size refresher."""
    refresher = VolumeSizeRefresher.get_instance()
    refresher.start()


# =============================================================================
# Docker Volume Name Encoding
# =============================================================================

def encode_username_for_docker(username):
    """
    Encode username for Docker volume/container names.
    Uses escapism library (same as DockerSpawner) for compatibility.
    e.g., 'user.name' -> 'user-2ename' (. = ASCII 46 = 0x2e)
    """
    from escapism import escape
    return escape(username, escape_char='-').lower()


class ManageVolumesHandler(BaseHandler):
    """Handler for managing user volumes"""

    async def delete(self, username):
        """
        Delete selected user volumes (only when server is stopped)

        DELETE /hub/api/users/{username}/manage-volumes
        Body: {"volumes": ["home", "workspace", "cache"]}
        """
        self.log.info(f"[Manage Volumes] API endpoint called for user: {username}")

        # 0. Check permissions: user must be admin or requesting their own volumes
        current_user = self.current_user
        if current_user is None:
            self.log.warning(f"[Manage Volumes] Authentication failed - no current user")
            raise web.HTTPError(403, "Not authenticated")

        self.log.info(f"[Manage Volumes] Request from user: {current_user.name}, admin: {current_user.admin}")

        if not (current_user.admin or current_user.name == username):
            self.log.warning(f"[Manage Volumes] Permission denied - user {current_user.name} attempted to manage {username}'s volumes")
            raise web.HTTPError(403, "Permission denied")

        self.log.info(f"[Manage Volumes] Permission check passed")

        # 1. Parse request body
        try:
            body = self.request.body.decode('utf-8')
            data = json.loads(body) if body else {}
            requested_volumes = data.get('volumes', [])
            self.log.info(f"[Manage Volumes] Requested volumes: {requested_volumes}")
        except Exception as e:
            self.log.error(f"[Manage Volumes] Failed to parse request body: {e}")
            return self.send_error(400, "Invalid request body")

        if not requested_volumes or not isinstance(requested_volumes, list):
            self.log.warning(f"[Manage Volumes] No volumes specified or invalid format")
            return self.send_error(400, "No volumes specified")

        # Validate volume types against configured USER_VOLUME_SUFFIXES
        from jupyterhub_config import USER_VOLUME_SUFFIXES
        valid_volumes = set(USER_VOLUME_SUFFIXES)
        invalid_volumes = set(requested_volumes) - valid_volumes
        if invalid_volumes:
            self.log.warning(f"[Manage Volumes] Invalid volume types: {invalid_volumes}")
            return self.send_error(400, f"Invalid volume types: {invalid_volumes}")

        # 2. Verify user exists
        user = self.find_user(username)
        if not user:
            self.log.warning(f"[Manage Volumes] User {username} not found")
            return self.send_error(404, "User not found")

        self.log.info(f"[Manage Volumes] User {username} found")

        # 3. Check server is stopped
        spawner = user.spawner
        self.log.info(f"[Manage Volumes] Server status for {username}: active={spawner.active}")

        if spawner.active:
            self.log.warning(f"[Manage Volumes] Server is running, cannot reset volumes")
            return self.send_error(400, "Server must be stopped before resetting volumes")

        self.log.info(f"[Manage Volumes] Server is stopped, proceeding with volume reset")

        # 4. Connect to Docker
        self.log.info(f"[Manage Volumes] Connecting to Docker daemon")
        try:
            docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
            self.log.info(f"[Manage Volumes] Successfully connected to Docker")
        except Exception as e:
            self.log.error(f"[Manage Volumes] Failed to connect to Docker: {e}")
            return self.send_error(500, "Failed to connect to Docker daemon")

        # 5. Remove requested volumes
        reset_volumes = []
        failed_volumes = []

        for volume_type in requested_volumes:
            volume_name = f'jupyterlab-{encode_username_for_docker(username)}_{volume_type}'
            self.log.info(f"[Manage Volumes] Processing volume: {volume_name}")

            try:
                volume = docker_client.volumes.get(volume_name)
                self.log.info(f"[Manage Volumes] Volume {volume_name} found, removing...")
                volume.remove()
                self.log.info(f"[Manage Volumes] Successfully removed volume {volume_name}")
                reset_volumes.append(volume_type)
            except docker.errors.NotFound:
                self.log.warning(f"[Manage Volumes] Volume {volume_name} not found, skipping")
                failed_volumes.append({"volume": volume_type, "reason": "not found"})
            except docker.errors.APIError as e:
                self.log.error(f"[Manage Volumes] Failed to remove volume {volume_name}: {e}")
                failed_volumes.append({"volume": volume_type, "reason": str(e)})

        docker_client.close()
        self.log.info(f"[Manage Volumes] Docker client closed")

        # 6. Return response
        response = {
            "message": f"Successfully reset {len(reset_volumes)} volume(s)",
            "reset_volumes": reset_volumes,
            "failed_volumes": failed_volumes
        }

        self.log.info(f"[Manage Volumes] Operation complete: {len(reset_volumes)} reset, {len(failed_volumes)} failed")
        self.set_status(200)
        self.finish(response)


class RestartServerHandler(BaseHandler):
    """Handler for restarting user servers"""

    async def post(self, username):
        """
        Restart a user's server using Docker container restart

        POST /hub/api/users/{username}/restart-server
        """
        self.log.info(f"[Restart Server] API endpoint called for user: {username}")

        # 0. Check permissions: user must be admin or requesting their own server
        current_user = self.current_user
        if current_user is None:
            self.log.warning(f"[Restart Server] Authentication failed - no current user")
            raise web.HTTPError(403, "Not authenticated")

        self.log.info(f"[Restart Server] Request from user: {current_user.name}, admin: {current_user.admin}")

        if not (current_user.admin or current_user.name == username):
            self.log.warning(f"[Restart Server] Permission denied - user {current_user.name} attempted to restart {username}'s server")
            raise web.HTTPError(403, "Permission denied")

        self.log.info(f"[Restart Server] Permission check passed")

        # 1. Verify user exists
        user = self.find_user(username)
        if not user:
            self.log.warning(f"[Restart Server] User {username} not found")
            return self.send_error(404, "User not found")

        self.log.info(f"[Restart Server] User {username} found")

        # 2. Check server is running
        spawner = user.spawner
        self.log.info(f"[Restart Server] Server status for {username}: active={spawner.active}")

        if not spawner.active:
            self.log.warning(f"[Restart Server] Server is not running, cannot restart")
            return self.send_error(400, "Server is not running")

        self.log.info(f"[Restart Server] Server is running, proceeding with restart")

        # 3. Get container name from spawner
        container_name = f'jupyterlab-{encode_username_for_docker(username)}'
        self.log.info(f"[Restart Server] Container name: {container_name}")

        # 4. Connect to Docker and restart container
        self.log.info(f"[Restart Server] Connecting to Docker daemon")
        try:
            docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
            self.log.info(f"[Restart Server] Successfully connected to Docker")
        except Exception as e:
            self.log.error(f"[Restart Server] Failed to connect to Docker: {e}")
            return self.send_error(500, "Failed to connect to Docker daemon")

        try:
            # Get the container
            self.log.info(f"[Restart Server] Getting container: {container_name}")
            container = docker_client.containers.get(container_name)
            self.log.info(f"[Restart Server] Container found, status: {container.status}")

            # Restart the container (graceful restart with 10s timeout)
            self.log.info(f"[Restart Server] Initiating container restart (timeout=10s)")
            container.restart(timeout=10)

            self.log.info(f"[Restart Server] Container {container_name} successfully restarted for user {username}")
            self.set_status(200)
            self.finish({"message": f"Container {container_name} successfully restarted"})
        except docker.errors.NotFound:
            self.log.warning(f"[Restart Server] Container {container_name} not found")
            return self.send_error(404, f"Container {container_name} not found")
        except docker.errors.APIError as e:
            self.log.error(f"[Restart Server] Failed to restart container {container_name}: {e}")
            return self.send_error(500, f"Failed to restart container: {str(e)}")
        finally:
            docker_client.close()
            self.log.info(f"[Restart Server] Docker client closed")


class NotificationsPageHandler(BaseHandler):
    """Handler for rendering the notifications broadcast page"""

    @web.authenticated
    async def get(self):
        """
        Render the notifications broadcast page (admin only)

        GET /notifications
        """
        current_user = self.current_user

        # Only admins can access notifications panel
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this page")

        self.log.info(f"[Notifications Page] Admin {current_user.name} accessed notifications panel")

        # Render the template (sync=True to get string instead of awaitable)
        html = self.render_template("notifications.html", sync=True, user=current_user)
        self.finish(html)


class ActiveServersHandler(BaseHandler):
    """Handler for listing active servers for notification targeting"""

    @web.authenticated
    async def get(self):
        """
        List all active JupyterLab servers (admin only)

        GET /hub/api/notifications/active-servers
        Returns: {"servers": [{"username": "user1"}, {"username": "user2"}, ...]}
        """
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can list active servers")

        self.log.info(f"[Active Servers] Request from admin: {current_user.name}")

        active_servers = []
        from jupyterhub import orm
        for orm_user in self.db.query(orm.User).all():
            user = self.find_user(orm_user.name)
            if user and user.spawner and user.spawner.active:
                active_servers.append({"username": user.name})

        self.log.info(f"[Active Servers] Found {len(active_servers)} active server(s)")
        self.finish({"servers": active_servers})


class BroadcastNotificationHandler(BaseHandler):
    """Handler for broadcasting notifications to active JupyterLab servers"""

    async def post(self):
        """
        Broadcast a notification to active JupyterLab servers

        POST /hub/api/notifications/broadcast
        Body: {
            "message": "string",
            "variant": "info|success|warning|error",
            "autoClose": false,
            "recipients": ["user1", "user2"]  # optional - if omitted, sends to all
        }
        """
        self.log.info(f"[Broadcast Notification] API endpoint called")

        # 0. Check permissions: only admins can broadcast
        current_user = self.current_user
        if current_user is None:
            self.log.warning(f"[Broadcast Notification] Authentication failed - no current user")
            raise web.HTTPError(403, "Not authenticated")

        if not current_user.admin:
            self.log.warning(f"[Broadcast Notification] Permission denied - user {current_user.name} is not admin")
            raise web.HTTPError(403, "Only administrators can broadcast notifications")

        self.log.info(f"[Broadcast Notification] Request from admin: {current_user.name}")

        # 1. Parse request body
        try:
            body = self.request.body.decode('utf-8')
            data = json.loads(body) if body else {}
            message = data.get('message', '').strip()
            variant = data.get('variant', 'info')
            auto_close = data.get('autoClose', False)
            recipients = data.get('recipients', None)  # Optional: list of usernames

            self.log.info(f"[Broadcast Notification] Message: {message[:50]}..., Variant: {variant}, AutoClose: {auto_close}, Recipients: {recipients or 'all'}")
        except Exception as e:
            self.log.error(f"[Broadcast Notification] Failed to parse request body: {e}")
            return self.send_error(400, "Invalid request body")

        # 2. Validate input
        if not message:
            self.log.warning(f"[Broadcast Notification] Empty message provided")
            return self.send_error(400, "Message cannot be empty")

        if len(message) > 140:
            self.log.warning(f"[Broadcast Notification] Message too long: {len(message)} characters")
            return self.send_error(400, "Message cannot exceed 140 characters")

        valid_variants = ['default', 'info', 'success', 'warning', 'error', 'in-progress']
        if variant not in valid_variants:
            self.log.warning(f"[Broadcast Notification] Invalid variant: {variant}")
            return self.send_error(400, f"Variant must be one of: {', '.join(valid_variants)}")

        # 3. Get all active spawners
        self.log.info(f"[Broadcast Notification] Querying active spawners")
        active_spawners = []

        from jupyterhub import orm
        for orm_user in self.db.query(orm.User).all():
            # Use find_user to get the wrapped user object with spawner property
            user = self.find_user(orm_user.name)
            if user and user.spawner and user.spawner.active:
                active_spawners.append((user, user.spawner))

        self.log.info(f"[Broadcast Notification] Found {len(active_spawners)} active server(s)")

        # 4. Filter by recipients if specified
        if recipients and isinstance(recipients, list) and len(recipients) > 0:
            recipients_set = set(recipients)
            active_spawners = [(u, s) for u, s in active_spawners if u.name in recipients_set]
            self.log.info(f"[Broadcast Notification] Filtered to {len(active_spawners)} selected recipient(s)")

        if not active_spawners:
            self.log.info(f"[Broadcast Notification] No active servers found")
            return self.finish({
                "total": 0,
                "successful": 0,
                "failed": 0,
                "details": [],
                "message": "No active servers found"
            })

        # 4. Broadcast to all active servers concurrently
        notification_payload = {
            "message": message,
            "type": variant,
            "autoClose": auto_close,
            "actions": [
                {
                    "label": "Dismiss",
                    "caption": "Close this notification",
                    "displayType": "default"
                }
            ]
        }

        tasks = []
        for user, spawner in active_spawners:
            task = self._send_notification(user, spawner, notification_payload)
            tasks.append(task)

        # Gather all results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 5. Compile response
        successful = 0
        failed = 0
        details = []

        for (user, spawner), result in zip(active_spawners, results):
            if isinstance(result, dict) and result.get('status') == 'success':
                successful += 1
                details.append({
                    "username": user.name,
                    "status": "success"
                })
            else:
                failed += 1
                error_msg = str(result) if isinstance(result, Exception) else result.get('error', 'Unknown error')
                details.append({
                    "username": user.name,
                    "status": "failed",
                    "error": error_msg
                })

        total = len(active_spawners)
        self.log.info(f"[Broadcast Notification] Complete: {successful}/{total} successful, {failed}/{total} failed")

        response = {
            "total": total,
            "successful": successful,
            "failed": failed,
            "details": details
        }

        self.set_status(200)
        self.finish(response)

    async def _send_notification(self, user, spawner, notification_payload):
        """
        Send notification to a single JupyterLab server

        Args:
            user: JupyterHub user object
            spawner: User's spawner object
            notification_payload: Notification data dict

        Returns:
            dict: {"status": "success"} or {"status": "failed", "error": "message"}
        """
        username = user.name

        try:
            # 1. Get or create API token for the user
            self.log.info(f"[Broadcast Notification] Getting API token for user: {username}")

            # Generate a new API token for notification purposes
            # Note: APIToken.token is write-only, we cannot read existing tokens
            # We create a new token with note identifying it as for notifications
            token = user.new_api_token(note="notification-broadcast", expires_in=300)
            self.log.info(f"[Broadcast Notification] Generated temporary API token for {username}")

            # 2. Construct JupyterLab URL
            # Use the spawner's internal connection URL (direct container access)
            # The spawner.server.url contains the public-facing URL
            if not spawner.server:
                self.log.warning(f"[Broadcast Notification] Spawner for {username} has no server")
                return {"status": "failed", "error": "Server not available"}

            # Get the base URL from spawner server (e.g., /jupyterhub/user/konrad/)
            base_url = spawner.server.base_url
            # Construct internal container URL
            container_url = f"http://jupyterlab-{encode_username_for_docker(username)}:8888"
            endpoint = f"{container_url}{base_url}jupyterlab-notifications-extension/ingest"

            self.log.info(f"[Notification] Constructed endpoint for {username}: {endpoint}")

            # 3. Make HTTP request
            http_client = AsyncHTTPClient()

            request = HTTPRequest(
                url=endpoint,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                },
                body=json.dumps(notification_payload),
                request_timeout=5.0,
                connect_timeout=5.0
            )

            response = await http_client.fetch(request, raise_error=False)

            if response.code == 200:
                self.log.info(f"[Notification] {username}: '{notification_payload['message'][:50]}' ({notification_payload['type']}) - SUCCESS")
                return {"status": "success"}
            else:
                error_msg = f"HTTP {response.code}: {response.reason}"
                self.log.warning(f"[Notification] {username}: '{notification_payload['message'][:50]}' ({notification_payload['type']}) - FAILED: {error_msg}")
                return {"status": "failed", "error": error_msg}

        except Exception as e:
            error_msg = str(e)

            # Provide more specific error messages
            if "Connection refused" in error_msg or "Connection timed out" in error_msg:
                error_msg = "Server not responding"
            elif "404" in error_msg:
                error_msg = "Notification extension not installed"
            elif "401" in error_msg or "403" in error_msg:
                error_msg = "Authentication failed"

            self.log.error(f"[Notification] {username}: '{notification_payload['message'][:50]}' ({notification_payload['type']}) - ERROR: {error_msg}")
            return {"status": "failed", "error": error_msg}


class GetUserCredentialsHandler(BaseHandler):
    """Handler for retrieving credentials of newly created users"""

    @web.authenticated
    async def post(self):
        """
        Retrieve cached credentials for newly created users (admin only)

        POST /hub/api/admin/credentials
        Body: {"usernames": ["user1", "user2", ...]}
        Returns: {"credentials": [{"username": "...", "password": "..."}, ...]}
        """
        # Admin-only permission check
        current_user = self.current_user
        if current_user is None or not current_user.admin:
            self.log.warning(f"[Get Credentials] Permission denied - admin required")
            raise web.HTTPError(403, "Only administrators can retrieve credentials")

        # Parse request body
        try:
            body = self.request.body.decode('utf-8')
            data = json.loads(body) if body else {}
            usernames = data.get('usernames', [])
        except Exception as e:
            self.log.error(f"[Get Credentials] Failed to parse request body: {e}")
            raise web.HTTPError(400, "Invalid request body")

        self.log.info(f"[Get Credentials] Admin {current_user.name} requesting credentials for: {usernames}")

        # Get credentials from cache
        credentials = []
        for username in usernames:
            password = get_cached_password(username)
            if password:
                credentials.append({"username": username, "password": password})
                self.log.info(f"[Get Credentials] Found cached password for: {username}")
            else:
                self.log.info(f"[Get Credentials] No cached password for: {username}")

        self.log.info(f"[Get Credentials] Returning {len(credentials)} credential(s)")
        self.finish({"credentials": credentials})


class SessionInfoHandler(BaseHandler):
    """Handler for getting session info including idle culler status and extension tracking"""

    @web.authenticated
    async def get(self, username):
        """
        Get session info for a user's server

        GET /hub/api/users/{username}/session-info
        Returns: {
            "culler_enabled": true,
            "server_active": true,
            "last_activity": "2024-01-18T10:30:00Z",
            "timeout_seconds": 86400,
            "time_remaining_seconds": 7200,
            "extensions_used_hours": 4,
            "extensions_available_hours": 20
        }
        """
        self.log.info(f"[Session Info] API endpoint called for user: {username}")

        # Check permissions: user must be admin or requesting their own info
        current_user = self.current_user
        if current_user is None:
            raise web.HTTPError(403, "Not authenticated")

        if not (current_user.admin or current_user.name == username):
            raise web.HTTPError(403, "Permission denied")

        # Get idle culler config from environment
        import os
        culler_enabled = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_ENABLED", 0)) == 1
        timeout_seconds = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_TIMEOUT", 86400))
        max_extension_hours = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION", 24))

        # Get user and spawner
        user = self.find_user(username)
        if not user:
            raise web.HTTPError(404, "User not found")

        spawner = user.spawner
        server_active = spawner.active if spawner else False

        response = {
            "culler_enabled": culler_enabled,
            "server_active": server_active,
            "timeout_seconds": timeout_seconds,
            "max_extension_hours": max_extension_hours,
        }

        if server_active and culler_enabled:
            # Get extension tracking from spawner state
            spawner_state = spawner.orm_spawner.state or {}
            extensions_used_hours = spawner_state.get('extension_hours_used', 0)
            extension_seconds = extensions_used_hours * 3600  # Convert to seconds

            # Calculate effective timeout (base timeout + extension)
            effective_timeout = timeout_seconds + extension_seconds

            self.log.info(f"[Session Info] {username}: base_timeout={timeout_seconds}s ({timeout_seconds/3600:.1f}h), extensions={extensions_used_hours}h, effective_timeout={effective_timeout}s ({effective_timeout/3600:.1f}h)")

            # Get last activity timestamp from SPAWNER (not user - user.last_activity updates on Hub access)
            # The idle culler uses spawner.last_activity, so we must use the same
            last_activity = spawner.orm_spawner.last_activity if spawner.orm_spawner else None
            if last_activity:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                last_activity_utc = last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity
                elapsed_seconds = (now - last_activity_utc).total_seconds()
                time_remaining_seconds = max(0, effective_timeout - elapsed_seconds)

                self.log.info(f"[Session Info] {username}: elapsed={elapsed_seconds:.0f}s ({elapsed_seconds/3600:.1f}h), remaining={time_remaining_seconds:.0f}s ({time_remaining_seconds/3600:.1f}h)")

                response["last_activity"] = last_activity_utc.isoformat()
                response["time_remaining_seconds"] = int(time_remaining_seconds)
            else:
                response["last_activity"] = None
                response["time_remaining_seconds"] = effective_timeout
                self.log.info(f"[Session Info] {username}: no last_activity, remaining={effective_timeout}s ({effective_timeout/3600:.1f}h)")

            response["extensions_used_hours"] = extensions_used_hours
            response["extensions_available_hours"] = max(0, max_extension_hours - extensions_used_hours)
        else:
            response["last_activity"] = None
            response["time_remaining_seconds"] = None
            response["extensions_used_hours"] = 0
            response["extensions_available_hours"] = max_extension_hours

        self.log.info(f"[Session Info] {username}: culler_enabled={culler_enabled}, active={server_active}, extensions_used={response.get('extensions_used_hours', 0)}h, available={response.get('extensions_available_hours', 0)}h")
        self.finish(response)


class ExtendSessionHandler(BaseHandler):
    """Handler for extending user session by adding extension hours"""

    @web.authenticated
    async def post(self, username):
        """
        Extend a user's session by adding hours to the extension allowance

        POST /hub/api/users/{username}/extend-session
        Body: {"hours": 2}
        Returns: {
            "success": true,
            "message": "Session extended by 2 hours",
            "session_info": {
                "time_remaining_seconds": 7200,
                "extensions_used_hours": 6,
                "extensions_available_hours": 18
            }
        }
        """
        self.log.info(f"[Extend Session] API endpoint called for user: {username}")

        # Check permissions: user must be admin or requesting their own extension
        current_user = self.current_user
        if current_user is None:
            raise web.HTTPError(403, "Not authenticated")

        if not (current_user.admin or current_user.name == username):
            raise web.HTTPError(403, "Permission denied")

        # Parse request body
        try:
            body = self.request.body.decode('utf-8')
            data = json.loads(body) if body else {}
            hours = data.get('hours', 1)
            if not isinstance(hours, (int, float)) or hours <= 0:
                raise ValueError("Invalid hours value")
            hours = int(hours)
        except (json.JSONDecodeError, ValueError) as e:
            self.log.error(f"[Extend Session] Invalid request: {e}")
            self.set_status(400)
            return self.finish({"success": False, "error": "Invalid request. Hours must be a positive number."})

        # Get idle culler config
        import os
        culler_enabled = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_ENABLED", 0)) == 1
        timeout_seconds = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_TIMEOUT", 86400))
        max_extension_hours = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION", 24))

        if not culler_enabled:
            self.set_status(400)
            return self.finish({"success": False, "error": "Idle culler is not enabled"})

        # Get user and spawner
        user = self.find_user(username)
        if not user:
            raise web.HTTPError(404, "User not found")

        spawner = user.spawner
        if not spawner or not spawner.active:
            self.set_status(400)
            return self.finish({"success": False, "error": "Server is not running"})

        # Get current extension usage from spawner state
        current_state = spawner.orm_spawner.state or {}
        current_extensions = current_state.get('extension_hours_used', 0)
        available = max_extension_hours - current_extensions

        # Check if no hours available
        if available <= 0:
            self.log.warning(f"[Extend Session] {username}: DENIED - no extension hours available (used={current_extensions}h, max={max_extension_hours}h)")
            self.set_status(400)
            return self.finish({
                "success": False,
                "error": f"Maximum extension limit reached ({max_extension_hours} hours). No more extensions available."
            })

        # Truncate requested hours to available if needed
        truncated = False
        original_hours = hours
        if hours > available:
            hours = available
            truncated = True
            self.log.warning(f"[Extend Session] {username}: requested +{original_hours}h exceeds available ({available}h), truncating to +{hours}h")

        new_total_extensions = current_extensions + hours
        self.log.info(f"[Extend Session] {username}: requesting +{hours}h, current extensions={current_extensions}h, new total={new_total_extensions}h, max={max_extension_hours}h")

        # ADD hours to extension total (don't reset last_activity - preserve elapsed time)
        from datetime import datetime, timezone
        new_state = dict(current_state)
        new_state['extension_hours_used'] = new_total_extensions
        spawner.orm_spawner.state = new_state
        self.db.commit()

        # Calculate new time remaining: base timeout + ALL extensions - elapsed
        extension_seconds = new_total_extensions * 3600
        effective_timeout = timeout_seconds + extension_seconds
        # Use spawner.last_activity (not user - matches what idle culler uses)
        last_activity = spawner.orm_spawner.last_activity if spawner.orm_spawner else None
        if last_activity:
            now_utc = datetime.now(timezone.utc)
            last_activity_utc = last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity
            elapsed_seconds = (now_utc - last_activity_utc).total_seconds()
            time_remaining = max(0, int(effective_timeout - elapsed_seconds))
            self.log.info(f"[Extend Session] {username}: effective_timeout={effective_timeout}s ({effective_timeout/3600:.1f}h), elapsed={elapsed_seconds:.0f}s ({elapsed_seconds/3600:.1f}h), remaining={time_remaining}s ({time_remaining/3600:.1f}h)")
        else:
            time_remaining = effective_timeout
            self.log.info(f"[Extend Session] {username}: no last_activity, remaining={time_remaining}s ({time_remaining/3600:.1f}h)")

        self.log.info(f"[Extend Session] {username}: SUCCESS - added {hours}h, total extensions={new_total_extensions}h, remaining={time_remaining/3600:.1f}h")

        # Build response message with warning if truncated
        message = f"Added {hours} hour(s) to session"
        if truncated:
            message += f" (requested {original_hours}h, limited to available {hours}h)"

        response = {
            "success": True,
            "message": message,
            "truncated": truncated,
            "session_info": {
                "time_remaining_seconds": time_remaining,
                "extensions_used_hours": new_total_extensions,
                "extensions_available_hours": max_extension_hours - new_total_extensions
            }
        }

        self.finish(response)


class SettingsPageHandler(BaseHandler):
    """Handler for rendering the settings page (admin only, read-only)"""

    # Settings dictionary file path
    SETTINGS_DICT_PATH = "/srv/jupyterhub/settings_dictionary.yml"

    @web.authenticated
    async def get(self):
        """
        Render the settings page showing key environment variables

        GET /settings
        """
        current_user = self.current_user

        # Only admins can access settings
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this page")

        self.log.info(f"[Settings Page] Admin {current_user.name} accessed settings panel")

        # Load settings from YAML dictionary
        settings = self._load_settings()

        # Render the template
        html = self.render_template("settings.html", sync=True, user=current_user, settings=settings)
        self.finish(html)

    def _load_settings(self):
        """Load settings from YAML dictionary file and populate with env values"""
        import yaml

        settings = []

        try:
            with open(self.SETTINGS_DICT_PATH, 'r') as f:
                config = yaml.safe_load(f)

            # Categories are top-level keys in the YAML
            for category, items in config.items():
                # Skip comment lines (strings starting with #)
                if not isinstance(items, list):
                    continue

                for item in items:
                    name = item.get('name', '')
                    default = str(item.get('default', ''))
                    value = os.environ.get(name, default)

                    # Handle empty_display for empty values
                    if not value and 'empty_display' in item:
                        value = item['empty_display']

                    settings.append({
                        "category": category,
                        "name": name,
                        "value": value,
                        "description": item.get('description', '')
                    })

        except FileNotFoundError:
            self.log.error(f"[Settings Page] Settings dictionary not found: {self.SETTINGS_DICT_PATH}")
        except Exception as e:
            self.log.error(f"[Settings Page] Error loading settings dictionary: {e}")

        return settings


class ActivityPageHandler(BaseHandler):
    """Handler for rendering the activity monitoring page (admin only)"""

    @web.authenticated
    async def get(self):
        """
        Render the activity monitoring page

        GET /activity
        """
        current_user = self.current_user

        # Only admins can access activity monitoring
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this page")

        self.log.info(f"[Activity Page] Admin {current_user.name} accessed activity monitor")

        # Render the template
        html = self.render_template("activity.html", sync=True, user=current_user)
        self.finish(html)


class ActivityDataHandler(BaseHandler):
    """Handler for providing activity data via API"""

    @web.authenticated
    async def get(self):
        """
        Get activity data for all users (admin only)

        GET /hub/api/activity
        Returns: {
            "users": [
                {
                    "username": "konrad",
                    "server_active": true,
                    "cpu_percent": 12.5,
                    "memory_mb": 1234,
                    "memory_percent": 15.2,
                    "time_remaining_seconds": 85500,
                    "activity_score": 80,
                    "sample_count": 24,
                    "last_activity": "2026-01-20T10:30:00Z"
                }
            ],
            "timestamp": "2026-01-20T11:00:00Z",
            "sampling_status": "48 samples for 2 users"
        }
        """
        current_user = self.current_user

        # Only admins can access activity data
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this endpoint")

        # Lazy start background processes on first access
        sampler = ActivitySampler.get_instance()
        if sampler.periodic_callback is None:
            sampler.start(self.db, self.find_user)

        refresher = VolumeSizeRefresher.get_instance()
        if refresher.periodic_callback is None:
            refresher.start()

        self.log.info(f"[Activity Data] Admin {current_user.name} requested activity data")

        # Get idle culler config
        culler_enabled = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_ENABLED", 0)) == 1
        timeout_seconds = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_TIMEOUT", 86400))
        max_extension_hours = int(os.environ.get("JUPYTERHUB_IDLE_CULLER_MAX_EXTENSION", 24))

        # Get cached volume sizes (non-blocking, triggers background refresh if stale)
        volume_sizes = await get_volume_sizes_with_refresh()

        # Collect data for all users
        users_data = []
        active_users = []  # Track users needing Docker stats
        from jupyterhub import orm

        for orm_user in self.db.query(orm.User).all():
            user = self.find_user(orm_user.name)
            if not user:
                continue

            spawner = user.spawner
            server_active = spawner.active if spawner else False

            # Get volume size for this user (using encoded username)
            encoded_name = encode_username_for_docker(user.name)
            user_volume_size = volume_sizes.get(encoded_name, 0)

            user_data = {
                "username": user.name,
                "server_active": server_active,
                "recently_active": False,  # True if activity within INACTIVE_AFTER threshold
                "cpu_percent": None,
                "memory_mb": None,
                "memory_percent": None,
                "time_remaining_seconds": None,
                "activity_score": None,
                "sample_count": 0,
                "last_activity": None,
                "volume_size_mb": user_volume_size
            }

            # Get activity score
            score, sample_count = calculate_activity_score(user.name)
            user_data["activity_score"] = score
            user_data["sample_count"] = sample_count

            # Get last_activity for ALL users (not just active servers)
            inactive_threshold = get_inactive_after_seconds()
            now = datetime.now(timezone.utc)

            if spawner and spawner.orm_spawner:
                last_activity = spawner.orm_spawner.last_activity
                if last_activity:
                    last_activity_utc = last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity
                    elapsed_seconds = (now - last_activity_utc).total_seconds()

                    user_data["last_activity"] = last_activity_utc.isoformat()
                    # Only mark as recently_active if server is actually running
                    user_data["recently_active"] = server_active and elapsed_seconds <= inactive_threshold

                    # Get time remaining (from idle culler) - only for active servers
                    if server_active and culler_enabled:
                        spawner_state = spawner.orm_spawner.state or {}
                        extensions_used_hours = spawner_state.get('extension_hours_used', 0)
                        extension_seconds = extensions_used_hours * 3600
                        effective_timeout = timeout_seconds + extension_seconds
                        time_remaining_seconds = max(0, effective_timeout - elapsed_seconds)
                        user_data["time_remaining_seconds"] = int(time_remaining_seconds)

            if server_active:
                # Mark for async Docker stats fetch
                active_users.append((user, spawner, user_data))

            # Include users with active servers, activity samples, or any last_activity
            if server_active or sample_count > 0 or user_data["last_activity"]:
                users_data.append(user_data)

        # Fetch Docker stats in parallel (non-blocking)
        if active_users:
            stats_tasks = [get_container_stats_async(u.name) for u, s, d in active_users]
            stats_results = await asyncio.gather(*stats_tasks, return_exceptions=True)

            for (user, spawner, user_data), stats in zip(active_users, stats_results):
                if stats and not isinstance(stats, Exception):
                    user_data["cpu_percent"] = stats["cpu_percent"]
                    user_data["memory_mb"] = stats["memory_mb"]
                    user_data["memory_percent"] = stats["memory_percent"]

        # Sort: active servers first, then by activity score descending
        users_data.sort(key=lambda u: (not u["server_active"], -(u["activity_score"] or 0)))

        response = {
            "users": users_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sampling_status": get_activity_sampling_status(),
            "inactive_after_seconds": get_inactive_after_seconds()
        }

        self.log.info(f"[Activity Data] Returning data for {len(users_data)} user(s)")
        self.finish(response)


class ActivityResetHandler(BaseHandler):
    """Handler for resetting activity data (admin only)"""

    @web.authenticated
    async def post(self):
        """
        Reset all activity data

        POST /hub/api/activity/reset
        Returns: {"success": true, "deleted": 123}
        """
        current_user = self.current_user

        # Only admins can reset activity data
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can reset activity data")

        self.log.info(f"[Activity Reset] Admin {current_user.name} requested activity reset")

        deleted = reset_all_activity_data()

        self.log.info(f"[Activity Reset] Deleted {deleted} samples")
        self.finish({"success": True, "deleted": deleted})


class ActivitySampleHandler(BaseHandler):
    """Handler for triggering activity sampling (admin only)"""

    @web.authenticated
    async def post(self):
        """
        Record activity samples for ALL users (active and offline).

        POST /hub/api/activity/sample
        Returns: {"success": true, "total": 7, "active": 3, "inactive": 1, "offline": 3}

        Can be called by cron job or scheduler to periodically record samples.
        """
        current_user = self.current_user

        # Only admins can trigger activity sampling
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can trigger activity sampling")

        self.log.info(f"[Activity Sample] Admin {current_user.name} triggered activity sampling")

        counts = record_samples_for_all_users(self.db, self.find_user)

        self.log.info(f"[Activity Sample] Recorded {counts['total']} samples: "
                      f"{counts['active']} active, {counts['inactive']} inactive, {counts['offline']} offline")
        self.finish({"success": True, **counts})
