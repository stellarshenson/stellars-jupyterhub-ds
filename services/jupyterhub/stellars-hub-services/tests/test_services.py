"""Functional tests for services.py - the activity sampler managed service.

Idle culling is no longer a managed service; it runs in-process via
`stellars_hub_services.idle_culler.schedule_idle_culler` (covered by test_idle_culler.py),
so `get_services_and_roles` only builds the activity sampler now.
"""

from stellars_hub_services.services import get_services_and_roles


class TestActivitySampler:
    def test_always_present(self):
        services, roles = get_services_and_roles(sample_interval=600)
        svc_names = [s["name"] for s in services]
        assert "activity-sampler" in svc_names

    def test_role_has_correct_scopes(self):
        services, roles = get_services_and_roles(sample_interval=600)
        sampler_role = next(r for r in roles if r["name"] == "activity-sampler-role")
        assert "list:users" in sampler_role["scopes"]
        assert "read:users:activity" in sampler_role["scopes"]
        assert "read:servers" in sampler_role["scopes"]


class TestNoExternalCuller:
    def test_idle_culler_is_not_a_managed_service(self):
        """The external jupyterhub-idle-culler service was replaced by the in-hub culler."""
        services, roles = get_services_and_roles(sample_interval=600)
        svc_names = [s["name"] for s in services]
        role_names = [r["name"] for r in roles]
        assert "jupyterhub-idle-culler" not in svc_names
        assert "jupyterhub-idle-culler-role" not in role_names
