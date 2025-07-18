# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# Configuration file for JupyterHub
import os
import json
import requests
import nativeauthenticator

c = get_config()  

# standard variables imported from env
JUPYTERHUB_SSL_ENABLED =  int(os.environ.get("JUPYTERHUB_SSL_ENABLED", 1))
GPU_SUPPORT_ENABLED= int(os.environ.get("GPU_SUPPORT_ENABLED", 0))
DOCKER_NOTEBOOK_DIR = "/home/lab/workspace"
JUPYTERHUB_BASE_URL = os.environ.get("JUPYTERHUB_BASE_URL")
JUPYTERHUB_ADMIN = os.environ.get("JUPYTERHUB_ADMIN")
NETWORK_NAME = os.environ["DOCKER_NETWORK_NAME"]

# ensure that we are using SSL, it should be enabled by default
if JUPYTERHUB_SSL_ENABLED == 1:
    c.JupyterHub.ssl_cert = '/mnt/certs/server.crt'
    c.JupyterHub.ssl_key = '/mnt/certs/server.key'

# we use dockerspawner
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"

# default env variables passed to the spawned containers
c.DockerSpawner.environment = {
     'GPU_SUPPORT_ENABLED': 0,
     'GPUSTAT_ENABLED': 0,
     'TF_CPP_MIN_LOG_LEVEL':3, # tensorflow logs ERR only
     'TENSORBOARD_LOGDIR':'/tmp/tensorboard',
     'MLFLOW_TRACKING_URI': 'http://localhost:5000',
     'MLFLOW_PORT':5000,
     'MLFLOW_HOST':'*',
     'ENABLE_SERVICE_MLFLOW':1,
     'ENABLE_SERVICE_GLANCES':1,
     'ENABLE_SERVICE_TENSORBOARD':1,
     'GPU_SUPPORT_ENABLED': GPU_SUPPORT_ENABLED,
     'GPUSTAT_ENABLED': GPU_SUPPORT_ENABLED
}

# configure access to GPU if possible
if GPU_SUPPORT_ENABLED == 1:
    c.DockerSpawner.extra_container_config = {
        'runtime': 'nvidia',
        'device_requests': [
            {
                'Driver': 'nvidia',
                'Count': -1,  # -1 means "all available GPUs"
                'Capabilities': [['gpu']]
            }
        ]
    }

# spawn containers from this image
c.DockerSpawner.image = os.environ["DOCKER_NOTEBOOK_IMAGE"]

# networking congfiguration
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.network_name = NETWORK_NAME

# prevent auto-spawn for admin users
# Redirect admin to admin panel instead
c.JupyterHub.default_url = JUPYTERHUB_BASE_URL + '/hub/home'  

# Force container user
c.DockerSpawner.notebook_dir = DOCKER_NOTEBOOK_DIR

# Set container name prefix
c.DockerSpawner.name_template = "jupyterlab-{username}"

# Mount the real user's Docker volume on the host to the notebook user's
# notebook directory in the container
c.DockerSpawner.volumes = {
    "jupyterlab-{username}_home": "/home",
    "jupyterlab-{username}_workspace": DOCKER_NOTEBOOK_DIR,
    "jupyterlab-{username}_cache": "/home/lab/.cache",
    "jupyterlab_shared": "/mnt/shared"
}

# Ensure containers can accept proxy connections
c.DockerSpawner.args = [
    '--ServerApp.allow_origin=*',
    '--ServerApp.disable_check_xsrf=True'
]

# update internal routing for spawned containers
c.JupyterHub.hub_connect_url = 'http://jupyterhub:8080' + JUPYTERHUB_BASE_URL + '/hub'

# remove containers once they are stopped
c.DockerSpawner.remove = True

# for debugging arguments passed to spawned containers
c.DockerSpawner.debug = False

# user containers will access hub by container name on the Docker network
c.JupyterHub.hub_ip = "jupyterhub"
c.JupyterHub.hub_port = 8080
c.JupyterHub.base_url = JUPYTERHUB_BASE_URL + '/'

# persist hub data on volume mounted inside container
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"

# authenticate users with Native Authenticator
# enable UI for native authenticator
c.JupyterHub.authenticator_class = 'native'
c.JupyterHub.template_paths = [f"{os.path.dirname(nativeauthenticator.__file__)}/templates/"]

# allow anyone to sign-up without approval
# allow all signed-up users to login
c.NativeAuthenticator.open_signup = False
c.NativeAuthenticator.enable_signup = True  
c.Authenticator.allow_all = True

# allowed admins
c.Authenticator.admin_users = [JUPYTERHUB_ADMIN]
c.JupyterHub.admin_access = True

# EOF
