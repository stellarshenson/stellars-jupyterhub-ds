"""Functional tests for branding.py - logo, favicon, JupyterLab icons."""

import os


class TestDefaults:
    def test_returns_dict_with_expected_keys(self):
        """Default branding returns dict with all keys empty/None."""
        from optimum_hub_services.branding import setup_branding
        result = setup_branding()

        assert isinstance(result, dict)
        expected_keys = {'logo_file', 'favicon_uri', 'favicon_busy_target',
                         'lab_main_icon_static', 'lab_main_icon_url',
                         'lab_splash_icon_static', 'lab_splash_icon_url', 'stage'}
        assert set(result.keys()) == expected_keys
        assert result['logo_file'] is None
        assert result['favicon_uri'] == ''
        assert result['favicon_busy_target'] == ''
        assert result['lab_main_icon_static'] == ''
        assert result['lab_main_icon_url'] == ''
        assert result['lab_splash_icon_static'] == ''
        assert result['lab_splash_icon_url'] == ''
        assert result['stage'] == ''


class TestLogo:
    def test_file_uri_existing_sets_logo_file(self, tmp_path):
        """file:// with existing file sets logo_file."""
        logo = tmp_path / "logo.svg"
        logo.write_text("<svg/>")

        from optimum_hub_services.branding import setup_branding
        result = setup_branding(logo_uri=f"file://{logo}")
        assert result['logo_file'] == str(logo)

    def test_file_uri_nonexistent_leaves_none(self):
        """file:// with nonexistent file leaves logo_file as None."""
        from optimum_hub_services.branding import setup_branding
        result = setup_branding(logo_uri="file:///no/such/file.svg")
        assert result['logo_file'] is None


class TestFavicon:
    def test_file_uri_copies_to_static(self, monkeypatch, tmp_path):
        """file:// favicon copies to static dir and clears favicon_uri."""
        favicon = tmp_path / "favicon.ico"
        favicon.write_bytes(b'\x00\x00\x01\x00')

        # Create the expected static path structure
        share_dir = tmp_path / "share" / "jupyterhub" / "static"
        share_dir.mkdir(parents=True)

        monkeypatch.setattr("optimum_hub_services.branding.sys", type("sys", (), {"prefix": str(tmp_path)})())

        from optimum_hub_services.branding import setup_branding
        result = setup_branding(favicon_uri=f"file://{favicon}")

        assert result['favicon_uri'] == ''
        assert (share_dir / "favicon.ico").exists()

    def test_url_passes_through(self):
        """URL favicon passes through in favicon_uri."""
        from optimum_hub_services.branding import setup_branding
        result = setup_branding(favicon_uri="https://example.com/fav.ico")
        assert result['favicon_uri'] == "https://example.com/fav.ico"


class TestBusyFavicon:
    def test_file_uri_copies_and_sets_static_target(self, monkeypatch, tmp_path):
        """file:// busy favicon copies to favicon-busy.ico and returns the hub-static target."""
        busy = tmp_path / "busy.ico"
        busy.write_bytes(b'\x00\x00\x01\x00')

        share_dir = tmp_path / "share" / "jupyterhub" / "static"
        share_dir.mkdir(parents=True)
        monkeypatch.setattr("optimum_hub_services.branding.sys", type("sys", (), {"prefix": str(tmp_path)})())

        from optimum_hub_services.branding import setup_branding
        result = setup_branding(favicon_busy_uri=f"file://{busy}")

        assert result['favicon_busy_target'] == 'hub/static/favicon-busy.ico'
        assert (share_dir / "favicon-busy.ico").exists()

    def test_file_uri_nonexistent_leaves_empty(self):
        """file:// busy favicon that doesn't exist leaves the target empty (no override)."""
        from optimum_hub_services.branding import setup_branding
        result = setup_branding(favicon_busy_uri="file:///no/such/busy.ico")
        assert result['favicon_busy_target'] == ''

    def test_url_passes_through_as_target(self):
        """URL busy favicon is used as the redirect target directly."""
        from optimum_hub_services.branding import setup_branding
        result = setup_branding(favicon_busy_uri="https://example.com/busy.ico")
        assert result['favicon_busy_target'] == "https://example.com/busy.ico"

    def test_empty_leaves_target_empty(self):
        """Empty busy URI leaves the target empty (JupyterLab default busy frames)."""
        from optimum_hub_services.branding import setup_branding
        result = setup_branding(favicon_uri="file:///some/fav.ico")
        assert result['favicon_busy_target'] == ''


class TestLabIcons:
    def test_file_uri_copies_with_extension(self, monkeypatch, tmp_path):
        """file:// lab icon copies to static dir with correct static name."""
        icon = tmp_path / "icon.png"
        icon.write_bytes(b'\x89PNG')

        share_dir = tmp_path / "share" / "jupyterhub" / "static"
        share_dir.mkdir(parents=True)
        monkeypatch.setattr("optimum_hub_services.branding.sys", type("sys", (), {"prefix": str(tmp_path)})())

        from optimum_hub_services.branding import setup_branding
        result = setup_branding(lab_main_icon_uri=f"file://{icon}")

        assert result['lab_main_icon_static'] == 'lab-main-icon.png'
        assert (share_dir / "lab-main-icon.png").exists()
        assert result['lab_main_icon_url'] == ''

    def test_url_passes_through(self):
        """URL lab icon passes through in lab_*_icon_url."""
        from optimum_hub_services.branding import setup_branding
        result = setup_branding(
            lab_main_icon_uri="https://example.com/icon.svg",
            lab_splash_icon_uri="https://example.com/splash.svg",
        )

        assert result['lab_main_icon_url'] == "https://example.com/icon.svg"
        assert result['lab_main_icon_static'] == ''
        assert result['lab_splash_icon_url'] == "https://example.com/splash.svg"
        assert result['lab_splash_icon_static'] == ''


class TestStage:
    def test_default_empty(self):
        """No stage -> empty string (no badge)."""
        from optimum_hub_services.branding import setup_branding
        assert setup_branding()['stage'] == ''

    def test_value_passthrough(self):
        """A stage value is returned as-is."""
        from optimum_hub_services.branding import setup_branding
        assert setup_branding(stage='PRD')['stage'] == 'PRD'

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace trimmed; whitespace-only -> empty."""
        from optimum_hub_services.branding import setup_branding
        assert setup_branding(stage='  DEV  ')['stage'] == 'DEV'
        assert setup_branding(stage='   ')['stage'] == ''

    def test_custom_text_passthrough(self):
        """Unrecognised text is preserved (the frontend greys it)."""
        from optimum_hub_services.branding import setup_branding
        assert setup_branding(stage='STAGING')['stage'] == 'STAGING'
