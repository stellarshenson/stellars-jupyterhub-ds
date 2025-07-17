# Stellars JupyterHub for Data Science Platform

**Multi-user JupyterHub 4 with Miniforge, Data Science stack, and NativeAuthenticator.**

This platform is built to support multiple data scientists on a shared environment with isolated sessions. Powered by JupyterHub, it ensures secure, user-specific access via the `NativeAuthenticator` plugin. It includes a full data science stack with GPU support (optional), and integrates seamlessly into modern Docker-based workflows.

This deployment provides access to a centralized JupyterHub instance for managing user sessions. Optional integrations such as TensorBoard, MLFlow, or Optuna can be added manually via service extensions.

## References

This project spawns user environments using docker image: `stellars/stellars-jupyterlab-ds`  

Visit the project page for stellars-jupyterlab-ds: https://github.com/stellarshenson/stellars-jupyterlab-ds

## Quickstart

### Docker Compose
1. Download `compose.yml` and `config/jupyterhub_config.py` config file
2. Run: `docker compose up --no-build`
3. Open `https://localhost/jupyterhub` in your browser 
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



