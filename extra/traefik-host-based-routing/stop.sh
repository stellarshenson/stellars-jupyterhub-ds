#!/bin/bash
# Stop services

set -e

cd "$(dirname "$0")"

# Default configuration (override via .env)
ENABLE_CIFS="${ENABLE_CIFS:-0}"

# Load environment variables if .env exists
if [[ -f .env ]]; then
    source .env
fi

# Build compose command with optional CIFS mount
COMPOSE_FILES="--env-file .env -f stellars-jupyterhub-ds/compose.yml -f compose_override.yml"
if [[ "${ENABLE_CIFS}" == "1" ]]; then
    COMPOSE_FILES="${COMPOSE_FILES} -f compose_cifs.yml"
fi

echo "Stopping services..."
docker compose ${COMPOSE_FILES} down

echo "Done."
