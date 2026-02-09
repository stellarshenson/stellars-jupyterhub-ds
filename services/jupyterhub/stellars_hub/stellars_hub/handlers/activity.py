"""Handlers for activity monitoring page and API."""

import asyncio
from datetime import datetime, timezone

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..activity.helpers import (
    calculate_activity_score,
    get_activity_sampling_status,
    get_inactive_after_seconds,
    record_samples_for_all_users,
    reset_all_activity_data,
)
from ..docker_utils import encode_username_for_docker, get_container_stats_async
from ..volume_cache import VolumeSizeRefresher, get_volume_sizes_with_refresh


class ActivityPageHandler(BaseHandler):
    """Handler for rendering the activity monitoring page (admin only)."""

    @web.authenticated
    async def get(self):
        """Render the activity monitoring page."""
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this page")

        self.log.info(f"[Activity Page] Admin {current_user.name} accessed activity monitor")
        html = self.render_template("activity.html", sync=True, user=current_user)
        self.finish(html)


class ActivityDataHandler(BaseHandler):
    """Handler for providing activity data via API."""

    @web.authenticated
    async def get(self):
        """Get activity data for all users (admin only)."""
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this endpoint")

        # Lazy start volume size refresher on first access
        refresher = VolumeSizeRefresher.get_instance()
        if refresher.periodic_callback is None:
            refresher.start()

        self.log.info(f"[Activity Data] Admin {current_user.name} requested activity data")

        stellars_config = self.settings['stellars_config']
        culler_enabled = stellars_config['idle_culler_enabled'] == 1
        timeout_seconds = stellars_config['idle_culler_timeout']
        max_extension_hours = stellars_config['idle_culler_max_extension']

        volume_sizes = await get_volume_sizes_with_refresh()

        users_data = []
        active_users = []
        from jupyterhub import orm

        for orm_user in self.db.query(orm.User).all():
            user = self.find_user(orm_user.name)
            if not user:
                continue

            spawner = user.spawner
            server_active = spawner.active if spawner else False

            encoded_name = encode_username_for_docker(user.name)
            user_volume_data = volume_sizes.get(encoded_name, {"total": 0, "volumes": {}})
            user_volume_size = user_volume_data.get("total", 0)
            user_volume_breakdown = user_volume_data.get("volumes", {})

            # Get authorization status from NativeAuthenticator
            is_authorized = False
            try:
                from sqlalchemy import text
                result = self.db.execute(
                    text("SELECT is_authorized FROM users_info WHERE username = :username"),
                    {"username": user.name},
                ).fetchone()
                if result:
                    is_authorized = bool(result[0])
            except Exception:
                pass

            user_data = {
                "username": user.name,
                "is_authorized": is_authorized,
                "server_active": server_active,
                "recently_active": False,
                "cpu_percent": None,
                "memory_mb": None,
                "memory_percent": None,
                "time_remaining_seconds": None,
                "activity_score": None,
                "sample_count": 0,
                "last_activity": None,
                "volume_size_mb": user_volume_size,
                "volume_breakdown": user_volume_breakdown,
            }

            score, sample_count = calculate_activity_score(user.name)
            user_data["activity_score"] = score
            user_data["sample_count"] = sample_count

            inactive_threshold = get_inactive_after_seconds()
            now = datetime.now(timezone.utc)

            if spawner and spawner.orm_spawner:
                last_activity = spawner.orm_spawner.last_activity
                if last_activity:
                    last_activity_utc = last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity
                    elapsed_seconds = (now - last_activity_utc).total_seconds()

                    user_data["last_activity"] = last_activity_utc.isoformat()
                    user_data["recently_active"] = server_active and elapsed_seconds <= inactive_threshold

                    if server_active and culler_enabled:
                        spawner_state = spawner.orm_spawner.state or {}
                        extensions_used_hours = spawner_state.get('extension_hours_used', 0)
                        extension_seconds = extensions_used_hours * 3600
                        effective_timeout = timeout_seconds + extension_seconds
                        time_remaining_seconds = max(0, effective_timeout - elapsed_seconds)
                        user_data["time_remaining_seconds"] = int(time_remaining_seconds)

            if server_active:
                active_users.append((user, spawner, user_data))

            if server_active or sample_count > 0 or user_data["last_activity"]:
                users_data.append(user_data)

        # Fetch Docker stats in parallel
        if active_users:
            stats_tasks = [get_container_stats_async(u.name) for u, s, d in active_users]
            stats_results = await asyncio.gather(*stats_tasks, return_exceptions=True)

            for (user, spawner, user_data), stats in zip(active_users, stats_results):
                if stats and not isinstance(stats, Exception):
                    user_data["cpu_percent"] = stats["cpu_percent"]
                    user_data["memory_mb"] = stats["memory_mb"]
                    user_data["memory_percent"] = stats["memory_percent"]

        users_data.sort(key=lambda u: (not u["server_active"], -(u["activity_score"] or 0)))

        response = {
            "users": users_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sampling_status": get_activity_sampling_status(),
            "inactive_after_seconds": get_inactive_after_seconds(),
        }

        self.log.info(f"[Activity Data] Returning data for {len(users_data)} user(s)")
        self.finish(response)


class ActivityResetHandler(BaseHandler):
    """Handler for resetting activity data (admin only)."""

    @web.authenticated
    async def post(self):
        """Reset all activity data."""
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can reset activity data")

        self.log.info(f"[Activity Reset] Admin {current_user.name} requested activity reset")
        deleted = reset_all_activity_data()

        self.log.info(f"[Activity Reset] Deleted {deleted} samples")
        self.finish({"success": True, "deleted": deleted})


class ActivitySampleHandler(BaseHandler):
    """Handler for triggering activity sampling (admin only)."""

    @web.authenticated
    async def post(self):
        """Record activity samples for ALL users (active and offline)."""
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can trigger activity sampling")

        self.log.info(f"[Activity Sample] Admin {current_user.name} triggered activity sampling")
        counts = record_samples_for_all_users(self.db, self.find_user)

        self.log.info(
            f"[Activity Sample] Recorded {counts['total']} samples: "
            f"{counts['active']} active, {counts['inactive']} inactive, {counts['offline']} offline"
        )
        self.finish({"success": True, **counts})
