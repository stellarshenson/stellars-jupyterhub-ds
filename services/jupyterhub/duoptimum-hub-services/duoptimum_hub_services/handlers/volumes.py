"""Handler for managing user volumes."""

import html
import json

import docker
from jupyterhub.handlers import BaseHandler
from tornado import web

from ..docker_utils import encode_username_for_docker
from ..event_log import record_event


class ManageVolumesHandler(BaseHandler):
    """Handler for managing user volumes."""

    def _check_auth_and_get_volumes(self, username):
        """Auth + Docker-client setup shared by GET and DELETE.

        Returns (user_volume_name_templates, encoded_username, docker_client) on
        success, or finishes the response and returns None on auth/client failure.
        """
        current_user = self.current_user
        if current_user is None:
            self.log.warning("[Manage Volumes] Authentication failed - no current user")
            raise web.HTTPError(403, "Not authenticated")
        if not (current_user.admin or current_user.name == username):
            self.log.warning(
                f"[Manage Volumes] Permission denied - user {current_user.name} "
                f"attempted to manage {username}'s volumes"
            )
            raise web.HTTPError(403, "Permission denied")
        templates = self.settings['stellars_config']['user_volume_name_templates']
        encoded = encode_username_for_docker(username)
        try:
            client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        except Exception as e:
            self.log.error(f"[Manage Volumes] Failed to connect to Docker: {e}")
            self.send_error(500, "Failed to connect to Docker daemon")
            return None
        return templates, encoded, client

    async def get(self, username):
        """List the volumes that actually exist on disk for this user.

        GET /hub/api/users/{username}/manage-volumes
        Returns: {"volumes": [{"suffix", "name", "description"}, ...]}

        DockerSpawner creates per-user volumes lazily on first spawn; querying
        Docker directly is the only reliable way to know which ones exist.
        """
        self.log.info(f"[Manage Volumes] List request for user: {username}")
        result = self._check_auth_and_get_volumes(username)
        if result is None:
            return
        templates, encoded, client = result
        # The platform settings_dictionary descriptions live in user_volumes
        # (list of {suffix, name_template, description}) - reach for that for
        # description text rather than re-parsing the templates dict.
        ui = self.settings['stellars_config'].get('user_volumes', None)
        descriptions = {v['suffix']: v.get('description', '') for v in (ui or [])}
        # suffix -> duoptimum-hub.volume.role, so the portal IDs each as a system volume by role
        roles = self.settings['stellars_config'].get('user_volume_roles', {}) or {}
        # label keys the hub stamped at spawn - read from env-sourced config, never a literal
        vol_role_key = self.settings['stellars_config'].get('volume_role_label_key', '')
        vol_desc_key = self.settings['stellars_config'].get('volume_description_label_key', '')

        existing = []
        for suffix, template in templates.items():
            volume_name = template.replace('{username}', encoded)
            try:
                vol = client.volumes.get(volume_name)
            except docker.errors.NotFound:
                continue
            except docker.errors.APIError as e:
                self.log.warning(f"[Manage Volumes] Docker error checking {volume_name}: {e}")
                continue
            # Self-describing volume: read role + description off the labels the hub stamped
            # at spawn; fall back to settings for legacy (pre-label) volumes.
            labels = (vol.attrs.get('Labels') or {})
            existing.append({
                'suffix': suffix,
                'name': volume_name,
                'description': (labels.get(vol_desc_key) if vol_desc_key else None) or descriptions.get(suffix, ''),
                'role': (labels.get(vol_role_key) if vol_role_key else None) or roles.get(suffix, suffix),
            })

        # Standard shared volume: a policy-controlled row, listed (not resettable)
        # only when this user's group policy grants it and the volume exists. Its
        # presence is governed by group policy, not the user - never user-deletable.
        shared_row = self._shared_volume_row(username, client)
        if shared_row:
            existing.append(shared_row)

        client.close()
        self.log.info(f"[Manage Volumes] {username} has {len(existing)} volume(s) on disk")
        self.set_status(200)
        self.finish({'volumes': existing})

    def _shared_volume_row(self, username, client):
        """The policy-controlled /mnt/shared row, or None when not granted/absent.

        Resolves this user's group policy to learn whether the standard shared mount
        is granted; shows it as a non-resettable row so the user sees it exists but
        cannot reset it. Fail-safe: any error -> no row (never breaks the list)."""
        try:
            cfg = self.settings.get('stellars_config') or {}
            shared_name = cfg.get('shared_volume_name', '')
            if not shared_name:
                return None
            from ..groups_config import GroupsConfigManager
            from ..policy import resolve_policies
            user = self.find_user(username)
            group_names = [g.name for g in user.groups] if user else []
            resolved = resolve_policies(
                user_group_names=group_names,
                all_group_configs=GroupsConfigManager.get_instance().get_all_configs(),
                gpu_available=False, reserved_names=frozenset(), reserved_prefixes=(),
            )
            shared = resolved.get('shared_mount')
            if not (shared and shared.get('allow')):
                return None
            try:
                client.volumes.get(shared_name)  # only list it when it really exists
            except docker.errors.NotFound:
                return None
            mode = shared.get('mode') or 'rw'
            return {
                'suffix': 'shared',
                'name': shared_name,
                'description': f'Shared across all users (group policy, {"read-only" if mode == "ro" else "read-write"})',
                'role': 'shared',
                'policy_controlled': True,  # not user-resettable
            }
        except Exception as e:  # pragma: no cover - defensive, never break the list
            self.log.warning(f"[Manage Volumes] shared-volume row skipped for {username}: {e}")
            return None

    async def delete(self, username):
        """Delete selected user volumes (only when server is stopped).

        DELETE /hub/api/users/{username}/manage-volumes
        Body: {"volumes": ["home", "workspace", "cache"]}
        """
        self.log.info(f"[Manage Volumes] API endpoint called for user: {username}")

        current_user = self.current_user
        if current_user is None:
            self.log.warning("[Manage Volumes] Authentication failed - no current user")
            raise web.HTTPError(403, "Not authenticated")

        self.log.info(f"[Manage Volumes] Request from user: {current_user.name}, admin: {current_user.admin}")

        if not (current_user.admin or current_user.name == username):
            self.log.warning(f"[Manage Volumes] Permission denied - user {current_user.name} attempted to manage {username}'s volumes")
            raise web.HTTPError(403, "Permission denied")

        # Parse request body
        try:
            body = self.request.body.decode('utf-8')
            data = json.loads(body) if body else {}
            requested_volumes = data.get('volumes', [])
            self.log.info(f"[Manage Volumes] Requested volumes: {requested_volumes}")
        except Exception as e:
            self.log.error(f"[Manage Volumes] Failed to parse request body: {e}")
            return self.send_error(400, "Invalid request body")

        if not requested_volumes or not isinstance(requested_volumes, list):
            self.log.warning("[Manage Volumes] No volumes specified or invalid format")
            return self.send_error(400, "No volumes specified")

        user_volume_suffixes = self.settings['stellars_config']['user_volume_suffixes']
        # Source-of-truth name templates (still carry the {username} placeholder),
        # built once from DOCKER_SPAWNER_VOLUMES at config-load time. Avoids
        # the handler re-deriving the name pattern and drifting from spawner.
        user_volume_name_templates = self.settings['stellars_config']['user_volume_name_templates']
        valid_volumes = set(user_volume_suffixes)
        invalid_volumes = set(requested_volumes) - valid_volumes
        if invalid_volumes:
            self.log.warning(f"[Manage Volumes] Invalid volume types: {invalid_volumes}")
            return self.send_error(400, f"Invalid volume types: {invalid_volumes}")

        user = self.find_user(username)
        if not user:
            self.log.warning(f"[Manage Volumes] User {username} not found")
            return self.send_error(404, "User not found")

        spawner = user.spawner
        if spawner.active:
            self.log.warning("[Manage Volumes] Server is running, cannot reset volumes")
            return self.send_error(400, "Server must be stopped before resetting volumes")

        try:
            docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        except Exception as e:
            self.log.error(f"[Manage Volumes] Failed to connect to Docker: {e}")
            return self.send_error(500, "Failed to connect to Docker daemon")

        reset_volumes = []
        failed_volumes = []

        encoded_username = encode_username_for_docker(username)
        for volume_type in requested_volumes:
            volume_name = user_volume_name_templates[volume_type].replace('{username}', encoded_username)
            self.log.info(f"[Manage Volumes] Processing volume: {volume_name}")

            try:
                volume = docker_client.volumes.get(volume_name)
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

        # audit the destructive reset on the event log (best-effort; never raises).
        # Names the actor and, when an admin resets someone else's volumes, the owner.
        if reset_volumes:
            vols = html.escape(', '.join(reset_volumes))
            actor = html.escape(str(current_user.name))
            owner = html.escape(str(username))
            text = (
                f'<b>{actor}</b> reset volumes: {vols}'
                if current_user.name == username
                else f'<b>{actor}</b> reset <b>{owner}</b> volumes: {vols}'
            )
            record_event('volume', text)

        response = {
            "message": f"Successfully reset {len(reset_volumes)} volume(s)",
            "reset_volumes": reset_volumes,
            "failed_volumes": failed_volumes,
        }

        self.log.info(f"[Manage Volumes] Operation complete: {len(reset_volumes)} reset, {len(failed_volumes)} failed")
        self.set_status(200)
        self.finish(response)
