"""Configuration and label constants for the per-user Docker socket proxy.

A single proxy process is bound to exactly one ``owner``. Identity is the
socket: whoever connects to the listen socket acts as that owner, so the stock
``docker`` CLI works unchanged (no tokens, no wrapper). The consumer
(JupyterHub) starts one proxy per limited user and mounts its socket at the
user container's ``/var/run/docker.sock``.
"""

import os
from dataclasses import dataclass, field
from typing import Tuple

# Label namespace; overridable via env to dodge clashes with host's own labels.
LABEL_NAMESPACE = os.environ.get(
    "JUPYTERHUB_DOCKER_PROXY_LABEL_PREFIX",
    "jupyterhub.docker.proxy",
)
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
    # Per-flag bypasses of dangerous_reason(). Quotas + labelling stay on.
    allow_privileged: bool = False
    allow_dangerous_flags: bool = False
    # When False, the proxy REWRITES the user's com.docker.compose.project label
    # to `compose_project` instead of leaving it alone. Strict mode for groups
    # that want every container pinned to the per-user project.
    allow_compose_project_override: bool = True
    # Network names this user is granted access to even though they are not
    # owner-labelled. Typical use: grant access to the hub network so user
    # containers can `--network <hub-net>` and resolve other containers by DNS.
    # Access is enforced everywhere: networks in this set appear in `docker
    # network ls`, container creates referencing them (HostConfig.NetworkMode
    # or NetworkingConfig.EndpointsConfig) are accepted, and `docker network
    # connect <net> <container>` is forwarded. Networks NOT in this set and
    # NOT owner-labelled are blocked end-to-end - hidden in list, container
    # creates referencing them are rejected with 403, and connect/disconnect
    # actions return 404. Built-in modes (bridge/none/default/container:*) are
    # always allowed and need no entry here.
    extra_accessible_networks: Tuple[str, ...] = field(default_factory=tuple)
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
