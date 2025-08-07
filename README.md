# Stellars JupyterHub for Data Science Platform
![Docker Image](https://img.shields.io/docker/image-size/stellars/stellars-jupyterhub-ds/latest?style=flat-square)

**Multi-user JupyterHub 4 with Miniforge, Data Science stack, and NativeAuthenticator.**

This platform is built to support multiple data scientists on a shared environment with isolated sessions. Powered by JupyterHub, it ensures secure, user-specific access via the `NativeAuthenticator` plugin. It includes a full data science stack with GPU support (optional), and integrates seamlessly into modern Docker-based workflows.

By default system is capable of **automatically detecting** NVIDIA CUDA-supported GPU

This deployment provides access to a centralized JupyterHub instance for managing user sessions. Optional integrations such as TensorBoard, MLFlow, or Optuna can be added manually via service extensions.

## References

This project spawns user environments using docker image: `stellars/stellars-jupyterlab-ds`  

Visit the project page for stellars-jupyterlab-ds: https://github.com/stellarshenson/stellars-jupyterlab-ds

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

<!-- EOF -->
