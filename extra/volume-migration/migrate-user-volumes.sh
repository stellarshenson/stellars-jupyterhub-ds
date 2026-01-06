#!/bin/bash
# Migrate all JupyterHub user volumes from one username to another
# Handles: home, workspace, cache volumes

set -e

SCRIPT_DIR="$(dirname "$0")"

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <old-username> <new-username> [--delete-source]"
    echo ""
    echo "Migrates JupyterHub user volumes:"
    echo "  - jupyterlab-{username}_home"
    echo "  - jupyterlab-{username}_workspace"
    echo "  - jupyterlab-{username}_cache"
    echo ""
    echo "Options:"
    echo "  --delete-source   Delete source volumes after successful copy"
    echo ""
    echo "Example:"
    echo "  $0 john john.doe"
    echo "  $0 john john.doe --delete-source"
    exit 1
fi

OLD_USER="$1"
NEW_USER="$2"
DELETE_FLAG=""

if [ "$3" = "--delete-source" ]; then
    DELETE_FLAG="--delete-source"
fi

VOLUME_SUFFIXES="home workspace cache"

echo "Migrating volumes for user: $OLD_USER -> $NEW_USER"
echo ""

# Check which volumes exist
VOLUMES_TO_MIGRATE=""
for SUFFIX in $VOLUME_SUFFIXES; do
    SOURCE="jupyterlab-${OLD_USER}_${SUFFIX}"
    if docker volume inspect "$SOURCE" >/dev/null 2>&1; then
        VOLUMES_TO_MIGRATE="$VOLUMES_TO_MIGRATE $SUFFIX"
        echo "  Found: $SOURCE"
    else
        echo "  Skip:  $SOURCE (not found)"
    fi
done

if [ -z "$VOLUMES_TO_MIGRATE" ]; then
    echo ""
    echo "No volumes found for user: $OLD_USER"
    exit 0
fi

echo ""
read -p "Proceed with migration? [y/N] " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Aborted"
    exit 0
fi

echo ""

# Migrate each volume
for SUFFIX in $VOLUMES_TO_MIGRATE; do
    SOURCE="jupyterlab-${OLD_USER}_${SUFFIX}"
    TARGET="jupyterlab-${NEW_USER}_${SUFFIX}"

    echo "--- Migrating $SUFFIX volume ---"
    "$SCRIPT_DIR/rename-volume.sh" "$SOURCE" "$TARGET" $DELETE_FLAG
    echo ""
done

echo "User volume migration complete: $OLD_USER -> $NEW_USER"
