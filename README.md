# Stellars JupyterHub for Data Science Platform
![Docker Pulls](https://img.shields.io/docker/pulls/stellars/stellars-jupyterhub-ds?style=flat-square)
![Docker Image](https://img.shields.io/docker/image-size/stellars/stellars-jupyterhub-ds/latest?style=flat-square)

Multi-user JupyterHub 4 deployment platform with data science stack, GPU support, and NativeAuthenticator. The platform spawns isolated JupyterLab environments per user using DockerSpawner, backed by the [stellars/stellars-jupyterlab-ds](https://hub.docker.com/r/stellars/stellars-jupyterlab-ds) image (from [stellars-jupyterlab-ds](https://github.com/stellarshenson/stellars-jupyterlab-ds) project).

## Features

- **GPU Auto-Detection**: Automatic NVIDIA CUDA GPU detection and configuration for spawned user containers
- **Notification Broadcast**: Admin broadcast to all active servers via `/hub/notifications`. Supports six notification types, 140-character limit. Requires [jupyterlab_notifications_extension](https://github.com/stellarshenson/jupyterlab_notifications_extension)
- **User Self-Service**: Users can restart their JupyterLab containers and selectively reset persistent volumes (home/workspace/cache) without admin intervention
- **Privileged Access Control**: Group-based docker.sock access for trusted users enabling container orchestration from within JupyterLab
- **Isolated Environments**: Each user gets dedicated JupyterLab container with persistent volumes via DockerSpawner
- **Native Authentication**: Built-in user management with NativeAuthenticator supporting self-registration and admin approval
- **Shared Storage**: Optional CIFS/NAS mount support for shared datasets across all users
- **Production Ready**: Traefik reverse proxy with TLS termination, automatic container updates via Watchtower

## User Interface

**User Control Panel**

User control panel with server restart and volume management options.

![User Control Panel](.resources/screenshot-home.png)

**Volume Management**

Access volume management when server is stopped.

![Manage Volumes](.resources/screenshot-volumes.png)

**Volume Selection**

Select individual volumes to reset - home directory, workspace files, or cache data.

![Volume Selection](.resources/screenshot-volumes-modal.png)

**Admin Notification Broadcast**

Admin panel for broadcasting notifications to all active JupyterLab servers.

![Admin Notification Broadcast](.resources/screenshot-send-notification.png)

## Architecture

```mermaid
graph TB
    User[User Browser] -->|HTTPS| Traefik[Traefik Proxy<br/>TLS Termination]
    Traefik --> Hub[JupyterHub<br/>Port 8000]

    Hub -->|Authenticates| Auth[NativeAuthenticator]
    Hub -->|Spawns via| Spawner[DockerSpawner]

    Spawner -->|Creates| Lab1[JupyterLab<br/>alice]
    Spawner -->|Creates| Lab2[JupyterLab<br/>bob]
    Spawner -->|Creates| Lab3[JupyterLab<br/>charlie]

    Lab1 --> Vol1[Volumes<br/>home/workspace/cache]
    Lab2 --> Vol2[Volumes<br/>home/workspace/cache]
    Lab3 --> Vol3[Volumes<br/>home/workspace/cache]

    Lab1 --> Shared[Shared Storage<br/>CIFS/NAS]
    Lab2 --> Shared
    Lab3 --> Shared

    style Hub stroke:#f59e0b,stroke-width:3px
    style Traefik stroke:#0284c7,stroke-width:3px
    style Auth stroke:#10b981,stroke-width:3px
    style Spawner stroke:#a855f7,stroke-width:3px
    style Lab1 stroke:#3b82f6,stroke-width:2px
    style Lab2 stroke:#3b82f6,stroke-width:2px
    style Lab3 stroke:#3b82f6,stroke-width:2px
    style Shared stroke:#ef4444,stroke-width:2px
```

Users access JupyterHub through Traefik reverse proxy with TLS termination. After authentication via NativeAuthenticator, JupyterHub spawns isolated JupyterLab containers per user using DockerSpawner. Each user gets dedicated persistent volumes for home directory, workspace files, and cache data, with optional shared storage for collaborative datasets.

## References

This project spawns user environments using docker image: [stellars/stellars-jupyterlab-ds](https://hub.docker.com/r/stellars/stellars-jupyterlab-ds)

Visit the project page for stellars-jupyterlab-ds: https://github.com/stellarshenson/stellars-jupyterlab-ds

## Requirements

**Docker Socket Access Required**: This JupyterHub implementation requires read-write access to the Docker socket (`/var/run/docker.sock`) mounted into the JupyterHub container. This is essential for:

- **DockerSpawner**: Spawning and managing isolated JupyterLab containers for each user
- **Volume Management**: Allowing users to reset their persistent volumes (home/workspace/cache)
- **Container Control**: Enabling server restart functionality from the user control panel
- **Privileged Access**: Supporting optional docker.sock access for trusted users within their JupyterLab environments

The `compose.yml` file includes this mount by default:
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:rw
```

<div class="alert alert-block alert-warning">
<b>Security Note:</b> The JupyterHub container has full access to the Docker daemon. Only trusted administrators should have access to JupyterHub configuration.
</div>

## Quickstart

### Docker Compose
1. Download `compose.yml` and `config/jupyterhub_config.py` config file
2. Run: `docker compose up --no-build`
3. Open https://localhost/jupyterhub in your browser 
4. Add `admin` user through self-sign-in (user will be authorised automatically)
5. Log in as `admin`

### Start Scripts
- `start.sh` or `start.bat` – standard startup for the environment
- `scripts/build.sh` alternatively `make build` – builds required Docker containers

### Authentication
This stack uses [NativeAuthenticator](https://github.com/jupyterhub/nativeauthenticator) for user management. Admins can whitelist users or allow self-registration. Passwords are stored securely.


## Deployment Notes

- Ensure `config/jupyterhub_config.py` is correctly set for your environment (e.g., TLS, admin list).
- Optional volume mounts and configuration can be modified in `jupyterhub_config.py` for shared storage.

## Customisation

You should customise the deployment by creating a `compose_override.yml` file.  

#### Custom configuration file
Example below introduces custom config file `jupyterhub_config_override.py` to use for your deployment:

```yaml
services:
  jupyterhub:
    volumes:
      - ./config/jupyterhub_config_override.py:/srv/jupyterhub/jupyterhub_config.py:ro # config file (read only)
```

#### Enable GPU

No changes required in the configuration if you allow NVidia autodetection to be performed.
Otherwise change the `ENABLE_GPU_SUPPORT = 1`

Changes in your `compose_override.yml`:
```yaml
services:
  jupyterhub:
    environment:
      - ENABLE_GPU_SUPPORT=1 # enable NVIDIA GPU, values: 0 - disabled, 1 - enabled, 2 - auto-detect
```

#### Enable shared CIFS mount

Changes in your `compose_override.yml`:
```yaml
  jupyterhub:
    volumes:
      - ./config/jupyterhub_config_override.py:/srv/jupyterhub/jupyterhub_config.py:ro # config file (read only)
      - jupyterhub_shared_nas:/mnt/shared # cifs share
    
volumes:
  # remote drive for large datasets
  jupyterhub_shared_nas:
    driver: local
    name: jupyterhub_shared_nas
    driver_opts:
      type: cifs
      device: //nas_ip_or_dns_name/data
      o: username=xxxx,password=yyyy,uid=1000,gid=1000
```

in the config file you will refer to this volume by its name `jupyterhub_shared_nas`:

```python
# User mounts in the spawned container
c.DockerSpawner.volumes = {
    "jupyterlab-{username}_home": "/home",
    "jupyterlab-{username}_workspace": DOCKER_NOTEBOOK_DIR,
    "jupyterlab-{username}_cache": "/home/lab/.cache",
    "jupyterhub_shared_nas": "/mnt/shared"
}
```

#### Grant Docker Socket Access to Privileged Users

<div class="alert alert-block alert-warning">
<b>Security Warning:</b> Docker socket access grants effective root-level control over the Docker host. Only grant this permission to trusted users.
</div>

The platform supports granting specific users read-write access to `/var/run/docker.sock` within their JupyterLab containers via the `docker-privileged` group. This enables container orchestration, Docker builds, and Docker Compose operations from within user environments.

**How to Grant Access**:

1. Log in as admin and navigate to Admin Panel (`https://localhost/jupyterhub/hub/admin`)
2. Click "Groups" in the navigation
3. Click on the `docker-privileged` group (automatically created at startup)
4. Add users who need docker.sock access to this group
5. Users must restart their server (Stop My Server -> Start My Server) for changes to take effect

**Technical Details**:

The `docker-privileged` group is a built-in protected group that cannot be permanently deleted. It is automatically created at JupyterHub startup and recreated before every container spawn if missing. A pre-spawn hook (`config/jupyterhub_config.py::pre_spawn_hook`) checks user group membership before spawning containers. Users in the `docker-privileged` group will have `/var/run/docker.sock` mounted with read-write permissions in their JupyterLab environment.

**Use Cases**:
- Building custom Docker images from within JupyterLab
- Running Docker Compose stacks for local development
- Container orchestration and management tasks
- Advanced DevOps workflows requiring Docker API access

<!-- EOF -->
