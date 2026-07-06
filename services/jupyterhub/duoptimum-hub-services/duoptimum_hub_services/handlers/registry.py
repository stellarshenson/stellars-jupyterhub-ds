"""The platform's custom API/page route table, as a builder.

Extracted from jupyterhub_config.py (Batch 1 of the config simplification) so the
config file reads like configuration, not a 35-line handler table plus a 30-name
import block. registered_handlers() returns the (pattern, HandlerClass) list in
first-match-wins order; DuoptimumHub splices it into the hub handler list via the
c.DuoptimumHub.registered_handlers trait, in the same slot the deprecated
c.JupyterHub.extra_handlers used (after built-ins, before the /logo + /api 404
catch-alls; see app.py::splice_before_catch_alls).

The config appends portal_handlers() itself, NOT this builder, so the SPA catch-all
ordering stays explicit and visible at the call site. Routes are relative to /hub/.
"""

from . import (
    ActivityDataHandler,
    ActivityResetHandler,
    ActivitySampleHandler,
    ActiveServersHandler,
    BroadcastNotificationHandler,
    EffectiveGrantsHandler,
    EventsDataHandler,
    ExtendSessionHandler,
    GetUserCredentialsHandler,
    GroupsConfigHandler,
    GroupsCreateHandler,
    GroupsDataHandler,
    GroupsDeleteHandler,
    GroupsReorderHandler,
    HealthCheckHandler,
    LabReadyHandler,
    ManageVolumesHandler,
    NativeUserAuthorizationHandler,
    NativeUsersHandler,
    RestartServerHandler,
    SentNotificationsDataHandler,
    ServerLogsHandler,
    SessionInfoHandler,
    SettingsDataHandler,
    UserDisplayPreferencesHandler,
    UserEnvVarsHandler,
    UserForcePasswordChangeHandler,
    UserProfileHandler,
    UserProfilesListHandler,
    UserRenameHandler,
)


def registered_handlers():
    """Return the platform's custom route table (pattern, HandlerClass), in order.

    Order is first-match-wins, so it must match the shipped list byte-for-byte; the
    portal SPA catch-all is appended by the caller after this list.
    """
    return [
        (r'/api/users/([^/]+)/manage-volumes', ManageVolumesHandler),    # DELETE - reset user volumes
        (r'/api/users/([^/]+)/restart-server', RestartServerHandler),    # POST - Docker container restart
        (r'/api/users/([^/]+)/server/logs', ServerLogsHandler),          # GET - bounded container-log tail (Start page)
        (r'/api/users/([^/]+)/lab-ready', LabReadyHandler),              # GET - silent lab readiness probe (always 200)
        (r'/api/users/([^/]+)/session-info', SessionInfoHandler),        # GET - idle culler status
        (r'/api/users/([^/]+)/profile', UserProfileHandler),             # GET/PUT - first/last name + email
        (r'/api/users/([^/]+)/force-password-change', UserForcePasswordChangeHandler), # POST - admin set/clear force-pw gate
        (r'/api/users/([^/]+)/rename', UserRenameHandler),               # POST - admin rename (records who renamed whom)
        (r'/api/users/([^/]+)/display-preferences', UserDisplayPreferencesHandler), # GET/PUT - per-user UI options
        (r'/api/users/([^/]+)/env-vars', UserEnvVarsHandler),            # GET/PUT - per-user environment variables
        (r'/api/users/([^/]+)/effective-grants', EffectiveGrantsHandler), # GET - resolved group policy grants
        (r'/api/user-profiles', UserProfilesListHandler),                # GET - all profiles (Users-list sub-names)
        (r'/api/settings', SettingsDataHandler),                          # GET - platform settings (read-only JSON)
        (r'/api/events', EventsDataHandler),                              # GET - recent platform events (audit feed)
        (r'/api/users/([^/]+)/extend-session', ExtendSessionHandler),    # POST - extend idle timeout
        (r'/api/notifications/active-servers', ActiveServersHandler),     # GET - list running servers
        (r'/api/notifications/broadcast', BroadcastNotificationHandler), # POST - broadcast to all servers
        (r'/api/notifications/sent', SentNotificationsDataHandler),       # GET - sent-broadcast history ("Past Notifications")
        (r'/api/admin/credentials', GetUserCredentialsHandler),          # GET - cached auto-generated passwords
        (r'/api/activity', ActivityDataHandler),                          # GET - activity data + Docker stats
        (r'/api/activity/reset', ActivityResetHandler),                   # POST - clear activity samples
        (r'/api/activity/sample', ActivitySampleHandler),                 # POST - trigger manual sampling
        (r'/api/admin/groups', GroupsDataHandler),                        # GET - list groups with config
        (r'/api/admin/groups/create', GroupsCreateHandler),               # POST - create new group
        (r'/api/admin/groups/reorder', GroupsReorderHandler),             # POST - update group priorities
        (r'/api/admin/groups/([^/]+)/delete', GroupsDeleteHandler),       # DELETE - delete group
        (r'/api/admin/groups/([^/]+)/config', GroupsConfigHandler),       # GET/PUT - group configuration
        (r'/api/native-users', NativeUsersHandler),                       # GET - list NativeAuth signups + auth state
        (r'/api/native-users/([^/]+)/authorization', NativeUserAuthorizationHandler),  # POST - idempotent set
        # Legacy server-rendered page handlers (/notifications, /settings, /activity,
        # /groups) were removed - the React portal owns these features as client
        # routes. Their /api/* data handlers above stay. Unregistering them frees the
        # bare paths so the hub-root portal (no /portal segment) can serve those SPA
        # routes without the old pages shadowing them. See docs/acceptance-criteria/acc-crit-drop-portal-path.md.
        (r'/health', HealthCheckHandler),                                 # GET - unauthenticated monitoring endpoint
    ]
