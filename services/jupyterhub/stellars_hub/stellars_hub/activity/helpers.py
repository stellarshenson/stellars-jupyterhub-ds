"""Convenience functions for activity monitoring (use singleton)."""

import logging
from datetime import datetime, timezone

from .monitor import ActivityMonitor

log = logging.getLogger('jupyterhub.custom_handlers')


def record_activity_sample(username, last_activity):
    return ActivityMonitor.get_instance().record_sample(username, last_activity)


def calculate_activity_score(username):
    return ActivityMonitor.get_instance().get_score(username)


def get_activity_sampling_status():
    return ActivityMonitor.get_instance().get_status()


def get_inactive_after_seconds():
    """Get the inactive threshold in seconds."""
    return ActivityMonitor.get_instance().inactive_after_minutes * 60


def rename_activity_user(old_username, new_username):
    return ActivityMonitor.get_instance().rename_user(old_username, new_username)


def delete_activity_user(username):
    return ActivityMonitor.get_instance().delete_user(username)


def initialize_activity_for_user(username):
    """Initialize activity tracking for a new user.

    Records an initial inactive sample so the user appears in the Activity Monitor
    with 0% activity rather than '--'.
    """
    return ActivityMonitor.get_instance().record_sample(username, last_activity=None)


def reset_all_activity_data():
    """Reset all activity data (delete all samples)."""
    return ActivityMonitor.get_instance().reset_all()


def record_samples_for_all_users(db, find_user_func):
    """Record activity samples for ALL users (active and offline).

    Args:
        db: JupyterHub database session (handler.db)
        find_user_func: Function to find user by name (handler.find_user)

    Returns:
        dict with counts: {'total': N, 'active': N, 'inactive': N, 'offline': N}
    """
    from jupyterhub import orm

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

        last_activity = None
        if spawner and spawner.orm_spawner:
            last_activity = spawner.orm_spawner.last_activity
            if last_activity and last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)

        monitor.record_sample(user.name, last_activity)
        counts['total'] += 1

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

    monitor.log_activity_tick(
        counts['total'],
        counts['active'],
        counts['inactive'],
        counts['offline'],
    )

    return counts
