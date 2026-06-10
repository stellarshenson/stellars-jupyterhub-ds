"""Scenario-matrix tests for the abuse-protection (Layer B) env parsing.

These pin the env-var contract documented in compose.yml and
settings_dictionary.yml: spawn/active caps default to JupyterHub's own
semantics, login lockout defaults ON at 5 attempts / 600s with 0 as the
explicit off-switch, and garbage env values fall back to defaults rather
than crash the hub at startup.
"""

import types

import pytest

from stellars_hub_services.abuse_protection import (
    DEFAULT_ACTIVE_SERVER_LIMIT,
    DEFAULT_CONCURRENT_SPAWN_LIMIT,
    DEFAULT_LOGIN_LOCKOUT_SECONDS,
    DEFAULT_LOGIN_MAX_FAILED_ATTEMPTS,
    apply_abuse_protection,
    build_app_protection,
    parse_int,
    ratelimit_disabled,
)


def _fake_config():
    """Stand-in for the traitlets config object (attribute sinks only)."""
    return types.SimpleNamespace(
        JupyterHub=types.SimpleNamespace(),
        NativeAuthenticator=types.SimpleNamespace(),
    )


# ── parse_int: garbage-tolerant env int parsing ──────────────────────────────

@pytest.mark.parametrize("raw, default, minimum, expected", [
    ("42", 5, 0, 42),
    (" 42 ", 5, 0, 42),            # whitespace tolerated
    ("0", 5, 0, 0),
    ("-3", 5, 0, 0),               # clamped to minimum, not default
    ("-3", 5, 1, 1),
    ("", 5, 0, 5),                 # empty -> default
    (None, 5, 0, 5),               # unset -> default
    ("abc", 5, 0, 5),              # non-numeric -> default
    ("4.5", 5, 0, 5),              # float string is not an int -> default
    (7, 5, 0, 7),                  # already an int
])
def test_parse_int_matrix(raw, default, minimum, expected):
    assert parse_int(raw, default, minimum) == expected


# ── build_app_protection: full env contract ──────────────────────────────────

def test_defaults_when_unset():
    result = build_app_protection({})
    assert result == {
        "concurrent_spawn_limit": DEFAULT_CONCURRENT_SPAWN_LIMIT,   # 100, JupyterHub default
        "active_server_limit": DEFAULT_ACTIVE_SERVER_LIMIT,         # 0 = unlimited
        "allowed_failed_logins": DEFAULT_LOGIN_MAX_FAILED_ATTEMPTS, # 5, lockout on
        "seconds_before_next_try": DEFAULT_LOGIN_LOCKOUT_SECONDS,   # 600
    }


def test_protective_deployment_maps_through_exactly():
    env = {
        "JUPYTERHUB_CONCURRENT_SPAWN_LIMIT": "20",
        "JUPYTERHUB_ACTIVE_SERVER_LIMIT": "50",
        "JUPYTERHUB_LOGIN_MAX_FAILED_ATTEMPTS": "5",
        "JUPYTERHUB_LOGIN_LOCKOUT_SECONDS": "600",
    }
    assert build_app_protection(env) == {
        "concurrent_spawn_limit": 20,
        "active_server_limit": 50,
        "allowed_failed_logins": 5,
        "seconds_before_next_try": 600,
    }


def test_lockout_disabled_with_zero_preserved():
    # 0 is the NativeAuth off-switch and must pass through verbatim - the
    # config only applies the throttle traits when this is > 0
    result = build_app_protection({"JUPYTERHUB_LOGIN_MAX_FAILED_ATTEMPTS": "0"})
    assert result["allowed_failed_logins"] == 0


def test_garbage_falls_back_to_defaults():
    env = {
        "JUPYTERHUB_CONCURRENT_SPAWN_LIMIT": "lots",
        "JUPYTERHUB_ACTIVE_SERVER_LIMIT": "",
        "JUPYTERHUB_LOGIN_MAX_FAILED_ATTEMPTS": "many",
        "JUPYTERHUB_LOGIN_LOCKOUT_SECONDS": "soon",
    }
    assert build_app_protection(env) == build_app_protection({})


def test_negatives_clamped():
    env = {
        "JUPYTERHUB_CONCURRENT_SPAWN_LIMIT": "-1",
        "JUPYTERHUB_ACTIVE_SERVER_LIMIT": "-9",
        "JUPYTERHUB_LOGIN_MAX_FAILED_ATTEMPTS": "-5",
        "JUPYTERHUB_LOGIN_LOCKOUT_SECONDS": "-600",
    }
    result = build_app_protection(env)
    assert result["concurrent_spawn_limit"] == 0
    assert result["active_server_limit"] == 0
    assert result["allowed_failed_logins"] == 0          # negative -> lockout off
    assert result["seconds_before_next_try"] == 1        # floor 1: a 0s window is meaningless


# ── apply_abuse_protection: the single config entry point ───────────────────

class TestApplyAbuseProtection:
    def test_defaults_wire_caps_and_lockout(self):
        c = _fake_config()
        settings = apply_abuse_protection(c, env={})
        assert c.JupyterHub.concurrent_spawn_limit == DEFAULT_CONCURRENT_SPAWN_LIMIT
        assert c.JupyterHub.active_server_limit == DEFAULT_ACTIVE_SERVER_LIMIT
        # lockout on by default (5/600) -> NativeAuth traits set
        assert c.NativeAuthenticator.allowed_failed_logins == DEFAULT_LOGIN_MAX_FAILED_ATTEMPTS
        assert c.NativeAuthenticator.seconds_before_next_try == DEFAULT_LOGIN_LOCKOUT_SECONDS
        assert settings == build_app_protection({})

    def test_lockout_off_leaves_nativeauth_untouched(self):
        c = _fake_config()
        apply_abuse_protection(c, env={"JUPYTERHUB_LOGIN_MAX_FAILED_ATTEMPTS": "0"})
        # caps always applied
        assert c.JupyterHub.concurrent_spawn_limit == DEFAULT_CONCURRENT_SPAWN_LIMIT
        # throttle traits never assigned -> NativeAuth defaults remain in force
        assert not hasattr(c.NativeAuthenticator, "allowed_failed_logins")
        assert not hasattr(c.NativeAuthenticator, "seconds_before_next_try")

    def test_custom_env_applied(self):
        c = _fake_config()
        apply_abuse_protection(c, env={
            "JUPYTERHUB_CONCURRENT_SPAWN_LIMIT": "20",
            "JUPYTERHUB_ACTIVE_SERVER_LIMIT": "50",
            "JUPYTERHUB_LOGIN_MAX_FAILED_ATTEMPTS": "3",
            "JUPYTERHUB_LOGIN_LOCKOUT_SECONDS": "300",
        })
        assert c.JupyterHub.concurrent_spawn_limit == 20
        assert c.JupyterHub.active_server_limit == 50
        assert c.NativeAuthenticator.allowed_failed_logins == 3
        assert c.NativeAuthenticator.seconds_before_next_try == 300


# ── ratelimit_disabled: the average=0 off-switch (Traefik semantic) ──────────

@pytest.mark.parametrize("average, expected", [
    ("0", True),
    (0, True),
    ("100", False),
    (1, False),
    ("", True),        # garbage fails open (disabled) rather than blocking traffic
    (None, True),
    ("off", True),
])
def test_ratelimit_disabled_matrix(average, expected):
    assert ratelimit_disabled(average) is expected
