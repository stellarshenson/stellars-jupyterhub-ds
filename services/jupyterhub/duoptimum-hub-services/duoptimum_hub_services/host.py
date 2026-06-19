"""Host-resource calculations.

Pure helpers the config calls with already-resolved inputs (e.g. an env-read
fraction). No env var reads here - the config owns those and passes them in.
"""


def resolve_memory_quota_mb(fraction):
    """Per-user memory warning threshold in MB as a fraction of host total RAM.

    Reads ``MemTotal`` from ``/proc/meminfo``; returns a 4 GB fallback when the
    file is unreadable. The caller passes the resolved fraction.
    """
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    total_kb = int(line.split()[1])
                    return int((total_kb / 1024) * fraction)
    except Exception:
        pass
    return 4096  # fallback: 4 GB if /proc/meminfo unavailable
