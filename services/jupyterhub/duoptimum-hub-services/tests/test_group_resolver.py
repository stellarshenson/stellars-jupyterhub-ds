"""Functional tests for the policy engine resolution - per-group CPU and memory caps.

CPU and memory limits use the same biggest-enabled-wins rule: a user's effective
cap is the largest enabled value among their groups, and a group with the limit
disabled never removes another group's cap. The resolver returns the raw value;
the spawn-time ceil-to-whole-cores happens in hooks.py.
"""

from duoptimum_hub_services.policy import POLICY_TYPES, resolve_policies

_BY_KEY = {pt.key: pt for pt in POLICY_TYPES}


def _grp(name, **config):
    return {"group_name": name, "config": config}


def _resolve(user_groups, all_configs, gpu_available=False):
    return resolve_policies(
        user_group_names=user_groups,
        all_group_configs=all_configs,
        gpu_available=gpu_available,
        reserved_names=frozenset(),
        reserved_prefixes=(),
    )


def validate_gpu_selection(gpu_access, gpu_all, gpu_device_ids):
    """GPU coherence via the registry (was a groups_config wrapper)."""
    return _BY_KEY['gpu'].validate(
        {'gpu_access': gpu_access, 'gpu_all': gpu_all, 'gpu_device_ids': gpu_device_ids})


def validate_docker_selection(docker_access, docker_limited, docker_privileged=False):
    """Docker coherence via the registry (was a groups_config wrapper)."""
    return _BY_KEY['docker'].validate(
        {'docker_access': docker_access, 'docker_limited': docker_limited,
         'docker_privileged': docker_privileged})


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
        assert validate_gpu_selection(False, False, [])[0] is True

    def test_all_gpus_valid(self):
        assert validate_gpu_selection(True, True, [])[0] is True

    def test_specific_with_ids_valid(self):
        assert validate_gpu_selection(True, False, ["0"])[0] is True

    def test_access_on_not_all_no_ids_invalid(self):
        valid, msg = validate_gpu_selection(True, False, [])
        assert valid is False
        assert "at least one GPU" in msg


class TestDockerLimited:
    def test_not_granted_by_default(self):
        cfgs = [_grp("a")]
        assert _resolve(["a"], cfgs)["docker_limited"] is False

    def test_granted_uses_defaults_when_unset(self):
        cfgs = [_grp("d", docker_limited=True)]
        r = _resolve(["d"], cfgs)
        assert r["docker_limited"] is True
        assert r["docker_limited_max_containers"] == 10
        assert r["docker_limited_max_volumes"] == 10
        assert r["docker_limited_max_networks"] == 3
        assert r["docker_limited_max_storage_gb"] == 50
        assert r["docker_limited_cpu_cap_cores"] == 2
        assert r["docker_limited_mem_cap_gb"] == 8

    def test_granted_with_custom_quota(self):
        cfgs = [_grp("d", docker_limited=True, docker_limited_max_containers=5,
                     docker_limited_max_volumes=4, docker_limited_max_networks=2,
                     docker_limited_max_storage_gb=20, docker_limited_cpu_cap_cores=1,
                     docker_limited_mem_cap_gb=3)]
        r = _resolve(["d"], cfgs)
        assert r["docker_limited_max_containers"] == 5
        assert r["docker_limited_max_volumes"] == 4
        assert r["docker_limited_max_networks"] == 2
        assert r["docker_limited_max_storage_gb"] == 20
        assert r["docker_limited_cpu_cap_cores"] == 1
        assert r["docker_limited_mem_cap_gb"] == 3

    def test_most_generous_quota_wins_across_groups(self):
        cfgs = [
            _grp("a", docker_limited=True, docker_limited_max_containers=5,
                 docker_limited_mem_cap_gb=4),
            _grp("b", docker_limited=True, docker_limited_max_containers=12,
                 docker_limited_mem_cap_gb=2),
        ]
        r = _resolve(["a", "b"], cfgs)
        assert r["docker_limited_max_containers"] == 12
        assert r["docker_limited_mem_cap_gb"] == 4

    def test_normal_access_supersedes_limited(self):
        cfgs = [
            _grp("norm", docker_access=True),
            _grp("lim", docker_limited=True, docker_limited_max_containers=5),
        ]
        r = _resolve(["norm", "lim"], cfgs)
        assert r["docker_access"] is True
        assert r["docker_limited"] is False

    def test_only_matched_groups_count(self):
        cfgs = [_grp("mine", docker_limited=True), _grp("other", docker_access=True)]
        r = _resolve(["mine"], cfgs)
        assert r["docker_limited"] is True
        assert r["docker_access"] is False

    def test_allow_dangerous_flags_off_by_default(self):
        cfgs = [_grp("d", docker_limited=True)]
        r = _resolve(["d"], cfgs)
        assert r["docker_limited_allow_dangerous_flags"] is False

    def test_allow_dangerous_flags_or_accumulates(self):
        cfgs = [
            _grp("a", docker_limited=True),
            _grp("b", docker_limited=True, docker_limited_allow_dangerous_flags=True),
        ]
        r = _resolve(["a", "b"], cfgs)
        assert r["docker_limited_allow_dangerous_flags"] is True

    def test_allow_dangerous_flags_independent_of_privileged(self):
        # docker_privileged does NOT imply allow_dangerous_flags.
        cfgs = [_grp("p", docker_limited=True, docker_privileged=True)]
        r = _resolve(["p"], cfgs)
        assert r["docker_privileged"] is True
        assert r["docker_limited_allow_dangerous_flags"] is False

    def test_allow_dangerous_flags_collapses_when_normal_supersedes(self):
        # Normal access wins over limited, and the limited-only bypass goes with it.
        cfgs = [
            _grp("norm", docker_access=True),
            _grp("lim", docker_limited=True, docker_limited_allow_dangerous_flags=True),
        ]
        r = _resolve(["norm", "lim"], cfgs)
        assert r["docker_limited"] is False
        assert r["docker_limited_allow_dangerous_flags"] is False

    def test_user_compose_project_defaults(self):
        # default_config has both enforce + allow_override on, so a fresh limited
        # group accumulates both as True.
        cfgs = [_grp("d", docker_limited=True,
                     docker_limited_user_compose_project_enabled=True,
                     docker_limited_user_compose_project_allow_override=True)]
        r = _resolve(["d"], cfgs)
        assert r["docker_limited_user_compose_project_enabled"] is True
        assert r["docker_limited_user_compose_project_allow_override"] is True

    def test_user_compose_project_can_be_disabled(self):
        cfgs = [_grp("d", docker_limited=True,
                     docker_limited_user_compose_project_enabled=False,
                     docker_limited_user_compose_project_allow_override=False)]
        r = _resolve(["d"], cfgs)
        assert r["docker_limited_user_compose_project_enabled"] is False
        assert r["docker_limited_user_compose_project_allow_override"] is False

    def test_user_compose_project_or_accumulates(self):
        cfgs = [
            _grp("a", docker_limited=True,
                 docker_limited_user_compose_project_enabled=False,
                 docker_limited_user_compose_project_allow_override=False),
            _grp("b", docker_limited=True,
                 docker_limited_user_compose_project_enabled=True,
                 docker_limited_user_compose_project_allow_override=True),
        ]
        r = _resolve(["a", "b"], cfgs)
        assert r["docker_limited_user_compose_project_enabled"] is True
        assert r["docker_limited_user_compose_project_allow_override"] is True

    def test_user_compose_project_collapses_when_normal_supersedes(self):
        cfgs = [
            _grp("norm", docker_access=True),
            _grp("lim", docker_limited=True,
                 docker_limited_user_compose_project_enabled=True,
                 docker_limited_user_compose_project_allow_override=True),
        ]
        r = _resolve(["norm", "lim"], cfgs)
        assert r["docker_limited_user_compose_project_enabled"] is False
        assert r["docker_limited_user_compose_project_allow_override"] is False

    def test_hub_network_access_default_on_from_default_config(self):
        cfgs = [_grp("d", docker_limited=True, docker_limited_hub_network_access=True)]
        r = _resolve(["d"], cfgs)
        assert r["docker_limited_hub_network_access"] is True

    def test_hub_network_access_or_accumulates(self):
        cfgs = [
            _grp("a", docker_limited=True, docker_limited_hub_network_access=False),
            _grp("b", docker_limited=True, docker_limited_hub_network_access=True),
        ]
        r = _resolve(["a", "b"], cfgs)
        assert r["docker_limited_hub_network_access"] is True

    def test_hub_network_access_collapses_when_normal_supersedes(self):
        cfgs = [
            _grp("norm", docker_access=True),
            _grp("lim", docker_limited=True, docker_limited_hub_network_access=True),
        ]
        r = _resolve(["norm", "lim"], cfgs)
        assert r["docker_limited_hub_network_access"] is False


class TestDockerSelectionValidation:
    def test_both_invalid(self):
        valid, msg = validate_docker_selection(True, True)
        assert valid is False
        assert "both" in msg.lower()

    def test_only_normal_valid(self):
        assert validate_docker_selection(True, False)[0] is True

    def test_only_limited_valid(self):
        assert validate_docker_selection(False, True)[0] is True

    def test_neither_valid(self):
        assert validate_docker_selection(False, False)[0] is True

    def test_root_alone_valid(self):
        """Root without an access mode is allowed: --privileged with no socket."""
        assert validate_docker_selection(False, False, docker_privileged=True)[0] is True

    def test_root_with_normal_valid(self):
        assert validate_docker_selection(True, False, docker_privileged=True)[0] is True

    def test_root_with_limited_valid(self):
        assert validate_docker_selection(False, True, docker_privileged=True)[0] is True

    def test_root_with_both_still_invalid_on_mutex(self):
        valid, msg = validate_docker_selection(True, True, docker_privileged=True)
        assert valid is False
        assert "both" in msg.lower()


class TestApiKeyPools:
    """The resolver collects pools as a priority-ordered LIST (not merged)."""

    def _pool_cfg(self, key_var, *keys):
        return {
            'enabled': True, 'mode': 'single', 'env_var_key': key_var,
            'credentials': [{'slot': f's{i}', 'key': k} for i, k in enumerate(keys)],
        }

    def test_no_pool_contributes_nothing(self):
        cfgs = [_grp("a", env_vars=[{'name': 'X', 'value': '1'}])]
        assert _resolve(["a"], cfgs)["api_key_pools"] == []

    def test_single_group_one_pool(self):
        cfgs = [_grp("a", api_keys_pool=self._pool_cfg('OPENAI_API_KEY', 'k0', 'k1'))]
        pools = _resolve(["a"], cfgs)["api_key_pools"]
        assert len(pools) == 1
        assert pools[0]['pool_id'] == 'a'
        assert pools[0]['env_var_key'] == 'OPENAI_API_KEY'
        assert pools[0]['slot_ids'] == ['s0', 's1']

    def test_two_groups_two_pools_priority_ordered(self):
        # all_group_configs is priority-descending; resolver preserves that order
        cfgs = [
            _grp("hi", api_keys_pool=self._pool_cfg('KEY_HI', 'h0')),
            _grp("lo", api_keys_pool=self._pool_cfg('KEY_LO', 'l0')),
        ]
        pools = _resolve(["hi", "lo"], cfgs)["api_key_pools"]
        assert [p['pool_id'] for p in pools] == ['hi', 'lo']

    def test_disabled_pool_excluded(self):
        cfg = self._pool_cfg('K', 'k0')
        cfg['enabled'] = False
        cfgs = [_grp("a", api_keys_pool=cfg)]
        assert _resolve(["a"], cfgs)["api_key_pools"] == []


class TestVolumeMounts:
    def test_no_groups_yields_empty(self):
        r = _resolve([], [])
        assert r["volume_mounts"] == [] and r["skipped_volume_mounts"] == []

    def test_single_group_passthrough(self):
        cfgs = [_grp("a", volume_mounts=[{"volume": "shared", "mountpoint": "/mnt/shared"}])]
        r = _resolve(["a"], cfgs)
        assert r["volume_mounts"] == [{"volume": "shared", "mountpoint": "/mnt/shared"}]

    def test_union_across_groups(self):
        cfgs = [
            _grp("a", volume_mounts=[{"volume": "shared", "mountpoint": "/mnt/shared"}]),
            _grp("b", volume_mounts=[{"volume": "datasets", "mountpoint": "/data"}]),
        ]
        r = _resolve(["a", "b"], cfgs)
        assert {m["volume"] for m in r["volume_mounts"]} == {"shared", "datasets"}

    def test_mountpoint_conflict_higher_priority_wins(self):
        # configs arrive priority-descending: group "a" outranks "b"
        cfgs = [
            _grp("a", volume_mounts=[{"volume": "vol_a", "mountpoint": "/mnt/shared"}]),
            _grp("b", volume_mounts=[{"volume": "vol_b", "mountpoint": "/mnt/shared"}]),
        ]
        r = _resolve(["a", "b"], cfgs)
        assert r["volume_mounts"] == [{"volume": "vol_a", "mountpoint": "/mnt/shared"}]
        assert r["skipped_volume_mounts"] == [
            {"volume": "vol_b", "mountpoint": "/mnt/shared", "group": "b", "reason": "shadowed"}
        ]

    def test_same_volume_same_mountpoint_dedupes_silently(self):
        cfgs = [
            _grp("a", volume_mounts=[{"volume": "shared", "mountpoint": "/mnt/shared"}]),
            _grp("b", volume_mounts=[{"volume": "shared", "mountpoint": "/mnt/shared"}]),
        ]
        r = _resolve(["a", "b"], cfgs)
        assert len(r["volume_mounts"]) == 1 and r["skipped_volume_mounts"] == []

    def test_same_volume_other_mountpoint_is_shadowed(self):
        # docker mounts are keyed by volume name - the higher-priority claim wins
        cfgs = [
            _grp("a", volume_mounts=[{"volume": "shared", "mountpoint": "/mnt/shared"}]),
            _grp("b", volume_mounts=[{"volume": "shared", "mountpoint": "/mnt/other"}]),
        ]
        r = _resolve(["a", "b"], cfgs)
        assert r["volume_mounts"] == [{"volume": "shared", "mountpoint": "/mnt/shared"}]
        assert r["skipped_volume_mounts"][0]["reason"] == "shadowed"

    def test_protected_mountpoint_skipped_defense_in_depth(self):
        # a stale/legacy DB row mounting over /etc never reaches the spawner
        cfgs = [_grp("a", volume_mounts=[{"volume": "v", "mountpoint": "/etc/evil"}])]
        r = _resolve(["a"], cfgs)
        assert r["volume_mounts"] == []
        assert r["skipped_volume_mounts"][0]["reason"] == "protected"

    def test_half_entries_ignored(self):
        cfgs = [_grp("a", volume_mounts=[
            {"volume": "", "mountpoint": "/mnt/x"},
            {"volume": "v", "mountpoint": ""},
            {"volume": "v2", "mountpoint": "relative/path"},
        ])]
        r = _resolve(["a"], cfgs)
        assert r["volume_mounts"] == []

    def test_mountpoint_normalised_trailing_slash(self):
        cfgs = [_grp("a", volume_mounts=[{"volume": "v", "mountpoint": "/mnt/data/"}])]
        r = _resolve(["a"], cfgs)
        assert r["volume_mounts"] == [{"volume": "v", "mountpoint": "/mnt/data"}]

    def test_group_without_mounts_contributes_nothing(self):
        cfgs = [
            _grp("a"),
            _grp("b", volume_mounts=[{"volume": "v", "mountpoint": "/mnt/x"}]),
        ]
        r = _resolve(["a", "b"], cfgs)
        assert len(r["volume_mounts"]) == 1


class TestSectionActiveFlags:
    """Section active flags: an inactive section reads as unconfigured at
    resolve time even though its data is present; a missing flag (legacy dict
    that bypassed _row_to_dict inference) defaults to active."""

    def test_inactive_env_vars_contribute_nothing(self):
        cfgs = [_grp("a", env_vars_active=False,
                     env_vars=[{"name": "FOO", "value": "1"}])]
        assert _resolve(["a"], cfgs)["env_vars"] == {}

    def test_active_env_vars_apply(self):
        cfgs = [_grp("a", env_vars_active=True,
                     env_vars=[{"name": "FOO", "value": "1"}])]
        assert _resolve(["a"], cfgs)["env_vars"] == {"FOO": "1"}

    def test_missing_env_flag_defaults_active(self):
        cfgs = [_grp("a", env_vars=[{"name": "FOO", "value": "1"}])]
        assert _resolve(["a"], cfgs)["env_vars"] == {"FOO": "1"}

    def test_inactive_docker_grants_nothing(self):
        cfgs = [_grp("a", docker_active=False, docker_access=True,
                     docker_limited=False, docker_privileged=True)]
        resolved = _resolve(["a"], cfgs)
        assert resolved["docker_access"] is False
        assert resolved["docker_privileged"] is False

    def test_inactive_docker_limited_grants_nothing(self):
        cfgs = [_grp("a", docker_active=False, docker_limited=True,
                     docker_limited_max_containers=99)]
        assert _resolve(["a"], cfgs)["docker_limited"] is False

    def test_inactive_volume_mounts_mount_nothing(self):
        cfgs = [_grp("a", volume_mounts_active=False,
                     volume_mounts=[{"volume": "v", "mountpoint": "/mnt/x"}])]
        assert _resolve(["a"], cfgs)["volume_mounts"] == []

    def test_mixed_groups_only_active_section_applies(self):
        cfgs = [
            _grp("on", env_vars_active=True,
                 env_vars=[{"name": "A", "value": "1"}]),
            _grp("off", env_vars_active=False,
                 env_vars=[{"name": "B", "value": "2"}]),
        ]
        assert _resolve(["on", "off"], cfgs)["env_vars"] == {"A": "1"}

    def test_inactive_docker_does_not_revoke_other_groups_grant(self):
        cfgs = [
            _grp("grants", docker_active=True, docker_access=True),
            _grp("folded", docker_active=False, docker_access=True),
        ]
        assert _resolve(["grants", "folded"], cfgs)["docker_access"] is True


class TestDownloadsAllow:
    """File downloads: section-gated, priority-wins. None until a configuring
    group (downloads_active on) is seen; the first such group (priority-
    descending) wins. A section-off group does not configure it; the hook
    applies the platform default when the resolved value is None."""

    def test_none_when_no_group_configures(self):
        cfgs = [_grp("a")]
        assert _resolve(["a"], cfgs)["downloads_allow"] is None

    def test_section_off_does_not_configure(self):
        cfgs = [_grp("a", downloads_active=False, downloads_allow=True)]
        assert _resolve(["a"], cfgs)["downloads_allow"] is None

    def test_single_group_allow(self):
        cfgs = [_grp("a", downloads_active=True, downloads_allow=True)]
        assert _resolve(["a"], cfgs)["downloads_allow"] is True

    def test_single_group_block(self):
        cfgs = [_grp("a", downloads_active=True, downloads_allow=False)]
        assert _resolve(["a"], cfgs)["downloads_allow"] is False

    def test_higher_priority_wins(self):
        cfgs = [
            _grp("hi", downloads_active=True, downloads_allow=False),
            _grp("lo", downloads_active=True, downloads_allow=True),
        ]
        assert _resolve(["hi", "lo"], cfgs)["downloads_allow"] is False

    def test_higher_priority_off_lower_configures(self):
        cfgs = [
            _grp("hi", downloads_active=False, downloads_allow=True),
            _grp("lo", downloads_active=True, downloads_allow=False),
        ]
        assert _resolve(["hi", "lo"], cfgs)["downloads_allow"] is False

    def test_only_matched_groups_count(self):
        cfgs = [
            _grp("mine", downloads_active=False),
            _grp("other", downloads_active=True, downloads_allow=False),
        ]
        assert _resolve(["mine"], cfgs)["downloads_allow"] is None


class TestSudoAccess:
    """Sudo access: section-gated, priority-wins. The resolver returns
    True/False when a group configures it (sudo_active on) and None when none
    do - the hook then applies the platform default. `all_configs` is passed
    priority-descending, so the first configuring group decides."""

    def test_unconfigured_returns_none(self):
        cfgs = [_grp("a")]
        assert _resolve(["a"], cfgs)["sudo_enable"] is None

    def test_section_off_does_not_configure(self):
        cfgs = [_grp("a", sudo_active=False, sudo_enable=False)]
        assert _resolve(["a"], cfgs)["sudo_enable"] is None

    def test_single_configuring_group_enable(self):
        cfgs = [_grp("a", sudo_active=True, sudo_enable=True)]
        assert _resolve(["a"], cfgs)["sudo_enable"] is True

    def test_single_configuring_group_disable(self):
        cfgs = [_grp("a", sudo_active=True, sudo_enable=False)]
        assert _resolve(["a"], cfgs)["sudo_enable"] is False

    def test_higher_priority_wins(self):
        # all_configs is priority-descending; "hi" is higher priority than "lo".
        cfgs = [
            _grp("hi", sudo_active=True, sudo_enable=False),
            _grp("lo", sudo_active=True, sudo_enable=True),
        ]
        assert _resolve(["hi", "lo"], cfgs)["sudo_enable"] is False

    def test_higher_priority_off_lower_on_decides(self):
        cfgs = [
            _grp("hi", sudo_active=False, sudo_enable=True),
            _grp("lo", sudo_active=True, sudo_enable=False),
        ]
        assert _resolve(["hi", "lo"], cfgs)["sudo_enable"] is False

    def test_only_matched_groups_count(self):
        cfgs = [
            _grp("mine", sudo_active=False),
            _grp("other", sudo_active=True, sudo_enable=False),
        ]
        assert _resolve(["mine"], cfgs)["sudo_enable"] is None
