"""stellars-docker-proxy: an owner-scoped reverse proxy for the Docker socket.

Self-contained and host-agnostic - it knows only an ``owner`` string. It stamps
owner labels on created resources, narrows lists/prunes to the owner, guards
actions by ownership, enforces count/storage quotas and per-container resource
caps, and streams everything else through. Identity resolution (e.g. a token
roundtrip) is the consumer's concern via the ``owner_resolver`` hook.
"""

from . import filters, quota
from .config import (
    LABEL_NAMESPACE,
    MANAGED_LABEL,
    OWNER_LABEL,
    ProxyConfig,
)
from .server import classify, create_app, run

__version__ = "0.1.0"

__all__ = [
    "ProxyConfig",
    "OWNER_LABEL",
    "MANAGED_LABEL",
    "LABEL_NAMESPACE",
    "create_app",
    "run",
    "classify",
    "filters",
    "quota",
]
