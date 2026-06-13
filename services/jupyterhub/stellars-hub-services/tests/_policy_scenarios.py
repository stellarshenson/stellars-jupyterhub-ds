"""Shared scenario matrix for policy-resolution regression tests.

Pure data, no imports from the code under test - so it survives the deletion of
the legacy resolver and is consumed by both the one-off golden generator
(`_gen_golden.py`, run once against the old `resolve_group_config`) and the
live comparison test (`test_policy_golden.py`, run against the new engine).

Each scenario is `(name, kwargs)` where kwargs match the resolver signature:
`user_group_names`, `all_group_configs` (priority-descending), `gpu_available`,
`reserved_names`, `reserved_prefixes`. Group configs are listed highest-priority
first, matching what GroupsConfigManager.get_all_configs() returns.
"""


def _grp(name, **config):
    return {"group_name": name, "config": config}


def _pair_pool(env_id, env_secret, *creds):
    return {
        "enabled": True, "mode": "pair",
        "env_var_id": env_id, "env_var_secret": env_secret, "env_var_key": "",
        "credentials": [
            {"slot": f"slot{i}", "id": cid, "secret": csec, "description": ""}
            for i, (cid, csec) in enumerate(creds)
        ],
    }


def _single_pool(env_key, *keys):
    return {
        "enabled": True, "mode": "single",
        "env_var_id": "", "env_var_secret": "", "env_var_key": env_key,
        "credentials": [
            {"slot": f"k{i}", "key": k, "description": ""}
            for i, k in enumerate(keys)
        ],
    }


def scenarios():
    """Return the full list of (name, resolver-kwargs) scenarios."""
    S = []

    def add(name, user_groups, configs, gpu_available=False,
            reserved_names=frozenset(), reserved_prefixes=()):
        S.append((name, {
            "user_group_names": user_groups,
            "all_group_configs": configs,
            "gpu_available": gpu_available,
            "reserved_names": reserved_names,
            "reserved_prefixes": reserved_prefixes,
        }))

    # --- empty / trivial ---
    add("empty_no_groups", [], [])
    add("user_in_no_matching_group", ["x"], [_grp("a", env_vars_active=True,
        env_vars=[{"name": "A", "value": "1"}])])

    # --- env vars ---
    add("env_single", ["a"], [_grp("a", env_vars_active=True,
        env_vars=[{"name": "FOO", "value": "bar"}])])
    add("env_priority_conflict", ["hi", "lo"], [
        _grp("hi", env_vars_active=True, env_vars=[{"name": "K", "value": "high"}]),
        _grp("lo", env_vars_active=True, env_vars=[{"name": "K", "value": "low"}]),
    ])
    add("env_section_off_ignored", ["a"], [_grp("a", env_vars_active=False,
        env_vars=[{"name": "FOO", "value": "bar"}])])
    add("env_reserved_stripped", ["a"], [_grp("a", env_vars_active=True, env_vars=[
        {"name": "FOO", "value": "ok"}, {"name": "PATH", "value": "x"},
        {"name": "JUPYTERHUB_X", "value": "y"}])],
        reserved_names=frozenset({"PATH"}), reserved_prefixes=("JUPYTERHUB_",))
    add("env_legacy_no_active_flag", ["a"], [_grp("a",
        env_vars=[{"name": "LEG", "value": "1"}])])

    # --- gpu ---
    add("gpu_all_available", ["a"], [_grp("a", gpu_access=True, gpu_all=True)],
        gpu_available=True)
    add("gpu_gated_no_hardware", ["a"], [_grp("a", gpu_access=True, gpu_all=True)],
        gpu_available=False)
    add("gpu_specific", ["a"], [_grp("a", gpu_access=True, gpu_all=False,
        gpu_device_ids=["1", "3"])], gpu_available=True)
    add("gpu_all_wins_over_specific", ["all", "spec"], [
        _grp("all", gpu_access=True, gpu_all=True),
        _grp("spec", gpu_access=True, gpu_all=False, gpu_device_ids=["2"]),
    ], gpu_available=True)
    add("gpu_specific_union", ["a", "b"], [
        _grp("a", gpu_access=True, gpu_all=False, gpu_device_ids=["0"]),
        _grp("b", gpu_access=True, gpu_all=False, gpu_device_ids=["2", "10"]),
    ], gpu_available=True)
    add("gpu_grant_no_selection_falls_back_all", ["a"], [_grp("a",
        gpu_access=True, gpu_all=False, gpu_device_ids=[])], gpu_available=True)

    # --- docker ---
    add("docker_access_raw", ["a"], [_grp("a", docker_active=True, docker_access=True)])
    add("docker_limited_defaults", ["a"], [_grp("a", docker_active=True,
        docker_limited=True)])
    add("docker_limited_custom_quota", ["a"], [_grp("a", docker_active=True,
        docker_limited=True, docker_limited_max_containers=25,
        docker_limited_mem_cap_gb=16)])
    add("docker_limited_max_quota_across_groups", ["a", "b"], [
        _grp("a", docker_active=True, docker_limited=True,
             docker_limited_max_containers=5, docker_limited_max_volumes=20),
        _grp("b", docker_active=True, docker_limited=True,
             docker_limited_max_containers=30, docker_limited_max_volumes=2),
    ])
    add("docker_raw_supersedes_limited", ["raw", "lim"], [
        _grp("raw", docker_active=True, docker_access=True),
        _grp("lim", docker_active=True, docker_limited=True,
             docker_limited_allow_dangerous_flags=True),
    ])
    add("docker_privileged", ["a"], [_grp("a", docker_active=True,
        docker_privileged=True)])
    add("docker_section_off_ignored", ["a"], [_grp("a", docker_active=False,
        docker_access=True, docker_privileged=True)])
    add("docker_limited_dangerous_flags_or", ["a", "b"], [
        _grp("a", docker_active=True, docker_limited=True,
             docker_limited_allow_dangerous_flags=False),
        _grp("b", docker_active=True, docker_limited=True,
             docker_limited_allow_dangerous_flags=True),
    ])

    # --- mem / cpu ---
    add("mem_single", ["a"], [_grp("a", mem_limit_enabled=True, mem_limit_gb=8)])
    add("mem_biggest_wins_swap_follows", ["big", "small"], [
        _grp("big", mem_limit_enabled=True, mem_limit_gb=16, mem_swap_disabled=True),
        _grp("small", mem_limit_enabled=True, mem_limit_gb=4, mem_swap_disabled=False),
    ])
    add("mem_disabled_does_not_uncap", ["capped", "open"], [
        _grp("capped", mem_limit_enabled=True, mem_limit_gb=8),
        _grp("open", mem_limit_enabled=False, mem_limit_gb=0),
    ])
    add("cpu_biggest_wins", ["a", "b"], [
        _grp("a", cpu_limit_enabled=True, cpu_limit_cores=8),
        _grp("b", cpu_limit_enabled=True, cpu_limit_cores=2),
    ])
    add("cpu_fractional", ["a"], [_grp("a", cpu_limit_enabled=True,
        cpu_limit_cores=2.5)])

    # --- sudo / downloads (section-gated, priority-wins, None unconfigured) ---
    add("sudo_unconfigured_none", ["a"], [_grp("a", env_vars_active=True,
        env_vars=[{"name": "X", "value": "1"}])])
    add("sudo_priority_wins", ["hi", "lo"], [
        _grp("hi", sudo_active=True, sudo_enable=False),
        _grp("lo", sudo_active=True, sudo_enable=True),
    ])
    add("sudo_section_off_does_not_configure", ["off", "on"], [
        _grp("off", sudo_active=False, sudo_enable=False),
        _grp("on", sudo_active=True, sudo_enable=True),
    ])
    add("downloads_unconfigured_none", ["a"], [_grp("a")])
    add("downloads_priority_block_wins", ["hi", "lo"], [
        _grp("hi", downloads_active=True, downloads_allow=False),
        _grp("lo", downloads_active=True, downloads_allow=True),
    ])

    # --- api keys pools ---
    add("apikeys_single", ["a"], [_grp("a",
        api_keys_pool=_single_pool("API_KEY", "k-aaa", "k-bbb"))])
    add("apikeys_pair_priority_order", ["hi", "lo"], [
        _grp("hi", api_keys_pool=_pair_pool("ID", "SECRET", ("id-1", "sec-1"))),
        _grp("lo", api_keys_pool=_pair_pool("ID", "SECRET", ("id-2", "sec-2"))),
    ])

    # --- volume mounts ---
    add("vol_single", ["a"], [_grp("a", volume_mounts_active=True,
        volume_mounts=[{"volume": "shared", "mountpoint": "/mnt/shared"}])])
    add("vol_union", ["a", "b"], [
        _grp("a", volume_mounts_active=True,
             volume_mounts=[{"volume": "v1", "mountpoint": "/mnt/a"}]),
        _grp("b", volume_mounts_active=True,
             volume_mounts=[{"volume": "v2", "mountpoint": "/mnt/b"}]),
    ])
    add("vol_conflict_priority_wins", ["hi", "lo"], [
        _grp("hi", volume_mounts_active=True,
             volume_mounts=[{"volume": "vhi", "mountpoint": "/mnt/shared"}]),
        _grp("lo", volume_mounts_active=True,
             volume_mounts=[{"volume": "vlo", "mountpoint": "/mnt/shared"}]),
    ])
    add("vol_protected_skipped", ["a"], [_grp("a", volume_mounts_active=True,
        volume_mounts=[{"volume": "bad", "mountpoint": "/etc"},
                       {"volume": "ok", "mountpoint": "/mnt/ok"}])])

    # --- kitchen sink: every feature, multiple groups ---
    add("kitchen_sink", ["power", "base"], [
        _grp("power",
             env_vars_active=True, env_vars=[{"name": "ENV", "value": "prod"}],
             gpu_access=True, gpu_all=True,
             docker_active=True, docker_limited=True, docker_limited_max_containers=50,
             mem_limit_enabled=True, mem_limit_gb=32, mem_swap_disabled=True,
             cpu_limit_enabled=True, cpu_limit_cores=16,
             sudo_active=True, sudo_enable=True,
             downloads_active=True, downloads_allow=False,
             volume_mounts_active=True,
             volume_mounts=[{"volume": "data", "mountpoint": "/mnt/data"}],
             api_keys_pool=_single_pool("TOKEN", "t-1", "t-2")),
        _grp("base",
             env_vars_active=True, env_vars=[{"name": "ENV", "value": "dev"},
                                             {"name": "EXTRA", "value": "1"}],
             mem_limit_enabled=True, mem_limit_gb=4,
             sudo_active=True, sudo_enable=False),
    ], gpu_available=True)

    return S
