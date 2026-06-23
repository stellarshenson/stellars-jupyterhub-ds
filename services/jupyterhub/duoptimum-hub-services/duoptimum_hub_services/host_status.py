"""Host-status provider abstraction.

Home-screen host-status view (host CPU cores, host RAM, GPU inventory + liveness)
is environment-specific. Each spawner declares a `HostStatusProvider`; hub
resolves ONE instance at boot (`resolve_host_status_provider`, reads the
configured spawner class) and the activity handler delegates the host aggregate
to it. Provider exposes any subset of {CPU, MEM, GPU}; portal renders only the
present dimensions, nothing when the set is empty.

Boundary: provider owns the HOST AGGREGATE only (host totals + GPU). Per-user
server rows stay in the activity handler - hub-generic (JupyterHub DB + per-user
container stats), not environment-specific.

Packageable: a new environment ships as a Duoptimum spawner subclass + its
provider. Constructor takes the boot context dict; future providers read the keys
they need. No portal rebuild - the contract is data, not React.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

# Dimension keys - also the strings emitted in `host_capabilities` on the wire.
CPU = "cpu"
MEM = "mem"
GPU = "gpu"

# Per-dimension status (provider contract; serialises through the existing flat
# response fields - a null host total reads as unavailable, gpu_connected=false
# as degraded - so no separate status object goes on the wire).
OK = "ok"  # real values
DEGRADED = "degraded"  # exposed, partially readable (stale inventory, no live sample)
UNAVAILABLE = "unavailable"  # exposed but unreadable right now


class HostStatusProvider(ABC):
    """One per environment, declared on the spawner, resolved once at boot."""

    @abstractmethod
    def capabilities(self) -> set[str]:
        """Dimensions this environment exposes - any subset of {CPU, MEM, GPU}.
        Empty set = no host-status panel."""

    @abstractmethod
    def get_status(self) -> dict:
        """Current host aggregate. Dict keyed by the EXPOSED dimensions only -
        every key present here is also in `capabilities()`. JSON-serializable;
        no provider object leaks to the wire.

        Shape (each top key optional):
          cpu: {host_total_cores: int|None, status: str}
          mem: {host_total_mb: float|None, status: str}
          gpu: {devices: list, connected: bool, status: str}
        """


def _host_total_memory_mb():
    """Total physical host RAM in MB - denominator for the "% of host" memory
    figure. Reads /proc/meminfo directly. NO fallback: returns None on any read
    failure so the frontend shows an explicit "unavailable" rather than a
    fabricated denominator (operator: better to say "I don't know" than guess)."""
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    return round(int(line.split()[1]) / 1024, 1)  # MemTotal is in kB
    except Exception:
        pass
    return None


def _host_cpu_count():
    """Total logical CPU cores on the host - denominator for the "% of host" CPU
    figure. Counts `processor` entries in /proc/cpuinfo (host-transparent inside a
    container). NO fallback: returns None on any read failure so the frontend
    shows "unavailable" rather than a fabricated denominator."""
    try:
        with open('/proc/cpuinfo') as f:
            count = sum(1 for line in f if line.startswith('processor'))
        return count or None
    except Exception:
        pass
    return None


class DockerHostStatusProvider(HostStatusProvider):
    """Reference provider: local Docker host. CPU/MEM from /proc, GPU from the
    gpuinfo sidecar. GPU is a capability ONLY when GPU mode resolved on at boot -
    when off, GPU is absent from capabilities() and get_status() entirely (not
    merely reported unavailable).

    Constructed from the hub boot context:
      gpu_enabled: boot GPU mode result (config `gpu_enabled`) - GPU capability gate
      gpu_list:    host GPU inventory enumerated once at startup (static for the
                   hub lifetime); the live per-GPU sample is fetched per call
    """

    def __init__(self, context: dict | None = None):
        context = context or {}
        self._gpu_enabled = bool(context.get('gpu_enabled'))
        self._gpu_list = context.get('gpu_list') or []

    def capabilities(self) -> set[str]:
        caps = {CPU, MEM}
        if self._gpu_enabled:
            caps.add(GPU)
        return caps

    def get_status(self) -> dict:
        cores = _host_cpu_count()
        mem_mb = _host_total_memory_mb()
        out = {
            CPU: {"host_total_cores": cores, "status": OK if cores else UNAVAILABLE},
            MEM: {"host_total_mb": mem_mb, "status": OK if mem_mb else UNAVAILABLE},
        }
        if self._gpu_enabled:
            out[GPU] = self._gpu_status()
        return out

    def _gpu_status(self) -> dict:
        # late import - gpu_cache pulls tornado/docker; keep this module import-cheap
        # (the spawner imports it to declare host_status_provider_class)
        from .gpu_cache import get_gpu_utilization_with_refresh, gpu_sidecar_connected

        gpu_list = self._gpu_list
        # live per-GPU sample merged by index onto the static inventory (same shape
        # the handler built inline before this moved here)
        gpu_util = get_gpu_utilization_with_refresh() if gpu_list else {}
        devices = []
        for g in gpu_list:
            idx = g.get("index")
            entry = {
                "index": idx,
                "name": g.get("name"),
                "uuid": g.get("uuid"),
                "memory_mb": g.get("memory_mb", 0),
            }
            sample = gpu_util.get(str(idx)) if idx is not None else None
            if sample:
                entry["utilization"] = sample.get("utilization")
                entry["memory_used_mb"] = sample.get("memory_used_mb")
                entry["temperature_c"] = sample.get("temperature_c")
                entry["power_w"] = sample.get("power_w")
                entry["processes"] = sample.get("processes", [])
            devices.append(entry)
        connected = gpu_sidecar_connected() if gpu_list else False
        # ok = sidecar live; degraded = (possibly stale) inventory but no live
        # sample; unavailable = no inventory at all
        status = OK if connected else (DEGRADED if devices else UNAVAILABLE)
        return {"devices": devices, "connected": connected, "status": status}


def resolve_host_status_provider(spawner_class, context: dict | None = None):
    """Instantiate the spawner's declared host-status provider, or None if the
    spawner declares none. `spawner_class` is the configured class or its dotted
    string (`c.JupyterHub.spawner_class`); the provider class is read off the
    spawner's `host_status_provider_class` attribute and constructed with the boot
    context dict."""
    if isinstance(spawner_class, str):
        from traitlets.utils.importstring import import_item

        spawner_class = import_item(spawner_class)
    provider_cls = getattr(spawner_class, 'host_status_provider_class', None)
    if provider_cls is None:
        return None
    return provider_cls(context or {})
