# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# Configuration file for JupyterHub
import os
import json
import requests
import nativeauthenticator

c = get_config()  

# We rely on environment variables to configure JupyterHub so that we
# avoid having to rebuild the JupyterHub container every time we change a
# configuration parameter.

# Spawn single-user servers as Docker containers
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"

# Environment variables for MLflow integration
c.DockerSpawner.environment = {
    'JUPYTERLAB_STARTUP_MODE': 'jupyterhub'
}

# Spawn containers from this image
c.DockerSpawner.image = os.environ["DOCKER_NOTEBOOK_IMAGE"]

# Connect containers to this Docker network
NETWORK_NAME = os.environ["DOCKER_NETWORK_NAME"]


c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.network_name = NETWORK_NAME

# Explicitly set notebook directory because we'll be mounting a volume to it.
# Most `jupyter/docker-stacks` *-notebook images run the Notebook server as
DOCKER_NOTEBOOK_DIR = "/home/lab/workspace"
DOCKER_HOME_DIR = "/home/lab"
JUPYTERHUB_BASE_URL = os.environ.get("JUPYTERHUB_BASE_URL")
JUPYTERHUB_ADMIN = os.environ.get("JUPYTERHUB_ADMIN")

# Prevent auto-spawn for admin users
c.JupyterHub.default_url = JUPYTERHUB_BASE_URL + '/hub/home'  # Redirect admin to admin panel instead

# Modify volume mounting
c.DockerSpawner.volumes = {}

# Force container user
c.DockerSpawner.container_user = "lab"
c.DockerSpawner.notebook_dir = DOCKER_NOTEBOOK_DIR

# Set container name prefix
c.DockerSpawner.name_template = "jupyterlab-{username}"

# Mount the real user's Docker volume on the host to the notebook user's
# notebook directory in the container
c.DockerSpawner.volumes = {
    "jupyterlab-{username}_home": DOCKER_HOME_DIR,
    "jupyterlab-{username}_workspace": DOCKER_NOTEBOOK_DIR,
    "jupyterlab-{username}_cache": "/mnt/cache",
    "jupyterlab-{username}_mlflow": "/mnt/mlflow",
    "jupyterlab-shared": "/mnt/shared"
}

# Ensure containers can accept proxy connections
c.DockerSpawner.args = [
    '--ServerApp.allow_origin=*',
    '--ServerApp.disable_check_xsrf=True'
]

# fix for the iframes loading local pages
c.JupyterHub.tornado_settings = {
    'headers': {
        'Content-Security-Policy': "frame-ancestors 'self'; default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:;"
    }
}

# Update internal routing for spawned containers
c.JupyterHub.hub_connect_url = 'http://jupyterhub:8080' + JUPYTERHUB_BASE_URL + '/hub'

# Remove containers once they are stopped
c.DockerSpawner.remove = True

# For debugging arguments passed to spawned containers
c.DockerSpawner.debug = False

# User containers will access hub by container name on the Docker network
c.JupyterHub.hub_ip = "jupyterhub"
c.JupyterHub.hub_port = 8080
c.JupyterHub.base_url = JUPYTERHUB_BASE_URL + '/'

# Persist hub data on volume mounted inside container
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"

# Authenticate users with Native Authenticator
c.JupyterHub.authenticator_class = 'native'
# enable UI for native authenticator
c.JupyterHub.template_paths = [f"{os.path.dirname(nativeauthenticator.__file__)}/templates/"]

# Allow anyone to sign-up without approval
# Allow all signed-up users to login
c.NativeAuthenticator.open_signup = False
c.NativeAuthenticator.enable_signup = True  
c.NativeAuthenticator.enable_admin_access = True
c.Authenticator.allow_all = True

# Allowed admins
c.Authenticator.admin_users = [JUPYTERHUB_ADMIN]
c.JupyterHub.admin_access = True

# EOF
