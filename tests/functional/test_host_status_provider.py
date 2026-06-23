"""Host-status provider seam - end-to-end.

The home-screen host aggregate is delegated to a spawner-declared HostStatusProvider
(DuoptimumDockerSpawner -> DockerHostStatusProvider). The activity API now reports
`host_capabilities` (the dimensions this environment exposes) and the portal renders
only those rows, hiding the panel entirely when none are present.

Two angles:
  - real stack: the live API reports cpu+mem, and gpu iff the platform has GPU
  - route-mocked: the frontend gates each row on host_capabilities (subset -> only
    those rows; empty -> no panel). The /activity response is intercepted and only
    host_capabilities rewritten, so this exercises the presence-gating in isolation.

The full-capability view (all three rows, unchanged) is covered by test_host_status
and test_resource_bars.
"""

import json

import pytest
from playwright.sync_api import expect


def _host_card(page):
    return page.locator(".ant-card").filter(has=page.locator("h3", has_text="Host Status"))


def _gpu_enabled(page):
    return bool(page.evaluate("() => !!(window.jhdata && window.jhdata.gpu_enabled)"))


def _route_host_capabilities(page, caps):
    """Intercept the activity API and rewrite ONLY host_capabilities, replaying the
    real (authenticated) response for everything else."""
    def handler(route):
        resp = route.fetch()
        try:
            data = resp.json()
        except Exception:
            route.fulfill(response=resp)
            return
        data["host_capabilities"] = caps
        route.fulfill(status=resp.status, content_type="application/json", body=json.dumps(data))
    page.route("**/hub/api/activity**", handler)


@pytest.mark.acc_crit(
    "host-status-provider::Handler delegates",
    "host-status-provider::GPU capability gated",
)
def test_activity_reports_host_capabilities(admin_portal, base_url, admin_api):
    # the seam is live: the activity API reports the provider's capabilities. A local
    # Docker host always exposes cpu+mem; gpu only when the platform has GPU.
    caps = admin_api.get(f"{base_url}/hub/api/activity", timeout=30).json().get("host_capabilities")
    assert isinstance(caps, list), "activity response is missing host_capabilities"
    assert "cpu" in caps and "mem" in caps, f"cpu/mem must always be exposed by the Docker host: {caps}"

    page = admin_portal.goto("/home", ready=".doh-res-row")
    assert ("gpu" in caps) == _gpu_enabled(page), \
        f"gpu capability {('gpu' in caps)} disagrees with the platform GPU flag"


@pytest.mark.acc_crit(
    "host-status-provider::Presence-gated render",
    "host-status-provider::Frontend test",
)
def test_panel_renders_only_capable_rows(admin_portal):
    # provider exposes CPU only -> the Host Status panel shows the CPU row and drops
    # Memory and GPU. Scoped to the Host Status card (the Server Status hero has its
    # own CPU/Memory rows).
    _route_host_capabilities(admin_portal.page, ["cpu"])
    page = admin_portal.goto("/home", ready=".doh-res-row")
    card = _host_card(page)
    expect(card).to_be_visible()
    expect(card.locator(".doh-res-label", has_text="CPU")).to_have_count(1)
    expect(card.locator(".doh-res-label", has_text="Memory")).to_have_count(0)
    expect(card.locator(".doh-res-label", has_text="GPU")).to_have_count(0)


@pytest.mark.acc_crit(
    "host-status-provider::Edge: empty capabilities",
    "host-status-provider::Frontend test",
)
def test_panel_hidden_when_no_capabilities(admin_portal):
    # provider exposes nothing -> the Host Status panel disappears entirely (no empty
    # shell). The rest of /home (Server Status hero, metric cards) still renders.
    _route_host_capabilities(admin_portal.page, [])
    page = admin_portal.goto("/home", ready=".ant-layout")
    expect(_host_card(page)).to_have_count(0)


@pytest.mark.gpu
@pytest.mark.acc_crit(
    "host-status-provider::GPU capability gated",
    "host-status-provider::Handler delegates",
)
def test_host_capabilities_includes_gpu_when_live(admin_portal, base_url, admin_api):
    # GPU regime: the provider advertises gpu in host_capabilities and the GPU row
    # renders via the capability path.
    page = admin_portal.goto("/home", ready=".doh-res-row")
    if not _gpu_enabled(page):
        pytest.skip("GPU not enabled on this stack (run the gpu regime / mock sidecar)")
    caps = admin_api.get(f"{base_url}/hub/api/activity", timeout=30).json().get("host_capabilities")
    assert isinstance(caps, list) and "gpu" in caps, f"gpu must be a capability when the platform has GPU: {caps}"
    card = _host_card(page)
    expect(card.locator(".doh-res-label", has_text="GPU")).to_have_count(1)


@pytest.mark.gpu
@pytest.mark.acc_crit(
    "host-status-provider::Presence-gated render",
    "host-status-provider::Frontend test",
)
def test_panel_gpu_only_via_caps(admin_portal):
    # GPU regime: provider exposes GPU only -> the Host Status panel shows the GPU row
    # and drops CPU and Memory (the complement of the cpu-only subset case).
    page0 = admin_portal.goto("/home", ready=".doh-res-row")
    if not _gpu_enabled(page0):
        pytest.skip("GPU not enabled on this stack")
    _route_host_capabilities(admin_portal.page, ["gpu"])
    page = admin_portal.goto("/home", ready=".doh-res-row")
    card = _host_card(page)
    expect(card.locator(".doh-res-label", has_text="GPU")).to_have_count(1)
    expect(card.locator(".doh-res-label", has_text="CPU")).to_have_count(0)
    expect(card.locator(".doh-res-label", has_text="Memory")).to_have_count(0)
