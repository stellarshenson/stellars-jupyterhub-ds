# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-user JupyterHub 4 deployment platform with data science stack, GPU support (auto-detection), and NativeAuthenticator. The platform spawns isolated JupyterLab environments per user using DockerSpawner, backed by the `stellars/stellars-jupyterlab-ds` image.

**Architecture**: Docker Compose orchestrates three main services:
- **Traefik**: Reverse proxy handling TLS termination and routing (ports 80, 443, 8080)
- **JupyterHub**: Central hub managing user authentication and spawning user containers
- **Watchtower**: Automatic image updates (daily at midnight)

User containers are dynamically spawned into the `jupyterhub_network` with per-user persistent volumes for home, workspace, and cache directories.

## Common Development Commands

### Building and Deployment

```bash
# Build the JupyterHub container
make build

# Build with verbose output
make build_verbose

# Build using script directly
./scripts/build.sh

# Pull latest image from DockerHub
make pull

# Push image to DockerHub
make push
```

### Starting and Stopping

```bash
# Start platform (detached mode, respects compose_override.yml if present)
./start.sh

# Start with docker compose directly
docker compose --env-file .env -f compose.yml up --no-recreate --no-build -d

# Start with override file
docker compose --env-file .env -f compose.yml -f compose_override.yml up --no-recreate --no-build -d

# Stop and clean up
make clean
```

### Accessing Services

- JupyterHub: `https://localhost/jupyterhub`
- Traefik Dashboard: `http://localhost:8080/dashboard`
- First-time setup: Self-register as `admin` user (auto-authorized)

## Configuration Architecture

### Primary Configuration: `config/jupyterhub_config.py`

This Python configuration file controls all JupyterHub behavior:

**Environment Variables** (set in compose.yml or compose_override.yml):
- `JUPYTERHUB_ADMIN`: Admin username (default: `admin`)
- `DOCKER_NOTEBOOK_IMAGE`: JupyterLab image to spawn (default: `stellars/stellars-jupyterlab-ds:latest`)
- `DOCKER_NETWORK_NAME`: Network for spawned containers (default: `jupyterhub_network`)
- `JUPYTERHUB_BASE_URL`: URL prefix (default: `/jupyterhub`)
- `ENABLE_GPU_SUPPORT`: GPU mode - `0` (disabled), `1` (enabled), `2` (auto-detect)
- `ENABLE_JUPYTERHUB_SSL`: Direct SSL config - `0` (disabled), `1` (enabled)
- `ENABLE_SERVICE_MLFLOW`: Enable MLflow tracking (`0`/`1`)
- `ENABLE_SERVICE_GLANCES`: Enable resource monitor (`0`/`1`)
- `ENABLE_SERVICE_TENSORBOARD`: Enable TensorBoard (`0`/`1`)
- `NVIDIA_AUTODETECT_IMAGE`: Image for GPU detection (default: `nvidia/cuda:12.9.1-base-ubuntu24.04`)

**GPU Auto-Detection**: When `ENABLE_GPU_SUPPORT=2`, the platform attempts to run `nvidia-smi` in a CUDA container. If successful, GPU support is enabled for all spawned user containers via `device_requests`.

**User Container Configuration**:
- Spawned containers use `DockerSpawner` with per-user volumes
- Default working directory: `/home/lab/workspace`
- Container name pattern: `jupyterlab-{username}`
- Persistent volumes:
  - `jupyterlab-{username}_home`: `/home`
  - `jupyterlab-{username}_workspace`: `/home/lab/workspace`
  - `jupyterlab-{username}_cache`: `/home/lab/.cache`
  - `jupyterhub_shared`: `/mnt/shared` (shared across all users)

### Override Pattern: `compose_override.yml`

Create this file to customize deployment without modifying tracked files:

```yaml
services:
  jupyterhub:
    volumes:
      - ./config/jupyterhub_config_override.py:/srv/jupyterhub/jupyterhub_config.py:ro
    environment:
      - ENABLE_GPU_SUPPORT=1
```

**IMPORTANT**: `compose_override.yml` contains deployment-specific credentials (CIFS passwords, etc.) and should never be committed.

### TLS Certificates

Certificates are auto-generated at startup by `/mkcert.sh` script and stored in `jupyterhub_certs` volume. Traefik reads certificates from `/mnt/certs/certs.yml` configuration file.

## Docker Image Build Process

**Dockerfile**: `services/jupyterhub/Dockerfile.jupyterhub`

Build stages:
1. Base image: `jupyterhub/jupyterhub:latest`
2. Install system packages from `conf/apt-packages.yml` using `yq` parser
3. Copy startup scripts from `conf/bin/` (executable permissions set to 755)
4. Install Python packages: `docker`, `dockerspawner`, `jupyterhub-nativeauthenticator`
5. Copy certificate templates from `templates/certs/`
6. Entrypoint: `/start-platform.sh`

**Platform Initialization**: `/start-platform.sh` executes scripts in `/start-platform.d/` directory sequentially before launching JupyterHub.

## Authentication

**NativeAuthenticator** configuration in `jupyterhub_config.py`:
- Self-registration enabled (`c.NativeAuthenticator.enable_signup = True`)
- Open signup disabled (`c.NativeAuthenticator.open_signup = False`)
- All registered users allowed to login (`c.Authenticator.allow_all = True`)
- Admin users defined by `JUPYTERHUB_ADMIN` environment variable
- Admin panel access: `https://localhost/jupyterhub/hub/home`

## Networking and Volumes

**Networks**:
- `jupyterhub_network`: Bridge network connecting hub, Traefik, and spawned user containers

**Volumes**:
- `jupyterhub_data`: Persistent database (`jupyterhub.sqlite`) and cookie secrets
- `jupyterhub_certs`: TLS certificates shared with Traefik
- `jupyterhub_shared`: Shared storage across all user environments (can be mounted as CIFS)
- Per-user volumes: Created dynamically on first spawn

## CIFS/NAS Integration

To mount network storage in user containers, override the `jupyterhub_shared` volume in `compose_override.yml`:

```yaml
volumes:
  jupyterhub_shared:
    driver: local
    name: jupyterhub_shared
    driver_opts:
      type: cifs
      device: //nas_ip/share_name
      o: username=xxx,password=yyy,uid=1000,gid=1000
```

User containers will access this at `/mnt/shared`.

## Troubleshooting

**GPU not detected**:
- Verify NVIDIA Docker runtime: `docker run --rm --gpus all nvidia/cuda:12.9.1-base-ubuntu24.04 nvidia-smi`
- Check `NVIDIA_AUTODETECT_IMAGE` matches your CUDA version
- Manually enable with `ENABLE_GPU_SUPPORT=1`

**Container spawn failures**:
- Check Docker socket permissions: `/var/run/docker.sock` must be accessible
- Verify network exists: `docker network inspect jupyterhub_network`
- Review logs: `docker logs <container-name>`

**Authentication issues**:
- Admin user must match `JUPYTERHUB_ADMIN` environment variable
- Database persisted in `jupyterhub_data` volume - may need reset if corrupted
- Cookie secret persisted in `/data/jupyterhub_cookie_secret`

## Related Projects

User environments spawned from: https://github.com/stellarshenson/stellars-jupyterlab-ds
