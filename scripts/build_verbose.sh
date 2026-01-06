#!/bin/sh
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export COMPOSE_BAKE=false

# Source project.env to get VERSION
set -a
. ../project.env
set +a

# Export VERSION for docker compose build
export VERSION

docker compose -f ../compose.yml build --progress=plain
