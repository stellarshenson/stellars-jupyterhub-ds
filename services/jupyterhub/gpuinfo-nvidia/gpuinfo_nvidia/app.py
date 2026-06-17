"""FastAPI app exposing the vendor-neutral GPU-info contract.

Endpoints:
  GET /health -> liveness + whether the driver is usable (always 200 if up)
  GET /gpus   -> {vendor, available, count, gpus[], timestamp}

Both are read-only and side-effect free. The app stays up and answers even when
no GPU/driver is present (``available: false``), so the hub's health-gated
dependency is satisfied on GPU-less hosts too.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from . import __version__, nvidia
from .schema import GpuReport, Health

# Ride uvicorn's configured logger so these lines land in the container's stdout
# (docker logs) alongside uvicorn's own startup/serving lines.
log = logging.getLogger("uvicorn.error")


def _gpu_health(g, total_mb):
    """One-line current-health summary for a GPU; skips any metric the driver did
    not report (so a partial sample never prints 'None')."""
    used = g.get("memory_used_mb")
    util = g.get("utilization")
    temp = g.get("temperature_c")
    power = g.get("power_w")
    parts = [
        f"{util}% util" if util is not None else "",
        f"{used / 1024:.1f}/{total_mb / 1024:.0f} GB mem" if used is not None and total_mb else "",
        f"{temp}C" if temp is not None else "",
        f"{power:.0f} W" if power is not None else "",
    ]
    return ", ".join(p for p in parts if p)


def _log_detected_hardware():
    """Sample the GPUs once at startup and log the inventory + current health (or
    the absence of any GPU)."""
    available, gpus = nvidia.sample()
    if not available or not gpus:
        log.warning("[gpuinfo-nvidia] no NVIDIA driver/GPU detected - serving empty inventory")
        return
    log.info("[gpuinfo-nvidia] detected %d GPU(s):", len(gpus))
    for g in gpus:
        mb = g.get("memory_total_mb")
        mem = f"{mb / 1024:.0f} GB" if mb else "? GB"
        health = _gpu_health(g, mb)
        log.info(
            "[gpuinfo-nvidia]   GPU %s: %s (%s, %s)%s",
            g.get("index"), g.get("name") or "unknown", g.get("uuid") or "no-uuid", mem,
            f" - health: {health}" if health else "",
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("[gpuinfo-nvidia] v%s starting (vendor=%s)", __version__, nvidia.VENDOR)
    _log_detected_hardware()
    log.info("[gpuinfo-nvidia] ready - serving /health and /gpus")
    yield
    log.info("[gpuinfo-nvidia] shutting down")


app = FastAPI(
    title="gpuinfo-nvidia",
    version=__version__,
    summary="Vendor-neutral GPU-info sidecar API (NVIDIA implementation)",
    lifespan=lifespan,
)


def _now():
    return datetime.now(timezone.utc).isoformat()


@app.get("/health", response_model=Health)
def health():
    return Health(status="ok", vendor=nvidia.VENDOR, driver_available=nvidia.driver_available())


@app.get("/gpus", response_model=GpuReport)
def gpus():
    available, gpu_list = nvidia.sample()
    return GpuReport(
        vendor=nvidia.VENDOR,
        available=available,
        count=len(gpu_list),
        gpus=gpu_list,
        timestamp=_now(),
    )
