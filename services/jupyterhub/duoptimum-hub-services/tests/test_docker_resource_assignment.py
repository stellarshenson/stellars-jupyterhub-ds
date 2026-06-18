"""Pure resource-assignment helpers in docker_utils: assigned cpu/memory and the
`limited` flags the UI uses to label a bar 'assigned' vs 'host (no limit)' and to
measure usage against the right ceiling. Tested independently of Docker."""
from duoptimum_hub_services.docker_utils import (
    derive_cpu_assignment,
    derive_memory_assignment,
    mem_usage_excluding_cache,
)

HOST_CORES = 16
HOST_RAM = 64 * 1024**3  # bytes
GB = 1024**3


# ── CPU ──────────────────────────────────────────────────────────────────────
def test_cpu_nano_cpus_is_limited():
    # DockerSpawner cpu_limit -> NanoCpus (billionths of a core)
    assert derive_cpu_assignment({"NanoCpus": 4_000_000_000}, HOST_CORES) == (4.0, True)


def test_cpu_cfs_quota_is_limited():
    # cgroup cfs quota: 200000 / 100000 = 2 cores
    assert derive_cpu_assignment({"CpuQuota": 200000, "CpuPeriod": 100000}, HOST_CORES) == (2.0, True)


def test_cpu_cfs_quota_uses_default_period_when_absent():
    assert derive_cpu_assignment({"CpuQuota": 150000}, HOST_CORES) == (1.5, True)


def test_cpu_unlimited_falls_back_to_host_cores():
    assert derive_cpu_assignment({}, HOST_CORES) == (HOST_CORES, False)


def test_cpu_nano_cpus_wins_over_quota():
    assert derive_cpu_assignment({"NanoCpus": 1_000_000_000, "CpuQuota": 800000}, HOST_CORES) == (1.0, True)


# ── Memory ───────────────────────────────────────────────────────────────────
def test_memory_explicit_limit_is_assigned():
    assert derive_memory_assignment({"Memory": 8 * 1024**3}, HOST_RAM) == (8 * 1024**3, True)


def test_memory_unlimited_falls_back_to_host_ram():
    # no HostConfig.Memory -> the cgroup limit Docker reports is the host RAM
    assert derive_memory_assignment({}, HOST_RAM) == (HOST_RAM, False)


def test_memory_zero_limit_is_unlimited():
    assert derive_memory_assignment({"Memory": 0}, HOST_RAM) == (HOST_RAM, False)


# ── Memory usage excluding page cache (regression: 143 GB vs real 41 GB) ──────
# The raw cgroup `usage` counts reclaimable file cache; docker stats / Docker
# Desktop subtract it. Counting it made an idle, file-heavy container report tens
# of GB it was not using, over-reporting the host memory bar.
def test_mem_usage_cgroup_v2_subtracts_inactive_file():
    # cgroup v2: usage 51 GB carries 11 GB inactive_file cache -> real 40 GB
    stats = {"usage": 51 * GB, "stats": {"inactive_file": 11 * GB}}
    assert mem_usage_excluding_cache(stats) == 40 * GB


def test_mem_usage_cgroup_v1_subtracts_total_inactive_file():
    # cgroup v1 uses the total_inactive_file key, preferred when both present
    stats = {"usage": 20 * GB, "stats": {"total_inactive_file": 8 * GB, "inactive_file": 3 * GB}}
    assert mem_usage_excluding_cache(stats) == 12 * GB


def test_mem_usage_no_cache_keys_returns_raw_usage():
    # older daemons may not expose the stats sub-dict at all
    assert mem_usage_excluding_cache({"usage": 5 * GB}) == 5 * GB
    assert mem_usage_excluding_cache({"usage": 5 * GB, "stats": {}}) == 5 * GB


def test_mem_usage_ignores_cache_larger_than_usage():
    # guard the docker-CLI invariant: never subtract when inactive >= usage
    # (would yield a negative/zero figure); fall back to raw usage
    stats = {"usage": 2 * GB, "stats": {"inactive_file": 9 * GB}}
    assert mem_usage_excluding_cache(stats) == 2 * GB


def test_mem_usage_empty_stats_is_zero():
    assert mem_usage_excluding_cache({}) == 0
