"""stellars-docker-proxy: an owner-scoped reverse proxy for the Docker socket.

Self-contained and host-agnostic. Two modes share the same per-owner ProxyApp:

* Library: `create_app(ProxyConfig)` builds an aiohttp app bound to one owner.
* Central (`python -m stellars_docker_proxy`): one process holds many such apps,
  each on its own per-user unix socket. Admin HTTP API to register/unregister
  users at runtime; identity stays baked-at-socket on the data path.

The proxy stamps owner labels on created resources, narrows lists/prunes to the
owner, guards actions by ownership, enforces count/storage quotas and CPU/mem
caps, and streams everything else through.
"""

from . import filters, quota
from .admin import create_admin_app
from .config import (
    LABEL_NAMESPACE,
    MANAGED_LABEL,
    OWNER_LABEL,
    ProxyConfig,
)
from .manager import Manager
from .server import classify, create_app, run

__version__ = "0.2.0"

__all__ = [
    "ProxyConfig",
    "OWNER_LABEL",
    "MANAGED_LABEL",
    "LABEL_NAMESPACE",
    "create_app",
    "create_admin_app",
    "Manager",
    "run",
    "classify",
    "filters",
    "quota",
]
