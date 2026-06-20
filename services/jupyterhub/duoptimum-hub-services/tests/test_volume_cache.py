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
    def test_unconfigured_cache_returns_incomplete(self):
        """Without templates _fetch_volume_sizes short-circuits to ({}, complete=False)."""
        vc.configure_volume_cache({})  # explicit reset
        assert vc._fetch_volume_sizes() == ({}, False)


# DEF-7: df hands back sizes mid-computation on a cold daemon (uncomputed volumes
# carry Size=-1). A pass with any -1 among our volumes is PARTIAL and must never be
# cached; the refresh waits for a complete pass instead.
TEMPLATES = {
    "home": "proj_jupyterlab_{username}_home",
    "workspace": "proj_jupyterlab_{username}_workspace",
    "cache": "proj_jupyterlab_{username}_cache",
}


def _mb(n):
    return n * 1024 * 1024


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAPIClient:
    """Stands in for docker.APIClient: _get(...).json() returns a canned df payload."""
    payload = {"Volumes": []}

    def __init__(self, *a, **k):
        pass

    def _url(self, path):
        return path

    def _get(self, *a, **k):
        return _FakeResp(type(self).payload)

    def close(self):
        pass


def _patch_df(monkeypatch, volumes):
    import docker
    _FakeAPIClient.payload = {"Volumes": volumes}
    monkeypatch.setattr(docker, "APIClient", _FakeAPIClient)


class TestDfCompleteness:
    def test_all_computed_is_complete(self, monkeypatch):
        vc.configure_volume_cache(TEMPLATES)
        _patch_df(monkeypatch, [
            {"Name": "proj_jupyterlab_alice_home", "UsageData": {"Size": _mb(2)}},
            {"Name": "proj_jupyterlab_alice_workspace", "UsageData": {"Size": 0}},   # empty -> 0, not pending
            {"Name": "proj_jupyterlab_bob_cache", "UsageData": {"Size": _mb(1)}},
            {"Name": "proj_other_volume", "UsageData": {"Size": _mb(9)}},            # non-matching -> ignored
        ])
        try:
            data, complete = vc._fetch_via_df()
        finally:
            vc.configure_volume_cache({})
        assert complete is True
        assert set(data) == {"alice", "bob"}, "only templated user volumes counted, orphans ignored"
        assert data["alice"]["volumes"]["home"] == 2.0
        assert data["alice"]["volumes"]["workspace"] == 0.0   # empty distinguishable from pending
        assert data["bob"]["volumes"]["cache"] == 1.0

    def test_minus_one_sentinel_marks_partial_and_is_skipped(self, monkeypatch):
        vc.configure_volume_cache(TEMPLATES)
        _patch_df(monkeypatch, [
            {"Name": "proj_jupyterlab_alice_home", "UsageData": {"Size": _mb(2)}},
            {"Name": "proj_jupyterlab_bob_cache", "UsageData": {"Size": -1}},        # not-yet-computed
        ])
        try:
            data, complete = vc._fetch_via_df()
        finally:
            vc.configure_volume_cache({})
        assert complete is False, "any -1 among our volumes makes the pass partial"
        assert "bob" not in data, "pending volume is skipped, never recorded as 0 (DEF-7)"
        assert data["alice"]["volumes"]["home"] == 2.0

    def test_error_is_incomplete(self, monkeypatch):
        vc.configure_volume_cache(TEMPLATES)
        import docker

        class _Boom(_FakeAPIClient):
            def _get(self, *a, **k):
                raise RuntimeError("docker down")

        monkeypatch.setattr(docker, "APIClient", _Boom)
        try:
            assert vc._fetch_via_df() == ({}, False)
        finally:
            vc.configure_volume_cache({})


class TestRefreshCachesOnlyComplete:
    def _reset(self):
        vc._volume_sizes_cache['data'] = {}
        vc._volume_sizes_cache['timestamp'] = None
        vc._volume_sizes_cache['refreshing'] = False

    @staticmethod
    def _count_save_cached(monkeypatch):
        """Patch save_cached with a call counter so tests assert the persist DID/ DID
        NOT happen - the previous no-op patch left the 'never persist a partial' DEF-7
        invariant unasserted (review finding)."""
        saves = {"n": 0}
        monkeypatch.setattr(vc, "save_cached", lambda *a, **k: saves.__setitem__("n", saves["n"] + 1))
        return saves

    def test_partial_then_complete_caches_complete(self, monkeypatch):
        self._reset()
        monkeypatch.setattr(vc, "_get_df_retry_delay", lambda: 0)
        monkeypatch.setattr(vc, "_get_df_max_attempts", lambda: 5)
        saves = self._count_save_cached(monkeypatch)
        passes = iter([
            ({"alice": {"total": 1.0, "volumes": {"home": 1.0}}}, False),  # partial -> not cached
            ({"alice": {"total": 2.0, "volumes": {"home": 2.0}}}, True),   # complete -> cached
        ])
        monkeypatch.setattr(vc, "_fetch_volume_sizes", lambda: next(passes))
        vc._refresh_volume_sizes_sync()
        assert vc._volume_sizes_cache['data'] == {"alice": {"total": 2.0, "volumes": {"home": 2.0}}}
        assert vc._volume_sizes_cache['timestamp'] is not None
        assert saves["n"] == 1, "persists exactly once - only the complete pass (not the partial)"
        assert vc._volume_sizes_cache['refreshing'] is False

    def test_all_partial_keeps_previous_and_does_not_cache(self, monkeypatch):
        self._reset()
        prev = {"bob": {"total": 5.0, "volumes": {"cache": 5.0}}}
        vc._volume_sizes_cache['data'] = dict(prev)
        monkeypatch.setattr(vc, "_get_df_retry_delay", lambda: 0)
        monkeypatch.setattr(vc, "_get_df_max_attempts", lambda: 3)
        saves = self._count_save_cached(monkeypatch)
        calls = {"n": 0}

        def _always_partial():
            calls["n"] += 1
            return ({"bob": {"total": 0.0, "volumes": {}}}, False)

        monkeypatch.setattr(vc, "_fetch_volume_sizes", _always_partial)
        vc._refresh_volume_sizes_sync()
        assert calls["n"] == 3, "retries up to the safety-net cap"
        assert saves["n"] == 0, "an all-partial run NEVER persists (DEF-7: no partial to disk)"
        assert vc._volume_sizes_cache['data'] == prev, "partial never overwrites the previous cache (DEF-7)"
        assert vc._volume_sizes_cache['timestamp'] is None
        assert vc._volume_sizes_cache['refreshing'] is False

    def test_reentry_guard_skips_when_already_refreshing(self, monkeypatch):
        """The lock-guarded 'refreshing' flag makes a second concurrent refresh a no-op
        (review: two submits could otherwise run two retry loops + pin two workers)."""
        self._reset()
        vc._volume_sizes_cache['refreshing'] = True  # simulate a refresh already in flight
        calls = {"n": 0}
        monkeypatch.setattr(vc, "_fetch_volume_sizes", lambda: calls.__setitem__("n", calls["n"] + 1) or ({}, True))
        vc._refresh_volume_sizes_sync()
        assert calls["n"] == 0, "did not fetch - the in-flight refresh owns the flag"
        assert vc._volume_sizes_cache['refreshing'] is True, "left the other refresh's flag untouched"

    def test_budget_caps_retry_before_attempt_cap(self, monkeypatch):
        """Wall-clock budget stops the loop well before a high attempt cap, so a slow df
        can't hold a worker for attempts x df-timeout (review finding 1.3)."""
        self._reset()
        monkeypatch.setattr(vc, "_get_df_retry_delay", lambda: 5)
        monkeypatch.setattr(vc, "_get_df_max_attempts", lambda: 100)  # high - budget must bite first
        monkeypatch.setattr(vc, "_get_df_budget", lambda: 12)
        self._count_save_cached(monkeypatch)
        monkeypatch.setattr(vc.time, "sleep", lambda *_: None)  # don't actually wait
        clock = {"t": 0.0}
        monkeypatch.setattr(vc.time, "monotonic", lambda: clock.__setitem__("t", clock["t"] + 5.0) or clock["t"])
        calls = {"n": 0}
        monkeypatch.setattr(vc, "_fetch_volume_sizes", lambda: calls.__setitem__("n", calls["n"] + 1) or ({}, False))
        vc._refresh_volume_sizes_sync()
        assert calls["n"] <= 3, "budget stopped the loop far short of the 100-attempt cap"
        assert vc._volume_sizes_cache['refreshing'] is False
