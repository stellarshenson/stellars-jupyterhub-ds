"""Host Status panel on the admin Home - DEF-3 (CPU/Memory tooltips when no servers
are active) and DEF-4 (GPU display gated on a LIVE gpuinfo sidecar).

GPU model (operator): "GPU available" = (a) the gpuinfo sidecar is live AND (b) GPUs
are detected, with a -> b (no b without a). The inventory is enumerated at startup and
seeded from a persisted cache that outlives the sidecar, so the display must gate on
the live `gpu_connected` signal, NOT the stale inventory.

Operator's run-1 / run-2 scenario maps onto two functest stacks (skip-gated, like
test_gpu_detection):
  - run 1 (GPU on):  make test-functional-gpu  -> mock gpuinfo sidecar; GPUs visible WITH health
  - run 2 (GPU off): make test-functional       -> GPU off (default); GPUs NOT visible
test_gpu_hidden_when_sidecar_down exercises a -> b directly: the live (mock) sidecar is
stopped and the GPU row must vanish.
"""

import time

import pytest
from playwright.sync_api import expect


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _delete(s, base, path):
    return s.delete(f"{base}{path}", headers={"X-XSRFToken": _xsrf(s)}, timeout=60)


def _wait(pred, timeout=180, interval=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return False


def _me(admin_api, base):
    return admin_api.get(f"{base}/hub/api/user", timeout=30).json()["name"]


def _gpu_enabled(page):
    """The frontend GPU capability (window.jhdata.gpu_enabled) - the startup-detected
    'platform has GPU' flag the widgets gate on."""
    return bool(page.evaluate("() => !!(window.jhdata && window.jhdata.gpu_enabled)"))


def _gpu_connected(admin_api, base):
    """Live sidecar reachability AND inventory (the a-AND-b 'GPU available' state)."""
    return bool(admin_api.get(f"{base}/hub/api/activity", timeout=30).json().get("gpu_connected"))


def _host_card(page):
    return page.locator(".ant-card").filter(has=page.locator("h3", has_text="Host Status"))


# ── DEF-3: Host Status CPU/Memory tooltips when no servers are active ─────────────

@pytest.mark.acc_crit(
    "resource-bars::0% still carries a tooltip",
    "resource-bars::Functional: idle-platform tooltip",
)
def test_host_status_bars_have_tooltips(admin_portal, base_url, admin_api):
    # DEF-3: with no active servers the Host Status CPU/Memory bars must still carry a
    # tooltip (the early-return regression dropped it, leaving a blank, broken-looking
    # bar). Stop the admin's own server so the platform is idle.
    _delete(admin_api, base_url, f"/hub/api/users/{_me(admin_api, base_url)}/server")

    page = admin_portal.goto("/home", ready=".oh-res-row")
    card = _host_card(page)
    expect(card).to_be_visible()
    for label in ("CPU", "Memory"):
        row = card.locator(".oh-res-row").filter(
            has=page.locator(".oh-res-label", has_text=label)
        ).first
        expect(row).to_be_visible()
        tip = (row.locator(".oh-res-val").get_attribute("title") or "").strip()
        assert tip, f"Host Status {label} bar has no tooltip when idle (DEF-3)"


# ── DEF-4: GPU display gated on the live sidecar (a -> b) ─────────────────────────

@pytest.mark.acc_crit(
    "gpu-gating::Host Status hides GPUs when disconnected",
)
def test_gpu_hidden_when_disabled(admin_portal):
    # operator run 2: GPU disabled (JUPYTERHUB_GPU_ENABLED=0) -> NO GPU widget anywhere
    # on the Host Status; the stale persisted inventory must NOT leak through.
    page = admin_portal.goto("/home", ready=".oh-res-row")
    if _gpu_enabled(page):
        pytest.skip("GPU enabled on this stack; run with FUNCTEST_GPU_ENABLED=0 for the disabled case")
    card = _host_card(page)
    assert card.locator(".oh-res-label", has_text="GPU").count() == 0, "GPU row shown while GPU is disabled"
    assert page.locator(".oh-gpurows").count() == 0, "GPU bars shown while GPU is disabled"


@pytest.mark.gpu
@pytest.mark.acc_crit(
    "gpu-gating::Host Status hides GPUs when disconnected",
    "gpu-gating::Edge: connected but idle",
)
def test_gpu_shown_with_health_when_enabled(admin_portal, base_url, admin_api):
    # operator run 1: GPU enabled + sidecar live -> the Host Status GPU row shows WITH
    # live health (the per-GPU tooltip carries utilisation / memory), never bare bars.
    page = admin_portal.goto("/home", ready=".oh-res-row")
    if not _gpu_enabled(page):
        pytest.skip("GPU not enabled on this stack (run `make test-functional-gpu` for the mock sidecar)")
    if not _gpu_connected(admin_api, base_url):
        pytest.skip("gpuinfo sidecar not connected; cannot assert live health")
    card = _host_card(page)
    rows = card.locator(".oh-gpurow")
    expect(rows.first).to_be_visible()
    tip = rows.first.get_attribute("title") or ""
    assert ("Utilisation" in tip) or ("Memory" in tip), \
        f"GPU row shows no live health while the sidecar is connected (DEF-4): {tip!r}"


@pytest.mark.gpu
@pytest.mark.acc_crit(
    "gpu-gating::Runtime: sidecar down hides GPUs",
)
def test_gpu_hidden_when_sidecar_down(admin_portal, base_url, admin_api, docker_client):
    # DEF-4 a -> b end-to-end: with GPU on + sidecar live the GPU row shows; stop the
    # gpuinfo sidecar and the row must disappear (no stale inventory with no health);
    # restart it for the rest of the suite.
    page = admin_portal.goto("/home", ready=".oh-res-row")
    if not _gpu_enabled(page):
        pytest.skip("GPU not enabled on this stack")
    if not _gpu_connected(admin_api, base_url):
        pytest.skip("gpuinfo sidecar not connected at start")
    assert page.locator(".oh-gpurows").count() >= 1, "expected the GPU row to show while connected"

    sidecar = next((c for c in docker_client.containers.list() if "gpuinfo-nvidia" in c.name), None)
    if sidecar is None:
        pytest.skip("gpuinfo sidecar container not found")

    sidecar.stop()
    try:
        # the next empty sample flips gpu_connected off (last_ok False); poll the API
        assert _wait(lambda: not _gpu_connected(admin_api, base_url), timeout=180, interval=5), \
            "sidecar stopped but gpu_connected stayed true"
        page = admin_portal.goto("/home", ready=".oh-res-row")
        assert page.locator(".oh-gpurows").count() == 0, \
            "GPU row still shown after the sidecar went down (DEF-4)"
    finally:
        sidecar.start()
