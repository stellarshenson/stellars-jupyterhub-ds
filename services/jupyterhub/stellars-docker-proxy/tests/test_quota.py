"""Unit tests for quota accounting helpers."""

from stellars_docker_proxy import quota as Q
from stellars_docker_proxy.config import BYTES_PER_GB, OWNER_LABEL


def test_list_count():
    assert Q.list_count([{}, {}, {}]) == 3
    assert Q.list_count({}) == 0
    assert Q.list_count(None) == 0


def test_over_count():
    assert Q.over_count(10, 10) is True
    assert Q.over_count(9, 10) is False
    assert Q.over_count(100, 0) is False  # 0 = unlimited


def test_storage_used_bytes_sums_owned_only():
    df = {
        "Volumes": [
            {"Labels": {OWNER_LABEL: "alice"}, "UsageData": {"Size": 3 * BYTES_PER_GB}},
            {"Labels": {OWNER_LABEL: "bob"}, "UsageData": {"Size": 9 * BYTES_PER_GB}},
            {"Labels": {OWNER_LABEL: "alice"}, "UsageData": {"Size": -1}},  # not computed
        ],
        "Containers": [
            {"Labels": {OWNER_LABEL: "alice"}, "SizeRw": 1 * BYTES_PER_GB},
            {"Labels": {OWNER_LABEL: "bob"}, "SizeRw": 5 * BYTES_PER_GB},
        ],
    }
    assert Q.storage_used_bytes(df, "alice") == 4 * BYTES_PER_GB


def test_over_storage_budget():
    df = {"Volumes": [{"Labels": {OWNER_LABEL: "alice"}, "UsageData": {"Size": 60 * BYTES_PER_GB}}]}
    assert Q.over_storage_budget(df, "alice", 50) is True
    assert Q.over_storage_budget(df, "alice", 0) is False  # disabled
    assert Q.over_storage_budget(df, "bob", 50) is False   # not bob's
