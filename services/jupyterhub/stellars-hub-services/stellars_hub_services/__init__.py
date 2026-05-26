"""Stellars JupyterHub platform logic package."""

__version__ = "3.8.0"

from .auth import StellarsNativeAuthenticator
from .branding import setup_branding
from .docker_proxy import detect_self_image, ensure_user_proxy, stop_user_proxy
from .events import register_events
from .gpu import is_wsl2, resolve_gpu_mode
from .hooks import make_pre_spawn_hook, schedule_startup_favicon_callback
from .idle_culler import (
    calc_available_hours,
    calc_ceiling,
    calc_effective_timeout,
    calc_new_extensions,
    calc_time_remaining,
    run_cull_pass,
    schedule_idle_culler,
    should_cull,
)
from .services import get_services_and_roles
from .volume_cache import configure_volume_cache
from .volumes import (
    get_user_volume_name_templates,
    get_user_volume_suffixes,
    load_merged_user_volumes,
)

__all__ = [
    "StellarsNativeAuthenticator",
    "calc_available_hours",
    "calc_ceiling",
    "calc_effective_timeout",
    "calc_new_extensions",
    "calc_time_remaining",
    "configure_volume_cache",
    "detect_self_image",
    "ensure_user_proxy",
    "stop_user_proxy",
    "get_services_and_roles",
    "run_cull_pass",
    "schedule_idle_culler",
    "should_cull",
    "get_user_volume_name_templates",
    "get_user_volume_suffixes",
    "is_wsl2",
    "load_merged_user_volumes",
    "make_pre_spawn_hook",
    "register_events",
    "resolve_gpu_mode",
    "schedule_startup_favicon_callback",
    "setup_branding",
]
