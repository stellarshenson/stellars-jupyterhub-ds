#!/bin/bash
# List all JupyterHub user volumes

echo "JupyterHub user volumes:"
echo ""

docker volume ls --format '{{.Name}}' | grep -E '^jupyterlab-' | sort | while read -r VOL; do
    SIZE=$(docker run --rm -v "$VOL":/data alpine sh -c "du -sh /data 2>/dev/null | cut -f1" 2>/dev/null || echo "?")
    printf "  %-50s %s\n" "$VOL" "$SIZE"
done

echo ""
