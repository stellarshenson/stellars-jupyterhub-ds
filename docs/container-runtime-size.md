# Container Runtime Size Monitoring

Container runtime size is the writable layer - data written inside a container beyond its base image. This includes installed packages, downloaded files, temp files, and logs written to the container filesystem (not to volumes). Unchecked growth here is the primary cause of Docker disk exhaustion.

## Checking Runtime Size

### Single container

```bash
docker ps -s --format "table {{.Names}}\t{{.Size}}"
```

The `Size` column shows two values: `X (virtual Y)` where X is the writable layer and Y includes the base image.

### All containers via Docker API

The `-s` flag can be slow or fail on deeply nested filesystems. Use the Docker API directly for reliable results:

```bash
curl -s --unix-socket /var/run/docker.sock \
  "http://localhost/containers/json?all=true&size=true" \
  | jq -r '.[] | "\(.SizeRw // 0)\t\(.Names[0])"' \
  | sort -rn \
  | awk -F'\t' '{
    size=$1; name=$2;
    if (size >= 1073741824) printf "%7.1f GB\t%s\n", size/1073741824, name;
    else if (size >= 1048576) printf "%7.1f MB\t%s\n", size/1048576, name;
    else printf "%7.1f KB\t%s\n", size/1024, name;
  }'
```

### Specific container deep inspection

Find what's consuming space inside a running container:

```bash
# Top-level breakdown (excludes mount points)
docker exec <container> du -xsh /* 2>/dev/null | sort -rh | head -10

# Block I/O stats (shows cumulative writes)
docker stats --no-stream --format "table {{.Name}}\t{{.BlockIO}}"
```

### Docker system overview

```bash
docker system df           # Summary
docker system df -v        # Detailed per-image and per-container
```

## Key Fields

- **SizeRw** - bytes written to the container's writable layer (the runtime size)
- **SizeRootFs** - total size including all read-only image layers
- **Block I/O** - cumulative read/write since container creation (from `docker stats`)

## Planned: Quota Enforcement

Future implementation in JupyterHub activity monitoring:

- Periodically query `/containers/json?size=true` for spawned JupyterLab containers
- Compare `SizeRw` against configurable threshold (e.g., `JUPYTERHUB_CONTAINER_SIZE_QUOTA=10GB`)
- Warn user via JupyterHub notification when approaching limit
- Auto-shutdown container when quota exceeded
- Report runtime sizes in the admin activity page

## Common Causes of Runaway Growth

- **Recursive exports** - tools like ClamAV exporting `/tmp` which includes the export itself, creating exponential nesting
- **Conda/pip installs inside container** - packages installed at runtime go to writable layer instead of cached volume
- **Model downloads** - ML models downloaded to container filesystem instead of mounted volume
- **Unrotated logs** - application logs written inside the container without size limits
