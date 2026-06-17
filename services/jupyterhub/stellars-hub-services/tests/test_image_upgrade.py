"""Lab-image upgrade detection (image-id comparison).

`image_upgrade_available` decides whether the home "Upgrade available" pill shows:
does the lab image tag now resolve to a different image than the one the running
container uses, and is that the repo's newest image? It compares image IDs, not
`Created` times - the running container's image is frequently pruned right after a
rebuild (the very moment an upgrade exists), so its timestamp is unreadable.
Unknown values never offer an upgrade.
"""

from stellars_hub_services.docker_utils import image_upgrade_available


def test_upgrade_when_tag_moved_to_newest():
    # :latest now points at B (the repo's newest); container runs A -> upgrade
    assert image_upgrade_available('B', 'A', 'B') is True


def test_no_upgrade_when_running_the_tag():
    assert image_upgrade_available('A', 'A', 'A') is False


def test_no_upgrade_when_tag_retagged_to_older():
    # :latest was re-tagged to OLD while a NEWer image exists -> never a false pill
    assert image_upgrade_available('OLD', 'A', 'NEW') is False


def test_no_upgrade_when_tag_unknown():
    # docker image ls empty / tag unresolved -> never offer an upgrade
    assert image_upgrade_available(None, 'A', 'B') is False


def test_no_upgrade_when_container_unknown():
    assert image_upgrade_available('B', None, 'B') is False


def test_no_upgrade_when_both_unknown():
    assert image_upgrade_available(None, None, None) is False
