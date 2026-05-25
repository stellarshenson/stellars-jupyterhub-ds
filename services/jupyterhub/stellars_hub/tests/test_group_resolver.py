"""Functional tests for group_resolver.py - per-group CPU and memory caps.

CPU and memory limits use the same biggest-enabled-wins rule: a user's effective
cap is the largest enabled value among their groups, and a group with the limit
disabled never removes another group's cap. The resolver returns the raw value;
the spawn-time ceil-to-whole-cores happens in hooks.py.
"""

from stellars_hub.group_resolver import resolve_group_config


def _grp(name, **config):
    return {"group_name": name, "config": config}


def _resolve(user_groups, all_configs, gpu_available=False):
    return resolve_group_config(
        user_group_names=user_groups,
        all_group_configs=all_configs,
        gpu_available=gpu_available,
        reserved_names=frozenset(),
        reserved_prefixes=(),
    )


class TestCpuLimit:
    def test_no_cap_returns_none(self):
        cfgs = [_grp("a", cpu_limit_enabled=False, cpu_limit_cores=0)]
        assert _resolve(["a"], cfgs)["cpu_limit_cores"] is None

    def test_single_group_cap(self):
        cfgs = [_grp("a", cpu_limit_enabled=True, cpu_limit_cores=4)]
        assert _resolve(["a"], cfgs)["cpu_limit_cores"] == 4

    def test_fractional_preserved(self):
        cfgs = [_grp("a", cpu_limit_enabled=True, cpu_limit_cores=2.5)]
        assert _resolve(["a"], cfgs)["cpu_limit_cores"] == 2.5

    def test_biggest_wins_across_groups(self):
        cfgs = [
            _grp("big", cpu_limit_enabled=True, cpu_limit_cores=8),
            _grp("small", cpu_limit_enabled=True, cpu_limit_cores=2),
        ]
        assert _resolve(["big", "small"], cfgs)["cpu_limit_cores"] == 8

    def test_disabled_group_does_not_uncap(self):
        cfgs = [
            _grp("capped", cpu_limit_enabled=True, cpu_limit_cores=4),
            _grp("uncapped", cpu_limit_enabled=False, cpu_limit_cores=0),
        ]
        assert _resolve(["capped", "uncapped"], cfgs)["cpu_limit_cores"] == 4

    def test_enabled_zero_is_no_cap(self):
        cfgs = [_grp("a", cpu_limit_enabled=True, cpu_limit_cores=0)]
        assert _resolve(["a"], cfgs)["cpu_limit_cores"] is None

    def test_invalid_value_ignored(self):
        cfgs = [_grp("a", cpu_limit_enabled=True, cpu_limit_cores="not-a-number")]
        assert _resolve(["a"], cfgs)["cpu_limit_cores"] is None

    def test_only_matched_groups_count(self):
        cfgs = [
            _grp("mine", cpu_limit_enabled=True, cpu_limit_cores=2),
            _grp("other", cpu_limit_enabled=True, cpu_limit_cores=16),
        ]
        # user only in 'mine' - 'other' must not leak in
        assert _resolve(["mine"], cfgs)["cpu_limit_cores"] == 2


class TestMemSwapDisabled:
    def test_default_swap_allowed(self):
        cfgs = [_grp("a", mem_limit_enabled=True, mem_limit_gb=16)]
        assert _resolve(["a"], cfgs)["mem_swap_disabled"] is False

    def test_swap_disabled_flag(self):
        cfgs = [_grp("a", mem_limit_enabled=True, mem_limit_gb=16, mem_swap_disabled=True)]
        assert _resolve(["a"], cfgs)["mem_swap_disabled"] is True

    def test_no_mem_limit_swap_flag_false(self):
        cfgs = [_grp("a", mem_limit_enabled=False, mem_swap_disabled=True)]
        result = _resolve(["a"], cfgs)
        assert result["mem_limit_gb"] is None
        assert result["mem_swap_disabled"] is False

    def test_swap_policy_follows_bigger_limit_disabled(self):
        # bigger cap disables swap -> swap disabled
        cfgs = [
            _grp("big", mem_limit_enabled=True, mem_limit_gb=128, mem_swap_disabled=True),
            _grp("small", mem_limit_enabled=True, mem_limit_gb=64, mem_swap_disabled=False),
        ]
        result = _resolve(["big", "small"], cfgs)
        assert result["mem_limit_gb"] == 128
        assert result["mem_swap_disabled"] is True

    def test_swap_policy_follows_bigger_limit_allowed(self):
        # bigger cap allows swap -> a smaller group's swap-disable is ignored
        cfgs = [
            _grp("big", mem_limit_enabled=True, mem_limit_gb=128, mem_swap_disabled=False),
            _grp("small", mem_limit_enabled=True, mem_limit_gb=64, mem_swap_disabled=True),
        ]
        result = _resolve(["big", "small"], cfgs)
        assert result["mem_limit_gb"] == 128
        assert result["mem_swap_disabled"] is False


class TestCpuAndMemoryIndependent:
    def test_cpu_and_memory_resolve_separately(self):
        cfgs = [
            _grp("a", mem_limit_enabled=True, mem_limit_gb=16,
                 cpu_limit_enabled=True, cpu_limit_cores=4),
        ]
        result = _resolve(["a"], cfgs)
        assert result["mem_limit_gb"] == 16
        assert result["cpu_limit_cores"] == 4

    def test_cpu_set_memory_unset(self):
        cfgs = [_grp("a", cpu_limit_enabled=True, cpu_limit_cores=4)]
        result = _resolve(["a"], cfgs)
        assert result["cpu_limit_cores"] == 4
        assert result["mem_limit_gb"] is None


class TestGpuSelection:
    def test_no_gpu_group(self):
        r = _resolve(["a"], [_grp("a")], gpu_available=True)
        assert r["gpu_access"] is False
        assert r["gpu_device_ids"] == []

    def test_all_gpus_when_available(self):
        cfgs = [_grp("a", gpu_access=True, gpu_all=True)]
        r = _resolve(["a"], cfgs, gpu_available=True)
        assert r["gpu_access"] is True
        assert r["gpu_all"] is True
        assert r["gpu_device_ids"] == []

    def test_specific_gpus(self):
        cfgs = [_grp("a", gpu_access=True, gpu_all=False, gpu_device_ids=["0", "2"])]
        r = _resolve(["a"], cfgs, gpu_available=True)
        assert r["gpu_access"] is True
        assert r["gpu_all"] is False
        assert r["gpu_device_ids"] == ["0", "2"]

    def test_gated_on_hardware(self):
        # GPU requested but host has none -> access denied, never reaches the spawner
        cfgs = [_grp("a", gpu_access=True, gpu_all=True)]
        assert _resolve(["a"], cfgs, gpu_available=False)["gpu_access"] is False

    def test_all_wins_over_specific(self):
        cfgs = [
            _grp("all", gpu_access=True, gpu_all=True),
            _grp("specific", gpu_access=True, gpu_all=False, gpu_device_ids=["1"]),
        ]
        assert _resolve(["all", "specific"], cfgs, gpu_available=True)["gpu_all"] is True

    def test_specific_union_across_groups(self):
        cfgs = [
            _grp("a", gpu_access=True, gpu_all=False, gpu_device_ids=["0"]),
            _grp("b", gpu_access=True, gpu_all=False, gpu_device_ids=["2", "0"]),
        ]
        r = _resolve(["a", "b"], cfgs, gpu_available=True)
        assert r["gpu_all"] is False
        assert r["gpu_device_ids"] == ["0", "2"]

    def test_default_gpu_all_true_when_unset(self):
        # grant without specifying gpu_all -> defaults to all
        r = _resolve(["a"], [_grp("a", gpu_access=True)], gpu_available=True)
        assert r["gpu_all"] is True

    def test_empty_selection_falls_back_to_all(self):
        # defensive: access on, not all, no ids -> all (validator rejects this at save)
        cfgs = [_grp("a", gpu_access=True, gpu_all=False, gpu_device_ids=[])]
        r = _resolve(["a"], cfgs, gpu_available=True)
        assert r["gpu_access"] is True
        assert r["gpu_all"] is True


class TestGpuSelectionValidation:
    def test_access_off_always_valid(self):
        from stellars_hub.groups_config import validate_gpu_selection
        assert validate_gpu_selection(False, False, [])[0] is True

    def test_all_gpus_valid(self):
        from stellars_hub.groups_config import validate_gpu_selection
        assert validate_gpu_selection(True, True, [])[0] is True

    def test_specific_with_ids_valid(self):
        from stellars_hub.groups_config import validate_gpu_selection
        assert validate_gpu_selection(True, False, ["0"])[0] is True

    def test_access_on_not_all_no_ids_invalid(self):
        from stellars_hub.groups_config import validate_gpu_selection
        valid, msg = validate_gpu_selection(True, False, [])
        assert valid is False
        assert "at least one GPU" in msg
