"""Unit tests for the pure discriminators in the download-block handlers.

These two helpers decide block-vs-allow and what the toast names, so they get
direct coverage independent of the Tornado machinery around them.
"""

from stellars_hub_services.handlers.downloads import (
    _filename_from_path,
    _is_download_arg,
)


class TestIsDownloadArg:
    def test_absent_is_not_download(self):
        assert _is_download_arg(None) is False

    def test_truthy_values_are_downloads(self):
        for v in ('1', 'true', 'True', 'TRUE', 'yes', 'anything'):
            assert _is_download_arg(v) is True, v

    def test_falsy_spellings_are_not_downloads(self):
        for v in ('', '0', 'false', 'False', 'no', 'off', '  '):
            assert _is_download_arg(v) is False, v


class TestFilenameFromPath:
    def test_basename(self):
        assert _filename_from_path('files/sub/dir/secret.csv') == 'secret.csv'

    def test_trailing_slash_directory(self):
        assert _filename_from_path('files/sub/dir/') == 'dir'

    def test_empty(self):
        assert _filename_from_path('') == ''
