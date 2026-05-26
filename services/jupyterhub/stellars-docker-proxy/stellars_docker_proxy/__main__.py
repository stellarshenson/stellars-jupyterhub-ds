"""CLI entrypoint.

Example:
    python -m stellars_docker_proxy \
        --owner alice --listen-socket /run/stellars/alice.sock \
        --max-containers 10 --compose-project jupyterhub
"""

import argparse
import asyncio
import logging

from .config import ProxyConfig
from .server import run


def _parse_args(argv=None):
    p = argparse.ArgumentParser(prog="stellars-docker-proxy")
    p.add_argument("--owner", required=True, help="owner all resources are scoped to")
    p.add_argument("--listen-socket", required=True, help="unix socket path to serve")
    p.add_argument("--upstream-socket", default="/var/run/docker.sock")
    p.add_argument("--max-containers", type=int, default=10)
    p.add_argument("--max-volumes", type=int, default=10)
    p.add_argument("--max-networks", type=int, default=3)
    p.add_argument("--max-storage-gb", type=float, default=50.0)
    p.add_argument("--cpu-cap-cores", type=float, default=2.0)
    p.add_argument("--mem-cap-gb", type=float, default=8.0)
    p.add_argument("--image-allow", action="append", default=[],
                   help="allowed image (repeatable); none = allow all")
    p.add_argument("--compose-project", default="",
                   help="group ad-hoc containers under this compose project")
    p.add_argument("--no-block-dangerous", action="store_true",
                   help="do not reject privileged/host-mount/host-net creates")
    p.add_argument("--socket-mode", default="0666", help="octal mode for the listen socket")
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="[%(levelname)1.1s %(asctime)s %(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    config = ProxyConfig(
        owner=args.owner,
        listen_socket=args.listen_socket,
        upstream_socket=args.upstream_socket,
        max_containers=args.max_containers,
        max_volumes=args.max_volumes,
        max_networks=args.max_networks,
        max_storage_gb=args.max_storage_gb,
        cpu_cap_cores=args.cpu_cap_cores,
        mem_cap_gb=args.mem_cap_gb,
        image_allowlist=tuple(args.image_allow),
        block_dangerous=not args.no_block_dangerous,
        compose_project=args.compose_project,
        socket_mode=int(args.socket_mode, 8),
    )
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
