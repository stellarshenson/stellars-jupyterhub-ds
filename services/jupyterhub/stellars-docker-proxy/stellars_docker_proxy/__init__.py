"""stellars-docker-proxy: an owner-scoped reverse proxy for the Docker socket.

Pure library, host-agnostic. Consumers (JupyterHub) host it in-process:

* `create_app(ProxyConfig)` builds an aiohttp app bound to one owner.
* `Manager(socket_dir)` keeps a dict of `user -> per-user UnixSite listener`,
  with `register(user, overrides)` and `unregister(user)` running on the
  caller's event loop. Identity is baked at socket-listener level.

The proxy stamps owner labels on created resources, narrows lists/prunes to
the owner, guards actions by ownership, enforces count/storage quotas and
CPU/mem caps, and streams everything else through. No HTTP admin surface,
no tokens, no standalone mode - the caller embeds it.
"""

from . import filters, quota
from .config import (
    LABEL_NAMESPACE,
    MANAGED_LABEL,
    OWNER_LABEL,
    ProxyConfig,
)
from .manager import Manager
from .server import classify, create_app, run

__version__ = "0.3.0"

__all__ = [
    "ProxyConfig",
    "OWNER_LABEL",
    "MANAGED_LABEL",
    "LABEL_NAMESPACE",
    "create_app",
    "Manager",
    "run",
    "classify",
    "filters",
    "quota",
]
