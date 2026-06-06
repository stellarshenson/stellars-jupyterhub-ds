"""Handlers for session info and extension.

The session-extension calculations live in `stellars_hub_services.idle_culler`
(single source of truth shared with the in-hub culler and the activity
dashboard). The model is a ceiling-bounded cull deadline stored in
`spawner.state['cull_at']`; see that module's docstring.
"""

import json
from datetime import datetime, timedelta, timezone

from jupyterhub.handlers import BaseHandler
from tornado import web

from stellars_hub_services.idle_culler import (
    calc_available_hours,
    calc_ceiling,
    calc_extended_remaining,
    remaining_seconds_for,
)

__all__ = [
    "SessionInfoHandler",
    "ExtendSessionHandler",
]


class SessionInfoHandler(BaseHandler):
    """Handler for getting session info including idle culler status."""

    @web.authenticated
    async def get(self, username):
        """Get session info for a user's server."""
        current_user = self.current_user
        if current_user is None:
            raise web.HTTPError(403, "Not authenticated")
        if not (current_user.admin or current_user.name == username):
            raise web.HTTPError(403, "Permission denied")

        stellars_config = self.settings['stellars_config']
        culler_enabled = stellars_config['idle_culler_enabled'] == 1
        timeout_seconds = stellars_config['idle_culler_timeout']
        max_extension_hours = stellars_config['idle_culler_max_extension']

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
            ceiling = calc_ceiling(timeout_seconds, max_extension_hours)
            now = datetime.now(timezone.utc)
            remaining = remaining_seconds_for(spawner.orm_spawner, timeout_seconds, ceiling, now)

            last_activity = spawner.orm_spawner.last_activity if spawner.orm_spawner else None
            response["last_activity"] = (
                (last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity).isoformat()
                if last_activity else None
            )
            response["time_remaining_seconds"] = remaining
            response["extensions_available_hours"] = calc_available_hours(remaining, ceiling)
        else:
            response["last_activity"] = None
            response["time_remaining_seconds"] = None
            response["extensions_available_hours"] = max_extension_hours

        self.finish(response)


class ExtendSessionHandler(BaseHandler):
    """Handler for extending user session."""

    @web.authenticated
    async def post(self, username):
        """Extend a user's session by pushing the cull deadline out, capped at the ceiling."""
        current_user = self.current_user
        if current_user is None:
            raise web.HTTPError(403, "Not authenticated")
        if not (current_user.admin or current_user.name == username):
            raise web.HTTPError(403, "Permission denied")

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

        stellars_config = self.settings['stellars_config']
        culler_enabled = stellars_config['idle_culler_enabled'] == 1
        timeout_seconds = stellars_config['idle_culler_timeout']
        max_extension_hours = stellars_config['idle_culler_max_extension']

        if not culler_enabled:
            self.set_status(400)
            return self.finish({"success": False, "error": "Idle culler is not enabled"})

        user = self.find_user(username)
        if not user:
            raise web.HTTPError(404, "User not found")

        spawner = user.spawner
        if not spawner or not spawner.active:
            self.set_status(400)
            return self.finish({"success": False, "error": "Server is not running"})

        ceiling = calc_ceiling(timeout_seconds, max_extension_hours)
        now = datetime.now(timezone.utc)
        remaining = remaining_seconds_for(spawner.orm_spawner, timeout_seconds, ceiling, now)
        available = calc_available_hours(remaining, ceiling)

        if available <= 0:
            self.log.warning(f"[Extend Session] {username}: DENIED - at ceiling (remaining={remaining/3600:.1f}h, ceiling={ceiling/3600:.0f}h)")
            self.set_status(400)
            return self.finish({
                "success": False,
                "error": f"Session already at maximum ({ceiling // 3600}h). Wait for time to elapse before extending.",
            })

        truncated = False
        original_hours = hours
        if hours > available:
            hours = available
            truncated = True

        # "Max means max": taking the full whole-hour offer lands remaining
        # exactly on the ceiling (no sub-hour shortfall from the floored offer).
        maxed = hours >= available
        new_remaining = calc_extended_remaining(remaining, hours, ceiling, maxed)

        # Persist the deadline; drop the legacy budget key so this server runs on
        # the deadline model from now on.
        new_state = dict(spawner.orm_spawner.state or {})
        new_state['cull_at'] = (now + timedelta(seconds=new_remaining)).isoformat()
        new_state.pop('extension_hours_used', None)
        spawner.orm_spawner.state = new_state
        self.db.commit()

        new_available = calc_available_hours(new_remaining, ceiling)

        self.log.info(f"[Extend Session] {username}: SUCCESS - added {hours}h, remaining={new_remaining/3600:.1f}h (ceiling={ceiling//3600}h)")

        if maxed:
            message = f"Session topped up to maximum ({ceiling // 3600}h)"
        else:
            message = f"Added {hours} hour(s) to session"
            if truncated:
                message += f" (requested {original_hours}h, limited to available {hours}h)"

        self.finish({
            "success": True,
            "message": message,
            "truncated": truncated,
            "session_info": {
                "time_remaining_seconds": new_remaining,
                "extensions_available_hours": new_available,
            },
        })
