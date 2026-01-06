#!/bin/bash
# Rename a Docker volume by copying data to a new volume

set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <source-volume> <target-volume> [--delete-source]"
    echo ""
    echo "Options:"
    echo "  --delete-source   Delete source volume after successful copy"
    echo ""
    echo "Example:"
    echo "  $0 jupyterlab-olduser_home jupyterlab-newuser_home"
    echo "  $0 jupyterlab-olduser_home jupyterlab-newuser_home --delete-source"
    exit 1
fi

SOURCE="$1"
TARGET="$2"
DELETE_SOURCE=false

if [ "$3" = "--delete-source" ]; then
    DELETE_SOURCE=true
fi

# Check source volume exists
if ! docker volume inspect "$SOURCE" >/dev/null 2>&1; then
    echo "ERROR: Source volume '$SOURCE' does not exist"
    exit 1
fi

# Check target volume doesn't exist
if docker volume inspect "$TARGET" >/dev/null 2>&1; then
    echo "ERROR: Target volume '$TARGET' already exists"
    echo "Delete it first or choose a different name"
    exit 1
fi

echo "Renaming volume:"
echo "  Source: $SOURCE"
echo "  Target: $TARGET"
echo ""

# Create target volume
echo "Creating target volume..."
docker volume create "$TARGET"

# Copy data using alpine container
echo "Copying data..."
CONTAINER_NAME="volume_copy_$(date +%s)_$$"

if docker run --rm \
    --name "$CONTAINER_NAME" \
    -v "$SOURCE":/source:ro \
    -v "$TARGET":/target \
    alpine \
    sh -c "cp -a /source/. /target/"; then

    echo "Data copied successfully"
else
    echo "ERROR: Copy failed"
    docker volume rm "$TARGET" 2>/dev/null || true
    exit 1
fi

# Delete source if requested
if [ "$DELETE_SOURCE" = true ]; then
    echo "Deleting source volume..."
    docker volume rm "$SOURCE"
    echo "Source volume deleted"
fi

echo ""
echo "Volume rename complete: $SOURCE -> $TARGET"
