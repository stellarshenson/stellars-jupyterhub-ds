"""Unit tests for the pure request/response transforms."""

import json

from stellars_docker_proxy import filters as F
from stellars_docker_proxy.config import (
    BYTES_PER_GB,
    MANAGED_LABEL,
    NANO_PER_CORE,
    OWNER_LABEL,
)


def test_inject_labels_adds_owner_and_managed():
    out = F.inject_labels({}, "alice")
    assert out["Labels"][OWNER_LABEL] == "alice"
    assert out["Labels"][MANAGED_LABEL] == "true"


def test_inject_labels_preserves_existing_and_does_not_mutate_input():
    body = {"Image": "x", "Labels": {"foo": "bar"}}
    out = F.inject_labels(body, "alice")
    assert out["Labels"]["foo"] == "bar"
    assert out["Labels"][OWNER_LABEL] == "alice"
    assert "Labels" in body and OWNER_LABEL not in body["Labels"]  # original untouched


def test_ensure_name_prefix():
    assert F.ensure_name_prefix(None, "user-alice-") is None
    assert F.ensure_name_prefix("", "user-alice-") is None
    assert F.ensure_name_prefix("web", "user-alice-") == "user-alice-web"
    assert F.ensure_name_prefix("user-alice-web", "user-alice-") == "user-alice-web"


def test_merge_label_filter_empty():
    merged = json.loads(F.merge_label_filter(None, "alice"))
    assert merged["label"] == [f"{OWNER_LABEL}=alice"]


def test_merge_label_filter_preserves_other_constraints():
    existing = json.dumps({"status": ["running"], "label": ["foo=bar"]})
    merged = json.loads(F.merge_label_filter(existing, "alice"))
    assert merged["status"] == ["running"]
    assert "foo=bar" in merged["label"]
    assert f"{OWNER_LABEL}=alice" in merged["label"]


def test_merge_label_filter_idempotent():
    once = F.merge_label_filter(None, "alice")
    twice = F.merge_label_filter(once, "alice")
    assert json.loads(twice)["label"].count(f"{OWNER_LABEL}=alice") == 1


def test_caps_violation_cpu_and_mem():
    over_cpu = {"HostConfig": {"NanoCpus": 4 * NANO_PER_CORE}}
    assert F.caps_violation(over_cpu, 2.0, 8.0)
    over_mem = {"HostConfig": {"Memory": 16 * BYTES_PER_GB}}
    assert F.caps_violation(over_mem, 2.0, 8.0)
    ok = {"HostConfig": {"NanoCpus": 1 * NANO_PER_CORE, "Memory": 4 * BYTES_PER_GB}}
    assert F.caps_violation(ok, 2.0, 8.0) is None
    assert F.caps_violation(over_cpu, 0, 0) is None  # caps disabled


def test_apply_caps_injects_when_absent_keeps_when_present():
    injected = F.apply_caps({}, 2.0, 8.0)["HostConfig"]
    assert injected["NanoCpus"] == int(2.0 * NANO_PER_CORE)
    assert injected["Memory"] == int(8.0 * BYTES_PER_GB)

    explicit = {"HostConfig": {"NanoCpus": NANO_PER_CORE, "Memory": BYTES_PER_GB}}
    kept = F.apply_caps(explicit, 2.0, 8.0)["HostConfig"]
    assert kept["NanoCpus"] == NANO_PER_CORE
    assert kept["Memory"] == BYTES_PER_GB


def test_dangerous_reason_flags_each_vector():
    assert F.dangerous_reason({"HostConfig": {"Privileged": True}})
    assert F.dangerous_reason({"HostConfig": {"Binds": ["/etc:/etc"]}})
    assert F.dangerous_reason({"HostConfig": {"Mounts": [{"Type": "bind", "Source": "/"}]}})
    assert F.dangerous_reason({"HostConfig": {"NetworkMode": "host"}})
    assert F.dangerous_reason({"HostConfig": {"PidMode": "host"}})
    assert F.dangerous_reason({"HostConfig": {"CapAdd": ["SYS_ADMIN"]}})
    assert F.dangerous_reason({"HostConfig": {"Devices": [{"PathOnHost": "/dev/x"}]}})


def test_dangerous_reason_allows_named_volume_mount():
    body = {"HostConfig": {"Mounts": [{"Type": "volume", "Source": "myvol", "Target": "/data"}]}}
    assert F.dangerous_reason(body) is None


def test_is_owned_container_and_volume():
    container = {"Config": {"Labels": {OWNER_LABEL: "alice"}}}
    assert F.is_owned(container, "alice")
    assert not F.is_owned(container, "bob")
    volume = {"Labels": {OWNER_LABEL: "alice"}}
    assert F.is_owned(volume, "alice")
    assert not F.is_owned({"Labels": {}}, "alice")
    assert not F.is_owned(None, "alice")


def test_compose_project_injection_and_respect_user_compose():
    plain = F.inject_compose_project({"Image": "x"}, "jhub")
    assert plain["Labels"][F.COMPOSE_PROJECT_LABEL] == "jhub"

    user = {"Labels": {F.COMPOSE_PROJECT_LABEL: "mine"}}
    assert F.has_compose_project(user)
    out = F.inject_compose_project(user, "jhub")
    assert out["Labels"][F.COMPOSE_PROJECT_LABEL] == "mine"  # not overridden

    assert F.inject_compose_project({"Image": "x"}, "") == {"Image": "x"}  # disabled
