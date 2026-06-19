"""Functional tests for docker_utils.py - username encoding + lab name."""

from duoptimum_hub_services.docker_utils import (
    encode_username_for_docker,
    encoded_username_from_lab_container,
    lab_container_name,
)


class TestEncodeUsername:
    def test_simple_alphanumeric_unchanged(self):
        """Plain alphanumeric name passes through unchanged."""
        assert encode_username_for_docker("simple") == "simple"

    def test_dot_escaped(self):
        """Dot is escaped: user.name -> user-2ename (. = ASCII 0x2e)."""
        assert encode_username_for_docker("user.name") == "user-2ename"

    def test_at_sign_escaped(self):
        """At sign is escaped: user@host -> user-40host (@ = ASCII 0x40)."""
        assert encode_username_for_docker("user@host") == "user-40host"


class TestLabContainerName:
    def test_default_template_matches_spawner_default(self, monkeypatch):
        """Default mirrors c.DockerSpawner.name_template (jupyterlab-{username})."""
        monkeypatch.delenv("JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE", raising=False)
        assert lab_container_name("simple") == "jupyterlab-simple"

    def test_encodes_username_in_default(self, monkeypatch):
        """Username is docker-encoded before substitution."""
        monkeypatch.delenv("JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE", raising=False)
        assert lab_container_name("user.name") == "jupyterlab-user-2ename"

    def test_env_template_override(self, monkeypatch):
        """A custom template renders with the encoded username, no hardcoded prefix."""
        monkeypatch.setenv("JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE", "lab_{username}_srv")
        assert lab_container_name("user.name") == "lab_user-2ename_srv"

    def test_empty_env_falls_back_to_default(self, monkeypatch):
        """Empty env value is treated as unset (no empty-prefix name)."""
        monkeypatch.setenv("JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE", "")
        assert lab_container_name("simple") == "jupyterlab-simple"


class TestEncodedUsernameFromLabContainer:
    def test_roundtrip_default(self, monkeypatch):
        """Inverse of lab_container_name on the default template."""
        monkeypatch.delenv("JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE", raising=False)
        assert encoded_username_from_lab_container("jupyterlab-user-2ename") == "user-2ename"

    def test_non_lab_container_returns_none(self, monkeypatch):
        """A container that does not match the template is skipped (None)."""
        monkeypatch.delenv("JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE", raising=False)
        assert encoded_username_from_lab_container("traefik") is None

    def test_roundtrip_custom_template_with_suffix(self, monkeypatch):
        """Prefix AND suffix are derived from the template, not hardcoded."""
        monkeypatch.setenv("JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE", "lab_{username}_srv")
        assert encoded_username_from_lab_container("lab_user-2ename_srv") == "user-2ename"
        # the old default prefix no longer matches once the template changes
        assert encoded_username_from_lab_container("jupyterlab-simple") is None

    def test_forward_reverse_consistency(self, monkeypatch):
        """lab_container_name and its inverse agree for any template."""
        monkeypatch.setenv("JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE", "lab_{username}_srv")
        name = lab_container_name("user.name")
        assert encoded_username_from_lab_container(name) == encode_username_for_docker("user.name")
