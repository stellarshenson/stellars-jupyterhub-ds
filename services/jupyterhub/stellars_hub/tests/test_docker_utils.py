"""Functional tests for docker_utils.py - username encoding."""

from stellars_hub.docker_utils import encode_username_for_docker


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
