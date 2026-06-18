"""Unit tests for the pure discriminators in the download-block handlers.

These two helpers decide block-vs-allow and what the toast names, so they get
direct coverage independent of the Tornado machinery around them.
"""

from duoptimum_hub_services.handlers.downloads import (
    _filename_from_path,
    _is_download_arg,
    _is_download_request,
)


class _FakeRequest:
    def __init__(self, headers, method):
        self.headers = headers
        self.method = method


class _FakeHandler:
    """Minimal stand-in exposing the surfaces _is_download_request reads:
    get_argument('download'), request.headers.get('Sec-Fetch-Dest'),
    request.method."""

    def __init__(self, download=None, dest=None, method='GET'):
        self._download = download
        headers = {}
        if dest is not None:
            headers['Sec-Fetch-Dest'] = dest
        self.request = _FakeRequest(headers, method)

    def get_argument(self, name, default=None):
        if name == 'download':
            return self._download if self._download is not None else default
        return default


class TestIsDownloadArg:
    def test_absent_is_not_download(self):
        assert _is_download_arg(None) is False

    def test_truthy_values_are_downloads(self):
        for v in ('1', 'true', 'True', 'TRUE', 'yes', 'anything'):
            assert _is_download_arg(v) is True, v

    def test_falsy_spellings_are_not_downloads(self):
        for v in ('', '0', 'false', 'False', 'no', 'off', '  '):
            assert _is_download_arg(v) is False, v


class TestIsDownloadRequest:
    # Inline subresource renders must keep working for a blocked user.
    def test_inline_media_dests_are_allowed(self):
        for dest in ('image', 'video', 'audio', 'font', 'style', 'script',
                     'object', 'embed', 'iframe', 'frame', 'track', 'manifest'):
            assert _is_download_request(_FakeHandler(dest=dest)) is False, dest

    def test_inline_dest_is_case_insensitive(self):
        assert _is_download_request(_FakeHandler(dest='IMAGE')) is False

    # Download / open-to-save vectors must block.
    def test_empty_dest_blocks(self):
        # fetch() and <a download> clicks
        assert _is_download_request(_FakeHandler(dest='empty')) is True

    def test_document_dest_blocks(self):
        # top-level navigation / open file URL in a new tab
        assert _is_download_request(_FakeHandler(dest='document')) is True

    def test_absent_dest_blocks_fail_closed(self):
        # non-browser client, or plain-HTTP context that omits fetch-metadata
        assert _is_download_request(_FakeHandler(dest=None)) is True

    def test_download_arg_blocks_regardless_of_dest(self):
        # a truthy ?download arg wins even when the dest looks inline
        assert _is_download_request(_FakeHandler(download='1', dest='image')) is True

    def test_download_arg_falsy_with_inline_dest_allowed(self):
        assert _is_download_request(_FakeHandler(download='0', dest='image')) is False

    def test_post_not_classified_by_dest(self):
        # nbconvert inline conversion POSTs carry Sec-Fetch-Dest=empty but are
        # not downloads - only a truthy ?download arg blocks a non-GET/HEAD.
        assert _is_download_request(_FakeHandler(dest='empty', method='POST')) is False
        assert _is_download_request(_FakeHandler(download='1', method='POST')) is True

    def test_head_classified_like_get(self):
        assert _is_download_request(_FakeHandler(dest='document', method='HEAD')) is True
        assert _is_download_request(_FakeHandler(dest='image', method='HEAD')) is False


class TestFilenameFromPath:
    def test_basename(self):
        assert _filename_from_path('files/sub/dir/secret.csv') == 'secret.csv'

    def test_trailing_slash_directory(self):
        assert _filename_from_path('files/sub/dir/') == 'dir'

    def test_empty(self):
        assert _filename_from_path('') == ''
