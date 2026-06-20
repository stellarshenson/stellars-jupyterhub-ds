"""Test env for the standalone docker-proxy suite.

config.py reads OWNER key+value RAW from JUPYTERHUB_LABEL_DOCKER_PROXY_* with NO hardcoded
fallback. In production the hub's Dockerfile ENV supplies them and the hub config validator
enforces presence before any proxy code runs (proxy runs in-process in the hub). Standalone
pytest has neither, so set them here - single source for the test process, mirroring Dockerfile
ENV for prod. Must run before any package import (config reads env at module load), so this sits
at conftest module top; pytest imports conftest before the test modules that import config.
"""
import os

os.environ.setdefault("JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_KEY", "hub.docker.proxy.owner")
os.environ.setdefault("JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_VALUE", "{username}")
