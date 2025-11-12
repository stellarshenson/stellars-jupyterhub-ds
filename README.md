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

## Configuration Flow

```mermaid
graph TB
    subgraph ENV["Environment Variables (compose.yml)"]
        ADMIN[JUPYTERHUB_ADMIN<br/>Admin username]
        BASEURL[JUPYTERHUB_BASE_URL<br/>URL prefix]
        IMG[DOCKER_NOTEBOOK_IMAGE<br/>User container image]
        NET[DOCKER_NETWORK_NAME<br/>Container network]
        SSL[ENABLE_JUPYTERHUB_SSL<br/>0=off, 1=on]
        GPU[ENABLE_GPU_SUPPORT<br/>0=off, 1=on, 2=auto]
        TFLOG[TF_CPP_MIN_LOG_LEVEL<br/>TensorFlow verbosity]
        NVIMG[NVIDIA_AUTODETECT_IMAGE<br/>CUDA test image]

        subgraph SVCEN["ENABLE_SERVICE_*<br/>Passed to Lab as env"]
            direction LR
            MLF[ENABLE_SERVICE_MLFLOW]
            GLN[ENABLE_SERVICE_GLANCES]
            TNS[ENABLE_SERVICE_TENSORBOARD]
            SVC_MORE[...]
        end
    end

    subgraph CONFIG["jupyterhub_config.py"]
        AUTH[NativeAuthenticator<br/>open_signup=False, enable_signup=True]
        SPAWN[DockerSpawner<br/>spawner_class, remove=True]
        NBDIR[DOCKER_NOTEBOOK_DIR<br/>/home/lab/workspace]
        VOLS[DOCKER_SPAWNER_VOLUMES<br/>home/workspace/cache/shared]
        VOLDESC[VOLUME_DESCRIPTIONS<br/>Optional UI labels]
        GROUPS[BUILTIN_GROUPS<br/>docker-privileged]
        HOOK[pre_spawn_hook<br/>Group check + docker.sock]
        HANDLERS[extra_handlers<br/>ManageVolumes, RestartServer, Notifications]
        TEMPLATES[template_paths<br/>Custom + Native + Default]
    end

    subgraph RUNTIME["Spawned User Container"]
        LAB[JupyterLab Server<br/>Port 8888]
        SERVICES[Services: MLflow, Glances, TensorBoard<br/>Controlled by ENABLE_SERVICE_* env]
        GPUACCESS[GPU Access<br/>device_requests if enabled]
    end

    ADMIN --> AUTH
    BASEURL --> CONFIG
    IMG --> SPAWN
    NET --> SPAWN
    SSL --> CONFIG
    TFLOG --> |Passed as env| LAB
    NVIMG --> |Used for auto-detect| CONFIG

    GPU --> |Auto-detect via nvidia-smi| SPAWN
    GPU --> |Passed as env| LAB
    GPU --> |device_requests| GPUACCESS

    SVCEN --> |Passed as env| LAB
    SVCEN --> |Controls startup| SERVICES

    AUTH --> |Validates| SPAWN
    SPAWN --> |Creates| LAB
    NBDIR --> SPAWN
    VOLS --> |Mounts| LAB
    VOLDESC --> HANDLERS
    GROUPS --> HOOK
    HOOK --> |Conditionally mounts<br/>docker.sock| LAB
    HANDLERS --> |API endpoints| LAB
    TEMPLATES --> |Custom UI| LAB

    style ENV stroke:#f59e0b,stroke-width:3px
    style SVCEN stroke:#a855f7,stroke-width:2px
    style CONFIG stroke:#10b981,stroke-width:3px
    style RUNTIME stroke:#3b82f6,stroke-width:3px
    style HOOK stroke:#ef4444,stroke-width:2px
    style HANDLERS stroke:#ef4444,stroke-width:2px
```

Environment variables defined in `compose.yml` are consumed by `config/jupyterhub_config.py` to configure authentication, spawner behavior, and GPU detection. The configuration defines `DOCKER_SPAWNER_VOLUMES` for persistent storage, `VOLUME_DESCRIPTIONS` for optional UI labels, and `BUILTIN_GROUPS` for protected group management. When spawning user containers, these settings control which services are enabled (MLflow, Glances, TensorBoard), whether GPU access is granted via `device_requests`, and what volumes are mounted. The pre-spawn hook checks user group membership against `BUILTIN_GROUPS` to conditionally mount docker.sock for privileged users.

## GPU Auto-Detection

```mermaid
graph LR
    START[ENABLE_GPU_SUPPORT=2] --> CHECK{Check value}
    CHECK -->|0| DISABLED[GPU Disabled]
    CHECK -->|1| ENABLED[GPU Enabled]
    CHECK -->|2| DETECT[Auto-detect]

    DETECT --> SPAWN[Spawn test container<br/>nvidia/cuda:12.9.1-base]
    SPAWN --> RUN[Execute nvidia-smi<br/>with runtime=nvidia]

    RUN --> SUCCESS{Success?}
    SUCCESS -->|Yes| SET_ON[Set ENABLE_GPU_SUPPORT=1<br/>Set NVIDIA_DETECTED=1]
    SUCCESS -->|No| SET_OFF[Set ENABLE_GPU_SUPPORT=0<br/>Set NVIDIA_DETECTED=0]

    SET_ON --> CLEANUP1[Remove test container<br/>jupyterhub_nvidia_autodetect]
    SET_OFF --> CLEANUP2[Remove test container<br/>jupyterhub_nvidia_autodetect]

    CLEANUP1 --> APPLY_ON[Apply device_requests<br/>to spawned containers]
    CLEANUP2 --> APPLY_OFF[No GPU access<br/>for spawned containers]

    ENABLED --> APPLY_ON
    DISABLED --> APPLY_OFF

    style START stroke:#f59e0b,stroke-width:3px
    style DETECT stroke:#a855f7,stroke-width:3px
    style SET_ON stroke:#10b981,stroke-width:2px
    style SET_OFF stroke:#ef4444,stroke-width:2px
    style APPLY_ON stroke:#10b981,stroke-width:3px
    style APPLY_OFF stroke:#6b7280,stroke-width:2px
```

When `ENABLE_GPU_SUPPORT=2` (auto-detect mode), JupyterHub spawns a temporary CUDA container running `nvidia-smi` with `runtime=nvidia`. If the command succeeds, GPU support is enabled and `device_requests` are added to spawned user containers. If it fails, GPU support is disabled. The test container is always removed after detection. Manual override is possible by setting `ENABLE_GPU_SUPPORT=1` (force enable) or `ENABLE_GPU_SUPPORT=0` (force disable).

## User Self-Service Workflow

```mermaid
graph LR
    HOME[Home Page] --> RUNNING{Server State}

    RUNNING -->|Running| RESTART[Restart Server<br/>container.restart]
    RUNNING -->|Stopped| START[Start Server<br/>spawner.start]
    RUNNING -->|Stopped| VOLUMES[Manage Volumes<br/>Select + Delete]

    RESTART --> |Docker API| REFRESH1[Page Refresh]
    VOLUMES --> |Docker API| DELETE[volume.remove]
    DELETE --> REFRESH2[Page Refresh]

    style HOME stroke:#0284c7,stroke-width:3px
    style RESTART stroke:#10b981,stroke-width:2px
    style VOLUMES stroke:#ef4444,stroke-width:2px
    style START stroke:#a855f7,stroke-width:2px
```

Users manage their servers through the home page. Running servers can be restarted via Docker API without recreation. Stopped servers can be started normally or have volumes selectively deleted through a modal interface presenting checkboxes for home, workspace, and cache volumes with optional descriptions from configuration.

## Volume Architecture

```mermaid
graph TB
    subgraph HOST["Docker Host"]
        VOLHOME1["jupyterlab-user1_home<br/>Docker Volume"]
        VOLWORK1["jupyterlab-user1_workspace<br/>Docker Volume"]
        VOLCACHE1["jupyterlab-user1_cache<br/>Docker Volume"]

        VOLHOME2["jupyterlab-user2_home<br/>Docker Volume"]
        VOLWORK2["jupyterlab-user2_workspace<br/>Docker Volume"]
        VOLCACHE2["jupyterlab-user2_cache<br/>Docker Volume"]

        VOLSHARED["jupyterhub_shared<br/>Docker Volume - Shared"]
    end

    subgraph CONTAINER1["User Container: user1"]
        M1HOME["/home"]
        M1WORK["/home/lab/workspace"]
        M1CACHE["/home/lab/.cache"]
        M1SHARED["/mnt/shared"]
    end

    subgraph CONTAINER2["User Container: user2"]
        M2HOME["/home"]
        M2WORK["/home/lab/workspace"]
        M2CACHE["/home/lab/.cache"]
        M2SHARED["/mnt/shared"]
    end

    VOLHOME1 -.->|Mount| M1HOME
    VOLWORK1 -.->|Mount| M1WORK
    VOLCACHE1 -.->|Mount| M1CACHE

    VOLHOME2 -.->|Mount| M2HOME
    VOLWORK2 -.->|Mount| M2WORK
    VOLCACHE2 -.->|Mount| M2CACHE

    VOLSHARED -.->|Mount| M1SHARED
    VOLSHARED -.->|Mount| M2SHARED

    style HOST stroke:#f59e0b,stroke-width:3px
    style CONTAINER1 stroke:#3b82f6,stroke-width:3px
    style CONTAINER2 stroke:#3b82f6,stroke-width:3px
    style VOLSHARED stroke:#10b981,stroke-width:3px
    style M1SHARED stroke:#10b981,stroke-width:2px
    style M2SHARED stroke:#10b981,stroke-width:2px
```

Each user receives four persistent volumes. Three user-specific volumes store home directory files, workspace projects, and cache data. The shared volume provides collaborative storage accessible across all user environments. Volume names follow the pattern `jupyterlab-{username}_<suffix>` for per-user isolation. The shared volume can be configured as CIFS mount for NAS integration.

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

> [!WARNING]
> The JupyterHub container has full access to the Docker daemon. Only trusted administrators should have access to JupyterHub configuration.

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

> [!WARNING]
> Docker socket access grants effective root-level control over the Docker host. Only grant this permission to trusted users.

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
