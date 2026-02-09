"""Background activity sampler using Tornado PeriodicCallback."""

import asyncio
import logging
import os
from datetime import datetime, timezone

from .monitor import ActivityMonitor

log = logging.getLogger('jupyterhub.custom_handlers')


class ActivitySampler:
    """Background scheduler that periodically samples activity for ALL users."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.periodic_callback = None
        self.db = None
        self.find_user = None
        self.interval_seconds = int(os.environ.get('JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL', 600))
        log.info(f"[ActivitySampler] Initialized with interval={self.interval_seconds}s")

    def start(self, db, find_user):
        """Start the periodic sampler."""
        from tornado.ioloop import PeriodicCallback
        self.db = db
        self.find_user = find_user

        if self.periodic_callback is not None:
            log.info("[ActivitySampler] Already running")
            return

        interval_ms = self.interval_seconds * 1000
        self.periodic_callback = PeriodicCallback(self._sample_tick, interval_ms)
        self.periodic_callback.start()
        log.info(f"[ActivitySampler] Started - sampling every {self.interval_seconds}s")

        asyncio.get_event_loop().call_soon(lambda: asyncio.ensure_future(self._sample_tick_async()))

    def stop(self):
        """Stop the periodic sampler."""
        if self.periodic_callback is not None:
            self.periodic_callback.stop()
            self.periodic_callback = None
            log.info("[ActivitySampler] Stopped")

    def _sample_tick(self):
        asyncio.ensure_future(self._sample_tick_async())

    async def _sample_tick_async(self):
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
        except Exception as e:
            log.info(f"[ActivitySampler] Error during sampling: {e}")


def start_activity_sampler(db, find_user):
    """Start the background activity sampler."""
    sampler = ActivitySampler.get_instance()
    sampler.start(db, find_user)
