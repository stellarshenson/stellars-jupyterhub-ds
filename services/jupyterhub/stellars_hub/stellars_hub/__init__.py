"""Stellars JupyterHub platform logic package."""

__version__ = "3.8.0"

from .admin_bootstrap import (
    BootstrapAdminAuthenticator,
    BootstrapAdminSignUpHandler,
    compute_bootstrap_window_open,
    make_admin_post_auth_hook,
    provision_admin_userinfo,
    query_admin_state,
)
from .auth import StellarsNativeAuthenticator
from .branding import setup_branding
from .events import register_events
from .gpu import resolve_gpu_mode
from .hooks import make_pre_spawn_hook, schedule_startup_favicon_callback
from .services import get_services_and_roles
from .volumes import get_user_volume_name_templates, get_user_volume_suffixes

__all__ = [
    "BootstrapAdminAuthenticator",
    "BootstrapAdminSignUpHandler",
    "StellarsNativeAuthenticator",
    "compute_bootstrap_window_open",
    "get_services_and_roles",
    "get_user_volume_name_templates",
    "get_user_volume_suffixes",
    "make_admin_post_auth_hook",
    "make_pre_spawn_hook",
    "provision_admin_userinfo",
    "query_admin_state",
    "register_events",
    "resolve_gpu_mode",
    "schedule_startup_favicon_callback",
    "setup_branding",
]
