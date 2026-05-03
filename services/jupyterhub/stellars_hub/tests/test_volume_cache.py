"""Functional tests for volume_cache.py - template-driven volume name parsing.

The activity monitor's volume-size cache parses on-disk Docker volume names
using regexes built from `user_volume_name_templates`. After the
COMPOSE_PROJECT_NAME refactor (v3.10.5), volumes are namespaced as
`{compose}_jupyterlab_{username}_{suffix}`; the previous `jupyterlab-`
prefix match silently filtered every modern volume out, leaving the activity
page with empty volume-size data.
"""

import pytest

from stellars_hub import volume_cache as vc


@pytest.fixture
def configured_cache():
    """Configure the cache with realistic templates and return the module."""
    templates = {
        "home": "stellars-tech-ai-lab_jupyterlab_{username}_home",
        "workspace": "stellars-tech-ai-lab_jupyterlab_{username}_workspace",
        "cache": "stellars-tech-ai-lab_jupyterlab_{username}_cache",
    }
    vc.configure_volume_cache(templates)
    yield vc
    # Reset module state so subsequent tests start clean
    vc.configure_volume_cache({})


class TestConfigureVolumeCache:
    def test_default_project_templates(self):
        """Default `jupyterhub` project templates compile and match."""
        templates = {
            "home": "jupyterhub_jupyterlab_{username}_home",
            "cache": "jupyterhub_jupyterlab_{username}_cache",
        }
        vc.configure_volume_cache(templates)
        assert len(vc._template_regexes) == 2
        # find the home regex and confirm a matching disk name
        home_regex = next(r for s, r in vc._template_regexes if s == "home")
        m = home_regex.match("jupyterhub_jupyterlab_alice_home")
        assert m and m.group(1) == "alice"

    def test_namespaced_project_extracts_encoded_username(self, configured_cache):
        """Compose-project-namespaced volumes recover the escapism-encoded username."""
        regexes = {s: r for s, r in configured_cache._template_regexes}
        m = regexes["home"].match("stellars-tech-ai-lab_jupyterlab_konrad-2ejelen_home")
        assert m and m.group(1) == "konrad-2ejelen"
        m = regexes["cache"].match("stellars-tech-ai-lab_jupyterlab_camilo-2esaa_cache")
        assert m and m.group(1) == "camilo-2esaa"

    def test_non_matching_volumes_skipped(self, configured_cache):
        """Volumes outside the per-user pattern do not match any template."""
        not_user_vols = [
            "stellars-tech-ai-lab_data",
            "stellars_shared",
            "some_other_volume",
            "jupyterlab-alice_home",  # legacy pre-3.10.5 pattern - should NOT match modern config
        ]
        for name in not_user_vols:
            assert not any(r.match(name) for _, r in configured_cache._template_regexes), \
                f"unexpected match for {name!r}"

    def test_reconfigure_replaces_state(self):
        """Calling configure twice swaps the templates rather than appending."""
        vc.configure_volume_cache({"home": "old_jupyterlab_{username}_home"})
        assert len(vc._template_regexes) == 1
        vc.configure_volume_cache({
            "home": "new_jupyterlab_{username}_home",
            "cache": "new_jupyterlab_{username}_cache",
        })
        assert len(vc._template_regexes) == 2
        # confirm the old prefix no longer matches anything
        assert not any(r.match("old_jupyterlab_alice_home") for _, r in vc._template_regexes)

    def test_username_with_special_chars_captured_intact(self, configured_cache):
        """Escapism-encoded usernames (with dots -> -2e) are captured intact."""
        regexes = {s: r for s, r in configured_cache._template_regexes}
        names = [
            ("stellars-tech-ai-lab_jupyterlab_marcin-2eszura_workspace", "marcin-2eszura"),
            ("stellars-tech-ai-lab_jupyterlab_user-2dwith-2ddashes_home", "user-2dwith-2ddashes"),
        ]
        for vol_name, expected_user in names:
            m = regexes[vol_name.rsplit("_", 1)[1]].match(vol_name)
            assert m and m.group(1) == expected_user


class TestEmptyConfigBehaviour:
    def test_unconfigured_cache_returns_empty(self):
        """Calling _fetch_volume_sizes without templates short-circuits to {}."""
        vc.configure_volume_cache({})  # explicit reset
        assert vc._fetch_volume_sizes() == {}
