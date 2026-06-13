"""Multi-step functional scenarios over the group / policy model - beyond single
UI actions, these drive realistic operator flows end-to-end through the running
hub: configure several policies on a group and verify the resolved badges and
hover tooltip, and reorder group priority. This is the layer that grows as the
platform evolves; add new scenarios here.
"""

from playwright.sync_api import expect

BASE = "/hub/groups"


def _create_group(page, base_url, name):
    page.goto(f"{base_url}{BASE}")
    page.get_by_role("button", name="Add Group").click()
    expect(page.locator("#add-group-modal")).to_be_visible()
    page.fill("#new-group-name", name)
    page.click("#create-group-btn")
    expect(page.locator(f"#groups-table-body tr[data-name='{name}']")).to_be_visible()


def _open_config(page, name):
    page.locator(f"#groups-table-body a.btn-config[data-name='{name}']").click()
    expect(page.locator("#config-group-modal")).to_be_visible()


def _delete_group(page, name):
    page.once("dialog", lambda d: d.accept())
    page.locator(f"#groups-table-body tr[data-name='{name}'] .btn-delete").click()
    page.wait_for_timeout(1000)
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.locator(f"#groups-table-body tr[data-name='{name}']")).to_have_count(0, timeout=10000)


def test_multi_policy_badges_and_tooltip(admin_page, base_url):
    name = "scen-multi"
    page = admin_page
    _create_group(page, base_url, name)
    _open_config(page, name)

    # Sudo on but disabled for members; downloads configured to block; memory cap 8G.
    page.check("#config-sudo-active")
    page.uncheck("#config-sudo-enable")
    page.check("#config-downloads-active")
    page.uncheck("#config-downloads-allow")
    page.check("#config-mem-limit-enabled")
    page.fill("#config-mem-limit-gb", "8")
    page.click("#save-config-btn")
    expect(page.locator("#config-group-modal")).to_be_hidden()

    row = page.locator(f"#groups-table-body tr[data-name='{name}']")
    expect(row).to_contain_text("Sudo off")
    expect(row).to_contain_text("Downloads off")
    expect(row).to_contain_text("Mem")

    # The hover tooltip (native title attr) is server-rendered from policy_summary.
    title = page.locator(f"#groups-table-body a.btn-config[data-name='{name}']").get_attribute("title")
    assert "Sudo: off" in title
    assert "Downloads: blocked" in title
    assert "Memory: 8" in title

    _delete_group(page, name)


def test_priority_reorder(admin_page, base_url):
    page = admin_page
    a, b = "scen-prio-a", "scen-prio-b"
    _create_group(page, base_url, a)
    _create_group(page, base_url, b)

    # Record the row order of the two test groups, then move the lower one up.
    def order():
        names = page.locator("#groups-table-body tr").evaluate_all(
            "rows => rows.map(r => r.getAttribute('data-name'))")
        return [n for n in names if n in (a, b)]

    before = order()
    lower = before[-1]
    page.locator(f"#groups-table-body tr[data-name='{lower}'] .btn-move-up").click()
    expect(page.locator(f"#groups-table-body tr[data-name='{lower}']")).to_be_visible()

    after = order()
    assert after[0] == lower, f"expected {lower} to move up; before={before} after={after}"

    _delete_group(page, a)
    _delete_group(page, b)
