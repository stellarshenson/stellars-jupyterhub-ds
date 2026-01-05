#!/bin/bash
# Start JupyterHub platform with latest upstream

set -e

cd "$(dirname "$0")"

REPO_URL="https://github.com/stellarshenson/stellars-jupyterhub-ds.git"
REPO_DIR="stellars-jupyterhub-ds"

if [ -d "$REPO_DIR" ]; then
    echo "Pulling latest $REPO_DIR..."
    git -C "$REPO_DIR" fetch origin main
    git -C "$REPO_DIR" checkout -B main origin/main
else
    echo "Cloning $REPO_DIR..."
    git clone "$REPO_URL"
fi

echo "Starting JupyterHub platform..."
docker compose -f stellars-jupyterhub-ds/compose.yml -f compose_override.yml pull
docker compose -f stellars-jupyterhub-ds/compose.yml -f compose_override.yml up -d --no-build

echo "Done. Access: https://jupyterhub.YOURDOMAIN/"
