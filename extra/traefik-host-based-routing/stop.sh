#!/bin/bash
# Stop services

set -e

echo "Stopping services..."
docker compose -f stellars-jupyterhub-ds/compose.yml -f compose_override.yml down

echo "Done."
