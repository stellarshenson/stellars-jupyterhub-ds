"""Stellars JupyterHub platform logic package."""

__version__ = "3.8.0"

from .auth import StellarsNativeAuthenticator
from .branding import setup_branding
from .events import register_events
from .gpu import resolve_gpu_mode
from .hooks import make_pre_spawn_hook, schedule_startup_favicon_callback
from .services import get_services_and_roles
from .volumes import get_user_volume_suffixes

__all__ = [
    "StellarsNativeAuthenticator",
    "setup_branding",
    "register_events",
    "resolve_gpu_mode",
    "make_pre_spawn_hook",
    "schedule_startup_favicon_callback",
    "get_services_and_roles",
    "get_user_volume_suffixes",
]
