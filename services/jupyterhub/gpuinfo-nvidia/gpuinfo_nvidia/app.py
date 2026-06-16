"""FastAPI app exposing the vendor-neutral GPU-info contract.

Endpoints:
  GET /health -> liveness + whether the driver is usable (always 200 if up)
  GET /gpus   -> {vendor, available, count, gpus[], timestamp}

Both are read-only and side-effect free. The app stays up and answers even when
no GPU/driver is present (``available: false``), so the hub's health-gated
dependency is satisfied on GPU-less hosts too.
"""

from datetime import datetime, timezone

from fastapi import FastAPI

from . import __version__, nvidia
from .schema import GpuReport, Health

app = FastAPI(
    title="gpuinfo-nvidia",
    version=__version__,
    summary="Vendor-neutral GPU-info sidecar API (NVIDIA implementation)",
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
