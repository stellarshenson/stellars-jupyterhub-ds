"""Servers CPU/MEM cells + explanatory column-header tooltips.

acc-crit-duoptimumhub.md -> "Servers host-relative resources":
- the per-server CPU cell is total CPU used (docker/top: 100% = one core) and ends
  in "%"; the MEM cell is the absolute GB used and ends in "GB"
- the cell tooltips reveal the assigned breakdown ("cores used" / "GB used" / "of
  assigned")
- the CPU/MEM column HEADERS carry an explanatory tooltip on hover so the
  host-relative figures are not misread

The header-tooltip checks need no running server (the columns render regardless);
the cell checks launch a lab and wait for the stats sample to land.
"""

import time

import pytest
from playwright.sync_api import expect


def _xsrf(s):
    return s.cookies.get("_xsrf")


def _post(s, base, path):
    return s.post(f"{base}{path}", headers={"X-XSRFToken": _xsrf(s)}, timeout=60)


def _delete(s, base, path):
    return s.delete(f"{base}{path}", headers={"X-XSRFToken": _xsrf(s)}, timeout=60)


def _ready(admin_api, base, user):
    r = admin_api.get(f"{base}/hub/api/users/{user}", timeout=30)
    srv = (r.json() or {}).get("servers", {}) if r.status_code < 400 else {}
    return bool(srv.get("", {}).get("ready"))


def _wait(pred, timeout=120, interval=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return False


@pytest.mark.acc_crit(
    "servers-host-relative-resources::CPU header tooltip",
    "servers-host-relative-resources::MEM header tooltip",
)
def test_cpu_mem_column_header_tooltips(admin_portal):
    """The CPU and Mem column headers explain what they measure on hover (antd
    Tooltip). No running server required - the columns render either way."""
    page = admin_portal.goto("/servers", ready=".ant-table")

    page.get_by_role("columnheader", name="CPU", exact=True).hover()
    expect(page.locator(".ant-tooltip-inner")).to_contain_text("one core")

    # move off, then hover the Mem header so a fresh tooltip renders
    page.mouse.move(0, 0)
    page.get_by_role("columnheader", name="Mem", exact=True).hover()
    expect(page.locator(".ant-tooltip-inner")).to_contain_text("Memory used")


@pytest.mark.acc_crit(
    "servers-host-relative-resources::CPU counter = cores-used %",
    "servers-host-relative-resources::MEM counter = absolute GB",
    "servers-host-relative-resources::Tooltips reveal all",
)
def test_cpu_mem_cells_report_cores_and_gb(admin_portal, base_url, admin_api):
    """A running server's CPU cell ends in "%" (cores-used, docker/top) and its MEM
    cell ends in "GB" (absolute); both cell tooltips reveal the assigned breakdown."""
    user = "res-user"
    _delete(admin_api, base_url, f"/hub/api/users/{user}")
    assert _post(admin_api, base_url, f"/hub/api/users/{user}").status_code < 400

    try:
        _post(admin_api, base_url, f"/hub/api/users/{user}/server")
        assert _wait(lambda: _ready(admin_api, base_url, user)), "server never became ready"
        time.sleep(8)
        _post(admin_api, base_url, "/hub/api/activity/sample")

        # the page does not live-refresh fast enough for the first stats sample, so
        # reload until the CPU cell (a .oh-num carrying the "cores used" tooltip) lands
        cpu_cell = mem_cell = None
        for _ in range(12):
            page = admin_portal.goto("/servers", ready=".ant-table")
            row = page.locator("tr.ant-table-row").filter(has_text=user).first
            expect(row).to_be_visible()
            cpu_cell = row.locator('span.oh-num[title*="cores used"]')
            mem_cell = row.locator('span.oh-num[title*="GB used"]')
            if cpu_cell.count() and mem_cell.count():
                break
            time.sleep(3)

        assert cpu_cell and cpu_cell.count(), "CPU cell never reported a sampled value"
        # CPU = cores-used %, ends in "%"; tooltip reveals cores used + % of assigned
        assert (cpu_cell.first.inner_text()).strip().endswith("%")
        cpu_tip = cpu_cell.first.get_attribute("title") or ""
        assert "cores used" in cpu_tip and "of assigned" in cpu_tip, cpu_tip
        # MEM = absolute GB, ends in "GB"; tooltip reveals GB used + % of assigned
        assert (mem_cell.first.inner_text()).strip().endswith("GB")
        mem_tip = mem_cell.first.get_attribute("title") or ""
        assert "GB used" in mem_tip and "of assigned" in mem_tip, mem_tip
    finally:
        _delete(admin_api, base_url, f"/hub/api/users/{user}/server")
        _delete(admin_api, base_url, f"/hub/api/users/{user}")
