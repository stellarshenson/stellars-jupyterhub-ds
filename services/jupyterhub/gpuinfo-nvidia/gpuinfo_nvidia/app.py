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


def _log_detected_hardware():
    """Sample the GPUs once at startup and log what was detected (or its absence)."""
    available, gpus = nvidia.sample()
    if not available or not gpus:
        log.warning("[gpuinfo-nvidia] no NVIDIA driver/GPU detected - serving empty inventory")
        return
    log.info("[gpuinfo-nvidia] detected %d GPU(s):", len(gpus))
    for g in gpus:
        mb = g.get("memory_total_mb")
        mem = f"{mb / 1024:.0f} GB" if mb else "? GB"
        log.info(
            "[gpuinfo-nvidia]   GPU %s: %s (%s, %s)",
            g.get("index"), g.get("name") or "unknown", g.get("uuid") or "no-uuid", mem,
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
