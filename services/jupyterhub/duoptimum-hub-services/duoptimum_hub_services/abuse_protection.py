"""Application-layer (L7) abuse-protection settings.

Two protection layers exist; this module backs the second:

- Layer A - Traefik ``rateLimit`` middleware on the shared ``duoptimumhub-rtr``
  router (configured via ``${JUPYTERHUB_RATELIMIT_*}`` compose interpolation in
  ``compose.yml``), bounding request velocity per source IP for the hub AND all
  spawned labs, since both ingress through CHP on the hub's :8000. A per-IP
  concurrency cap (``inFlightReq``) is deliberately NOT shipped: JupyterLab
  legitimately holds many simultaneous long-lived connections (kernels,
  terminals, comms, polling), so it would stall real usage - documented as an
  optional operator add-on in the README.
- Layer B - JupyterHub + NativeAuthenticator limits (concurrent-spawn cap,
  active-server cap, login lockout) parsed here from environment variables and
  wired onto ``c.*`` in ``config/jupyterhub_config.py``.

Pure stdlib so the parsing/clamping stays trivially testable (same shape as
``idle_culler.py``); the config file only applies the returned values.
"""

__all__ = [
    "parse_int",
    "build_app_protection",
    "apply_abuse_protection",
    "ratelimit_disabled",
]

# Layer-B defaults (documented in compose.yml and settings_dictionary.yml)
DEFAULT_CONCURRENT_SPAWN_LIMIT = 100   # JupyterHub's own default
DEFAULT_ACTIVE_SERVER_LIMIT = 0        # 0 = unlimited (JupyterHub semantic)
DEFAULT_LOGIN_MAX_FAILED_ATTEMPTS = 5  # 0 = lockout disabled (NativeAuth semantic)
DEFAULT_LOGIN_LOCKOUT_SECONDS = 600    # NativeAuth seconds_before_next_try default


def parse_int(raw, default, minimum=0):
    """Parse an env value to an int, falling back to ``default`` on garbage
    (empty / non-numeric / None) and clamping to ``minimum``."""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return minimum if value < minimum else value


def build_app_protection(env):
    """Resolve the Layer-B limits from an environ-like mapping.

    Returns ``{concurrent_spawn_limit, active_server_limit,
    allowed_failed_logins, seconds_before_next_try}``. A zero
    ``allowed_failed_logins`` means lockout off and the caller must then leave
    the NativeAuthenticator throttle traits untouched.
    """
    return {
        "concurrent_spawn_limit": parse_int(
            env.get("JUPYTERHUB_CONCURRENT_SPAWN_LIMIT"), DEFAULT_CONCURRENT_SPAWN_LIMIT
        ),
        "active_server_limit": parse_int(
            env.get("JUPYTERHUB_ACTIVE_SERVER_LIMIT"), DEFAULT_ACTIVE_SERVER_LIMIT
        ),
        "allowed_failed_logins": parse_int(
            env.get("JUPYTERHUB_LOGIN_MAX_FAILED_ATTEMPTS"), DEFAULT_LOGIN_MAX_FAILED_ATTEMPTS
        ),
        "seconds_before_next_try": parse_int(
            env.get("JUPYTERHUB_LOGIN_LOCKOUT_SECONDS"), DEFAULT_LOGIN_LOCKOUT_SECONDS,
            minimum=1,
        ),
    }


def apply_abuse_protection(c, env=None):
    """Wire the Layer-B limits onto a JupyterHub config object.

    The single entry point for ``jupyterhub_config.py`` - maps the env vars,
    sets the JupyterHub spawn/active caps, and applies the NativeAuthenticator
    login-lockout traits only when lockout is enabled (``allowed_failed_logins
    > 0``), so ``0`` is a true no-op. Returns the resolved dict for logging.
    """
    if env is None:
        import os
        env = os.environ
    settings = build_app_protection(env)
    c.JupyterHub.concurrent_spawn_limit = settings["concurrent_spawn_limit"]
    c.JupyterHub.active_server_limit = settings["active_server_limit"]
    if settings["allowed_failed_logins"] > 0:
        c.NativeAuthenticator.allowed_failed_logins = settings["allowed_failed_logins"]
        c.NativeAuthenticator.seconds_before_next_try = settings["seconds_before_next_try"]
    return settings


def ratelimit_disabled(average):
    """True when the Traefik rateLimit middleware is effectively off.

    Traefik's native semantic: ``average=0`` disables the limiter. Garbage is
    treated as disabled (0) so a misconfigured value fails open rather than
    blocking traffic.
    """
    return parse_int(average, 0) == 0
