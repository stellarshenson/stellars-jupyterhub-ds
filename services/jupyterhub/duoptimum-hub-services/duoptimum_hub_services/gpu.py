"""GPU detection via the GPU-info sidecar (vendor-neutral).

The hub has no GPU access of its own; it asks the sidecar (see ``gpu_client``)
for the host inventory instead of spawning an ephemeral nvidia container. The
same sidecar serves live utilisation (see ``gpu_cache``), so one long-running
peer backs both detection and sampling.

Detection runs once at hub startup and must not stall the boot: the sidecar is
self-started just before this, so a short bounded probe catches it; if it is
still unreachable we fall back to the last-known inventory persisted on the data
volume (see ``persisted_cache``) rather than blocking or showing nothing.
"""

from .persisted_cache import load_cached, save_cached

# inventory rarely changes between restarts, so a short bounded probe (~5s worst
# case: 3 attempts x (1s timeout + 0.5s delay)) is enough to catch a just-self-
# started local sidecar - never the old 20x1s stall. A miss falls back to the
# last-known inventory and self-heals on the next background refresh.
_BOOT_PROBE = {'attempts': 3, 'delay': 0.5, 'timeout': 1}
_INVENTORY_CACHE = 'gpu_inventory'


def enumerate_gpus(_image=None, **probe):
    """List the host GPUs from the sidecar.

    Returns ``[{index, name, uuid, memory_mb}]`` (index/name/uuid as strings,
    memory_mb as int), or ``[]`` on any failure (sidecar down, no GPU). The
    legacy CUDA-image argument is accepted and ignored - the sidecar owns the
    probe now - so existing callers keep working. ``probe`` overrides the
    retry budget (attempts/delay/timeout).
    """
    from . import gpu_client

    payload = gpu_client.fetch_payload_with_retry(**{**_BOOT_PROBE, **probe})
    if not payload:
        return []
    gpus = []
    for g in payload.get('gpus', []) or []:
        idx = g.get('index')
        if idx is None:
            continue
        gpus.append({
            'index': str(idx),
            'name': g.get('name') or '',
            'uuid': g.get('uuid') or '',
            'memory_mb': int(g.get('memory_total_mb') or 0),
        })
    return gpus


def resolve_gpu_mode(gpu_enabled, _image=None, probe_sidecar=True):
    """Resolve GPU mode from env setting. Returns (gpu_enabled, nvidia_detected, gpu_list).

    Two modes only:
      0          = deliberately OFF - never touches the sidecar, no GPUs
      1          = AUTODETECT (the default) - probe the sidecar and turn GPU on iff
                   GPUs are actually detected
      other != 0 = autodetect too (the legacy value 2 still works, for back-compat)

    There is no "forced on": the platform never claims GPUs it cannot back.

    In autodetect the sidecar is queried for the host inventory (short bounded probe),
    but only when ``probe_sidecar`` is True (the caller's self-start succeeded, or an
    operator/compose-managed sidecar is configured). If the sidecar is known-unreachable
    (``probe_sidecar`` False) the probe is skipped so a missing sidecar never stalls boot
    on DNS/connect. A fresh probe result is persisted as the last-known inventory; an
    empty/skipped probe seeds from that persisted snapshot, so a cold/slow sidecar at
    boot reuses last-known GPUs rather than dropping to off. Presence is derived from the
    (possibly seeded) inventory, so the mode collapses to on/off.
    """
    if gpu_enabled == 0:
        return 0, 0, []
    gpu_list = enumerate_gpus() if probe_sidecar else []
    if gpu_list:
        save_cached(_INVENTORY_CACHE, gpu_list)          # refresh last-known
    else:
        seeded = load_cached(_INVENTORY_CACHE)           # fall back to last-known
        if seeded is not None:
            gpu_list = seeded[0] or []
    nvidia_detected = 1 if gpu_list else 0
    return (1 if nvidia_detected else 0), nvidia_detected, gpu_list


def gpu_summary_lines():
    """Readable per-GPU lines for the hub startup log: capabilities (name, total
    memory) plus a live health snapshot (utilisation, used memory, temperature,
    power) fetched once from the sidecar. Any metric the sidecar did not report is
    omitted (never printed as None). Returns [] when the sidecar is unreachable -
    the caller logs nothing extra (no health to report for unreachable cards).
    """
    from . import gpu_client

    payload = gpu_client.fetch_payload_with_retry(attempts=1, delay=0, timeout=1)
    lines = []
    for g in (payload or {}).get('gpus', []) or []:
        idx = g.get('index', '?')
        name = g.get('name') or 'unknown'
        total_mb = g.get('memory_total_mb')
        cap = f"GPU {idx}: {name}" + (f" ({total_mb / 1024:.0f} GB)" if total_mb else "")
        health = []
        if g.get('utilization') is not None:
            health.append(f"{g['utilization']}% util")
        used_mb = g.get('memory_used_mb')
        if used_mb is not None:
            health.append(f"{used_mb / 1024:.1f}/{total_mb / 1024:.0f} GB" if total_mb else f"{used_mb / 1024:.1f} GB used")
        if g.get('temperature_c') is not None:
            health.append(f"{g['temperature_c']} C")
        if g.get('power_w') is not None:
            health.append(f"{g['power_w']:.0f} W")
        lines.append(cap + (" - " + ", ".join(health) if health else ""))
    return lines


def is_wsl2():
    """True if the host is WSL2.

    On WSL2 GPUs come through a single paravirtual /dev/dxg, so per-GPU container
    isolation is not enforceable - selection becomes advisory. Detected from the
    kernel release string (containers share the host kernel).
    """
    try:
        with open('/proc/version') as f:
            v = f.read().lower()
        return 'microsoft' in v or 'wsl2' in v
    except Exception:
        return False
