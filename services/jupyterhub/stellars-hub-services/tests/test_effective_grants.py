"""Tests for the per-user effective-grants view (engine.effective_grants).

effective_grants turns the resolved cross-group policy into the display rows the
portal shows on Home / UserConfig: one {key, label, value, from} per capability
the user actually gets, each citing the highest-priority granting group. It must
stay honest - no row for a capability no group grants.
"""

from stellars_hub_services.policy import effective_grants, resolve_policies


def _grp(name, **config):
    return {"group_name": name, "config": config}


def _grants(user_groups, all_configs, gpu_available=False):
    resolved = resolve_policies(
        user_group_names=user_groups,
        all_group_configs=all_configs,
        gpu_available=gpu_available,
        reserved_names=frozenset(),
        reserved_prefixes=(),
    )
    user_set = set(user_groups)
    matched = [c for c in all_configs if c.get("group_name") in user_set]
    return effective_grants(matched, resolved)


def _by_key(grants):
    return {g["key"]: g for g in grants}


class TestEmpty:
    def test_no_groups_no_grants(self):
        assert _grants([], []) == []

    def test_groups_grant_nothing(self):
        cfgs = [_grp("plain")]
        assert _grants(["plain"], cfgs) == []


class TestMemory:
    def test_memory_grant_and_source(self):
        cfgs = [_grp("data-science", mem_limit_enabled=True, mem_limit_gb=16)]
        g = _by_key(_grants(["data-science"], cfgs))["memory"]
        assert g == {"key": "memory", "label": "Memory", "value": "16 GB", "from": "data-science"}

    def test_no_swap_annotated(self):
        cfgs = [_grp("ds", mem_limit_enabled=True, mem_limit_gb=8, mem_swap_disabled=True)]
        assert _by_key(_grants(["ds"], cfgs))["memory"]["value"] == "8 GB (no swap)"

    def test_biggest_wins_with_attribution(self):
        # priority-descending list; the larger cap wins and cites its group
        cfgs = [
            _grp("small", mem_limit_enabled=True, mem_limit_gb=8),
            _grp("big", mem_limit_enabled=True, mem_limit_gb=32),
        ]
        g = _by_key(_grants(["small", "big"], cfgs))["memory"]
        assert g["value"] == "32 GB"
        assert g["from"] == "big"

    def test_fractional_kept(self):
        cfgs = [_grp("ds", mem_limit_enabled=True, mem_limit_gb=1.5)]
        assert _by_key(_grants(["ds"], cfgs))["memory"]["value"] == "1.5 GB"


class TestCpu:
    def test_cpu_grant(self):
        cfgs = [_grp("compute", cpu_limit_enabled=True, cpu_limit_cores=8)]
        g = _by_key(_grants(["compute"], cfgs))["cpu"]
        assert g == {"key": "cpu", "label": "CPU", "value": "8 cores", "from": "compute"}

    def test_no_cpu_limit_no_row(self):
        cfgs = [_grp("compute", cpu_limit_enabled=False, cpu_limit_cores=0)]
        assert "cpu" not in _by_key(_grants(["compute"], cfgs))


class TestGpu:
    def test_gpu_all(self):
        cfgs = [_grp("gpu", gpu_access=True, gpu_all=True)]
        g = _by_key(_grants(["gpu"], cfgs, gpu_available=True))["gpu"]
        assert g == {"key": "gpu", "label": "GPU", "value": "all devices", "from": "gpu"}

    def test_gpu_subset(self):
        cfgs = [_grp("gpu", gpu_access=True, gpu_all=False, gpu_device_ids=["0", "1"])]
        g = _by_key(_grants(["gpu"], cfgs, gpu_available=True))["gpu"]
        assert g["value"] == "GPU 0, 1"

    def test_gpu_hidden_without_hardware(self):
        # resolver gates gpu_access on gpu_available; no hardware -> no grant
        cfgs = [_grp("gpu", gpu_access=True, gpu_all=True)]
        assert "gpu" not in _by_key(_grants(["gpu"], cfgs, gpu_available=False))


class TestSudo:
    def test_sudo_enabled(self):
        cfgs = [_grp("admins", sudo_active=True, sudo_enable=True)]
        g = _by_key(_grants(["admins"], cfgs))["shield"]
        assert g == {"key": "shield", "label": "Sudo", "value": "enabled", "from": "admins"}

    def test_sudo_disabled_shown(self):
        cfgs = [_grp("locked", sudo_active=True, sudo_enable=False)]
        assert _by_key(_grants(["locked"], cfgs))["shield"]["value"] == "disabled"

    def test_sudo_unconfigured_absent(self):
        # section off -> resolver returns None -> no row (platform default applies)
        cfgs = [_grp("plain", sudo_active=False)]
        assert "shield" not in _by_key(_grants(["plain"], cfgs))


class TestDocker:
    def test_socket(self):
        cfgs = [_grp("ops", docker_active=True, docker_access=True)]
        g = _by_key(_grants(["ops"], cfgs))["box"]
        assert g == {"key": "box", "label": "Docker", "value": "socket", "from": "ops"}

    def test_limited(self):
        cfgs = [_grp("builders", docker_active=True, docker_limited=True)]
        assert _by_key(_grants(["builders"], cfgs))["box"]["value"] == "limited"

    def test_privileged_annotated_on_socket(self):
        cfgs = [_grp("ops", docker_active=True, docker_access=True, docker_privileged=True)]
        assert _by_key(_grants(["ops"], cfgs))["box"]["value"] == "socket + privileged"

    def test_privileged_only(self):
        cfgs = [_grp("hw", docker_active=True, docker_privileged=True)]
        assert _by_key(_grants(["hw"], cfgs))["box"]["value"] == "privileged"

    def test_socket_supersedes_limited(self):
        # one group grants raw socket, another limited; resolver collapses limited
        cfgs = [
            _grp("ops", docker_active=True, docker_access=True),
            _grp("builders", docker_active=True, docker_limited=True),
        ]
        g = _by_key(_grants(["ops", "builders"], cfgs))["box"]
        assert g["value"] == "socket"
        assert g["from"] == "ops"


def test_unique_keys_for_react():
    # the frontend keys grant rows by `key`; the full fanout must stay unique
    cfgs = [_grp(
        "everything",
        gpu_access=True, gpu_all=True,
        mem_limit_enabled=True, mem_limit_gb=64,
        cpu_limit_enabled=True, cpu_limit_cores=16,
        sudo_active=True, sudo_enable=True,
        docker_active=True, docker_access=True, docker_privileged=True,
    )]
    keys = [g["key"] for g in _grants(["everything"], cfgs, gpu_available=True)]
    assert keys == sorted(set(keys), key=keys.index)  # no duplicates
    assert set(keys) == {"gpu", "memory", "cpu", "shield", "box"}
