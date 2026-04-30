"""Functional tests for volumes.py - volume suffix extraction."""

from stellars_hub.volumes import get_user_volume_suffixes


class TestGetUserVolumeSuffixes:
    def test_standard_volumes(self):
        """Standard volumes extract expected suffixes (default project = 'jupyterhub')."""
        volumes = {
            "jupyterhub_jupyterlab_{username}_home": "/home",
            "jupyterhub_jupyterlab_{username}_workspace": "/home/lab/workspace",
            "jupyterhub_jupyterlab_{username}_cache": "/home/lab/.cache",
            "jupyterhub_shared": "/mnt/shared",
        }
        suffixes = sorted(get_user_volume_suffixes(volumes))
        assert suffixes == ["cache", "home", "workspace"]

    def test_custom_project(self):
        """A non-default compose project name flows through to the matcher."""
        volumes = {
            "actone-ds_jupyterlab_{username}_home": "/home",
            "actone-ds_jupyterlab_{username}_workspace": "/home/lab/workspace",
            "jupyterhub_shared": "/mnt/shared",
        }
        suffixes = sorted(get_user_volume_suffixes(volumes, "actone-ds"))
        assert suffixes == ["home", "workspace"]

    def test_non_matching_keys_excluded(self):
        """Keys not matching <project>_jupyterlab_{username}_ pattern are excluded."""
        volumes = {
            "other_volume": "/data",
            "jupyterhub_data": "/srv/data",
        }
        assert get_user_volume_suffixes(volumes) == []

    def test_empty_dict(self):
        """Empty dict returns empty list."""
        assert get_user_volume_suffixes({}) == []
