"""HTTP client for the GPU-info sidecar (vendor-neutral API).

The hub container has no GPU access of its own. Rather than spawn an ephemeral
nvidia container on every probe, it queries a long-running sidecar
(``gpuinfo-nvidia``, or a future amd / intel / applesilicon peer implementing the
same API) over a dedicated docker network.

Contract: ``GET {url}/gpus`` -> ``{vendor, available, count, gpus[], timestamp}``
where each gpu carries ``index, name, uuid, utilization, memory_used_mb,
memory_total_mb, processes[]``. Stdlib-only (urllib) so it works in the sync
thread-pool that drives the periodic sampler.
"""

import json
import logging
import os
import time
import urllib.request

log = logging.getLogger('jupyterhub')

_GPUINFO_URL = os.environ.get('JUPYTERHUB_GPUINFO_NVIDIA_URL', '').rstrip('/')  # a {hostname} template until configure() overrides it at startup with the sidecar's runtime-discovered address; empty default avoids a hardcoded sidecar host


def configure(url):
    """Point the client at the sidecar base URL (called once at hub startup)."""
    global _GPUINFO_URL
    if url:
        _GPUINFO_URL = url.rstrip('/')


def get_url():
    return _GPUINFO_URL


def fetch_payload(timeout=5):
    """Return the full ``/gpus`` payload dict, or None if the sidecar is unreachable."""
    try:
        with urllib.request.urlopen(f'{_GPUINFO_URL}/gpus', timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8', 'replace'))
    except Exception:
        return None


def fetch_gpus(timeout=5):
    """List of per-GPU dicts from the sidecar ([] on any failure)."""
    payload = fetch_payload(timeout=timeout)
    return (payload or {}).get('gpus', []) or []


def fetch_payload_with_retry(attempts=20, delay=1.0, timeout=5):
    """Block until the sidecar answers, retrying only while it is unreachable.

    Used at hub startup for inventory: a sidecar still booting (no answer) is
    retried (the inventory is computed once, so a transient miss would leave GPU
    off until the next hub restart); a sidecar that answers with zero GPUs returns
    immediately (that is an authoritative "no GPU", not a transient miss). Returns
    the payload dict, or None if every attempt was unreachable.
    """
    payload = None
    for _ in range(max(1, attempts)):
        payload = fetch_payload(timeout=timeout)
        if payload is not None:
            return payload
        time.sleep(delay)
    return payload
