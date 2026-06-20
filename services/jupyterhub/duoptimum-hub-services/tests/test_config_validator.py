"""Tests for the central hub-config validator: required vars, consistency, warnings."""

import pytest

from duoptimum_hub_services.config_validator import (
    ValidationResult,
    validate_hub_config,
)


def _valid_values(**overrides):
    """A fully-valid config (all required present, consistent, resolved); override per-test."""
    values = {
        "admin": "admin",
        "lab_image": "stellars/stellars-jupyterlab-ds:latest",
        "namespace": "duoptimum-hub",
        "lab_network_name": "duoptimum-hub_hub_network",
        "network_role_label_key": "duoptimum-hub.network.role",
        "volume_role_label_key": "duoptimum-hub.volume.role",
        "container_role_label_key": "duoptimum-hub.container.role",
        "lab_network_role_label": "lab",
        "gpuinfo_network_role_label": "gpuinfo",
        "shared_volume_role_label": "shared",
        "docker_proxy_volume_role_label": "docker-proxy",
        "gpuinfo_container_role_label": "gpuinfo",
        "lab_container_name_template": "jupyterlab-{username}",
        "gpuinfo_nvidia_image": "stellars/duoptimum-gpuinfo-nvidia:latest",
        "gpuinfo_nvidia_container_name": "gpuinfo-nvidia",
        "gpuinfo_nvidia_url": "http://{hostname}:8000",
        "docker_proxy_socket_dir": "/var/run/docker-proxy-sockets",
        "docker_proxy_sockets_volume": "duoptimum-hub_hub_docker",
        "user_compose_project_template": "{username}_containers",
        "volume_description_label_key": "duoptimum-hub.volume.description",
        "volume_owner_label_key": "duoptimum-hub.volume.owner",
        "container_description_label_key": "duoptimum-hub.container.description",
        "docker_proxy_owner_label_key": "duoptimum-hub.docker.proxy.owner",
        "docker_proxy_owner_label_value": "{username}",
        # optional / resolved-at-runtime (present = no warning)
        "gpuinfo_network_name": "duoptimum-hub_hub_gpuinfo_network",
        "shared_volume_name": "duoptimum-hub_hub_shared",
        "branding_logo_uri": "",
        "branding_favicon_uri": "",
        "branding_favicon_busy_uri": "",
        "branding_lab_main_icon_uri": "",
        "branding_lab_splash_uri": "",
    }
    values.update(overrides)
    return values


class TestValidConfig:
    def test_fully_valid_passes_clean(self):
        result = validate_hub_config(_valid_values())
        assert result.ok
        assert result.errors == []
        assert result.warnings == []


class TestRequiredErrors:
    @pytest.mark.parametrize(
        "key",
        [
            "admin",
            "lab_image",
            "namespace",
            "lab_network_name",
            "network_role_label_key",
            "volume_role_label_key",
            "container_role_label_key",
            "lab_network_role_label",
            "gpuinfo_network_role_label",
            "shared_volume_role_label",
            "docker_proxy_volume_role_label",
            "gpuinfo_container_role_label",
            "lab_container_name_template",
            "gpuinfo_nvidia_image",
            "gpuinfo_nvidia_container_name",
            "gpuinfo_nvidia_url",
            "docker_proxy_socket_dir",
            "docker_proxy_sockets_volume",
            "user_compose_project_template",
            "volume_description_label_key",
            "volume_owner_label_key",
            "container_description_label_key",
            "docker_proxy_owner_label_key",
            "docker_proxy_owner_label_value",
        ],
    )
    def test_missing_required_is_error(self, key):
        result = validate_hub_config(_valid_values(**{key: ""}))
        assert not result.ok
        assert any(key.split("_")[0] in e.lower() or e for e in result.errors)

    def test_none_value_is_error(self):
        result = validate_hub_config(_valid_values(admin=None))
        assert not result.ok

    def test_whitespace_only_is_error(self):
        result = validate_hub_config(_valid_values(lab_image="   "))
        assert not result.ok

    def test_all_errors_aggregated(self):
        result = validate_hub_config(_valid_values(admin="", lab_image="", namespace=""))
        assert len(result.errors) >= 3


class TestConsistencyErrors:
    def test_equal_network_roles_is_error(self):
        result = validate_hub_config(
            _valid_values(lab_network_role_label="net", gpuinfo_network_role_label="net")
        )
        assert not result.ok
        assert any("indistinguishable" in e for e in result.errors)

    def test_equal_volume_roles_is_error(self):
        result = validate_hub_config(
            _valid_values(shared_volume_role_label="vol", docker_proxy_volume_role_label="vol")
        )
        assert not result.ok
        assert any("indistinguishable" in e for e in result.errors)

    def test_name_template_without_username_is_error(self):
        result = validate_hub_config(_valid_values(lab_container_name_template="jupyterlab-fixed"))
        assert not result.ok
        assert any("{username}" in e for e in result.errors)

    def test_user_compose_template_without_username_is_error(self):
        result = validate_hub_config(_valid_values(user_compose_project_template="containers"))
        assert not result.ok
        assert any("per-user docker compose" in e for e in result.errors)

    def test_proxy_owner_value_without_username_is_error(self):
        result = validate_hub_config(_valid_values(docker_proxy_owner_label_value="owner"))
        assert not result.ok
        assert any("{username}" in e for e in result.errors)


class TestWarnings:
    def test_unresolved_gpuinfo_network_warns_not_errors(self):
        result = validate_hub_config(_valid_values(gpuinfo_network_name=""))
        assert result.ok  # degraded, still boots
        assert any("GPU features are OFF" in w for w in result.warnings)

    def test_unresolved_shared_volume_warns_not_errors(self):
        result = validate_hub_config(_valid_values(shared_volume_name=""))
        assert result.ok
        assert any("/mnt/shared" in w for w in result.warnings)

    def test_missing_branding_file_warns(self):
        result = validate_hub_config(
            _valid_values(branding_logo_uri="file:///does/not/exist.png"),
            path_exists=lambda p: False,
        )
        assert result.ok
        assert any("hub logo" in w for w in result.warnings)

    def test_existing_branding_file_no_warn(self):
        result = validate_hub_config(
            _valid_values(branding_logo_uri="file:///exists.png"),
            path_exists=lambda p: True,
        )
        assert result.warnings == []

    def test_http_branding_uri_never_warns(self):
        result = validate_hub_config(
            _valid_values(branding_favicon_uri="https://cdn.example/favicon.ico"),
            path_exists=lambda p: False,
        )
        assert result.warnings == []


class TestRaiseIfErrors:
    def test_raises_systemexit_on_error(self):
        result = validate_hub_config(_valid_values(admin=""))
        with pytest.raises(SystemExit, match="refusing to start"):
            result.raise_if_errors()

    def test_no_raise_when_clean(self):
        result = validate_hub_config(_valid_values())
        result.raise_if_errors()  # must not raise

    def test_warnings_logged_then_no_raise(self):
        logged = []

        class _Log:
            def warning(self, fmt, *args):
                logged.append(fmt % args)

        result = validate_hub_config(_valid_values(shared_volume_name=""))
        result.raise_if_errors(log=_Log())
        assert any("/mnt/shared" in m for m in logged)

    def test_warnings_logged_even_when_raising(self):
        logged = []

        class _Log:
            def warning(self, fmt, *args):
                logged.append(fmt % args)

        result = validate_hub_config(_valid_values(admin="", shared_volume_name=""))
        with pytest.raises(SystemExit):
            result.raise_if_errors(log=_Log())
        assert any("/mnt/shared" in m for m in logged)


class TestValidationResult:
    def test_empty_result_is_ok(self):
        assert ValidationResult().ok

    def test_result_with_error_not_ok(self):
        assert not ValidationResult(errors=["boom"]).ok

    def test_result_with_only_warning_is_ok(self):
        assert ValidationResult(warnings=["heads up"]).ok
