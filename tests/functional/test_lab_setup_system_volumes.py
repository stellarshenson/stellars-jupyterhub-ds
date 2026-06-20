"""Lab Setup: system-volumes panel (#383).

The Lab Setup page shows a second panel for the platform system volumes - the
shared volume and the docker-proxy sockets volume - resolved by their
duoptimum-hub.volume.role labels and described by their duoptimum-hub.volume.
description labels (NOT volumes_dictionary.yml, which stays lab-only).

End-to-end on the rebuilt image:
- /hub/api/activity carries system_volumes with the shared (role=shared,
  mount=/mnt/shared) and docker-proxy (role=docker-proxy, mount=/run/dockersock)
  rows, each with its description read off the volume label
- the Lab Setup page renders the System Volumes panel + the policy-controlled
  access note
"""

import re

import pytest
from playwright.sync_api import expect


def _activity(admin_api, base_url):
    r = admin_api.get(f"{base_url}/hub/api/activity", timeout=30)
    assert r.status_code == 200, f"/activity {r.status_code}: {r.text[:200]}"
    return r.json()


def _row(system_volumes, role):
    rows = [v for v in system_volumes if v.get("role") == role]
    assert rows, f"no system volume with role={role!r} in {system_volumes}"
    return rows[0]


@pytest.mark.acc_crit(
    "lab-setup-system-volumes::Payload carries system_volumes",
    "lab-setup-system-volumes::Shared volume row",
    "lab-setup-system-volumes::Docker-proxy volume row",
    "lab-setup-system-volumes::Descriptions from labels",
)
def test_system_volumes_in_activity(admin_api, base_url):
    sv = _activity(admin_api, base_url).get("system_volumes")
    assert isinstance(sv, list) and sv, f"system_volumes missing/empty: {sv!r}"

    shared = _row(sv, "shared")
    assert shared["mount"] == "/mnt/shared"
    assert shared["name"], "shared volume name not resolved"
    assert shared["description"] == "Platform-wide shared storage for all users"

    proxy = _row(sv, "docker-proxy")
    assert proxy["mount"] == "/run/dockersock"
    assert proxy["name"], "docker-proxy volume name not resolved"
    assert proxy["description"] == "Per-user docker-proxy sockets"


@pytest.mark.acc_crit(
    "lab-setup-system-volumes::Panel present",
    "lab-setup-system-volumes::Policy note",
)
def test_lab_setup_page_shows_system_volumes_panel(admin_portal):
    page = admin_portal.goto("/lab-container")
    # both panels render
    expect(page.get_by_text("Standard Volumes", exact=True)).to_be_visible()
    expect(page.get_by_text("System Volumes", exact=True)).to_be_visible()
    # the shared volume description (read off the label) is shown in the panel
    expect(page.get_by_text("Platform-wide shared storage for all users", exact=False)).to_be_visible()
    # the policy-controlled access note is present (single terse notice copy)
    expect(page.get_by_text(re.compile(r"granted by group policy"))).to_be_visible()
