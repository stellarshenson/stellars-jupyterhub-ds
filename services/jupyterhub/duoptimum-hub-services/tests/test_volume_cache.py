"""Functional tests for volume_cache.py - template-driven volume name parsing.

The activity monitor's volume-size cache parses on-disk Docker volume names
using regexes built from `user_volume_name_templates`. After the
COMPOSE_PROJECT_NAME refactor (v3.10.5), volumes are namespaced as
`{compose}_jupyterlab_{username}_{suffix}`; the previous `jupyterlab-`
prefix match silently filtered every modern volume out, leaving the activity
page with empty volume-size data.
"""

import pytest

from duoptimum_hub_services import volume_cache as vc


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


# DEF-7: the targeted-du path measures only the user volumes by walking the
# bind-mounted host volumes dir, deterministically (no partial/cold-boot snapshot).
TEMPLATES = {
    "home": "proj_jupyterlab_{username}_home",
    "workspace": "proj_jupyterlab_{username}_workspace",
    "cache": "proj_jupyterlab_{username}_cache",
}


def _mkvol(root, name, payload_bytes):
    data = root / name / "_data"
    data.mkdir(parents=True)
    if payload_bytes:
        (data / "blob").write_bytes(b"x" * payload_bytes)


class TestDuFetch:
    def test_du_measures_only_matching_user_volumes(self, tmp_path, monkeypatch):
        root = tmp_path / "volumes"
        _mkvol(root, "proj_jupyterlab_alice_home", 2 * 1024 * 1024)      # ~2 MB
        _mkvol(root, "proj_jupyterlab_alice_workspace", 0)              # empty -> ~0
        _mkvol(root, "proj_jupyterlab_bob_cache", 1024 * 1024)         # ~1 MB
        _mkvol(root, "proj_other_volume", 9 * 1024 * 1024)            # non-matching -> ignored
        _mkvol(root, "some_system_volume", 7 * 1024 * 1024)          # non-matching -> ignored
        vc.configure_volume_cache(TEMPLATES)
        monkeypatch.setenv("JUPYTERHUB_DOCKER_VOLUMES_DIR", str(root))
        try:
            data = vc._fetch_volume_sizes()
        finally:
            vc.configure_volume_cache({})

        assert set(data) == {"alice", "bob"}, "only templated user volumes counted, orphans ignored"
        assert data["alice"]["volumes"]["home"] >= 1.9          # ~2 MB
        assert data["alice"]["volumes"]["workspace"] == 0.0     # empty volume reports 0, not an error
        assert 1.9 <= data["alice"]["total"] <= 2.2
        assert data["bob"]["volumes"]["cache"] >= 0.9           # ~1 MB

    def test_empty_volume_reports_zero_not_error(self, tmp_path, monkeypatch):
        root = tmp_path / "volumes"
        _mkvol(root, "proj_jupyterlab_carol_home", 0)
        vc.configure_volume_cache(TEMPLATES)
        monkeypatch.setenv("JUPYTERHUB_DOCKER_VOLUMES_DIR", str(root))
        try:
            data = vc._fetch_volume_sizes()
        finally:
            vc.configure_volume_cache({})
        assert data["carol"]["volumes"]["home"] == 0.0


class TestFetchDispatch:
    def test_uses_du_when_volume_root_present(self, tmp_path, monkeypatch):
        root = tmp_path / "vols"
        root.mkdir()
        vc.configure_volume_cache({"home": "p_jupyterlab_{username}_home"})
        monkeypatch.setenv("JUPYTERHUB_DOCKER_VOLUMES_DIR", str(root))
        monkeypatch.setattr(vc, "_fetch_via_df", lambda: {"_df": True})
        monkeypatch.setattr(vc, "_fetch_via_du", lambda r: {"_du": r})
        try:
            out = vc._fetch_volume_sizes()
        finally:
            vc.configure_volume_cache({})
        assert out == {"_du": str(root)}, "bind-mount present -> du path, never df"

    def test_falls_back_to_df_when_root_absent(self, tmp_path, monkeypatch):
        vc.configure_volume_cache({"home": "p_jupyterlab_{username}_home"})
        monkeypatch.setenv("JUPYTERHUB_DOCKER_VOLUMES_DIR", str(tmp_path / "does-not-exist"))
        monkeypatch.setattr(vc, "_fetch_via_df", lambda: {"_df": True})
        try:
            out = vc._fetch_volume_sizes()
        finally:
            vc.configure_volume_cache({})
        assert out == {"_df": True}, "no bind-mount -> df fallback"
