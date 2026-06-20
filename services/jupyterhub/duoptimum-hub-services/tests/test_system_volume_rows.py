"""Tests for build_system_volume_rows (Lab Setup system-volumes panel data).

Pure builder: turns resolved (name, mount, role) specs + a label reader into the
UI rows the Lab Setup page renders. read_labels is injected so these run without
docker. Covers: both volumes present, each absent, both absent, missing volume,
label-less volume, description passthrough, order.
"""

from duoptimum_hub_services.docker_utils import build_system_volume_rows

DESC_KEY = "duoptimum-hub.volume.description"

SHARED = ("hub_shared", "/mnt/shared", "shared")
PROXY = ("hub_docker", "/run/dockersock", "docker-proxy")


def _labels(mapping):
    """read_labels stub: name -> labels dict, None when the name is absent."""
    return lambda name: mapping.get(name)


def test_both_present_with_descriptions():
    rows = build_system_volume_rows(
        [SHARED, PROXY],
        DESC_KEY,
        _labels({
            "hub_shared": {DESC_KEY: "Shared storage"},
            "hub_docker": {DESC_KEY: "Per-user docker sockets"},
        }),
    )
    assert rows == [
        {"name": "hub_shared", "mount": "/mnt/shared", "role": "shared", "description": "Shared storage"},
        {"name": "hub_docker", "mount": "/run/dockersock", "role": "docker-proxy", "description": "Per-user docker sockets"},
    ]


def test_order_preserved_shared_then_proxy():
    rows = build_system_volume_rows([SHARED, PROXY], DESC_KEY, _labels({}))
    assert [r["name"] for r in rows] == ["hub_shared", "hub_docker"]


def test_shared_absent_row_omitted():
    rows = build_system_volume_rows(
        [("", "/mnt/shared", "shared"), PROXY], DESC_KEY,
        _labels({"hub_docker": {DESC_KEY: "sockets"}}),
    )
    assert [r["name"] for r in rows] == ["hub_docker"]


def test_proxy_absent_row_omitted():
    rows = build_system_volume_rows(
        [SHARED, ("", "/run/dockersock", "docker-proxy")], DESC_KEY,
        _labels({"hub_shared": {DESC_KEY: "shared"}}),
    )
    assert [r["name"] for r in rows] == ["hub_shared"]


def test_both_absent_empty():
    rows = build_system_volume_rows(
        [("", "/mnt/shared", "shared"), ("", "/run/dockersock", "docker-proxy")],
        DESC_KEY, _labels({}),
    )
    assert rows == []


def test_volume_missing_blank_description():
    # read_labels returns None (volume not found) -> description '' not error
    rows = build_system_volume_rows([SHARED], DESC_KEY, _labels({}))
    assert rows[0]["description"] == ""


def test_volume_present_but_label_missing_blank_description():
    # volume exists ({} labels) but carries no description label -> ''
    rows = build_system_volume_rows([SHARED], DESC_KEY, _labels({"hub_shared": {}}))
    assert rows[0]["description"] == ""


def test_other_labels_present_description_absent():
    rows = build_system_volume_rows(
        [SHARED], DESC_KEY, _labels({"hub_shared": {"duoptimum-hub.volume.role": "shared"}}),
    )
    assert rows[0]["description"] == ""


def test_empty_specs_empty_rows():
    assert build_system_volume_rows([], DESC_KEY, _labels({})) == []
