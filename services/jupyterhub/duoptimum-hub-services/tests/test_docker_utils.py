"""Functional tests for docker_utils.py - username encoding + lab name + network discovery."""

import sys
from types import SimpleNamespace

from duoptimum_hub_services.docker_utils import (
    encode_username_for_docker,
    encoded_username_from_lab_container,
    lab_container_name,
    resolve_network_placeholder,
    resolve_self_network_by_label,
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


class TestResolveSelfNetworkByLabel:
    """The hub<->sidecar network is DISCOVERED by its compose-declared marker label among
    the hub's OWN attached networks - so its real namespaced name can never drift, and a
    second stack carrying the same label on the host is never picked by mistake."""

    @staticmethod
    def _install_fake_docker(monkeypatch, *, attached=None, networks=None, get_raises=False):
        # attached: name -> {NetworkID}; networks: id/name -> labels dict
        networks = networks or {}

        class _Net:
            def __init__(self, name, labels):
                self.name = name
                self.attrs = {"Labels": labels}

        class _Networks:
            def get(self, key):
                name, labels = networks[key]
                return _Net(name, labels)

        class _Containers:
            def get(self, host):
                if get_raises:
                    raise RuntimeError("not found")
                return SimpleNamespace(attrs={"NetworkSettings": {"Networks": attached or {}}})

        class _Client:
            def __init__(self, *a, **k):
                self.containers = _Containers()
                self.networks = _Networks()

            def close(self):
                pass

        monkeypatch.setitem(sys.modules, "docker", SimpleNamespace(DockerClient=_Client))

    def test_returns_attached_network_carrying_label(self, monkeypatch):
        # hub attached to two networks; only the gpuinfo one carries the marker label
        self._install_fake_docker(
            monkeypatch,
            attached={"hub_net": {"NetworkID": "id-hub"}, "gpu_net": {"NetworkID": "id-gpu"}},
            networks={
                "id-hub": ("duoptimum-hub_hub_network", {}),
                "id-gpu": ("duoptimum-hub_hub_gpuinfo_network", {"duoptimum.gpuinfo.network": "true"}),
            },
        )
        assert resolve_self_network_by_label("duoptimum.gpuinfo.network") == "duoptimum-hub_hub_gpuinfo_network"

    def test_none_when_no_attached_network_has_label(self, monkeypatch):
        self._install_fake_docker(
            monkeypatch,
            attached={"hub_net": {"NetworkID": "id-hub"}},
            networks={"id-hub": ("duoptimum-hub_hub_network", {})},
        )
        assert resolve_self_network_by_label("duoptimum.gpuinfo.network") is None

    def test_none_when_self_container_undeterminable(self, monkeypatch):
        self._install_fake_docker(monkeypatch, get_raises=True)
        assert resolve_self_network_by_label("duoptimum.gpuinfo.network") is None

    def test_role_value_match_selects_the_right_net(self, monkeypatch):
        # both nets share the key; the value (role) picks the right one
        self._install_fake_docker(
            monkeypatch,
            attached={"lab": {"NetworkID": "id-lab"}, "gpu": {"NetworkID": "id-gpu"}},
            networks={
                "id-lab": ("proj_hub_network", {"duoptimum.network.role": "lab"}),
                "id-gpu": ("proj_hub_gpuinfo_network", {"duoptimum.network.role": "gpuinfo"}),
            },
        )
        assert resolve_self_network_by_label("duoptimum.network.role", "lab") == "proj_hub_network"
        assert resolve_self_network_by_label("duoptimum.network.role", "gpuinfo") == "proj_hub_gpuinfo_network"

    def test_none_when_role_value_no_match(self, monkeypatch):
        self._install_fake_docker(
            monkeypatch,
            attached={"lab": {"NetworkID": "id-lab"}},
            networks={"id-lab": ("proj_hub_network", {"duoptimum.network.role": "lab"})},
        )
        assert resolve_self_network_by_label("duoptimum.network.role", "gpuinfo") is None

    def test_value_none_keeps_presence_match(self, monkeypatch):
        # legacy presence behaviour preserved when no value is given
        self._install_fake_docker(
            monkeypatch,
            attached={"lab": {"NetworkID": "id-lab"}},
            networks={"id-lab": ("proj_hub_network", {"duoptimum.network.role": "lab"})},
        )
        assert resolve_self_network_by_label("duoptimum.network.role") == "proj_hub_network"


class TestResolveNetworkPlaceholder:
    """{network} token in an env value -> the resolved net for that context; literal passes through."""

    def test_substitutes_token(self):
        assert resolve_network_placeholder("{network}", "proj_hub_network") == "proj_hub_network"

    def test_literal_passthrough(self):
        # operator override: a real name with no token is used verbatim
        assert resolve_network_placeholder("my_net", "proj_hub_network") == "my_net"

    def test_empty_value_noop(self):
        assert resolve_network_placeholder("", "proj_hub_network") == ""

    def test_empty_network_blanks_token(self):
        # unresolved net -> token becomes empty (caller treats as fatal/degrade)
        assert resolve_network_placeholder("{network}", "") == ""
