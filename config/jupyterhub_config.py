# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# Configuration file for JupyterHub
import os
import json
import requests
import nativeauthenticator
from nativeauthenticator import NativeAuthenticator
from nativeauthenticator.handlers import AuthorizationAreaHandler as BaseAuthorizationHandler
from jupyterhub.scopes import needs_scope
import docker # for gpu autodetection


# Custom AuthorizationAreaHandler that passes hub_usernames to template
class CustomAuthorizationAreaHandler(BaseAuthorizationHandler):
    """Override to pass hub_usernames to template for server-side Discard button logic"""

    @needs_scope('admin:users')
    async def get(self):
        from nativeauthenticator.orm import UserInfo
        from jupyterhub import orm

        # Get hub usernames (users with actual JupyterHub accounts)
        hub_usernames = {u.name for u in self.db.query(orm.User).all()}

        html = await self.render_template(
            "authorization-area.html",
            ask_email=self.authenticator.ask_email_on_signup,
            users=self.db.query(UserInfo).all(),
            hub_usernames=hub_usernames,  # NEW: pass to template
        )
        self.finish(html)


# Custom NativeAuthenticator that uses our authorization handler
class StellarsNativeAuthenticator(NativeAuthenticator):
    """Custom authenticator that injects CustomAuthorizationAreaHandler"""

    def get_handlers(self, app):
        # Get default handlers from parent
        handlers = super().get_handlers(app)

        # Replace AuthorizationAreaHandler with our custom one
        new_handlers = []
        for pattern, handler in handlers:
            if handler.__name__ == 'AuthorizationAreaHandler':
                new_handlers.append((pattern, CustomAuthorizationAreaHandler))
            else:
                new_handlers.append((pattern, handler))
        return new_handlers

# Only call get_config() when running as JupyterHub config (not when imported as module)
try:
    c = get_config()
except NameError:
    # Being imported as a module, not loaded by JupyterHub
    c = None

# SQLAlchemy event listener to sync NativeAuthenticator on user rename
# This intercepts ALL User.name changes (admin panel, API, etc.) and syncs UserInfo.username
from sqlalchemy import event
from jupyterhub import orm

@event.listens_for(orm.User.name, 'set')
def sync_nativeauth_on_rename(target, value, oldvalue, initiator):
    """Sync NativeAuthenticator UserInfo when User.name changes"""
    if oldvalue == value or oldvalue is None:
        return  # No change or initial set

    try:
        from nativeauthenticator.orm import UserInfo
        from sqlalchemy.orm import object_session

        session = object_session(target)
        if session:
            user_info = session.query(UserInfo).filter(UserInfo.username == oldvalue).first()
            if user_info:
                user_info.username = value
                # Don't commit here - let the parent transaction handle it
                print(f"[NativeAuth Sync] Queued UserInfo rename: {oldvalue} -> {value}")
    except ImportError:
        pass  # NativeAuthenticator not available
    except Exception as e:
        print(f"[NativeAuth Sync] Error: {e}")


@event.listens_for(orm.User, 'after_insert')
def create_nativeauth_on_user_insert(mapper, connection, target):
    """Auto-create NativeAuthenticator UserInfo when a new User is created via admin panel.
    Generates a memorable password and auto-approves the user."""
    username = target.name
    try:
        import bcrypt
        import random
        from sqlalchemy import text

        # Check if UserInfo already exists (user might have signed up normally)
        result = connection.execute(
            text("SELECT id FROM users_info WHERE username = :username"),
            {"username": username}
        )
        if result.fetchone():
            print(f"[NativeAuth Auto-Create] UserInfo already exists for: {username}")
            return

        # Generate memorable 3-word password
        words = ['apple', 'beach', 'cloud', 'dance', 'eagle', 'flame', 'grape', 'happy',
                 'ivory', 'jolly', 'karma', 'lemon', 'mango', 'noble', 'ocean', 'piano',
                 'quest', 'river', 'storm', 'tiger', 'urban', 'vivid', 'water', 'zebra']
        password = '-'.join(random.sample(words, 3))

        # Hash password with bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Insert into users_info with is_authorized=1 (auto-approved since admin created them)
        connection.execute(
            text("INSERT INTO users_info (username, password, is_authorized) VALUES (:username, :password, 1)"),
            {"username": username, "password": hashed_password}
        )

        # Cache password for admin retrieval
        from custom_handlers import cache_password
        cache_password(username, password)

        print(f"[NativeAuth Auto-Create] User '{username}' created and authorized")

    except Exception as e:
        print(f"[NativeAuth Auto-Create] Error for {username}: {e}")


@event.listens_for(orm.User, 'after_delete')
def remove_nativeauth_on_user_delete(mapper, connection, target):
    """Remove NativeAuthenticator UserInfo when a User is deleted."""
    username = target.name
    try:
        from sqlalchemy import text

        result = connection.execute(
            text("DELETE FROM users_info WHERE username = :username"),
            {"username": username}
        )
        if result.rowcount > 0:
            print(f"[NativeAuth Cleanup] Removed UserInfo for deleted user: {username}")

        # Clear cached password if any
        try:
            from custom_handlers import clear_cached_password
            clear_cached_password(username)
        except ImportError:
            pass

    except Exception as e:
        print(f"[NativeAuth Cleanup] Error removing UserInfo for {username}: {e}")


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
ENABLE_SIGNUP = int(os.environ.get("ENABLE_SIGNUP", 1))  # 0 - disabled (admin creates users), 1 - enabled (self-registration) 
TF_CPP_MIN_LOG_LEVEL = int(os.environ.get("TF_CPP_MIN_LOG_LEVEL", 3)) 
DOCKER_NOTEBOOK_DIR = "/home/lab/workspace"
JUPYTERHUB_BASE_URL = os.environ.get("JUPYTERHUB_BASE_URL")
# Normalize base URL - use empty string for root path to avoid double slashes
if JUPYTERHUB_BASE_URL in ['/', '', None]:
    JUPYTERHUB_BASE_URL_PREFIX = ''
else:
    JUPYTERHUB_BASE_URL_PREFIX = JUPYTERHUB_BASE_URL
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
    c.JupyterHub.default_url = JUPYTERHUB_BASE_URL_PREFIX + '/hub/home'  

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

    # Custom logo - mount/copy logo file to /srv/jupyterhub/logo.svg (or set path via env)
    # JupyterHub serves this at {{ base_url }}logo automatically
    logo_file = os.environ.get('JUPYTERHUB_LOGO_FILE', '/srv/jupyterhub/logo.svg')
    if os.path.exists(logo_file):
        c.JupyterHub.logo_file = logo_file

    # Make volume suffixes, descriptions, and version available to templates
    c.JupyterHub.template_vars = {
        'user_volume_suffixes': USER_VOLUME_SUFFIXES,
        'volume_descriptions': VOLUME_DESCRIPTIONS,
        'stellars_version': os.environ.get('STELLARS_JUPYTERHUB_VERSION', 'dev'),
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
    c.JupyterHub.hub_connect_url = 'http://jupyterhub:8080' + JUPYTERHUB_BASE_URL_PREFIX + '/hub'

    # remove containers once they are stopped
    c.DockerSpawner.remove = True

    # for debugging arguments passed to spawned containers
    c.DockerSpawner.debug = False

    # user containers will access hub by container name on the Docker network
    c.JupyterHub.hub_ip = "jupyterhub"
    c.JupyterHub.hub_port = 8080
    c.JupyterHub.base_url = JUPYTERHUB_BASE_URL_PREFIX + '/' if JUPYTERHUB_BASE_URL_PREFIX else '/'

    # persist hub data on volume mounted inside container
    c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"
    c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"

    # authenticate users with Custom Native Authenticator
    # (subclass that injects hub_usernames into authorization template)
    c.JupyterHub.authenticator_class = StellarsNativeAuthenticator

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
    c.NativeAuthenticator.enable_signup = bool(ENABLE_SIGNUP)  # controlled by ENABLE_SIGNUP env var
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
        BroadcastNotificationHandler,
        GetUserCredentialsHandler
    )

    c.JupyterHub.extra_handlers = [
        (r'/api/users/([^/]+)/manage-volumes', ManageVolumesHandler),
        (r'/api/users/([^/]+)/restart-server', RestartServerHandler),
        (r'/api/notifications/broadcast', BroadcastNotificationHandler),
        (r'/api/admin/credentials', GetUserCredentialsHandler),
        (r'/notifications', NotificationsPageHandler),
    ]

# EOF
