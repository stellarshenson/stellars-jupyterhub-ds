"""Handlers for session info and extension."""

import json
from datetime import datetime, timezone

from jupyterhub.handlers import BaseHandler
from tornado import web


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
            spawner_state = spawner.orm_spawner.state or {}
            extensions_used_hours = spawner_state.get('extension_hours_used', 0)
            extension_seconds = extensions_used_hours * 3600
            effective_timeout = timeout_seconds + extension_seconds

            last_activity = spawner.orm_spawner.last_activity if spawner.orm_spawner else None
            if last_activity:
                now = datetime.now(timezone.utc)
                last_activity_utc = last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity
                elapsed_seconds = (now - last_activity_utc).total_seconds()
                time_remaining_seconds = max(0, effective_timeout - elapsed_seconds)

                response["last_activity"] = last_activity_utc.isoformat()
                response["time_remaining_seconds"] = int(time_remaining_seconds)
            else:
                response["last_activity"] = None
                response["time_remaining_seconds"] = effective_timeout

            response["extensions_used_hours"] = extensions_used_hours
            response["extensions_available_hours"] = max(0, max_extension_hours - extensions_used_hours)
        else:
            response["last_activity"] = None
            response["time_remaining_seconds"] = None
            response["extensions_used_hours"] = 0
            response["extensions_available_hours"] = max_extension_hours

        self.finish(response)


class ExtendSessionHandler(BaseHandler):
    """Handler for extending user session."""

    @web.authenticated
    async def post(self, username):
        """Extend a user's session by adding hours to the extension allowance."""
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

        current_state = spawner.orm_spawner.state or {}
        current_extensions = current_state.get('extension_hours_used', 0)
        available = max_extension_hours - current_extensions

        if available <= 0:
            self.log.warning(f"[Extend Session] {username}: DENIED - no extension hours available (used={current_extensions}h, max={max_extension_hours}h)")
            self.set_status(400)
            return self.finish({
                "success": False,
                "error": f"Maximum extension limit reached ({max_extension_hours} hours). No more extensions available.",
            })

        truncated = False
        original_hours = hours
        if hours > available:
            hours = available
            truncated = True

        new_total_extensions = current_extensions + hours

        new_state = dict(current_state)
        new_state['extension_hours_used'] = new_total_extensions
        spawner.orm_spawner.state = new_state
        self.db.commit()

        extension_seconds = new_total_extensions * 3600
        effective_timeout = timeout_seconds + extension_seconds
        last_activity = spawner.orm_spawner.last_activity if spawner.orm_spawner else None
        if last_activity:
            now_utc = datetime.now(timezone.utc)
            last_activity_utc = last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity
            elapsed_seconds = (now_utc - last_activity_utc).total_seconds()
            time_remaining = max(0, int(effective_timeout - elapsed_seconds))
        else:
            time_remaining = effective_timeout

        self.log.info(f"[Extend Session] {username}: SUCCESS - added {hours}h, total extensions={new_total_extensions}h, remaining={time_remaining/3600:.1f}h")

        message = f"Added {hours} hour(s) to session"
        if truncated:
            message += f" (requested {original_hours}h, limited to available {hours}h)"

        self.finish({
            "success": True,
            "message": message,
            "truncated": truncated,
            "session_info": {
                "time_remaining_seconds": time_remaining,
                "extensions_used_hours": new_total_extensions,
                "extensions_available_hours": max_extension_hours - new_total_extensions,
            },
        })
