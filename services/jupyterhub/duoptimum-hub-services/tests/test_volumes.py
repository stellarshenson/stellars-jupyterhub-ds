"""Functional tests for volumes.py - volume suffix extraction + role mapping."""

from duoptimum_hub_services.volumes import (
    get_user_volume_roles,
    get_user_volume_suffixes,
)


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


class TestGetUserVolumeRoles:
    def test_explicit_role_wins(self):
        """The volumes-dict `role` field is the role label value (lab- prefixed)."""
        volumes = {
            "jupyterhub_jupyterlab_{username}_home": {"mount": "/home", "role": "lab-home"},
            "jupyterhub_jupyterlab_{username}_workspace": {"mount": "/w", "role": "lab-workspace"},
            "jupyterhub_jupyterlab_{username}_cache": {"mount": "/c", "role": "lab-cache"},
            "jupyterhub_shared": {"mount": "/mnt/shared"},  # not a per-user volume - ignored
        }
        assert get_user_volume_roles(volumes) == {
            "home": "lab-home",
            "workspace": "lab-workspace",
            "cache": "lab-cache",
        }

    def test_role_defaults_to_suffix(self):
        """An entry with no `role` falls back to the suffix."""
        volumes = {"jupyterhub_jupyterlab_{username}_models": {"mount": "/models"}}
        assert get_user_volume_roles(volumes) == {"models": "models"}

    def test_custom_project(self):
        volumes = {"actone-ds_jupyterlab_{username}_home": {"mount": "/home", "role": "lab-home"}}
        assert get_user_volume_roles(volumes, "actone-ds") == {"home": "lab-home"}

    def test_empty_dict(self):
        assert get_user_volume_roles({}) == {}
