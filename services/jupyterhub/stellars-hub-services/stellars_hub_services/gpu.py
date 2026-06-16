"""GPU detection via the GPU-info sidecar (vendor-neutral).

The hub has no GPU access of its own; it asks the sidecar (see ``gpu_client``)
for the host inventory instead of spawning an ephemeral nvidia container. The
same sidecar serves live utilisation (see ``gpu_cache``), so one long-running
peer backs both detection and sampling.
"""


def enumerate_gpus(_image=None):
    """List the host GPUs from the sidecar.

    Returns ``[{index, name, uuid, memory_mb}]`` (index/name/uuid as strings,
    memory_mb as int), or ``[]`` on any failure (sidecar down, no GPU). The
    legacy CUDA-image argument is accepted and ignored - the sidecar owns the
    probe now - so existing callers keep working.
    """
    from . import gpu_client

    payload = gpu_client.fetch_payload_with_retry()
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


def resolve_gpu_mode(gpu_enabled, _image=None):
    """Resolve GPU mode from env setting. Returns (gpu_enabled, nvidia_detected, gpu_list).

    gpu_enabled: 0=disabled, 1=enabled, 2=autodetect

    Whenever GPU is on - forced (mode 1) or autodetected (mode 2) - the sidecar is
    queried for the host inventory. In autodetect, presence is derived from the
    inventory so the mode collapses to on/off. In forced mode the grant stays on
    regardless of what the inventory finds; the list is still populated for the
    UI. Mode 0 never touches the sidecar.
    """
    nvidia_detected = 0
    gpu_list = []
    if gpu_enabled in (1, 2):
        gpu_list = enumerate_gpus()
        nvidia_detected = 1 if gpu_list else 0
        if gpu_enabled == 2:
            gpu_enabled = 1 if nvidia_detected else 0
    return gpu_enabled, nvidia_detected, gpu_list


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
