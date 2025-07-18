#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <volume-name-regex> [backup-directory]"
    exit 1
fi

REGEX="$1"
BACKUP_DIR="${2:-./volumes}"
DATE_SUFFIX=$(date +"%Y-%m-%d")

mkdir -p "$BACKUP_DIR"

VOLUMES=$(docker volume ls --format '{{.Name}}' | grep -E "$REGEX")

if [ -z "$VOLUMES" ]; then
    echo "No volumes matched regex: $REGEX"
    exit 0
fi

echo "The following volumes will be backed up:"
echo "$VOLUMES"
echo

echo "$VOLUMES" | while read -r VOLUME; do
    echo "Backing up volume: $VOLUME"

    EXPORT_PATH="${BACKUP_DIR}/${VOLUME}_${DATE_SUFFIX}.tar.gz"
    ABS_BACKUP_DIR=$(realpath "$BACKUP_DIR")

    docker run --rm \
        -u "$(id -u):$(id -g)" \
        -v "$VOLUME":/data:ro \
        -v "$ABS_BACKUP_DIR":/backup \
        alpine \
        sh -c "tar czf /backup/$(basename "$EXPORT_PATH") -C /data ."

    echo "Backup complete: $EXPORT_PATH"
done

echo
echo "All matching volumes have been backed up to $BACKUP_DIR"

