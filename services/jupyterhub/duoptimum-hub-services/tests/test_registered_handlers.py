"""Content lock for registered_handlers() (Batch 1 config simplification).

The custom route table moved from jupyterhub_config.py into handlers/registry.py.
The config file cannot be unit-booted, so this pins the exact patterns and their
first-match-wins order - a dropped, reordered or renamed route is caught here
instead of at hub boot. The splice MECHANISM is covered by test_app_handler_registry.
"""

from tornado.web import RequestHandler

from duoptimum_hub_services.handlers.registry import registered_handlers

# The shipped route table, in order. Byte-identical to the list that lived in
# config/jupyterhub_config.py before the extraction.
EXPECTED_PATTERNS = [
    r'/api/users/([^/]+)/manage-volumes',
    r'/api/users/([^/]+)/restart-server',
    r'/api/users/([^/]+)/server/logs',
    r'/api/users/([^/]+)/lab-ready',
    r'/api/users/([^/]+)/session-info',
    r'/api/users/([^/]+)/profile',
    r'/api/users/([^/]+)/force-password-change',
    r'/api/users/([^/]+)/rename',
    r'/api/users/([^/]+)/display-preferences',
    r'/api/users/([^/]+)/env-vars',
    r'/api/users/([^/]+)/effective-grants',
    r'/api/user-profiles',
    r'/api/settings',
    r'/api/events',
    r'/api/users/([^/]+)/extend-session',
    r'/api/notifications/active-servers',
    r'/api/notifications/broadcast',
    r'/api/notifications/sent',
    r'/api/admin/credentials',
    r'/api/activity',
    r'/api/activity/reset',
    r'/api/activity/sample',
    r'/api/admin/groups',
    r'/api/admin/groups/create',
    r'/api/admin/groups/reorder',
    r'/api/admin/groups/([^/]+)/delete',
    r'/api/admin/groups/([^/]+)/config',
    r'/api/native-users',
    r'/api/native-users/([^/]+)/authorization',
    r'/health',
]


def test_patterns_and_order_are_pinned():
    got = [t[0] for t in registered_handlers()]
    assert got == EXPECTED_PATTERNS


def test_every_entry_is_pattern_plus_handler_class():
    for entry in registered_handlers():
        assert len(entry) == 2, entry
        pattern, cls = entry
        assert isinstance(pattern, str)
        assert isinstance(cls, type)
        assert issubclass(cls, RequestHandler), cls


def test_no_duplicate_patterns():
    pats = [t[0] for t in registered_handlers()]
    assert len(pats) == len(set(pats))


def test_health_route_is_last():
    # /health is the final custom route; the config appends the portal SPA catch-all
    # AFTER this list, so /health must stay last here for the documented ordering.
    assert registered_handlers()[-1][0] == r'/health'


def test_returns_a_fresh_list_each_call():
    # a builder, not a shared module-level list - callers must not alias each other
    assert registered_handlers() is not registered_handlers()
