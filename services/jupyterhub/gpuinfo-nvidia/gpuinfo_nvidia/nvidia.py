"""NVIDIA backend: sample GPU state by parsing ``nvidia-smi`` CSV output.

Every function is defensive - any failure (no driver, no GPU, nvidia-smi absent,
timeout) degrades to "unavailable" / empty rather than raising, so the sidecar
keeps answering and the hub falls back to plain inventory.
"""

import subprocess

VENDOR = "nvidia"

_GPU_QUERY = "index,name,uuid,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw"
_PROC_QUERY = "gpu_uuid,pid,process_name,used_gpu_memory"


def _run(args, timeout=10):
    """Run nvidia-smi with the given args, return stdout text (raises on failure)."""
    return subprocess.run(
        ["nvidia-smi", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    ).stdout


def _to_int(value):
    """Parse an nvidia-smi numeric cell ('1493' or '1493 MiB') to int, or None."""
    try:
        return int(str(value).strip().split()[0])
    except (ValueError, IndexError, AttributeError):
        return None


def _to_float(value):
    """Parse an nvidia-smi numeric cell ('125.34' or '125.34 W') to float, or None."""
    try:
        return float(str(value).strip().split()[0])
    except (ValueError, IndexError, AttributeError):
        return None


def driver_available():
    """True if nvidia-smi responds (driver present and usable)."""
    try:
        _run(["--query-gpu=count", "--format=csv,noheader,nounits"], timeout=5)
        return True
    except Exception:
        return False


def _query_processes():
    """Map gpu_uuid -> [{pid, name, used_memory_mb}] for running compute processes."""
    by_uuid = {}
    try:
        out = _run([f"--query-compute-apps={_PROC_QUERY}", "--format=csv,noheader,nounits"])
    except Exception:
        return by_uuid
    for line in out.strip().splitlines():
        # Split defensively: process_name (3rd field) may itself contain commas,
        # so anchor on the fixed first two and last fields and re-join the middle.
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue
        uuid = parts[0]
        try:
            pid = int(parts[1])
        except ValueError:
            continue
        used_mem = _to_int(parts[-1])
        name = ",".join(parts[2:-1]).strip()
        by_uuid.setdefault(uuid, []).append(
            {"pid": pid, "name": name, "used_memory_mb": used_mem}
        )
    return by_uuid


def sample():
    """Return ``(available, gpus)`` where gpus is a list of per-GPU dicts.

    Never raises. ``available`` is False (and gpus empty) when nvidia-smi cannot
    be queried. Each GPU carries utilisation, memory and the processes holding it.
    """
    try:
        out = _run([f"--query-gpu={_GPU_QUERY}", "--format=csv,noheader,nounits"])
    except Exception:
        return False, []

    procs = _query_processes()
    gpus = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 8:
            continue
        uuid = parts[2] or None
        gpus.append(
            {
                "index": parts[0],
                "name": parts[1] or None,
                "uuid": uuid,
                "utilization": _to_int(parts[3]),
                "memory_used_mb": _to_int(parts[4]),
                "memory_total_mb": _to_int(parts[5]),
                "temperature_c": _to_int(parts[6]),
                "power_w": _to_float(parts[7]),
                "processes": procs.get(parts[2], []),
            }
        )
    return True, gpus
