#!/bin/bash
# Stop services

set -e

cd "$(dirname "$0")"

# Load defaults, then local overrides
source .env.default
if [[ -f .env ]]; then
    source .env
fi

# Build compose command with optional CIFS mount
COMPOSE_FILES="--env-file .env.default"
if [[ -f .env ]]; then
    COMPOSE_FILES="${COMPOSE_FILES} --env-file .env"
fi
COMPOSE_FILES="${COMPOSE_FILES} -f stellars-jupyterhub-ds/compose.yml -f compose_override.yml"
if [[ "${ENABLE_CIFS}" == "1" ]]; then
    COMPOSE_FILES="${COMPOSE_FILES} -f compose_cifs.yml"
fi

echo "Stopping services..."
docker compose ${COMPOSE_FILES} down

echo "Done."
