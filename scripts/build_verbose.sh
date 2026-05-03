#!/bin/sh
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export COMPOSE_BAKE=false

# Compose VERSION from pyproject.toml (PEP-621 + [tool.stellars])
# Requires python3 >=3.11 for stdlib tomllib.
VERSION=$(python3 -c 'import tomllib;d=tomllib.load(open("../pyproject.toml","rb"));print(d["project"]["version"]+"_cuda-"+d["tool"]["stellars"]["cuda"]+"_jh-"+d["tool"]["stellars"]["jupyterhub"])')
[ -n "$VERSION" ] || { echo "ERROR: failed to read VERSION from ../pyproject.toml" >&2; exit 1; }
export VERSION

docker compose -f ../compose.yml build --progress=plain "$@"
