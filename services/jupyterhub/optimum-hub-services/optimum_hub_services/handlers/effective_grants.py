"""Handler for a user's effective (cross-group resolved) policy grants."""

from jupyterhub.handlers import BaseHandler
from tornado import web

from ..groups_config import GroupsConfigManager
from ..policy import effective_grants, resolve_policies


class EffectiveGrantsHandler(BaseHandler):
    """GET a user's effective capability grants, resolved across their groups.

    Self-or-admin (the same rule the profile/manage-volumes handlers use).
    Returns ``{grants: [{key, label, value, from}]}`` - the real resolved policy
    with each grant citing the winning group. Empty list when the user's groups
    grant nothing special (honest: the user runs on platform defaults).
    """

    def _authorize(self, username):
        current_user = self.current_user
        if current_user is None:
            raise web.HTTPError(403)
        if not current_user.admin and current_user.name != username:
            raise web.HTTPError(403, "You can only view your own grants")

    @web.authenticated
    async def get(self, username):
        self._authorize(username)
        from jupyterhub import orm

        orm_user = self.db.query(orm.User).filter(orm.User.name == username).first()
        if orm_user is None:
            raise web.HTTPError(404, f"User '{username}' not found")
        group_names = [g.name for g in orm_user.groups]

        try:
            all_configs = GroupsConfigManager.get_instance().get_all_configs()
        except Exception as e:
            self.log.error(f"[EffectiveGrants] Failed to load group configs: {e}")
            all_configs = []

        stellars_config = self.settings.get('stellars_config') or {}
        resolved = resolve_policies(
            user_group_names=group_names,
            all_group_configs=all_configs,
            gpu_available=stellars_config.get('gpu_available', False),
            reserved_names=stellars_config.get('reserved_env_var_names', frozenset()),
            reserved_prefixes=stellars_config.get('reserved_env_var_prefixes', ()),
        )
        # matched (priority-descending) is recomputed here for grant attribution;
        # resolve_policies derives the same internally but does not return it.
        matched = [c for c in all_configs if c.get('group_name') in set(group_names)]
        self.finish({'grants': effective_grants(matched, resolved)})
