"""Configuration and label constants for the per-user Docker socket proxy.

A single proxy process is bound to exactly one ``owner``. Identity is the
socket: whoever connects to the listen socket acts as that owner, so the stock
``docker`` CLI works unchanged (no tokens, no wrapper). The consumer
(JupyterHub) starts one proxy per limited user and mounts its socket at the
user container's ``/var/run/docker.sock``.
"""

from dataclasses import dataclass, field
from typing import Tuple

# Label namespace stamped on every resource the proxy creates. Ownership and
# all filtering keys off OWNER_LABEL; MANAGED_LABEL marks proxy-created objects
# so a janitor can find them later.
LABEL_NAMESPACE = "stellars"
OWNER_LABEL = f"{LABEL_NAMESPACE}.owner"
MANAGED_LABEL = f"{LABEL_NAMESPACE}.managed"

BYTES_PER_GB = 1024 ** 3
NANO_PER_CORE = 1_000_000_000


@dataclass
class ProxyConfig:
    """Per-owner proxy settings.

    Counts are hard quotas (rejected at create). ``max_storage_gb`` is a soft
    budget enforced by blocking new creates once measured usage is over it -
    a single existing volume can still grow past it (no FS-level wall on
    Docker Desktop / WSL2). CPU/memory caps are per created container.
    """

    owner: str
    listen_socket: str
    upstream_socket: str = "/var/run/docker.sock"
    max_containers: int = 10
    max_volumes: int = 10
    max_networks: int = 3
    max_storage_gb: float = 50.0
    cpu_cap_cores: float = 2.0
    mem_cap_gb: float = 8.0
    image_allowlist: Tuple[str, ...] = field(default_factory=tuple)
    block_dangerous: bool = True
    # When set, ad-hoc `docker run` containers are grouped under this compose
    # project (Docker Desktop dashboard grouping). Empty = free-floating. A
    # container the user creates via `docker compose` (already carrying a
    # com.docker.compose.project label) is left untouched.
    compose_project: str = ""
    # Permission bits on the listen socket. Defaults world-rw because the socket
    # is already owner-scoped and access is governed by which container mounts it.
    socket_mode: int = 0o666
    name_prefix: str = ""

    def __post_init__(self):
        if not self.owner:
            raise ValueError("owner is required")
        if not self.listen_socket:
            raise ValueError("listen_socket is required")
        if not self.name_prefix:
            self.name_prefix = f"user-{self.owner}-"
