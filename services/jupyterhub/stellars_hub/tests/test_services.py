"""Functional tests for services.py - activity sampler and idle culler definitions."""

from stellars_hub.services import get_services_and_roles


class TestActivitySampler:
    def test_always_present(self):
        """Activity sampler service is always returned."""
        services, roles = get_services_and_roles(
            culler_enabled=0, culler_timeout=86400, culler_interval=600,
            culler_max_age=0, sample_interval=600,
        )
        svc_names = [s["name"] for s in services]
        assert "activity-sampler" in svc_names

    def test_role_has_correct_scopes(self):
        """Activity sampler role has required scopes."""
        services, roles = get_services_and_roles(
            culler_enabled=0, culler_timeout=86400, culler_interval=600,
            culler_max_age=0, sample_interval=600,
        )
        sampler_role = next(r for r in roles if r["name"] == "activity-sampler-role")
        assert "list:users" in sampler_role["scopes"]
        assert "read:users:activity" in sampler_role["scopes"]
        assert "read:servers" in sampler_role["scopes"]


class TestIdleCullerDisabled:
    def test_not_present_when_disabled(self):
        """Idle culler not in services when disabled."""
        services, roles = get_services_and_roles(
            culler_enabled=0, culler_timeout=86400, culler_interval=600,
            culler_max_age=0, sample_interval=600,
        )
        svc_names = [s["name"] for s in services]
        assert "jupyterhub-idle-culler" not in svc_names


class TestIdleCullerEnabled:
    def test_present_when_enabled(self):
        """Idle culler present when enabled."""
        services, roles = get_services_and_roles(
            culler_enabled=1, culler_timeout=3600, culler_interval=300,
            culler_max_age=0, sample_interval=600,
        )
        svc_names = [s["name"] for s in services]
        assert "jupyterhub-idle-culler" in svc_names

    def test_command_includes_timeout_and_interval(self):
        """Culler command has --timeout and --cull-every flags."""
        services, _ = get_services_and_roles(
            culler_enabled=1, culler_timeout=3600, culler_interval=300,
            culler_max_age=0, sample_interval=600,
        )
        culler = next(s for s in services if s["name"] == "jupyterhub-idle-culler")
        cmd_str = " ".join(culler["command"])
        assert "--timeout=3600" in cmd_str
        assert "--cull-every=300" in cmd_str

    def test_max_age_only_when_positive(self):
        """--max-age flag only appears when > 0."""
        # max_age = 0: no flag
        services_0, _ = get_services_and_roles(
            culler_enabled=1, culler_timeout=3600, culler_interval=300,
            culler_max_age=0, sample_interval=600,
        )
        culler_0 = next(s for s in services_0 if s["name"] == "jupyterhub-idle-culler")
        assert not any("--max-age" in arg for arg in culler_0["command"])

        # max_age = 7200: flag present
        services_1, _ = get_services_and_roles(
            culler_enabled=1, culler_timeout=3600, culler_interval=300,
            culler_max_age=7200, sample_interval=600,
        )
        culler_1 = next(s for s in services_1 if s["name"] == "jupyterhub-idle-culler")
        assert any("--max-age=7200" in arg for arg in culler_1["command"])
