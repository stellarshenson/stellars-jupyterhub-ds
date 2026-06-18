"""Handlers for activity monitoring page and API."""

from datetime import datetime, timezone

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..activity.helpers import (
    calculate_activity_score,
    calculate_avg_active_hours,
    get_activity_sampling_status,
    get_activity_target_hours,
    get_inactive_after_seconds,
    record_samples_for_all_users,
    reset_all_activity_data,
)


def _host_total_memory_mb():
    """Total physical host RAM in MB - the denominator for the "% of host" memory
    figure (a mem-limited user's memory_total_mb is their ceiling, not the host).
    None on any read failure (honest empty, never fabricated)."""
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024 * 1024), 1)
    except Exception:
        return None
from ..docker_utils import encode_username_for_docker, newer_lab_image_available
from ..container_size_cache import get_container_sizes_with_refresh
from ..container_stats_cache import get_container_stats_with_refresh
from ..gpu_cache import get_gpu_utilization_with_refresh
from ..hydrate import start_activity_refreshers
from ..idle_culler import calc_ceiling, remaining_seconds_for
from ..volume_cache import get_volume_sizes_with_refresh


class ActivityDataHandler(BaseHandler):
    """Handler for providing activity data via API."""

    @web.authenticated
    async def get(self):
        """Get activity data for all users (admin only)."""
        current_user = self.current_user
        if not current_user.admin:
            raise web.HTTPError(403, "Only administrators can access this endpoint")

        # Ensure the background refreshers are running (idempotent). Startup
        # hydration normally starts them at boot; this is the fallback so a direct
        # /activity hit still works if hydration was skipped. GPU utilisation is
        # gated on a non-empty inventory (enumerated once at startup).
        start_activity_refreshers((self.settings.get('stellars_config') or {}).get('gpu_list'))

        self.log.info(f"[Activity Data] Admin {current_user.name} requested activity data")

        stellars_config = self.settings['stellars_config']
        culler_enabled = stellars_config['idle_culler_enabled'] == 1
        timeout_seconds = stellars_config['idle_culler_timeout']
        max_extension_hours = stellars_config['idle_culler_max_extension']

        volume_sizes = get_volume_sizes_with_refresh()
        container_sizes = get_container_sizes_with_refresh()

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
            user_ctr_size = container_sizes.get(encoded_name, {})

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
                "cpu_cores": None,
                "cpu_cores_limited": False,
                "memory_mb": None,
                "memory_percent": None,
                "memory_total_mb": None,
                "memory_limited": False,
                "time_remaining_seconds": None,
                "timeout_seconds": None,  # base idle-culler TTL (the "standard limit"); configurable, exposed so the UI never hardcodes it
                "server_started": None,
                "lab_image_upgrade_available": False,
                "activity_score": None,
                "activity_hours": None,
                "sample_count": 0,
                "last_activity": None,
                "volume_size_mb": user_volume_size,
                "volume_breakdown": user_volume_breakdown,
                "container_size_rw_mb": user_ctr_size.get("size_rw_mb"),
                "container_size_rootfs_mb": user_ctr_size.get("size_rootfs_mb"),
            }

            score, sample_count = calculate_activity_score(user.name)
            user_data["activity_score"] = score
            user_data["activity_hours"] = calculate_avg_active_hours(user.name)
            user_data["sample_count"] = sample_count

            inactive_threshold = get_inactive_after_seconds()
            now = datetime.now(timezone.utc)

            if spawner and spawner.orm_spawner:
                # server uptime = when the spawner (container) started
                started = getattr(spawner.orm_spawner, 'started', None)
                if server_active and started:
                    started_utc = started.replace(tzinfo=timezone.utc) if started.tzinfo is None else started
                    user_data["server_started"] = started_utc.isoformat()

                last_activity = spawner.orm_spawner.last_activity
                if last_activity:
                    last_activity_utc = last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity
                    elapsed_seconds = (now - last_activity_utc).total_seconds()

                    user_data["last_activity"] = last_activity_utc.isoformat()
                    user_data["recently_active"] = server_active and elapsed_seconds <= inactive_threshold

                    if server_active and culler_enabled:
                        ceiling = calc_ceiling(timeout_seconds, max_extension_hours)
                        user_data["time_remaining_seconds"] = remaining_seconds_for(
                            spawner.orm_spawner, timeout_seconds, ceiling, now
                        )
                        user_data["timeout_seconds"] = timeout_seconds

            if server_active:
                active_users.append((user, spawner, user_data))

            if server_active or sample_count > 0 or user_data["last_activity"]:
                users_data.append(user_data)

        # Per-user CPU/memory from the warm, activity-gated snapshot - no
        # synchronous docker-stats gather on the request path (that was the 5-6s
        # lag). The refresh samples ONLY recently-active users (the kernel's
        # last_activity signal); idle-but-running containers keep their last value
        # and are never polled, and an all-idle deployment makes no docker calls.
        if active_users:
            # configured lab image the upgrade check compares each container against
            _lab_image = stellars_config.get('lab_image', '')
            active_encoded = {
                encode_username_for_docker(u.name)
                for u, s, d in active_users
                if d.get("recently_active")
            }
            stats_by_user = get_container_stats_with_refresh(active_encoded)

            for (user, spawner, user_data) in active_users:
                stats = stats_by_user.get(encode_username_for_docker(user.name))
                if stats:
                    user_data["cpu_percent"] = stats["cpu_percent"]
                    user_data["cpu_cores"] = stats.get("cpu_cores")
                    user_data["cpu_cores_limited"] = stats.get("cpu_cores_limited", False)
                    user_data["memory_mb"] = stats["memory_mb"]
                    user_data["memory_percent"] = stats["memory_percent"]
                    user_data["memory_total_mb"] = stats.get("memory_total_mb")
                    user_data["memory_limited"] = stats.get("memory_limited", False)
                    user_data["lab_image_upgrade_available"] = newer_lab_image_available(_lab_image, stats.get("image_id"))

        users_data.sort(key=lambda u: (not u["server_active"], -(u["activity_score"] or 0)))

        container_max = stellars_config.get('container_max_extra_space_mb', 10240)
        volume_max = stellars_config.get('volume_max_total_size_mb', 51200)
        memory_max = stellars_config.get('memory_max_usage_mb', 0)

        # Host GPU inventory enumerated once at startup (cached read, no container
        # spin per request); empty when GPU is disabled or none are present. Live
        # per-GPU utilisation is sampled in the background by GpuUtilizationRefresher
        # (querying the GPU-info sidecar) and merged in by index - so each device
        # carries its real load, used memory and the processes holding it when a
        # sample exists, and falls back to inventory-only otherwise.
        gpu_list = stellars_config.get('gpu_list', []) or []
        gpu_util = get_gpu_utilization_with_refresh() if gpu_list else {}
        gpus = []
        for g in gpu_list:
            idx = g.get("index")
            entry = {
                "index": idx,
                "name": g.get("name"),
                "uuid": g.get("uuid"),
                "memory_mb": g.get("memory_mb", 0),
            }
            sample = gpu_util.get(str(idx)) if idx is not None else None
            if sample:
                entry["utilization"] = sample.get("utilization")
                entry["memory_used_mb"] = sample.get("memory_used_mb")
                entry["temperature_c"] = sample.get("temperature_c")
                entry["power_w"] = sample.get("power_w")
                entry["processes"] = sample.get("processes", [])
            gpus.append(entry)

        # Lab Container page facts: the spawn image and the standard per-user
        # volumes every lab gets (cached config reads). Shared/extra volumes are
        # granted per group via the volume-mounts policy, not platform-wide here.
        lab_image = stellars_config.get('lab_image', '')
        lab_volumes = stellars_config.get('lab_volumes', []) or []

        response = {
            "users": users_data,
            "container_max_extra_space_mb": container_max,
            "volume_max_total_size_mb": volume_max,
            "memory_max_usage_mb": memory_max,
            "memory_host_total_mb": _host_total_memory_mb(),
            "activity_target_hours": get_activity_target_hours(),
            "gpus": gpus,
            "lab_image": lab_image,
            "lab_volumes": lab_volumes,
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
