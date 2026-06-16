"""Vendor-neutral GPU-info API schema.

Shared contract across all sidecar implementations (nvidia today; amd / intel /
applesilicon later). Vendor-specific fields a backend cannot report are left
``None`` (e.g. a backend with no utilisation counter), never omitted, so the hub
parses one stable shape regardless of which sidecar answers.
"""

from typing import List, Optional

from pydantic import BaseModel


class GpuProcess(BaseModel):
    """A process holding GPU memory - the hook for attributing load to a user."""

    pid: int
    name: str
    used_memory_mb: Optional[int] = None


class Gpu(BaseModel):
    index: str
    name: Optional[str] = None
    uuid: Optional[str] = None
    utilization: Optional[int] = None  # percent; None if the backend has no counter
    memory_used_mb: Optional[int] = None
    memory_total_mb: Optional[int] = None
    processes: List[GpuProcess] = []


class GpuReport(BaseModel):
    vendor: str
    available: bool  # False when the driver/tooling is missing (gpus then empty)
    count: int
    gpus: List[Gpu] = []
    timestamp: str


class Health(BaseModel):
    status: str
    vendor: str
    driver_available: bool
