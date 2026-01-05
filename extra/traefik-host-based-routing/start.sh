#!/bin/bash
# Clone/pull latest and start services

set -e

REPO_URL="https://github.com/stellarshenson/stellars-jupyterhub-ds.git"
REPO_DIR="stellars-jupyterhub-ds"

if [ -d "$REPO_DIR" ]; then
    echo "Pulling latest $REPO_DIR..."
    git -C "$REPO_DIR" pull origin main
else
    echo "Cloning $REPO_DIR..."
    git clone "$REPO_URL"
fi

echo "Starting services..."
docker compose -f stellars-jupyterhub-ds/compose.yml -f compose_override.yml up -d

echo "Done. View logs with: make logs"
