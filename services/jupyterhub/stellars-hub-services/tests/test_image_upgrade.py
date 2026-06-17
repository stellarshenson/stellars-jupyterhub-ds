"""Lab-image upgrade detection (pure recency comparison).

`image_upgrade_available` decides whether the home "Upgrade available" pill shows:
is the most recent local image (from `docker image ls`) created later than the
image the running container uses? `Created` values are docker epochs (ints).
Unknown values never offer an upgrade.
"""

from stellars_hub_services.docker_utils import image_upgrade_available


def test_upgrade_when_local_newer():
    assert image_upgrade_available(2000, 1000) is True


def test_no_upgrade_when_same_age():
    assert image_upgrade_available(1000, 1000) is False


def test_no_upgrade_when_local_older():
    assert image_upgrade_available(1000, 2000) is False


def test_no_upgrade_when_newest_unknown():
    # docker image ls empty / unreachable -> never offer an upgrade
    assert image_upgrade_available(None, 1000) is False


def test_no_upgrade_when_container_unknown():
    assert image_upgrade_available(2000, None) is False


def test_no_upgrade_when_both_unknown():
    assert image_upgrade_available(None, None) is False
