"""Functional tests for volumes.py - volume suffix extraction."""

from stellars_hub.volumes import get_user_volume_suffixes


class TestGetUserVolumeSuffixes:
    def test_standard_volumes(self):
        """Standard volumes extract expected suffixes."""
        volumes = {
            "jupyterlab-{username}_home": "/home",
            "jupyterlab-{username}_workspace": "/home/lab/workspace",
            "jupyterlab-{username}_cache": "/home/lab/.cache",
            "jupyterhub_shared": "/mnt/shared",
        }
        suffixes = sorted(get_user_volume_suffixes(volumes))
        assert suffixes == ["cache", "home", "workspace"]

    def test_non_matching_keys_excluded(self):
        """Keys not matching jupyterlab-{username}_ pattern are excluded."""
        volumes = {
            "other_volume": "/data",
            "jupyterhub_data": "/srv/data",
        }
        assert get_user_volume_suffixes(volumes) == []

    def test_empty_dict(self):
        """Empty dict returns empty list."""
        assert get_user_volume_suffixes({}) == []
