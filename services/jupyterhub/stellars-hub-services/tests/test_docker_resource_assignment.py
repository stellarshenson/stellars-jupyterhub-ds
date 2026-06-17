"""Pure resource-assignment helpers in docker_utils: assigned cpu/memory and the
`limited` flags the UI uses to label a bar 'assigned' vs 'host (no limit)' and to
measure usage against the right ceiling. Tested independently of Docker."""
from stellars_hub_services.docker_utils import derive_cpu_assignment, derive_memory_assignment

HOST_CORES = 16
HOST_RAM = 64 * 1024**3  # bytes


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
