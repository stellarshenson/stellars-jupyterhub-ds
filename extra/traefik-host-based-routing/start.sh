#!/bin/bash
# Start JupyterHub platform
# Usage: ./start.sh [--refresh]

set -e

cd "$(dirname "$0")"

REPO_URL="https://github.com/stellarshenson/stellars-jupyterhub-ds.git"
REPO_DIR="stellars-jupyterhub-ds"
REFRESH=false

# Default configuration (override via .env)
ENABLE_CIFS="${ENABLE_CIFS:-0}"

# Load environment variables if .env exists
if [[ -f .env ]]; then
    source .env
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --refresh)
            REFRESH=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--refresh]"
            exit 1
            ;;
    esac
done

if [ -d "$REPO_DIR" ]; then
    if [ "$REFRESH" = true ]; then
        echo "Refreshing $REPO_DIR..."
        git -C "$REPO_DIR" fetch origin main
        git -C "$REPO_DIR" checkout -B main origin/main
    else
        echo "Using existing $REPO_DIR (use --refresh to update)"
    fi
else
    echo "Cloning $REPO_DIR..."
    git clone "$REPO_URL"
fi

# Build compose command with optional CIFS mount
COMPOSE_FILES="-f stellars-jupyterhub-ds/compose.yml -f compose_override.yml"
if [[ "${ENABLE_CIFS}" == "1" ]]; then
    echo "CIFS mount enabled"
    COMPOSE_FILES="${COMPOSE_FILES} -f compose_cifs.yml"
fi

echo "Starting JupyterHub platform..."
docker compose ${COMPOSE_FILES} pull
docker pull stellars/stellars-jupyterlab-ds:latest
docker compose ${COMPOSE_FILES} up -d --no-build

echo "Done. Access: https://jupyterhub.${HOSTNAME:-localhost}/"
