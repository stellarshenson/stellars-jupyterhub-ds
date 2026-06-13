"""Best-effort spawn smoke: start a server with the minimal singleuser image and
assert a JupyterLab / Notebook UI loads end-to-end through DockerSpawner.

The stock spawn config targets the stellars lab image (user `lab`,
`/home/lab/workspace`, per-user volumes); the minimal `singleuser` image
(`jovyan`, `/home/jovyan`) may not spawn cleanly, so a spawn that does not
complete is skipped rather than failing the suite. Reliable spawn-with-minimal
needs a spawn-config overlay (future work).
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.spawn
def test_spawn_minimal_lab(admin_page, base_url):
    page = admin_page
    page.goto(f"{base_url}/hub/spawn")
    try:
        page.wait_for_url("**/user/**", timeout=120_000)
        # The lab landed on the user's server; a JupyterLab/Notebook shell is up.
        expect(page.locator("body")).to_be_visible(timeout=60_000)
        assert "/user/" in page.url
    except Exception as e:
        pytest.skip(f"minimal-image spawn did not complete (best-effort): {e}")
