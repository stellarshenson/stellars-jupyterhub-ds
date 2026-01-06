#!/bin/bash
# Rename Docker volumes from one user pattern to another
# Handles Docker's dot-to-hex encoding (. becomes -2e)

set -e

show_help() {
    cat << EOF
Usage: $0 [--dry-run] [--keep-orig] <source-pattern> <target-username>

Rename Docker volumes from one user to another (. encoded as -2e).

  --dry-run     Show mappings without changes
  --keep-orig   Keep original volumes

Example: $0 --dry-run oldnick first.last
         jupyterlab-oldnick_home -> jupyterlab-first-2elast_home
EOF
    exit 0
}

# Parse arguments
DRY_RUN=false
KEEP_ORIG=false
POSITIONAL=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --keep-orig)
            KEEP_ORIG=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Use --help for usage"
            exit 1
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done

# Check required arguments
if [ ${#POSITIONAL[@]} -lt 2 ]; then
    show_help
fi

SOURCE_PATTERN="${POSITIONAL[0]}"
TARGET_USER="${POSITIONAL[1]}"

# Encode dots as -2e for Docker volume names
TARGET_ENCODED=$(echo "$TARGET_USER" | sed 's/\./-2e/g')

# Find matching volumes
VOLUMES=$(docker volume ls --format '{{.Name}}' | grep -E "jupyterlab-${SOURCE_PATTERN}[_-]" || true)

if [ -z "$VOLUMES" ]; then
    echo "No volumes found matching pattern: jupyterlab-${SOURCE_PATTERN}[_-]*"
    exit 0
fi

echo "Volume rename mappings:"
echo ""

# Build mapping list
declare -a SOURCES
declare -a TARGETS

while IFS= read -r VOL; do
    # Replace source pattern with encoded target
    NEW_VOL=$(echo "$VOL" | sed "s/jupyterlab-${SOURCE_PATTERN}/jupyterlab-${TARGET_ENCODED}/")
    SOURCES+=("$VOL")
    TARGETS+=("$NEW_VOL")
    echo "  $VOL"
    echo "    -> $NEW_VOL"
    echo ""
done <<< "$VOLUMES"

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] No changes made"
    exit 0
fi

echo "---"
if [ "$KEEP_ORIG" = true ]; then
    echo "Mode: copy (original volumes will be kept)"
else
    echo "Mode: move (original volumes will be deleted)"
fi
echo ""

read -p "Proceed with rename? [y/N] " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Aborted"
    exit 0
fi

echo ""

# Perform renames
for i in "${!SOURCES[@]}"; do
    SOURCE="${SOURCES[$i]}"
    TARGET="${TARGETS[$i]}"

    echo "Renaming: $SOURCE -> $TARGET"

    # Check target doesn't exist
    if docker volume inspect "$TARGET" >/dev/null 2>&1; then
        echo "  ERROR: Target volume already exists, skipping"
        continue
    fi

    # Create target volume
    docker volume create "$TARGET" >/dev/null

    # Copy data
    CONTAINER_NAME="vol_copy_$(date +%s)_$$_$i"
    if docker run --rm \
        --name "$CONTAINER_NAME" \
        -v "$SOURCE":/source:ro \
        -v "$TARGET":/target \
        alpine \
        sh -c "cp -a /source/. /target/" 2>/dev/null; then

        echo "  Copied successfully"

        # Remove original if not keeping
        if [ "$KEEP_ORIG" = false ]; then
            docker volume rm "$SOURCE" >/dev/null
            echo "  Original removed"
        fi
    else
        echo "  ERROR: Copy failed"
        docker volume rm "$TARGET" 2>/dev/null || true
    fi
done

echo ""
echo "Done"
