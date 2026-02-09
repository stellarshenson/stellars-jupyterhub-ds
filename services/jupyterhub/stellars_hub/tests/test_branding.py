"""Functional tests for branding.py - logo, favicon, JupyterLab icons."""

import os


class TestDefaults:
    def test_returns_dict_with_six_keys(self):
        """Default branding returns dict with 6 keys, all empty/None."""
        from stellars_hub.branding import setup_branding
        result = setup_branding()

        assert isinstance(result, dict)
        expected_keys = {'logo_file', 'favicon_uri', 'lab_main_icon_static',
                         'lab_main_icon_url', 'lab_splash_icon_static', 'lab_splash_icon_url'}
        assert set(result.keys()) == expected_keys
        assert result['logo_file'] is None
        assert result['favicon_uri'] == ''
        assert result['lab_main_icon_static'] == ''
        assert result['lab_main_icon_url'] == ''
        assert result['lab_splash_icon_static'] == ''
        assert result['lab_splash_icon_url'] == ''


class TestLogo:
    def test_file_uri_existing_sets_logo_file(self, tmp_path):
        """file:// with existing file sets logo_file."""
        logo = tmp_path / "logo.svg"
        logo.write_text("<svg/>")

        from stellars_hub.branding import setup_branding
        result = setup_branding(logo_uri=f"file://{logo}")
        assert result['logo_file'] == str(logo)

    def test_file_uri_nonexistent_leaves_none(self):
        """file:// with nonexistent file leaves logo_file as None."""
        from stellars_hub.branding import setup_branding
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

        monkeypatch.setattr("stellars_hub.branding.sys", type("sys", (), {"prefix": str(tmp_path)})())

        from stellars_hub.branding import setup_branding
        result = setup_branding(favicon_uri=f"file://{favicon}")

        assert result['favicon_uri'] == ''
        assert (share_dir / "favicon.ico").exists()

    def test_url_passes_through(self):
        """URL favicon passes through in favicon_uri."""
        from stellars_hub.branding import setup_branding
        result = setup_branding(favicon_uri="https://example.com/fav.ico")
        assert result['favicon_uri'] == "https://example.com/fav.ico"


class TestLabIcons:
    def test_file_uri_copies_with_extension(self, monkeypatch, tmp_path):
        """file:// lab icon copies to static dir with correct static name."""
        icon = tmp_path / "icon.png"
        icon.write_bytes(b'\x89PNG')

        share_dir = tmp_path / "share" / "jupyterhub" / "static"
        share_dir.mkdir(parents=True)
        monkeypatch.setattr("stellars_hub.branding.sys", type("sys", (), {"prefix": str(tmp_path)})())

        from stellars_hub.branding import setup_branding
        result = setup_branding(lab_main_icon_uri=f"file://{icon}")

        assert result['lab_main_icon_static'] == 'lab-main-icon.png'
        assert (share_dir / "lab-main-icon.png").exists()
        assert result['lab_main_icon_url'] == ''

    def test_url_passes_through(self):
        """URL lab icon passes through in lab_*_icon_url."""
        from stellars_hub.branding import setup_branding
        result = setup_branding(
            lab_main_icon_uri="https://example.com/icon.svg",
            lab_splash_icon_uri="https://example.com/splash.svg",
        )

        assert result['lab_main_icon_url'] == "https://example.com/icon.svg"
        assert result['lab_main_icon_static'] == ''
        assert result['lab_splash_icon_url'] == "https://example.com/splash.svg"
        assert result['lab_splash_icon_static'] == ''
