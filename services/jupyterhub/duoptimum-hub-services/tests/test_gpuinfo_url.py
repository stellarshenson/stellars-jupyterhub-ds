"""resolve_gpuinfo_url() - the {hostname} substitution that fills the sidecar URL
template with the address the hub DISCOVERS for the running sidecar, so the host is
never hardcoded.

The URL is configured as a template (``http://{hostname}:8000``); at boot the hub
creates the sidecar, reads its address (IP on the dedicated network) from the live
container, and substitutes it here. A literal URL (no placeholder) passes through
unchanged; an empty hostname leaves the placeholder so the host stays unreachable
(GPU degrades to off) rather than silently inventing one.
"""

from duoptimum_hub_services.gpuinfo_sidecar import resolve_gpuinfo_url


def test_substitutes_hostname_with_discovered_ip():
    assert resolve_gpuinfo_url("http://{hostname}:8000", "172.20.0.3") == "http://172.20.0.3:8000"


def test_substitutes_hostname_with_container_name_fallback():
    assert resolve_gpuinfo_url("http://{hostname}:8000", "gpuinfo-nvidia") == "http://gpuinfo-nvidia:8000"


def test_literal_url_passes_through_unchanged():
    assert resolve_gpuinfo_url("http://gpuinfo-nvidia:8000", "172.20.0.3") == "http://gpuinfo-nvidia:8000"


def test_empty_hostname_leaves_placeholder():
    # no discovered host -> no substitution; the unreachable {hostname} degrades to GPU-off, never a guess
    assert resolve_gpuinfo_url("http://{hostname}:8000", "") == "http://{hostname}:8000"


def test_empty_url_passes_through():
    assert resolve_gpuinfo_url("", "172.20.0.3") == ""
