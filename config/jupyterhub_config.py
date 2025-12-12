# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# Configuration file for JupyterHub
import os
import json
import requests
import nativeauthenticator
import docker # for gpu autodetection

# Only call get_config() when running as JupyterHub config (not when imported as module)
try:
    c = get_config()
except NameError:
    # Being imported as a module, not loaded by JupyterHub
    c = None  

# NVIDIA GPU auto-detection 
def detect_nvidia(nvidia_autodetect_image='nvidia/cuda:12.9.1-base-ubuntu24.04'):
    """ function to run docker image with nvidia driver, and execute `nvidia-smi` utility
    to verify if nvidia GPU is present and in functional state """
    client = docker.DockerClient('unix://var/run/docker.sock')
    # spin up a container to test if nvidia works
    result = 0
    container = None
    try:
        client.containers.run(
            image=nvidia_autodetect_image,
            command='nvidia-smi',
            runtime='nvidia',
            name='jupyterhub_nvidia_autodetect',
            stderr=True,
            stdout=True,
        )
        result = 1
    except:
        result = 0
    # cleanup that container
    try:
        container = client.containers.get('jupyterhub_nvidia_autodetect').remove(force=True)
    except:
        pass
    return result


# standard variables imported from env
ENABLE_JUPYTERHUB_SSL =  int(os.environ.get("ENABLE_JUPYTERHUB_SSL", 1))
ENABLE_GPU_SUPPORT = int(os.environ.get("ENABLE_GPU_SUPPORT", 2)) 
ENABLE_SERVICE_MLFLOW = int(os.environ.get("ENABLE_SERVICE_MLFLOW", 1)) 
ENABLE_SERVICE_GLANCES = int(os.environ.get("ENABLE_SERVICE_GLANCES", 1)) 
ENABLE_SERVICE_TENSORBOARD = int(os.environ.get("ENABLE_SERVICE_TENSORBOARD", 1)) 
TF_CPP_MIN_LOG_LEVEL = int(os.environ.get("TF_CPP_MIN_LOG_LEVEL", 3)) 
DOCKER_NOTEBOOK_DIR = "/home/lab/workspace"
JUPYTERHUB_BASE_URL = os.environ.get("JUPYTERHUB_BASE_URL")
JUPYTERHUB_ADMIN = os.environ.get("JUPYTERHUB_ADMIN")
NETWORK_NAME = os.environ["DOCKER_NETWORK_NAME"]
NVIDIA_AUTODETECT_IMAGE = os.environ.get("NVIDIA_AUTODETECT_IMAGE", 'nvidia/cuda:12.9.1-base-ubuntu24.04') 

# perform autodetection when ENABLE_GPU_SUPPORT is set to autodetect
# gpu support: 0 - disabled, 1 - enabled, 2 - autodetect
if ENABLE_GPU_SUPPORT == 2:
    NVIDIA_DETECTED = detect_nvidia(NVIDIA_AUTODETECT_IMAGE)
    if NVIDIA_DETECTED: ENABLE_GPU_SUPPORT = 1 # means - gpu enabled
    else: ENABLE_GPU_SUPPORT = 0 # means - disable 

# Apply JupyterHub configuration (only when loaded by JupyterHub, not when imported)
if c is not None:
    # ensure that we are using SSL, it should be enabled by default
    if ENABLE_JUPYTERHUB_SSL == 1:
        c.JupyterHub.ssl_cert = '/mnt/certs/server.crt'
        c.JupyterHub.ssl_key = '/mnt/certs/server.key'

    # we use dockerspawner
    c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"

    # default env variables passed to the spawned containers
    c.DockerSpawner.environment = {
         'TF_CPP_MIN_LOG_LEVEL':TF_CPP_MIN_LOG_LEVEL, # tensorflow logging level: 3 - err only
         'TENSORBOARD_LOGDIR':'/tmp/tensorboard',
         'MLFLOW_TRACKING_URI': 'http://localhost:5000',
         'MLFLOW_PORT':5000,
         'MLFLOW_HOST':'0.0.0.0',  # new 3.5 mlflow launched with guinicorn requires this
         'MLFLOW_WORKERS':1,
         'ENABLE_SERVICE_MLFLOW': ENABLE_SERVICE_MLFLOW,
         'ENABLE_SERVICE_GLANCES': ENABLE_SERVICE_GLANCES,
         'ENABLE_SERVICE_TENSORBOARD': ENABLE_SERVICE_TENSORBOARD,
         'ENABLE_GPU_SUPPORT': ENABLE_GPU_SUPPORT,
         'ENABLE_GPUSTAT': ENABLE_GPU_SUPPORT,
         'NVIDIA_DETECTED': NVIDIA_DETECTED,
    }

    # configure access to GPU if possible
    if ENABLE_GPU_SUPPORT == 1:
        c.DockerSpawner.extra_host_config = {
            'device_requests': [
                {
                    'Driver': 'nvidia',
                    'Count': -1,
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

# User mounts in the spawned container (defined as constant for import by handlers)
DOCKER_SPAWNER_VOLUMES = {
    "jupyterlab-{username}_home": "/home",
    "jupyterlab-{username}_workspace": DOCKER_NOTEBOOK_DIR,
    "jupyterlab-{username}_cache": "/home/lab/.cache",
    "jupyterhub_shared": "/mnt/shared" # shared drive across hub
}

# Optional descriptions for user volumes (shown in UI)
# If a volume suffix is not listed here, no description will be shown
VOLUME_DESCRIPTIONS = {
    'home': 'User home directory files, configurations',
    'workspace': 'Project files, notebooks, code',
    'cache': 'Temporary files, pip cache, conda cache'
}

# Helper function to extract user-specific volume suffixes
def get_user_volume_suffixes(volumes_dict):
    """Extract volume suffixes from volumes dict that follow jupyterlab-{username}_<suffix> pattern"""
    suffixes = []
    for volume_name in volumes_dict.keys():
        # Match pattern: jupyterlab-{username}_<suffix>
        if volume_name.startswith("jupyterlab-{username}_"):
            suffix = volume_name.replace("jupyterlab-{username}_", "")
            suffixes.append(suffix)
    return suffixes

# Store user volume suffixes for use in templates and handlers (importable by custom_handlers.py)
USER_VOLUME_SUFFIXES = get_user_volume_suffixes(DOCKER_SPAWNER_VOLUMES)

# Apply configuration only when running as JupyterHub config
if c is not None:
    # Force container user
    c.DockerSpawner.notebook_dir = DOCKER_NOTEBOOK_DIR

    # Set container name prefix
    c.DockerSpawner.name_template = "jupyterlab-{username}"

    # Set volumes from constant
    c.DockerSpawner.volumes = DOCKER_SPAWNER_VOLUMES

    # Make volume suffixes and descriptions available to templates
    c.JupyterHub.template_vars = {
        'user_volume_suffixes': USER_VOLUME_SUFFIXES,
        'volume_descriptions': VOLUME_DESCRIPTIONS
    }

# Built-in groups that cannot be deleted (auto-recreated if missing)
# docker-sock: grants /var/run/docker.sock access (container orchestration)
# docker-privileged: runs container with --privileged flag (full host access)
BUILTIN_GROUPS = ['docker-sock', 'docker-privileged']

# Pre-spawn hook to conditionally grant docker access based on group membership
async def pre_spawn_hook(spawner):
    """Grant docker access to users based on group membership"""
    from jupyterhub.orm import Group

    # Ensure built-in groups exist (protection against deletion)
    for group_name in BUILTIN_GROUPS:
        existing_group = spawner.db.query(Group).filter(Group.name == group_name).first()
        if not existing_group:
            spawner.log.warning(f"Built-in group '{group_name}' was missing - recreating")
            new_group = Group(name=group_name)
            spawner.db.add(new_group)
            spawner.db.commit()

    username = spawner.user.name
    user_groups = [g.name for g in spawner.user.groups]

    # docker-sock: mount docker.sock for container orchestration
    if 'docker-sock' in user_groups:
        spawner.log.info(f"Granting docker.sock access to user: {username}")
        spawner.volumes['/var/run/docker.sock'] = '/var/run/docker.sock'
    else:
        spawner.volumes.pop('/var/run/docker.sock', None)

    # docker-privileged: run container with --privileged flag
    if 'docker-privileged' in user_groups:
        spawner.log.info(f"Granting privileged container mode to user: {username}")
        spawner.extra_host_config['privileged'] = True
    else:
        spawner.extra_host_config.pop('privileged', None)

# Apply remaining configuration (only when loaded by JupyterHub, not when imported)
if c is not None:
    c.DockerSpawner.pre_spawn_hook = pre_spawn_hook

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

    # Template paths - must include default JupyterHub templates
    import jupyterhub
    c.JupyterHub.template_paths = [
        "/srv/jupyterhub/templates/",  # Custom templates (highest priority)
        f"{os.path.dirname(nativeauthenticator.__file__)}/templates/",  # NativeAuthenticator templates
        f"{os.path.dirname(jupyterhub.__file__)}/templates"  # Default JupyterHub templates
    ]

    # allow anyone to sign-up without approval
    # allow all signed-up users to login
    c.NativeAuthenticator.open_signup = False
    c.NativeAuthenticator.enable_signup = True
    c.Authenticator.allow_all = True

    # allowed admins
    c.Authenticator.admin_users = [JUPYTERHUB_ADMIN]
    c.JupyterHub.admin_access = True

    # Custom API handlers for volume management and server control
    import sys
    sys.path.insert(0, '/srv/jupyterhub')
    sys.path.insert(0, '/start-platform.d')
    sys.path.insert(0, '/')

    from custom_handlers import (
        ManageVolumesHandler,
        RestartServerHandler,
        NotificationsPageHandler,
        BroadcastNotificationHandler
    )

    c.JupyterHub.extra_handlers = [
        (r'/api/users/([^/]+)/manage-volumes', ManageVolumesHandler),
        (r'/api/users/([^/]+)/restart-server', RestartServerHandler),
        (r'/api/notifications/broadcast', BroadcastNotificationHandler),
        (r'/notifications', NotificationsPageHandler),
    ]

# EOF
