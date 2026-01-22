#!/usr/bin/env python3
"""
Activity Sampler Service for JupyterHub

Runs as a JupyterHub managed service to periodically sample user activity.
Uses JupyterHub REST API to fetch user data and records samples to a separate
SQLite database for activity scoring.

This service is independent of page views - it starts with JupyterHub and runs
continuously in the background.

Environment Variables:
    JUPYTERHUB_API_TOKEN: API token (provided by JupyterHub when running as service)
    JUPYTERHUB_API_URL: Hub API URL (provided by JupyterHub)
    JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL: Sampling interval in seconds (default: 600)
    JUPYTERHUB_ACTIVITYMON_RETENTION_DAYS: Days to retain samples (default: 7)
    JUPYTERHUB_ACTIVITYMON_HALF_LIFE: Score decay half-life in hours (default: 24)
    JUPYTERHUB_ACTIVITYMON_INACTIVE_AFTER: Minutes before marking inactive (default: 60)
"""

import asyncio
import json
import logging
import math
import os
import sys
from datetime import datetime, timedelta, timezone

import aiohttp
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)1.1s %(asctime)s.%(msecs)03d %(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger('activity_sampler')

# Database model (must match custom_handlers.py)
ActivityBase = declarative_base()

class ActivitySample(ActivityBase):
    """Activity sample record - tracks user activity at a point in time"""
    __tablename__ = 'activity_samples'

    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, nullable=True)
    active = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index('ix_activity_user_time', 'username', 'timestamp'),
    )


class ActivitySamplerService:
    """
    Service that periodically samples user activity via JupyterHub API
    and records to activity database.
    """

    def __init__(self):
        # API configuration
        self.api_token = os.environ.get('JUPYTERHUB_API_TOKEN')
        self.api_url = os.environ.get('JUPYTERHUB_API_URL', 'http://127.0.0.1:8081/hub/api')

        # Sampling configuration
        self.sample_interval = int(os.environ.get('JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL', 600))
        self.retention_days = int(os.environ.get('JUPYTERHUB_ACTIVITYMON_RETENTION_DAYS', 7))
        self.half_life_hours = int(os.environ.get('JUPYTERHUB_ACTIVITYMON_HALF_LIFE', 24))
        self.inactive_after_minutes = int(os.environ.get('JUPYTERHUB_ACTIVITYMON_INACTIVE_AFTER', 60))

        # Database
        self.db_url = 'sqlite:////data/activity_samples.sqlite'
        self._engine = None
        self._session = None

        log.info(f"Config: interval={self.sample_interval}s, retention={self.retention_days}d, "
                 f"half_life={self.half_life_hours}h, inactive_after={self.inactive_after_minutes}m")

    def _init_db(self):
        """Initialize database connection"""
        if self._session is not None:
            return self._session

        try:
            self._engine = create_engine(self.db_url)
            ActivityBase.metadata.create_all(self._engine)
            Session = sessionmaker(bind=self._engine)
            self._session = Session()
            log.info(f"Database initialized: {self.db_url}")
            return self._session
        except Exception as e:
            log.error(f"Database init failed: {e}")
            return None

    async def fetch_users(self):
        """Fetch all users and their activity from JupyterHub API"""
        if not self.api_token:
            log.error("No API token available")
            return []

        headers = {'Authorization': f'token {self.api_token}'}
        url = f"{self.api_url}/users"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        log.error(f"API request failed: {resp.status}")
                        return []
                    return await resp.json()
        except Exception as e:
            log.error(f"Error fetching users: {e}")
            return []

    def record_sample(self, username, last_activity_str):
        """Record an activity sample for a user"""
        db = self._init_db()
        if db is None:
            return False

        try:
            now = datetime.now(timezone.utc)

            # Parse last_activity timestamp
            last_activity = None
            if last_activity_str:
                try:
                    # JupyterHub returns ISO format with Z suffix
                    last_activity = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass

            # User is "active" if last_activity is within INACTIVE_AFTER minutes
            active = False
            if last_activity:
                age_seconds = (now - last_activity).total_seconds()
                active = age_seconds <= (self.inactive_after_minutes * 60)

            # Insert new sample
            db.add(ActivitySample(
                username=username,
                timestamp=now,
                last_activity=last_activity,
                active=active
            ))
            db.commit()

            # Prune old samples for this user
            cutoff = now - timedelta(days=self.retention_days)
            deleted = db.query(ActivitySample).filter(
                ActivitySample.username == username,
                ActivitySample.timestamp < cutoff
            ).delete()
            if deleted > 0:
                db.commit()

            return True
        except Exception as e:
            log.error(f"Error recording sample for {username}: {e}")
            db.rollback()
            return False

    async def sample_all_users(self):
        """Fetch all users and record activity samples"""
        users = await self.fetch_users()
        if not users:
            log.warning("No users fetched")
            return

        counts = {'total': 0, 'active': 0, 'inactive': 0, 'offline': 0}
        now = datetime.now(timezone.utc)
        inactive_threshold = self.inactive_after_minutes * 60

        for user in users:
            username = user.get('name')
            if not username:
                continue

            # Get last_activity from user's server if running
            servers = user.get('servers', {})
            default_server = servers.get('', {})
            server_active = default_server.get('ready', False)

            # Use server's last_activity if available, else user's last_activity
            last_activity_str = default_server.get('last_activity') or user.get('last_activity')

            self.record_sample(username, last_activity_str)
            counts['total'] += 1

            # Count by status
            if server_active:
                if last_activity_str:
                    try:
                        last_activity = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
                        elapsed = (now - last_activity).total_seconds()
                        if elapsed <= inactive_threshold:
                            counts['active'] += 1
                        else:
                            counts['inactive'] += 1
                    except (ValueError, AttributeError):
                        counts['inactive'] += 1
                else:
                    counts['inactive'] += 1
            else:
                counts['offline'] += 1

        log.info(f"Sampled {counts['total']} users: {counts['active']} active, "
                 f"{counts['inactive']} inactive, {counts['offline']} offline")

    async def run(self):
        """Main run loop"""
        log.info(f"Starting activity sampler (interval: {self.sample_interval}s)")

        # Initial delay to let JupyterHub fully start
        await asyncio.sleep(5)

        while True:
            try:
                await self.sample_all_users()
            except Exception as e:
                log.error(f"Error in sampling loop: {e}")

            await asyncio.sleep(self.sample_interval)


def main():
    """Entry point"""
    service = ActivitySamplerService()
    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        log.info("Shutting down")
        sys.exit(0)


if __name__ == '__main__':
    main()
