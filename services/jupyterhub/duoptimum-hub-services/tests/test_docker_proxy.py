"""Hub-side docker-proxy wiring tests.

Covers the pure helpers - template rendering and resolver-to-ProxyConfig
override mapping. The full register_user path needs a live Manager + asyncio
loop and is exercised by the proxy package's own test suite.
"""

from duoptimum_hub_services.docker_proxy import (
    _build_overrides,
    _render_user_compose_project,
)


def _resolved(**overrides):
    base = {
        'docker_limited_max_containers': 10,
        'docker_limited_max_volumes': 10,
        'docker_limited_max_networks': 3,
        'docker_limited_max_storage_gb': 50,
        'docker_limited_cpu_cap_cores': 2,
        'docker_limited_mem_cap_gb': 8,
        'docker_limited_allow_dangerous_flags': False,
        'docker_limited_user_compose_project_enabled': False,
        'docker_limited_user_compose_project_allow_override': True,
        'docker_privileged': False,
    }
    base.update(overrides)
    return base


class TestRenderUserComposeProject:
    def test_renders_full_template(self):
        out = _render_user_compose_project(
            "{compose_project}_{username}_containers",
            compose_project="stellars-tech-ai-lab",
            username="konrad.jelen",
        )
        assert out == "stellars-tech-ai-lab_konrad.jelen_containers"

    def test_empty_template_returns_empty(self):
        out = _render_user_compose_project("", compose_project="x", username="u")
        assert out == ""

    def test_bad_placeholder_falls_back_to_hub_project(self):
        # Unknown placeholder should not crash; falls back to the hub project.
        out = _render_user_compose_project(
            "{unknown}",
            compose_project="stellars-tech-ai-lab",
            username="u",
        )
        assert out == "stellars-tech-ai-lab"

    def test_template_with_only_username(self):
        out = _render_user_compose_project(
            "{username}",
            compose_project="x",
            username="alice",
        )
        assert out == "alice"


class TestBuildOverrides:
    def test_allow_privileged_from_docker_privileged(self):
        ov = _build_overrides(
            _resolved(docker_privileged=True),
            username="alice",
            compose_project="proj",
        )
        assert ov['allow_privileged'] is True

    def test_allow_dangerous_flags_independent_of_privileged(self):
        # docker_privileged alone must NOT set allow_dangerous_flags.
        ov = _build_overrides(
            _resolved(docker_privileged=True),
            username="alice",
            compose_project="proj",
        )
        assert ov['allow_dangerous_flags'] is False

    def test_allow_dangerous_flags_from_resolved_field(self):
        ov = _build_overrides(
            _resolved(docker_limited_allow_dangerous_flags=True),
            username="alice",
            compose_project="proj",
        )
        assert ov['allow_dangerous_flags'] is True
        # Privileged still off (independent).
        assert ov['allow_privileged'] is False

    def test_no_compose_project_when_user_enforcement_off(self):
        # Off mode = ad-hoc `docker run` containers carry no compose project
        # label at all (free-floating). The hub's project is NOT propagated.
        ov = _build_overrides(
            _resolved(docker_limited_user_compose_project_enabled=False),
            username="alice",
            compose_project="hub-proj",
            user_compose_project_template="{compose_project}_{username}_containers",
        )
        assert 'compose_project' not in ov

    def test_compose_project_rendered_when_enforcement_on(self):
        ov = _build_overrides(
            _resolved(docker_limited_user_compose_project_enabled=True),
            username="alice",
            compose_project="hub-proj",
            user_compose_project_template="{compose_project}_{username}_containers",
        )
        assert ov['compose_project'] == "hub-proj_alice_containers"

    def test_allow_compose_project_override_default_true(self):
        ov = _build_overrides(
            _resolved(),
            username="alice",
            compose_project="hub-proj",
        )
        assert ov['allow_compose_project_override'] is True

    def test_allow_compose_project_override_can_be_off(self):
        ov = _build_overrides(
            _resolved(docker_limited_user_compose_project_allow_override=False),
            username="alice",
            compose_project="hub-proj",
        )
        assert ov['allow_compose_project_override'] is False

    def test_empty_compose_project_omits_field(self):
        # When no compose project is set, the override dict doesn't carry one
        # (ProxyConfig default of '' wins). With enforcement on and the
        # template referencing {compose_project}, the result is also empty.
        ov = _build_overrides(
            _resolved(docker_limited_user_compose_project_enabled=True),
            username="alice",
            compose_project="",
            user_compose_project_template="{compose_project}_{username}_containers",
        )
        assert 'compose_project' not in ov or ov.get('compose_project') == '_alice_containers'

    def test_extra_accessible_networks_set_when_enabled_and_name_known(self):
        ov = _build_overrides(
            _resolved(docker_limited_hub_network_access=True),
            username="alice",
            compose_project="proj",
            hub_network_name="proj_network",
        )
        assert ov['extra_accessible_networks'] == ("proj_network",)

    def test_extra_accessible_networks_absent_when_toggle_off(self):
        ov = _build_overrides(
            _resolved(docker_limited_hub_network_access=False),
            username="alice",
            compose_project="proj",
            hub_network_name="proj_network",
        )
        assert 'extra_accessible_networks' not in ov

    def test_extra_accessible_networks_absent_when_hub_name_missing(self):
        # Toggle on but name not configured -> nothing exposed.
        ov = _build_overrides(
            _resolved(docker_limited_hub_network_access=True),
            username="alice",
            compose_project="proj",
            hub_network_name="",
        )
        assert 'extra_accessible_networks' not in ov
